"""Live view on meari cameras through Home Assistant's native WebRTC."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from enki.api.meari_signaling import MeariCandidate, MeariSignalingError
from enki.camera import EnkiEventSnapshotCamera, EnkiLiveCamera, async_setup_entry
from enki.domain.models import EnkiDevice
from homeassistant.components.camera import CameraEntityFeature, WebRTCError
from webrtc_models import RTCIceCandidateInit


def _camera(capabilities: list[str]) -> EnkiDevice:
    return EnkiDevice(
        home_id="home",
        device_id="dev",
        node_id="node-cam",
        device_name="Caméra",
        device_type="cameras",
        is_enabled=True,
        state="ACTIVE",
        capabilities=capabilities,
    )


SOLAR = _camera(["check_camera_events", "check_camera_state", "change_night_vision_mode"])
IPC = _camera(["check_camera_events", "check_camera_last_event"])


@pytest.mark.asyncio
async def test_only_meari_cameras_stream() -> None:
    coordinator = MagicMock()
    coordinator.data = [SOLAR, IPC]
    added: list = []
    await async_setup_entry(MagicMock(), MagicMock(runtime_data=coordinator), added.extend)

    live, still = added
    assert type(live) is EnkiLiveCamera
    assert live._attr_supported_features == CameraEntityFeature.STREAM
    assert type(still) is EnkiEventSnapshotCamera
    # Same unique id: an existing snapshot entity gains the live view in place.
    assert live._attr_unique_id.endswith("-event-snapshot")


@pytest.mark.asyncio
async def test_candidates_trickled_during_negotiation_are_kept() -> None:
    """The browser sends candidates while we wake the camera and authenticate."""
    started = asyncio.Event()
    release = asyncio.Event()

    async def slow_start(home_id, node_id, session, offer_sdp):
        started.set()
        await release.wait()

    coordinator = MagicMock()
    coordinator.api.async_start_camera_live = AsyncMock(side_effect=slow_start)
    camera = EnkiLiveCamera(coordinator, SOLAR)

    offer = asyncio.create_task(camera.async_handle_async_webrtc_offer("OFFER", "s1", MagicMock()))
    await started.wait()
    await camera.async_on_webrtc_candidate(
        "s1",
        RTCIceCandidateInit(
            candidate="candidate:1 1 udp 1 1.2.3.4 5 typ host", sdp_mid="0", sdp_m_line_index=0
        ),
    )
    session = camera._sessions["s1"]
    assert session._pending_candidates == [
        MeariCandidate("candidate:1 1 udp 1 1.2.3.4 5 typ host", "0", 0)
    ]

    release.set()
    await offer


@pytest.mark.asyncio
async def test_refused_live_view_reports_one_error_and_forgets_the_session() -> None:
    coordinator = MagicMock()
    coordinator.api.async_start_camera_live = AsyncMock(
        side_effect=MeariSignalingError("the camera service returned no live-view access")
    )
    camera = EnkiLiveCamera(coordinator, SOLAR)
    sent: list = []

    await camera.async_handle_async_webrtc_offer("OFFER", "s1", sent.append)

    assert sent == [
        WebRTCError("camera_signaling", "the camera service returned no live-view access")
    ]
    assert "s1" not in camera._sessions


@pytest.mark.asyncio
async def test_closing_the_view_closes_the_signaling_session() -> None:
    coordinator = MagicMock()
    coordinator.api.async_start_camera_live = AsyncMock()
    camera = EnkiLiveCamera(coordinator, SOLAR)
    camera.hass = MagicMock()
    await camera.async_handle_async_webrtc_offer("OFFER", "s1", MagicMock())

    camera.close_webrtc_session("s1")

    assert "s1" not in camera._sessions
    camera.hass.async_create_task.assert_called_once()
    camera.hass.async_create_task.call_args.args[0].close()  # silence "never awaited"
