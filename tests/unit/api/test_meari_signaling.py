"""Meari live-view signaling against a fake signaling server.

The fake replays what the reporter's solar camera did (#216): accept the option,
answer the offer, send candidates — or fail the way a sleeping camera does.
"""

from __future__ import annotations

import asyncio
import json

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer
from enki.api.meari_signaling import (
    MeariCandidate,
    MeariSignalingError,
    MeariSignalingSession,
    reject_unanswered,
)

CAMERA_ANSWER = "v=0\r\nm=audio 9 UDP/TLS/RTP/SAVPF 0\r\nm=video 9 UDP/TLS/RTP/SAVPF 96\r\n"
CAMERA_CANDIDATE = {
    "candidate": "candidate:1 1 udp 1 10.0.0.2 5000 typ host",
    "sdpMid": "0",
    "sdpMLineIndex": 0,
}


def _connect_info(url: str) -> dict:
    return {
        "wssUrl": url,
        "accessId": "a",
        "signature": "s",
        "token": "t",
        "expires": "1",
        "callee": "cam",
        "deviceCode": "dev",
    }


class _FakeMeari:
    """Signaling server; ``mode`` picks the scenario."""

    def __init__(self, mode: str = "answer") -> None:
        self.mode = mode
        self.frames: list[dict] = []
        self.closed = asyncio.Event()

    async def handler(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        async for message in ws:
            frame = json.loads(message.data)
            self.frames.append(frame)
            method = frame.get("method")
            if method == "option":
                if self.mode == "asleep":
                    await ws.send_json(
                        {
                            "sid": frame["sid"],
                            "errid": 400,
                            "errstr": "device dormancy",
                            "desc": "device dormancy",
                        }
                    )
                    continue
                await ws.send_json(
                    {
                        "sid": frame["sid"],
                        "method": "option",
                        "action": "resp",
                        "cmd": "mts",
                        "params": {
                            "coturn_host": "h",
                            "coturn_ip": "1.2.3.4",
                            "coturn_port": 3478,
                            "username": "u",
                            "pwd": "p",
                        },
                    }
                )
            elif method == "offer":
                await ws.send_json(
                    {
                        "sid": frame["sid"],
                        "method": "answer",
                        "action": "resp",
                        "cmd": "mts",
                        "params": {"sdp": CAMERA_ANSWER},
                    }
                )
                await ws.send_json(
                    {
                        "sid": frame["sid"],
                        "method": "candidate",
                        "action": "req",
                        "cmd": "mts",
                        "params": {"candidate": CAMERA_CANDIDATE},
                    }
                )
                if self.mode == "late_error":
                    await ws.send_json(
                        {
                            "sid": frame["sid"],
                            "errid": 488,
                            "errstr": "Connection Failed-conn timeout",
                        }
                    )
        self.closed.set()
        return ws


async def _run(fake: _FakeMeari, *, early_candidate: bool = False):
    app = web.Application()
    app.router.add_get("/ws", fake.handler)
    server = TestServer(app)
    await server.start_server()
    answers, candidates, errors = [], [], []
    session = MeariSignalingSession(
        on_answer=answers.append, on_candidate=candidates.append, on_error=errors.append
    )
    async with aiohttp.ClientSession() as http:
        if early_candidate:
            # Trickled by the browser before the offer is even sent.
            await session.add_candidate(
                MeariCandidate("candidate:9 1 udp 1 192.168.1.5 6000 typ host", "0", 0)
            )
        await session.start(http, _connect_info(str(server.make_url("/ws"))), "BROWSER-OFFER")
        await asyncio.sleep(0.1)
        await session.add_candidate(MeariCandidate("", None, None))  # end-of-candidates
        await session.close()
    await server.close()
    return answers, candidates, errors


@pytest.mark.asyncio
async def test_full_negotiation_relays_offer_answer_and_candidates() -> None:
    fake = _FakeMeari()
    answers, candidates, errors = await _run(fake, early_candidate=True)

    assert answers == [CAMERA_ANSWER]
    assert candidates == [MeariCandidate(CAMERA_CANDIDATE["candidate"], "0", 0)]
    assert errors == []

    methods = [frame["method"] for frame in fake.frames]
    # Early candidate held back until the offer is out; preview after the answer;
    # stop-preview on close. The end-of-candidates marker is never sent.
    assert methods == ["option", "offer", "candidate", "settings", "settings"]
    option, offer = fake.frames[0], fake.frames[1]
    assert option["auth"] == {"accessId": "a", "signature": "s", "token": "t"}
    assert option["params"]["devicecode"] == "dev"
    assert offer["params"]["sdp"] == "BROWSER-OFFER"
    start, stop = fake.frames[3], fake.frames[4]
    assert start["params"]["settings"]["streams"] == [{"channel": 0, "stream": 1, "stop": 0}]
    assert stop["params"]["settings"]["streams"] == [{"channel": 0, "stream": 1, "stop": 1}]


@pytest.mark.asyncio
async def test_sleeping_camera_fails_once_and_sends_no_offer() -> None:
    fake = _FakeMeari("asleep")
    answers, _, errors = await _run(fake)

    assert answers == []
    (error,) = errors  # exactly one error, not a second one after a timeout
    assert isinstance(error, MeariSignalingError)
    assert error.camera_asleep is True
    assert [frame["method"] for frame in fake.frames] == ["option"]


@pytest.mark.asyncio
async def test_error_after_the_answer_is_not_fatal() -> None:
    answers, _, errors = await _run(_FakeMeari("late_error"))
    assert answers == [CAMERA_ANSWER]
    assert errors == []


@pytest.mark.asyncio
async def test_missing_signaling_address_is_refused() -> None:
    session = MeariSignalingSession(on_answer=print, on_candidate=print, on_error=print)
    async with aiohttp.ClientSession() as http:
        with pytest.raises(MeariSignalingError):
            await session.start(http, {}, "OFFER")


def test_answer_gets_the_dropped_data_channel_back_as_rejected() -> None:
    # Home Assistant's frontend offers a data channel; the camera drops it.
    offer = (
        "v=0\r\nm=audio 9 UDP/TLS/RTP/SAVPF 0\r\na=mid:0\r\n"
        "m=video 9 UDP/TLS/RTP/SAVPF 96\r\na=mid:1\r\n"
        "m=application 9 UDP/DTLS/SCTP webrtc-datachannel\r\na=mid:2\r\na=sctp-port:5000\r\n"
    )
    assert reject_unanswered(offer, CAMERA_ANSWER) == (
        CAMERA_ANSWER
        + "m=application 0 UDP/DTLS/SCTP webrtc-datachannel\r\nc=IN IP4 0.0.0.0\r\na=mid:2\r\n"
    )
    assert reject_unanswered("v=0\r\nm=audio 9 X 0\r\n", CAMERA_ANSWER) == CAMERA_ANSWER
