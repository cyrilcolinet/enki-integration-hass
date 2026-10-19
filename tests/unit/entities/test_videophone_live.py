"""Live view of a video doorbell, over the two SDP routes (#259)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from enki.api.transport import EnkiHttpClient
from enki.api.videophone_signaling import VideophoneLiveSession
from enki.camera import EnkiVideophoneCamera, async_setup_entry
from enki.domain.models import EnkiDevice
from enki.domain.videophone import offer_candidates, parse_sdp_answer, unescape_sdp
from enki.exceptions import EnkiConnectionError
from homeassistant.components.camera import (
    CameraEntityFeature,
    WebRTCAnswer,
    WebRTCCandidate,
    WebRTCError,
)
from webrtc_models import RTCIceCandidateInit

# A browser offer: two m-sections, the candidate the frontend had gathered by
# the time it sent it, and the role an offer always proposes.
OFFER = "\r\n".join(
    [
        "v=0",
        "o=- 1 2 IN IP4 127.0.0.1",
        "s=-",
        "t=0 0",
        "m=audio 9 UDP/TLS/RTP/SAVPF 111",
        "a=mid:0",
        "a=setup:actpass",
        "a=candidate:1 1 udp 2122260223 192.168.1.20 51234 typ host",
        "m=video 9 UDP/TLS/RTP/SAVPF 96",
        "a=mid:1",
        "a=setup:actpass",
        "",
    ]
)
# What the doorbell deposits back: the same SDP shape, committed to a role, and
# with its newlines written out rather than sent.
ANSWER_LINES = [
    "v=0",
    "o=- 3 4 IN IP4 10.0.0.5",
    "s=-",
    "t=0 0",
    "m=audio 9 UDP/TLS/RTP/SAVPF 111",
    "a=mid:0",
    "a=setup:active",
    "m=video 9 UDP/TLS/RTP/SAVPF 96",
    "a=mid:1",
    "a=setup:active",
]
ANSWER_AS_SENT = "\\r\\n".join(ANSWER_LINES)
ANSWER_CANDIDATES = [
    {"candidate": "candidate:2 1 udp 2122260223 10.0.0.5 40000 typ host", "sdpMid": "0",
     "sdpMLineIndex": 0},
    {"candidate": "candidate:3 1 udp 41885439 51.15.1.1 50000 typ relay", "sdpMid": "1",
     "sdpMLineIndex": 1},
]  # fmt: skip


@pytest.fixture(autouse=True)
def _fast(monkeypatch: pytest.MonkeyPatch) -> None:
    """The real waits are seconds long; the sequence is what is under test."""
    monkeypatch.setattr("enki.api.videophone_signaling._GATHER_SECONDS", 0.05)
    monkeypatch.setattr("enki.api.videophone_signaling._ANSWER_SECONDS", 0.2)
    monkeypatch.setattr("enki.api.videophone_signaling._POLL_SECONDS", 0.01)


def _doorbell() -> EnkiDevice:
    return EnkiDevice(
        home_id="home",
        device_id="dev",
        node_id="node-bell",
        device_name="Visiophone",
        device_type="videophones",
        is_enabled=True,
        state="ACTIVE",
        capabilities=["check_videophone_state", "check_videophone_events"],
    )


def _transport(reads: list[dict]) -> MagicMock:
    http = MagicMock(spec_set=EnkiHttpClient)
    http.change_videophone_sdp_info = AsyncMock(return_value=None)
    http.get_videophone_sdp_info = AsyncMock(side_effect=reads)
    return http


def _camera(reads: list[dict]) -> tuple[EnkiVideophoneCamera, MagicMock]:
    http = _transport(reads)
    coordinator = MagicMock()
    coordinator.last_update_success = True

    async def start(home_id, node_id, session):
        return await session.negotiate(http, home_id, node_id)

    coordinator.api.async_start_videophone_live = AsyncMock(side_effect=start)
    return EnkiVideophoneCamera(coordinator, _doorbell()), http


@pytest.mark.asyncio
async def test_a_doorbell_streams_and_keeps_its_snapshot_entity() -> None:
    coordinator = MagicMock()
    coordinator.data = [_doorbell()]
    added: list = []
    await async_setup_entry(MagicMock(), MagicMock(runtime_data=coordinator), added.extend)

    (camera,) = added
    assert type(camera) is EnkiVideophoneCamera
    assert camera._attr_supported_features == CameraEntityFeature.STREAM
    # Same unique id as before: the existing entity gains the live view in place.
    assert camera._attr_unique_id.endswith("-event-snapshot")


def test_the_candidates_the_offer_already_carries_are_read_back() -> None:
    """The frontend appends what it has gathered to the offer it sends."""
    assert offer_candidates(OFFER) == [
        {
            "candidate": "candidate:1 1 udp 2122260223 192.168.1.20 51234 typ host",
            "sdpMid": "0",
            "sdpMLineIndex": 0,
        }
    ]


def test_an_escaped_answer_becomes_an_sdp_again() -> None:
    """One line of escapes is what the doorbell sends; no peer would take it."""
    assert unescape_sdp(ANSWER_AS_SENT).splitlines() == ANSWER_LINES
    assert unescape_sdp("v=0\r\na=mid:0") == "v=0\r\na=mid:0", "a real SDP is left alone"


def test_reading_our_own_offer_back_is_not_an_answer() -> None:
    """One mailbox per node: the first poll can return what was just posted."""
    assert parse_sdp_answer({"sdp": OFFER, "candidates": []}, offered=OFFER) is None
    # Same offer, re-encoded by the service: still ours, still not an answer.
    assert parse_sdp_answer({"sdp": OFFER.replace("\r\n", "\\r\\n")}, offered=OFFER) is None
    assert parse_sdp_answer({}, offered=OFFER) is None
    # Re-escaped and with no role line to tell on it, it is still what we posted.
    roleless = OFFER.replace("a=setup:actpass\r\n", "")
    assert parse_sdp_answer({"sdp": roleless.replace("\r\n", "\\r\\n")}, offered=roleless) is None


def test_an_answer_from_another_peer_is_taken_on_its_role_alone() -> None:
    """A doorbell that reworded the SDP still commits to a role; an offer does not."""
    answer, candidates = parse_sdp_answer(
        {"sdp": ANSWER_AS_SENT, "candidates": ANSWER_CANDIDATES}, offered=OFFER
    )

    assert "a=setup:active" in answer
    assert candidates == ANSWER_CANDIDATES


@pytest.mark.asyncio
async def test_the_offer_waits_for_the_candidates_the_browser_trickles() -> None:
    """They go in the same body, so one posted too early never reaches the doorbell."""
    camera, http = _camera([{"sdp": ANSWER_AS_SENT, "candidates": ANSWER_CANDIDATES}])
    sent: list = []

    offer = asyncio.create_task(camera.async_handle_async_webrtc_offer(OFFER, "s1", sent.append))
    await asyncio.sleep(0)
    await camera.async_on_webrtc_candidate(
        "s1",
        RTCIceCandidateInit(
            candidate="candidate:9 1 udp 41885439 51.15.9.9 60000 typ relay",
            sdp_mid="1",
            sdp_m_line_index=1,
        ),
    )
    await offer

    _, _, posted = http.change_videophone_sdp_info.call_args.args
    assert posted["sdp"] == OFFER
    assert [c["candidate"].split(" ")[-1] for c in posted["candidates"]] == ["host", "relay"]


@pytest.mark.asyncio
async def test_the_answer_and_its_candidates_reach_the_browser() -> None:
    # Empty first: the doorbell has nothing to say yet, and 204 reads as {}.
    camera, _ = _camera([{}, {"sdp": ANSWER_AS_SENT, "candidates": ANSWER_CANDIDATES}])
    sent: list = []

    await camera.async_handle_async_webrtc_offer(OFFER, "s1", sent.append)

    answer, *candidates = sent
    assert isinstance(answer, WebRTCAnswer)
    assert answer.answer.splitlines() == ANSWER_LINES
    assert [c.candidate.candidate for c in candidates] == [
        c["candidate"] for c in ANSWER_CANDIDATES
    ]
    assert all(isinstance(c, WebRTCCandidate) for c in candidates)


@pytest.mark.asyncio
async def test_a_doorbell_that_never_answers_reports_one_error() -> None:
    camera, _ = _camera([{}] * 100)
    sent: list = []

    await camera.async_handle_async_webrtc_offer(OFFER, "s1", sent.append)

    (error,) = sent
    assert isinstance(error, WebRTCError)
    assert "did not answer" in error.message
    assert camera._sessions == {}, "a failed session must not be left behind"


@pytest.mark.asyncio
async def test_closing_the_stream_stops_the_negotiation() -> None:
    """Nothing to hang up with: the doorbell is left alone and the poll stops."""
    camera, http = _camera([{}] * 100)
    sent: list = []

    offer = asyncio.create_task(camera.async_handle_async_webrtc_offer(OFFER, "s1", sent.append))
    await asyncio.sleep(0.05)
    camera.close_webrtc_session("s1")
    await offer

    assert isinstance(sent[0], WebRTCError)
    assert camera._sessions == {}


@pytest.mark.asyncio
async def test_a_session_closed_before_it_posted_posts_nothing() -> None:
    session = VideophoneLiveSession(OFFER)
    http = _transport([])
    session.close()

    with pytest.raises(EnkiConnectionError):
        await session.negotiate(http, "home", "node-bell")

    http.change_videophone_sdp_info.assert_not_awaited()


@pytest.mark.asyncio
async def test_the_data_channel_the_doorbell_drops_comes_back_rejected() -> None:
    """The app opens none, so the firmware answers none, and a browser refuses that."""
    offer_with_data = OFFER + "\r\n".join(
        ["m=application 9 UDP/DTLS/SCTP webrtc-datachannel", "a=mid:2", "a=setup:actpass", ""]
    )
    camera, _ = _camera([{"sdp": ANSWER_AS_SENT, "candidates": []}])
    sent: list = []

    await camera.async_handle_async_webrtc_offer(offer_with_data, "s1", sent.append)

    (answer,) = sent
    lines = answer.answer.splitlines()
    assert [line for line in lines if line.startswith("m=")] == [
        "m=audio 9 UDP/TLS/RTP/SAVPF 111",
        "m=video 9 UDP/TLS/RTP/SAVPF 96",
        "m=application 0 UDP/DTLS/SCTP webrtc-datachannel",
    ]
    assert "a=mid:2" in lines
