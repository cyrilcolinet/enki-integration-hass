"""Energy a device has consumed over a period, from its chart data (#270).

``consumption/nodes/{nodeId}?startDate=&timePeriod=`` is what the Enki app's
consumption screen reads. ``startDate`` picks a period rather than a range: the
response snaps to the period enclosing that instant, and comes back as buckets —
24 hours for ``DAILY``, days for ``WEEKLY`` and ``MONTHLY``, 12 months for
``YEARLY``. Field names are the app's own (``ConsumptionApiModel``)::

    {"firstMeasurementDate": …, "lastMeasurementDate": …,
     "periodConsumption": {"value": 25.255, "unit": "kWh", "date": …},
     "periodChart": {"series": [{"data": [{"x": 1, "value": null},
                                          {"x": 2, "value": 0.0}, …],
                                 "unit": "kWh"}]}}

Each bucket is an ``{"x", "value"}`` object, not a bare number (seen on an
Equation water heater, #270); a bare number is still read, in case another
device answers that way.

``null`` is "no reading", not zero: future hours and anything before
``firstMeasurementDate`` come back null, while a real zero is ``0.0``. The
difference matters — a month whose buckets are all null is a device we have
heard nothing from, and reporting 0 for it would tell Home Assistant the meter
reset and cost the user their long-term total.

The period total is the sum of its buckets, so that is what we sum: it survives
a response that omits ``periodConsumption``.
"""

from __future__ import annotations

from typing import Any

# The month, in daily buckets: the granularity the app charts, and the one
# confirmed to accrue while the month is still running.
MONTHLY = "MONTHLY"


def _bucket_value(bucket: Any) -> Any:
    return bucket.get("value") if isinstance(bucket, dict) else bucket


def _buckets(payload: dict[str, Any]) -> list[Any]:
    chart = payload.get("periodChart")
    if not isinstance(chart, dict):
        return []
    series = chart.get("series")
    if not isinstance(series, list):
        return []
    return [
        _bucket_value(bucket)
        for entry in series
        if isinstance(entry, dict) and isinstance(entry.get("data"), list)
        for bucket in entry["data"]
    ]


def _unit(payload: dict[str, Any]) -> str | None:
    total = payload.get("periodConsumption")
    if isinstance(total, dict) and isinstance(total.get("unit"), str):
        return total["unit"]
    chart = payload.get("periodChart")
    series = chart.get("series") if isinstance(chart, dict) else None
    if isinstance(series, list):
        for entry in series:
            if isinstance(entry, dict) and isinstance(entry.get("unit"), str):
                return entry["unit"]
    return None


def _text(payload: dict[str, Any], field: str) -> str | None:
    value = payload.get(field)
    return value if isinstance(value, str) and value else None


def parse_energy_history(payload: dict[str, Any]) -> dict[str, Any]:
    """Reduce one period's chart to the flat state keys the sensor reads."""
    if not isinstance(payload, dict):
        return {}

    readings = [value for value in _buckets(payload) if isinstance(value, (int, float))]
    state: dict[str, Any] = {
        # No reading at all stays None: 0.0 would read as a meter reset.
        "energy_period_total": round(sum(readings), 3) if readings else None,
        "energy_period_buckets": len(readings),
    }
    unit = _unit(payload)
    if unit is not None:
        state["energy_period_unit"] = unit
    for key, field in (
        ("energy_first_measurement_at", "firstMeasurementDate"),
        ("energy_last_measurement_at", "lastMeasurementDate"),
    ):
        value = _text(payload, field)
        if value is not None:
            state[key] = value
    return state
