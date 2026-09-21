"""Live view of a meari-generation Lexman camera: its WebRTC signaling.

The app reaches the camera through a signaling WebSocket whose address and
credentials come from ``check-camera-connect-wss``. Every frame shares one
envelope — ``{"sid", "method", "action": "req", "cmd": "mts", "params"}`` — and
the exchange is plain WebRTC:

1. ``option`` — authenticate; the reply carries the camera's TURN relay;
2. ``offer`` — our SDP; the camera replies ``answer``;
3. ``candidate`` — ICE candidates, both ways;
4. ``settings`` / ``preview`` — start the stream once the answer is in.

Errors arrive as ``{"errid", "errstr"}``; a sleeping camera says so in ``errstr``.

Confirmed on a real solar camera up to the answer and its candidates (#216), with
a synthetic offer — so without media yet. The media itself never goes through
here: Home Assistant's frontend is the WebRTC peer, this only relays signaling.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
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
        await self._send(
            "offer",
            {
                **self._peer,
                "devicecode": self._info.get("deviceCode"),
                "sdp": offer_sdp,
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
            error = MeariSignalingError(str(payload.get("errstr") or ""))
            if self._answered:
                LOGGER.debug("Camera signaling error after answer: %s", error)
            else:
                self._fail(error)
            return
        method = payload.get("method")
        params = payload.get("params")
        params = params if isinstance(params, dict) else {}
        if method == "option":
            self._authenticated.set()
        elif method == "answer" and isinstance(params.get("sdp"), str):
            self._answered = True
            self._on_answer(params["sdp"])
            await self._preview(stop=False)
        elif method == "candidate":
            candidate = params.get("candidate")
            if isinstance(candidate, dict) and isinstance(candidate.get("candidate"), str):
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
                if self._answered:
                    await self._preview(stop=True)
                await self._ws.close()
        if self._reader is not None and self._reader is not asyncio.current_task():
            self._reader.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reader
