"""Evology 2-channel in-wall module → one switch per channel (#152)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from enki.api.capability_routing import CAPABILITY_READS
from enki.domain.models import EnkiDevice
from enki.switch import EnkiChannelSwitch, _build_switch_entities


def _module(**overrides) -> EnkiDevice:
    defaults = {
        "home_id": "home",
        "device_id": "dev",
        "node_id": "node-module",
        "device_name": "Evology module",
        "device_type": "modules",
        "is_enabled": True,
        "state": "ACTIVE",
        "capabilities": [
            "check_channel1_electrical_power",
            "check_channel2_electrical_power",
            "check_in_wall_plug_2_channels_state",
            "switch_channel1_electrical_power",
            "switch_channel2_electrical_power",
            "switch_channel_electrical_power",
        ],
        "last_reported_value": {
            "channel1_electrical_power": "ON",
            "channel2_electrical_power": "OFF",
        },
    }
    defaults.update(overrides)
    return EnkiDevice(**defaults)


def test_profile_detects_two_channels_and_not_an_outlet() -> None:
    profile = _module().profile
    assert profile.channel_power_indices == [1, 2]
    assert profile.supports_channel_power is True
    assert profile.is_outlet is False  # no switch_electrical_power → no outlet entity


def test_channel_reads_route_via_power_service() -> None:
    read = next(
        (r for r in CAPABILITY_READS if r.capability == "check_channel1_electrical_power"), None
    )
    assert read is not None
    assert read.transport_id == "power"
    assert read.state_key == "channel1_electrical_power"


def test_builds_one_switch_per_channel_with_state() -> None:
    entities = [e for e in _build_switch_entities(MagicMock(), _module())]
    channels = [e for e in entities if isinstance(e, EnkiChannelSwitch)]
    assert len(channels) == 2
    by_channel = {e._channel: e for e in channels}
    assert by_channel[1].is_on is True  # ON
    assert by_channel[2].is_on is False  # OFF


@pytest.mark.asyncio
async def test_turn_on_posts_channel_switch_capability() -> None:
    coordinator = MagicMock()
    coordinator.api.async_set_capability_value = AsyncMock()
    switch = EnkiChannelSwitch(coordinator, _module(), channel=2)
    await switch.async_turn_on()
    coordinator.api.async_set_capability_value.assert_awaited_once_with(
        "home",
        "node-module",
        "power",
        "switch_channel2_electrical_power",
        "ON",
    )
