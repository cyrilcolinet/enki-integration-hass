"""Shipped gateway keys resolve by transport alias."""

from __future__ import annotations

from enki.api.gateway_keys import transport_key


def test_wired_fan_and_power_keys_match_live_traffic() -> None:
    """Regression: APK 2.25.1 extractor misassigned power/airflow (#45)."""
    import enki.gateway_keys_data as keys_module

    assert transport_key("airflow") == "hder4GeBrdbzQlV2R22dm2a9pbfTTHPj"
    assert transport_key("power") == "DZ9MSuTT7sQxJWxxkBokAGvIt57qVl9N"
    assert keys_module.ENKI_LIGHTS_API_KEY == "3OVsNulRsUXfr7Hze54OHx8l6qDu2UcE"


def test_unknown_transport_has_no_key() -> None:
    assert transport_key("no-such-service") is None


def test_empty_shipped_key_reads_as_missing(monkeypatch) -> None:
    import enki.gateway_keys_data as keys_module

    monkeypatch.setattr(keys_module, "ENKI_HEATING_API_KEY", "")
    assert transport_key("heating") is None
