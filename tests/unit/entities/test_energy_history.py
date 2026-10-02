"""Month-to-date energy from the consumption chart (#270)."""

from __future__ import annotations

from unittest.mock import MagicMock

from enki.domain.energy_history import parse_energy_history
from enki.domain.models import EnkiDevice
from enki.sensor import EnkiEnergySensor

# September 2026 on the reporter's water heater: the shape and the numbers he
# reported — 30 daily buckets, 12 with a reading, 25.255 kWh over the month,
# 0 kWh on the 19th and a 3.7 kWh peak on the 27th — with the daily values laid
# out to match. The app's own monthly screen showed 25 kWh. Days before the
# first measurement come back null; a day that drew nothing comes back 0.0.
SEPTEMBER_DAYS: list[float | None] = [
    None, None, None, None, None, None, None, None, None, None,
    None, None, None, None, None, None, None, None, 0.0, 1.805,
    2.42, 3.11, 2.65, 1.97, 2.4, 2.21, 3.7, 2.99, 1.0, 1.0,
]  # fmt: skip

SEPTEMBER = {
    "firstMeasurementDate": "2026-09-19T00:00:00.000Z",
    "lastMeasurementDate": "2026-09-30T23:59:59.000Z",
    "periodConsumption": {"value": 25.255, "unit": "kWh", "date": "2026-09-01T00:00:00.000Z"},
    "periodChart": {
        "series": [
            {
                "data": SEPTEMBER_DAYS,
                "startDateFormatted": "01/09/2026",
                "endDateFormatted": "30/09/2026",
                "unit": "kWh",
            }
        ],
        "type": "BAR",
        "yScale": {"minimum": 0.0, "maximum": 3.7},
    },
}


def _heater(**reported) -> EnkiDevice:
    return EnkiDevice(
        home_id="home-1",
        device_id="dev-1",
        node_id="node-wh",
        device_name="Water heater",
        device_type="water_heaters",
        is_enabled=True,
        state="ACTIVE",
        capabilities=["check_electrical_consumption"],
        last_reported_value=reported,
    )


def _sensor(device: EnkiDevice) -> EnkiEnergySensor:
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.get_device_by_node = lambda node_id: device
    return EnkiEnergySensor(coordinator, device)


def test_the_month_total_is_the_sum_of_its_buckets() -> None:
    state = parse_energy_history(SEPTEMBER)

    assert state["energy_period_total"] == 25.255
    assert state["energy_period_total"] == SEPTEMBER["periodConsumption"]["value"]
    assert state["energy_period_buckets"] == 12
    assert state["energy_period_unit"] == "kWh"
    assert state["energy_first_measurement_at"] == "2026-09-19T00:00:00.000Z"


def test_a_real_zero_counts_as_a_reading() -> None:
    """19 September read 0.0 — a day the heater drew nothing, not a missing day."""
    state = parse_energy_history(
        {"periodChart": {"series": [{"data": [0.0, None, None], "unit": "kWh"}]}}
    )

    assert state["energy_period_total"] == 0.0
    assert state["energy_period_buckets"] == 1


def test_a_month_with_no_reading_at_all_is_unknown_not_zero() -> None:
    """Reporting 0 for silence would tell Home Assistant the meter reset."""
    state = parse_energy_history(
        {"periodChart": {"series": [{"data": [None] * 31, "unit": "kWh"}]}}
    )

    assert state["energy_period_total"] is None
    assert state["energy_period_buckets"] == 0


def test_a_response_without_a_chart_yields_nothing_usable() -> None:
    assert parse_energy_history({})["energy_period_total"] is None
    assert parse_energy_history({"periodChart": {"series": []}})["energy_period_total"] is None


def test_the_unit_falls_back_to_the_series() -> None:
    payload = {"periodChart": {"series": [{"data": [1.0], "unit": "kWh"}]}}

    assert parse_energy_history(payload)["energy_period_unit"] == "kWh"


def test_the_sensor_reports_the_month_total_as_a_rising_meter() -> None:
    sensor = _sensor(_heater(**parse_energy_history(SEPTEMBER)))

    assert sensor.native_value == 25.255
    assert sensor.extra_state_attributes["first_measurement_at"] == "2026-09-19T00:00:00.000Z"


def test_the_sensor_is_unknown_when_nothing_was_measured() -> None:
    sensor = _sensor(_heater())

    assert sensor.native_value is None
