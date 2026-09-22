"""Live view of a meari-generation Lexman camera: its WebRTC signaling.

The app reaches the camera through a signaling WebSocket whose address and
credentials come from ``check-camera-connect-wss``. Every frame shares one
envelope — ``{"sid", "method", "action": "req", "cmd": "mts", "params"}`` — and
the exchange is plain WebRTC:

1. ``option`` — authenticate; the reply carries the camera's TURN relay;
2. ``offer`` — our SDP; the camera replies ``answer``;
3. ``candidate`` — ICE candidates, both ways;
4. ``settings`` / ``preview`` — start the stream once the camera reports the
   connection up (``errid`` 0, "Connect Success"), like the app.

Errors arrive as ``{"errid", "errstr"}``; a sleeping camera says so in ``errstr``.

Confirmed on a real solar camera up to the answer and its candidates (#216), with
a synthetic offer — so without media yet. The media itself never goes through
here: Home Assistant's frontend is the WebRTC peer, this only relays signaling.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import aiohttp

from ..const import LOGGER

# What the app treats as "the camera is asleep or unreachable", not as a bug.
DORMANT_ERRORS = frozenset(
    {"device dormancy", "device awaken timeout", "device offline", "session not found"}
)

_AUTH_TIMEOUT_SECONDS = 15.0

# What the camera answered with, on an offer it accepted (#216).
_CAMERA_CODECS = {"audio": {"opus", "pcmu", "pcma"}, "video": {"h264"}}
_PER_FORMAT = ("a=rtpmap:", "a=fmtp:", "a=rtcp-fb:")


def _media_lines(sdp: str) -> list[str]:
    """The m= lines of an SDP: enough to debug a refusal, no credentials."""
    return [line for line in sdp.splitlines() if line.startswith("m=")]


def slim_offer(sdp: str) -> str:
    """Cut a browser offer down to the codecs the camera speaks.

    The camera answers a short offer, but refuses the browser's full one (488,
    "remote sdp error"): VP8/VP9/AV1, RTX, RED and header extensions go.
    """
    header, *sections = re.split(r"\r?\n(?=m=)", sdp.strip())
    header = "\r\n".join(x for x in header.splitlines() if not x.startswith("a=extmap"))
    return "\r\n".join([header, *map(_slim_section, sections)]) + "\r\n"


def _slim_section(section: str) -> str:
    lines = section.splitlines()
    kind, port, proto, *formats = lines[0][2:].split(" ")
    codecs = {
        line[9:].split(" ")[0]: line.split(" ", 1)[1].split("/")[0].lower()
        for line in lines
        if line.startswith("a=rtpmap:") and " " in line
    }
    fmtp = {line[7:].split(" ")[0]: line for line in lines if line.startswith("a=fmtp:")}
    kept = [
        fmt
        for fmt in formats
        if codecs.get(fmt) in _CAMERA_CODECS.get(kind, ())
        # The camera fragments its frames: H264 in packetization mode 1 only.
        and (codecs[fmt] != "h264" or "packetization-mode=1" in fmtp.get(fmt, ""))
    ]
    if not kept:  # the data channel, or nothing the camera would take anyway
        return section

    def keep(line: str) -> bool:
        if line.startswith("a=extmap"):
            return False
        prefix = next((p for p in _PER_FORMAT if line.startswith(p)), None)
        return prefix is None or line[len(prefix) :].split(" ")[0] in kept

    return "\r\n".join([f"m={kind} {port} {proto} {' '.join(kept)}", *filter(keep, lines[1:])])


def reject_unanswered(offer: str, answer: str) -> str:
    """Add back, as rejected, the offer's trailing m-sections the camera dropped.

    The camera answers audio and video only and drops the frontend's data
    channel, but a browser refuses an answer with fewer m-sections than its offer.
    """
    # ponytail: assumes the camera keeps the offer's order and only drops the tail.
    sections = re.split(r"\r?\n(?=m=)", offer)[1:]
    missing = sections[len(_media_lines(answer)) :]
    if not missing:
        return answer
    rejected = []
    for section in missing:
        lines = section.splitlines()
        kind, _port, proto, *formats = lines[0][2:].split(" ")
        rejected += [f"m={kind} 0 {proto} {' '.join(formats)}", "c=IN IP4 0.0.0.0"]
        rejected += [line for line in lines if line.startswith("a=mid:")]
    return answer.rstrip("\r\n") + "\r\n" + "\r\n".join(rejected) + "\r\n"


@dataclass(frozen=True, slots=True)
class MeariCandidate:
    candidate: str
    sdp_mid: str | None
    sdp_m_line_index: int | None


class MeariSignalingError(Exception):
    """The signaling server or the camera refused or dropped the session."""

    @property
    def camera_asleep(self) -> bool:
        return str(self) in DORMANT_ERRORS


class MeariSignalingSession:
    """One live-view negotiation with one camera, relayed for a WebRTC peer.

    Callbacks are plain functions — Home Assistant's ``send_message`` is one.
    Errors are fatal only until the camera answers: afterwards the peer's own ICE
    decides, and a late error is just logged.
    """

    def __init__(
        self,
        *,
        on_answer: Callable[[str], None],
        on_candidate: Callable[[MeariCandidate], None],
        on_error: Callable[[MeariSignalingError], None],
    ) -> None:
        # No I/O here: the session must exist before the first network call, so
        # the peer's early ICE candidates have somewhere to wait.
        self._info: dict[str, Any] = {}
        self._offer_sdp = ""
        self._on_answer = on_answer
        self._on_candidate = on_candidate
        self._on_error = on_error
        self._sid = str(uuid.uuid4()).upper()
        self._caller = uuid.uuid4().hex[:16]
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._reader: asyncio.Task[None] | None = None
        self._authenticated = asyncio.Event()
        self._offered = False
        self._answered = False
        self._streaming = False
        self._closed = False
        self._failed = False
        self._pending_candidates: list[MeariCandidate] = []

    @property
    def _peer(self) -> dict[str, Any]:
        return {"caller": self._caller, "callee": self._info.get("callee")}

    async def _send(self, method: str, params: dict[str, Any], **extra: Any) -> None:
        if self._ws is None or self._ws.closed:
            return
        frame = {"sid": self._sid, "method": method, "action": "req", "cmd": "mts"}
        frame.update(extra)
        frame["params"] = params
        await self._ws.send_str(json.dumps(frame))

    async def start(
        self, http: aiohttp.ClientSession, connect_info: dict[str, Any], offer_sdp: str
    ) -> None:
        """Authenticate, then hand the peer's offer to the camera."""
        self._info = connect_info
        self._offer_sdp = offer_sdp
        url = connect_info.get("wssUrl")
        if not isinstance(url, str) or not url:
            raise MeariSignalingError("no signaling address for this camera")
        self._ws = await http.ws_connect(url, heartbeat=30)
        if self._closed:  # the peer gave up while we were connecting
            await self._ws.close()
            return
        self._reader = asyncio.create_task(self._read_loop())
        await self._send(
            "option",
            {
                **self._peer,
                "devicecode": self._info.get("deviceCode"),
                "expires": self._info.get("expires"),
                "continent": "Europe",
                "country": "France",
            },
            auth={
                "accessId": self._info.get("accessId"),
                "signature": self._info.get("signature"),
                "token": self._info.get("token"),
            },
        )
        try:
            await asyncio.wait_for(self._authenticated.wait(), _AUTH_TIMEOUT_SECONDS)
        except TimeoutError as err:
            await self.close()
            raise MeariSignalingError("signaling authentication timed out") from err
        if self._closed or self._failed:  # already reported through on_error
            return
        slim = slim_offer(offer_sdp)
        LOGGER.debug(
            "Camera signaling offer (%d of %d bytes): %s",
            len(slim),
            len(offer_sdp),
            _media_lines(slim),
        )
        await self._send(
            "offer",
            {
                **self._peer,
                "devicecode": self._info.get("deviceCode"),
                "sdp": slim,
                "settings": {"method": "preview"},
            },
        )
        self._offered = True
        pending, self._pending_candidates = self._pending_candidates, []
        for candidate in pending:
            await self._send_candidate(candidate)

    async def add_candidate(self, candidate: MeariCandidate) -> None:
        """Relay one of the peer's ICE candidates (held until the offer is out)."""
        if not candidate.candidate:  # end-of-candidates marker
            return
        if not self._offered:
            self._pending_candidates.append(candidate)
            return
        await self._send_candidate(candidate)

    async def _send_candidate(self, candidate: MeariCandidate) -> None:
        await self._send(
            "candidate",
            {
                **self._peer,
                "candidate": {
                    "candidate": candidate.candidate,
                    "sdpMid": candidate.sdp_mid,
                    "sdpMLineIndex": candidate.sdp_m_line_index,
                },
            },
        )

    async def _preview(self, *, stop: bool) -> None:
        await self._send(
            "settings",
            {
                **self._peer,
                "settings": {
                    "sid": self._sid,
                    "method": "preview",
                    "streams": [{"channel": 0, "stream": 1, "stop": int(stop)}],
                },
            },
        )

    async def _read_loop(self) -> None:
        assert self._ws is not None
        try:
            async for message in self._ws:
                if message.type is not aiohttp.WSMsgType.TEXT:
                    break
                try:
                    payload = json.loads(message.data)
                except ValueError:
                    continue
                if isinstance(payload, dict):
                    await self._dispatch(payload)
        except aiohttp.ClientError as err:
            LOGGER.debug("Camera signaling read failed: %s", err)
        if not self._closed and not self._answered:
            self._fail(MeariSignalingError("signaling connection closed"))

    async def _dispatch(self, payload: dict[str, Any]) -> None:
        if "errid" in payload:
            LOGGER.debug(
                "Camera signaling error %s: %s (%s)",
                payload.get("errid"),
                payload.get("errstr"),
                payload.get("desc"),
            )
            if payload.get("errid") == 0:  # "Connect Success": the app starts the stream here
                self._streaming = True
                await self._preview(stop=False)
            elif not self._answered:  # afterwards the peer's own ICE decides
                self._fail(MeariSignalingError(str(payload.get("errstr") or "")))
            return
        method = payload.get("method")
        params = payload.get("params")
        params = params if isinstance(params, dict) else {}
        if method == "option":
            LOGGER.debug("Camera signaling authenticated")
            self._authenticated.set()
        elif method == "answer" and isinstance(params.get("sdp"), str):
            LOGGER.debug("Camera signaling answer: %s", _media_lines(params["sdp"]))
            self._answered = True
            self._on_answer(reject_unanswered(self._offer_sdp, params["sdp"]))
        elif method == "candidate":
            candidate = params.get("candidate")
            if isinstance(candidate, dict) and isinstance(candidate.get("candidate"), str):
                LOGGER.debug(
                    "Camera signaling candidate: %s",
                    candidate["candidate"].partition(" typ ")[2].split(" ")[0] or "?",
                )
                self._on_candidate(
                    MeariCandidate(
                        candidate["candidate"],
                        candidate.get("sdpMid"),
                        candidate.get("sdpMLineIndex"),
                    )
                )

    def _fail(self, error: MeariSignalingError) -> None:
        if self._closed or self._failed:
            return
        self._failed = True
        # Release start() at once instead of letting it wait out the auth timeout
        # and report a second, misleading error.
        self._authenticated.set()
        self._on_error(error)

    async def close(self) -> None:
        """Stop the stream and drop the signaling connection."""
        if self._closed:
            return
        self._closed = True
        if self._ws is not None and not self._ws.closed:
            with contextlib.suppress(aiohttp.ClientError, ConnectionError):
                if self._streaming:
                    await self._preview(stop=True)
                await self._ws.close()
        if self._reader is not None and self._reader is not asyncio.current_task():
            self._reader.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reader
