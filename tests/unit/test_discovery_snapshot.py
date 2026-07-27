"""Discovery must publish its snapshot atomically (see issue #87).

A poll re-runs full discovery every 30 s. Readers hitting that window, or a poll
raising midway, used to see an empty discovery_records while the coordinator kept
serving its cached devices — diagnostics then reported devices but zero profiles.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from enki.api.client import EnkiAPI
from enki.domain.profile import build_discovery_record


def _record(device_type: str = "boiler"):
    return build_discovery_record(
        device_type=device_type,
        bff_device_type=device_type,
        capabilities=[],
        possible_values={},
        manufacturer=None,
        model=None,
        firmware_version=None,
        supported_by_integration=False,
    )


def _api_with_one_home() -> EnkiAPI:
    api = EnkiAPI("user", "pass")
    http = AsyncMock()
    http.get_homes = AsyncMock(return_value=["home-1"])
    api._get_http = AsyncMock(return_value=http)  # noqa: SLF001
    return api


@pytest.mark.asyncio
async def test_whenDiscoveryRaises_thenPreviousSnapshotSurvives() -> None:
    # Given a completed discovery
    api = _api_with_one_home()
    with patch.object(EnkiAPI, "_discover_home", AsyncMock(return_value=(["dev"], [_record()]))):
        await api.async_get_devices()
    assert len(api.discovery_records) == 1

    # When the next poll blows up midway
    with (
        patch.object(EnkiAPI, "_discover_home", AsyncMock(side_effect=RuntimeError("boom"))),
        pytest.raises(RuntimeError),
    ):
        await api.async_get_devices()

    # Then diagnostics still have something to show
    assert len(api.discovery_records) == 1


@pytest.mark.asyncio
async def test_whenReadDuringDiscovery_thenSnapshotIsNeverEmpty() -> None:
    # Given a completed discovery and a slow poll in flight
    api = _api_with_one_home()
    with patch.object(EnkiAPI, "_discover_home", AsyncMock(return_value=(["dev"], [_record()]))):
        await api.async_get_devices()

    async def slow_discover(*_args, **_kwargs):
        await asyncio.sleep(0)
        return ["dev"], [_record("lights")]

    # When diagnostics read while the poll is running
    with patch.object(EnkiAPI, "_discover_home", slow_discover):
        task = asyncio.create_task(api.async_get_devices())
        await asyncio.sleep(0)
        mid_poll = api.discovery_records
        await task

    # Then the reader saw the previous snapshot, not a half-built one
    assert len(mid_poll) == 1
    assert [record.device_type for record in api.discovery_records] == ["lights"]


@pytest.mark.asyncio
async def test_whenDiscoverySucceeds_thenStaleProfilesAreDropped() -> None:
    # Given
    api = _api_with_one_home()
    with patch.object(EnkiAPI, "_discover_home", AsyncMock(return_value=(["dev"], [_record()]))):
        await api.async_get_devices()

    # When a later poll returns fewer profiles
    with patch.object(EnkiAPI, "_discover_home", AsyncMock(return_value=([], []))):
        await api.async_get_devices()

    # Then the published snapshot replaces the old one rather than accumulating
    assert api.discovery_records == []
