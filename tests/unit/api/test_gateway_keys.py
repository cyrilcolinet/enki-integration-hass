"""Unit tests for mobile-config gateway key parsing."""

from __future__ import annotations

from enki.api.gateway_keys import GatewayKeyStore, parse_mobile_config_keys


def test_parse_mobile_config_service_api_key_pairs() -> None:
    payload = {
        "gateways": [
            {
                "service": "api-enki-heating-prod",
                "apiKey": "a" * 32,
            },
            {
                "microService": "api-enki-rolling-prod",
                "gatewayApiKey": "b" * 32,
            },
        ]
    }
    mapped = parse_mobile_config_keys(payload)
    assert mapped["ENKI_HEATING_API_KEY"] == "a" * 32
    assert mapped["ENKI_ACCESS_MOTORIZATION_API_KEY"] == "b" * 32


def test_parse_mobile_config_slug_as_dict_key() -> None:
    payload = {
        "api-enki-water-leak-detector-prod": "c" * 32,
    }
    mapped = parse_mobile_config_keys(payload)
    assert mapped["ENKI_WATER_SENSOR_API_KEY"] == "c" * 32


def test_parse_mobile_config_legacy_water_sensor_slug() -> None:
    payload = {
        "services": [
            {
                "slug": "api-enki-water-sensor-prod",
                "apiKey": "d" * 32,
            }
        ]
    }
    mapped = parse_mobile_config_keys(payload)
    assert mapped["ENKI_WATER_SENSOR_API_KEY"] == "d" * 32


def test_gateway_key_store_applies_to_const(monkeypatch) -> None:
    import enki.gateway_keys_data as keys_module

    monkeypatch.setattr(keys_module, "ENKI_HEATING_API_KEY", "")
    store = GatewayKeyStore()
    store.reload_from_const()
    payload = {"api-enki-heating-prod": "e" * 32}
    applied = store.apply_mobile_config(payload)
    assert applied["ENKI_HEATING_API_KEY"] == "e" * 32
    assert keys_module.ENKI_HEATING_API_KEY == "e" * 32
    assert store.get_transport_key("heating") == "e" * 32


def test_gateway_key_store_does_not_override_filled_const(monkeypatch) -> None:
    import enki.gateway_keys_data as keys_module

    monkeypatch.setattr(keys_module, "ENKI_HOME_API_KEY", "existing-home-key-0123456789012")
    store = GatewayKeyStore()
    store.reload_from_const()
    payload = {"api-enki-home-prod": "f" * 32}
    store.apply_mobile_config(payload)
    assert keys_module.ENKI_HOME_API_KEY == "existing-home-key-0123456789012"


def test_wired_fan_and_power_keys_match_live_traffic() -> None:
    """Regression: APK 2.25.1 extractor misassigned power/airflow (#45)."""
    import enki.gateway_keys_data as keys_module

    store = GatewayKeyStore()
    assert store.get_transport_key("airflow") == "hder4GeBrdbzQlV2R22dm2a9pbfTTHPj"
    assert store.get_transport_key("power") == "DZ9MSuTT7sQxJWxxkBokAGvIt57qVl9N"
    assert keys_module.ENKI_LIGHTS_API_KEY == "3OVsNulRsUXfr7Hze54OHx8l6qDu2UcE"
