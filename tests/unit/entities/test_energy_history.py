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


def test_the_instant_sensor_surfaces_when_the_device_last_reported() -> None:
    """Enki relays the last value the device sent, which can sit minutes behind (#279)."""
    from enki.sensor import EnkiElectricalConsumptionSensor

    device = _heater(
        electrical_consumption=0.0,
        electrical_consumption_unit="W",
        electrical_consumption_at="2026-10-02T10:32:13.114Z",
    )
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.get_device_by_node = lambda node_id: device
    sensor = EnkiElectricalConsumptionSensor(coordinator, device)

    assert sensor.native_value == 0.0
    assert sensor.extra_state_attributes["last_reported_at"] == "2026-10-02T10:32:13.114Z"


# The same month exactly as the service sent it (captured from app 2.26.3 on the
# reporter's AD-HEWH3-1): each bucket is an {"x", "value"} object, and dates are
# dd/mm/yyyy. The 12 readings add up to the 25.25 kWh the YEARLY chart shows for
# September, and to periodConsumption to the last decimal.
SEPTEMBER_AS_SENT = {
    "firstMeasurementDate": "19/09/2026",
    "lastMeasurementDate": "02/10/2026",
    "periodConsumption": {"value": 25.254620000000003, "unit": "kWh", "date": "19/09/2026"},
    "periodChart": {
        "series": [
            {
                "data": [{"x": day, "value": None} for day in range(1, 19)]
                + [
                    {"x": 19, "value": 0.0},
                    {"x": 20, "value": 3.38451},
                    {"x": 21, "value": 0.41722},
                    {"x": 22, "value": 2.63024},
                    {"x": 23, "value": 2.09989},
                    {"x": 24, "value": 2.3895600000000004},
                    {"x": 25, "value": 2.243879999999999},
                    {"x": 26, "value": 1.3907299999999996},
                    {"x": 27, "value": 3.7487600000000008},
                    {"x": 28, "value": 2.2479799999999983},
                    {"x": 29, "value": 3.0025600000000026},
                    {"x": 30, "value": 1.6992900000000013},
                ],
                "startDateFormatted": "01/09/2026",
                "endDateFormatted": "30/09/2026",
                "unit": "kWh",
            }
        ],
        "type": "column",
        "yScale": {"minimum": 0.0, "maximum": 5.0},
    },
}


def test_buckets_sent_as_x_value_objects_are_summed() -> None:
    """The real shape: a list of objects read as no reading at all (#270)."""
    state = parse_energy_history(SEPTEMBER_AS_SENT)

    assert state["energy_period_total"] == 25.255
    assert state["energy_period_total"] == round(SEPTEMBER_AS_SENT["periodConsumption"]["value"], 3)
    assert state["energy_period_buckets"] == 12
    assert state["energy_period_unit"] == "kWh"


def test_a_day_with_no_reading_yet_comes_back_as_null_value() -> None:
    month = {
        "periodChart": {"series": [{"data": [{"x": 1, "value": 3.06209}, {"x": 2, "value": None}]}]}
    }

    assert parse_energy_history(month)["energy_period_total"] == 3.062


def test_a_period_with_nothing_yet_has_no_total() -> None:
    """A DAILY read just after midnight UTC: chart and total both come back null."""
    empty = {
        "firstMeasurementDate": "19/09/2026",
        "lastMeasurementDate": "05/10/2026",
        "periodChart": None,
        "periodConsumption": None,
    }

    assert parse_energy_history(empty)["energy_period_total"] is None
