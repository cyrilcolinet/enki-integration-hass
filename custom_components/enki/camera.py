"""Camera platform for Lexman cameras.

Every camera shows the snapshot of its latest motion event. The meari generation
(the solar camera, #216) and the video doorbell (#259) also stream live: Home
Assistant's frontend is the WebRTC peer, and these entities only relay signaling
to the device — no media ever goes through the integration. Their signaling has
nothing in common: the camera has a WebSocket, the doorbell a pair of REST routes
used as a mailbox. The pre-meari IPC1xxKF cameras stream over a proprietary P2P
tunnel instead, out of reach here (#165).
"""

from __future__ import annotations

import asyncio

from homeassistant.components.camera import (
    Camera,
    CameraEntityFeature,
    WebRTCAnswer,
    WebRTCCandidate,
    WebRTCError,
    WebRTCSendMessage,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from webrtc_models import RTCIceCandidateInit

from .api.meari_signaling import MeariCandidate, MeariSignalingError, MeariSignalingSession
from .api.videophone_signaling import VideophoneLiveSession
from .const import DOMAIN, LOGGER
from .coordinator import EnkiCoordinator
from .domain.models import EnkiDevice
from .entity import EnkiEntity
from .exceptions import EnkiConnectionError


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EnkiCoordinator = entry.runtime_data
    async_add_entities(
        _camera_class(device)(coordinator, device)
        for device in coordinator.data or []
        if device.profile.is_camera or device.profile.is_videophone
    )


def _camera_class(device: EnkiDevice) -> type[EnkiEventSnapshotCamera]:
    if device.profile.is_videophone:
        return EnkiVideophoneCamera
    if device.profile.supports_camera_settings:
        return EnkiLiveCamera
    return EnkiEventSnapshotCamera


class EnkiEventSnapshotCamera(EnkiEntity, Camera):
    """Still image of the camera's most recent motion event."""

    _attr_translation_key = "event_snapshot"
    _image_url_field = "camera_last_image_url"

    def __init__(self, coordinator: EnkiCoordinator, device: EnkiDevice) -> None:
        EnkiEntity.__init__(self, coordinator, device)
        Camera.__init__(self)
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-event-snapshot"
        # Not `_cache`: Camera keeps its cached properties there.
        self._snapshot: tuple[str, bytes] | None = None

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        url = getattr(self._device.reported, self._image_url_field)
        if not url:
            return None
        if self._snapshot is not None and self._snapshot[0] == url:
            return self._snapshot[1]
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    LOGGER.debug("Camera snapshot HTTP %s for %s", response.status, self.node_id)
                    return self._snapshot[1] if self._snapshot else None
                data = await response.read()
        except Exception as err:  # noqa: BLE001 - a broken snapshot must not crash HA
            LOGGER.debug("Camera snapshot fetch failed for %s: %s", self.node_id, err)
            return self._snapshot[1] if self._snapshot else None
        self._snapshot = (url, data)
        return data


class EnkiVideophoneCamera(EnkiEventSnapshotCamera):
    """A video doorbell: live view over WebRTC, last call's snapshot as its still.

    The doorbell answers an offer whoever sends it, with nobody at the door, so
    the live view needs no ring (#259).
    """

    _attr_translation_key = "videophone_snapshot"
    _image_url_field = "videophone_last_image_url"
    _attr_supported_features = CameraEntityFeature.STREAM

    def __init__(self, coordinator: EnkiCoordinator, device: EnkiDevice) -> None:
        super().__init__(coordinator, device)
        self._sessions: dict[str, VideophoneLiveSession] = {}
        # ponytail: one mailbox per node, so one negotiation at a time. Two
        # viewers opening at once would overwrite each other's offer.
        self._negotiating = asyncio.Lock()

    async def async_handle_async_webrtc_offer(
        self, offer_sdp: str, session_id: str, send_message: WebRTCSendMessage
    ) -> None:
        session = VideophoneLiveSession(offer_sdp)
        # Registered before the wait: the browser trickles its ICE candidates
        # while the offer is still being held back for them.
        self._sessions[session_id] = session
        try:
            async with self._negotiating:
                answer, candidates = await self.coordinator.api.async_start_videophone_live(
                    self._device.home_id, self._device.node_id, session
                )
        except EnkiConnectionError as err:
            LOGGER.debug("Live view refused for %s: %s", self.node_id, err)
            self._sessions.pop(session_id, None)
            send_message(WebRTCError("videophone_signaling", str(err)))
            return
        send_message(WebRTCAnswer(answer))
        for candidate in candidates:
            send_message(
                WebRTCCandidate(
                    RTCIceCandidateInit(
                        candidate=candidate["candidate"],
                        sdp_mid=candidate.get("sdpMid"),
                        sdp_m_line_index=candidate.get("sdpMLineIndex"),
                    )
                )
            )

    async def async_on_webrtc_candidate(
        self, session_id: str, candidate: RTCIceCandidateInit
    ) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            return
        session.add_candidate(
            {
                "candidate": candidate.candidate,
                "sdpMid": candidate.sdp_mid,
                "sdpMLineIndex": candidate.sdp_m_line_index,
            }
        )

    @callback
    def close_webrtc_session(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if session is not None:
            session.close()

    async def async_will_remove_from_hass(self) -> None:
        sessions, self._sessions = list(self._sessions.values()), {}
        for session in sessions:
            session.close()
        await super().async_will_remove_from_hass()


class EnkiLiveCamera(EnkiEventSnapshotCamera):
    """A meari camera: live view over WebRTC, last-event snapshot as its still.

    Same unique id as the snapshot camera, so an existing entity simply gains the
    live view instead of being duplicated.
    """

    _attr_translation_key = "live"
    _attr_supported_features = CameraEntityFeature.STREAM

    def __init__(self, coordinator: EnkiCoordinator, device: EnkiDevice) -> None:
        super().__init__(coordinator, device)
        self._sessions: dict[str, MeariSignalingSession] = {}

    async def async_handle_async_webrtc_offer(
        self, offer_sdp: str, session_id: str, send_message: WebRTCSendMessage
    ) -> None:
        def on_candidate(candidate: MeariCandidate) -> None:
            send_message(
                WebRTCCandidate(
                    RTCIceCandidateInit(
                        candidate=candidate.candidate,
                        sdp_mid=candidate.sdp_mid,
                        sdp_m_line_index=candidate.sdp_m_line_index,
                    )
                )
            )

        session = MeariSignalingSession(
            on_answer=lambda sdp: send_message(WebRTCAnswer(sdp)),
            on_candidate=on_candidate,
            on_error=lambda err: send_message(
                WebRTCError("camera_asleep" if err.camera_asleep else "camera_signaling", str(err))
            ),
        )
        # Registered before any network call: the browser trickles its ICE
        # candidates while we wake the camera and authenticate.
        self._sessions[session_id] = session
        try:
            await self.coordinator.api.async_start_camera_live(
                self._device.home_id, self._device.node_id, session, offer_sdp
            )
        except (MeariSignalingError, EnkiConnectionError) as err:
            LOGGER.debug("Live view refused for %s: %s", self.node_id, err)
            self._sessions.pop(session_id, None)
            await session.close()
            send_message(WebRTCError("camera_signaling", str(err)))

    async def async_on_webrtc_candidate(
        self, session_id: str, candidate: RTCIceCandidateInit
    ) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            return
        await session.add_candidate(
            MeariCandidate(candidate.candidate, candidate.sdp_mid, candidate.sdp_m_line_index)
        )

    @callback
    def close_webrtc_session(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if session is not None:
            self.hass.async_create_task(session.close())

    async def async_will_remove_from_hass(self) -> None:
        sessions, self._sessions = list(self._sessions.values()), {}
        for session in sessions:
            await session.close()
        await super().async_will_remove_from_hass()
