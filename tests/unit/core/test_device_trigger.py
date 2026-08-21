"""Unit tests for Enki binary-sensor device triggers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from enki import device_trigger
from homeassistant.components.binary_sensor import BinarySensorDeviceClass


def _entry(*, domain="binary_sensor", platform="enki", device_class=None, entity_id="id-1"):
    return SimpleNamespace(
        domain=domain,
        platform=platform,
        device_class=device_class,
        original_device_class=device_class,
        id=entity_id,
    )


def test_trigger_types_cover_expected_events() -> None:
    for t in ("motion_detected", "leak_detected", "window_opened", "vibration_detected"):
        assert t in device_trigger.TRIGGER_TYPES
    # every trigger type maps to an (from, to) state pair
    assert all(len(v) == 2 for v in device_trigger._TRIGGER_STATES.values())  # noqa: SLF001


@pytest.mark.asyncio
async def test_get_triggers_builds_motion_and_leak() -> None:
    entries = [
        _entry(device_class=BinarySensorDeviceClass.MOTION, entity_id="e-motion"),
        _entry(device_class=BinarySensorDeviceClass.MOISTURE, entity_id="e-leak"),
    ]
    with patch.object(device_trigger.er, "async_entries_for_device", return_value=entries):
        triggers = await device_trigger.async_get_triggers(MagicMock(), "dev-1")

    types = {t["type"] for t in triggers}
    assert {"motion_detected", "motion_stopped", "leak_detected", "leak_cleared"} <= types
    assert all(t["domain"] == "enki" and t["device_id"] == "dev-1" for t in triggers)


@pytest.mark.asyncio
async def test_get_triggers_skips_foreign_and_non_binary() -> None:
    entries = [
        _entry(platform="zha", device_class=BinarySensorDeviceClass.MOTION),
        _entry(domain="sensor", device_class=BinarySensorDeviceClass.MOTION),
        _entry(device_class=None),  # no device class → no triggers
    ]
    with patch.object(device_trigger.er, "async_entries_for_device", return_value=entries):
        triggers = await device_trigger.async_get_triggers(MagicMock(), "dev-1")
    assert triggers == []


@pytest.mark.asyncio
async def test_attach_trigger_translates_to_state_trigger() -> None:
    config = {"type": "motion_detected", "entity_id": "binary_sensor.enki_motion"}
    with (
        patch.object(
            device_trigger.state_trigger,
            "async_validate_trigger_config",
            new=AsyncMock(side_effect=lambda hass, cfg: cfg),
        ),
        patch.object(
            device_trigger.state_trigger,
            "async_attach_trigger",
            new=AsyncMock(return_value="unsub"),
        ) as attach,
    ):
        result = await device_trigger.async_attach_trigger(
            MagicMock(), config, MagicMock(), MagicMock()
        )

    assert result == "unsub"
    sent_config = attach.await_args.args[1]
    # motion_detected fires on off → on
    assert sent_config["from"] == "off"
    assert sent_config["to"] == "on"
    assert sent_config["entity_id"] == "binary_sensor.enki_motion"
