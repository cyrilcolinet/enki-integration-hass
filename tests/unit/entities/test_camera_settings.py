"""Meari-generation camera settings (the Lexman solar camera, #216)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from enki.domain.camera_settings import (
    CAMERA_NUMBERS,
    CAMERA_SELECTS,
    number_range,
    parse_camera_status,
    select_values,
)
from enki.domain.models import EnkiDevice
from enki.domain.profile import build_discovery_record
from enki.domain.telemetry_coverage import discovery_record_needs_telemetry
from enki.number import EnkiCameraSensitivityNumber
from enki.number import async_setup_entry as setup_numbers
from enki.select import EnkiCameraSettingSelect
from enki.switch import EnkiCameraSettingSwitch, _build_switch_entities

# check-camera-status exactly as the reporter's solar camera returned it.
REAL_STATUS = {
    "batteryLevel": "100",
    "wifiStrength": "52",
    "motionDetection": "HUMAN_FORM",
    "indicatorLight": "ON",
    "batteryChargingStatus": "CHARGING_FULL",
    "motionDetectionSensitivityLevel": 6,
    "humanFormDetectionSensitivityLevel": 3,
    "flipScreenMode": "NOT_FLIP",
    "lightMode": "ON",
    "nightVisionMode": "SMART",
    "recordingDuration": "TEN_SECONDS",
    "firmware": {"otaEnabled": True, "otaVersion": "6.1.3", "newOtaAvailable": False},
    "sdCard": {"state": "NO_CARD_INSERTED", "total": 0, "free": 0},
}

SOLAR_CAPABILITIES = [
    "change_detection_zone",
    "change_flip_screen_mode",
    "change_humanoid_detection_sensitivity_level",
    "change_indicator_light_mode",
    "change_light_mode",
    "change_motion_detection_mode",
    "change_motion_detection_sensitivity_level",
    "change_night_vision_mode",
    "change_recording_duration",
    "check_camera_events",
    "check_camera_last_event",
    "check_camera_state",
    "check_detection_zone",
    "delete_camera_events",
    "format_sd_card",
    "update_firmware_version",
]


def _solar(possible_values: dict | None = None) -> EnkiDevice:
    return EnkiDevice(
        home_id="home",
        device_id="dev",
        node_id="node-solar",
        device_name="Caméra jardin",
        device_type="cameras",
        is_enabled=True,
        state="ACTIVE",
        capabilities=SOLAR_CAPABILITIES,
        possible_values=possible_values or {},
        last_reported_value=parse_camera_status(REAL_STATUS),
    )


def _coordinator() -> MagicMock:
    coordinator = MagicMock()
    coordinator.api.async_set_camera_setting = AsyncMock()
    return coordinator


def test_real_status_is_flattened() -> None:
    state = parse_camera_status(REAL_STATUS)
    assert state["camera_night_vision_mode"] == "SMART"
    assert state["camera_motion_detection_mode"] == "HUMAN_FORM"
    assert state["camera_motion_sensitivity"] == 6
    assert state["camera_battery_level"] == 100  # sent as the string "100"
    assert state["camera_wifi_strength"] == 52
    assert state["camera_sd_state"] == "NO_CARD_INSERTED"
    # The mode must not land on the motion sensors' own state key.
    assert "motion_detection" not in state


def test_only_meari_cameras_get_settings() -> None:
    assert _solar().profile.supports_camera_settings is True
    older = EnkiDevice(
        home_id="home",
        device_id="dev",
        node_id="node-ipc",
        device_name="IPC176KF",
        device_type="cameras",
        is_enabled=True,
        state="ACTIVE",
        capabilities=["check_camera_events", "check_camera_last_event", "remove_camera_events"],
    )
    assert older.profile.supports_camera_settings is False


def test_select_choices_prefer_the_referentiel() -> None:
    night = next(s for s in CAMERA_SELECTS if s.capability == "change_night_vision_mode")
    assert select_values(night, {}) == ("SMART", "FULL_COLOR", "BLACK_AND_WHITE")
    listed = {"change_night_vision_mode": {"values": ["SMART", "BLACK_AND_WHITE"]}}
    assert select_values(night, listed) == ("SMART", "BLACK_AND_WHITE")


def test_sensitivity_range_comes_only_from_the_referentiel() -> None:
    spec = CAMERA_NUMBERS[0]
    assert number_range(spec, {}) is None
    ranged = {spec.capability: {"range": {"min": 1, "max": 10, "step": 1}}}
    assert number_range(spec, ranged) == (1.0, 10.0, 1.0)


def test_select_reads_and_writes_the_api_value() -> None:
    spec = next(s for s in CAMERA_SELECTS if s.capability == "change_night_vision_mode")
    select = EnkiCameraSettingSelect(_coordinator(), _solar(), spec)
    assert select._attr_options == ["smart", "full_color", "black_and_white"]
    assert select.current_option == "smart"


@pytest.mark.asyncio
async def test_select_sends_the_uppercase_value() -> None:
    coordinator = _coordinator()
    spec = next(s for s in CAMERA_SELECTS if s.capability == "change_night_vision_mode")
    select = EnkiCameraSettingSelect(coordinator, _solar(), spec)

    await select.async_select_option("full_color")

    coordinator.api.async_set_camera_setting.assert_awaited_once_with(
        "home", "node-solar", "change_night_vision_mode", "FULL_COLOR"
    )
    coordinator.update_cached_value.assert_called_once_with(
        "node-solar", "camera_night_vision_mode", "FULL_COLOR"
    )


@pytest.mark.asyncio
async def test_flip_switch_maps_flip_and_not_flip() -> None:
    coordinator = _coordinator()
    switches = {
        e._spec.capability: e
        for e in _build_switch_entities(coordinator, _solar())
        if isinstance(e, EnkiCameraSettingSwitch)
    }
    assert set(switches) == {"change_indicator_light_mode", "change_flip_screen_mode"}
    flip = switches["change_flip_screen_mode"]
    assert flip.is_on is False  # NOT_FLIP

    await flip.async_turn_on()
    coordinator.api.async_set_camera_setting.assert_awaited_once_with(
        "home", "node-solar", "change_flip_screen_mode", "FLIP"
    )


@pytest.mark.asyncio
async def test_sensitivity_number_needs_a_range() -> None:
    coordinator = _coordinator()
    coordinator.data = [_solar()]
    added: list = []
    await setup_numbers(MagicMock(), MagicMock(runtime_data=coordinator), added.extend)
    assert not [e for e in added if isinstance(e, EnkiCameraSensitivityNumber)]

    ranged = {
        "change_motion_detection_sensitivity_level": {"range": {"min": 1, "max": 10, "step": 1}}
    }
    coordinator.data = [_solar(ranged)]
    added.clear()
    await setup_numbers(MagicMock(), MagicMock(runtime_data=coordinator), added.extend)
    (number,) = [e for e in added if isinstance(e, EnkiCameraSensitivityNumber)]
    assert number.native_value == 6.0

    await number.async_set_native_value(8)
    coordinator.api.async_set_camera_setting.assert_awaited_once_with(
        "home", "node-solar", "change_motion_detection_sensitivity_level", 8
    )


def test_solar_camera_is_no_longer_a_capability_gap() -> None:
    record = build_discovery_record(
        device_type="cameras",
        bff_device_type="cameras",
        capabilities=SOLAR_CAPABILITIES,
        possible_values={},
        manufacturer="Lexman",
        model=None,
        firmware_version=None,
        supported_by_integration=True,
    )
    assert discovery_record_needs_telemetry(record) is False
