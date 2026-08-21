"""Unit tests for the camera event-snapshot image fetch."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from enki.camera import EnkiEventSnapshotCamera
from enki.domain.models import EnkiDevice


def _device(**kwargs) -> EnkiDevice:
    defaults = {
        "home_id": "home-1",
        "device_id": "dev-1",
        "node_id": "node-cam",
        "device_name": "Camera",
        "device_type": "cameras",
        "is_enabled": True,
        "state": "ACTIVE",
        "capabilities": ["check_camera_events"],
    }
    defaults.update(kwargs)
    return EnkiDevice(**defaults)


def _camera(reported: dict) -> EnkiEventSnapshotCamera:
    device = _device(last_reported_value=reported)
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.get_device_by_node = lambda node_id: device
    entity = EnkiEventSnapshotCamera(coordinator, device)
    entity.hass = MagicMock()
    return entity


def _session_returning(status: int, body: bytes) -> MagicMock:
    response = MagicMock()
    response.status = status
    response.read = AsyncMock(return_value=body)

    @asynccontextmanager
    async def _get(_url):
        yield response

    session = MagicMock()
    session.get = _get
    return session


@pytest.mark.asyncio
async def test_no_url_returns_none() -> None:
    cam = _camera({})
    assert await cam.async_camera_image() is None


@pytest.mark.asyncio
async def test_fetches_and_caches_image() -> None:
    cam = _camera({"camera_last_image_url": "https://x/snap.jpg"})
    with patch(
        "enki.camera.async_get_clientsession",
        return_value=_session_returning(200, b"JPEGDATA"),
    ):
        assert await cam.async_camera_image() == b"JPEGDATA"
    # Same URL → served from cache, no session call.
    with patch("enki.camera.async_get_clientsession", side_effect=AssertionError("refetched")):
        assert await cam.async_camera_image() == b"JPEGDATA"


@pytest.mark.asyncio
async def test_non_200_returns_none_without_cache() -> None:
    cam = _camera({"camera_last_image_url": "https://x/a.jpg"})
    with patch(
        "enki.camera.async_get_clientsession",
        return_value=_session_returning(404, b""),
    ):
        assert await cam.async_camera_image() is None


@pytest.mark.asyncio
async def test_fetch_error_returns_none() -> None:
    cam = _camera({"camera_last_image_url": "https://x/a.jpg"})
    session = MagicMock()
    session.get = MagicMock(side_effect=RuntimeError("boom"))
    with patch("enki.camera.async_get_clientsession", return_value=session):
        assert await cam.async_camera_image() is None
