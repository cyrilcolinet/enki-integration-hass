"""Which devices belong in the Enki cloud integration vs Zigbee2MQTT / ZHA."""

from __future__ import annotations

# Enki / Leroy Merlin ecosystem brands (official catalogue).
# Many use Zigbee radio — that is not an exclusion criterion.
_ENKI_ECOSYSTEM_MANUFACTURERS = frozenset(
    {
        "adeo",
        "acova",
        "edisio",
        "eglo",
        "enki",
        "envertech",
        "equation",
        "evology",
        "inspire",
        "lexman",
        "nodon",
        "noirot",
        "sedea",
    }
)

# Referentiel types reserved for the Enki catalogue (manufacturer sometimes missing from API).
# `boiler` is the Enki "chauffe-eau piloté" module: the app re-types a plain Enki relay to
# this profile when it is wired to a water heater, and the referentiel then serves it with an
# empty manufacturer. It is native Enki (dedicated api-enki-boiler-system-prod service), not
# third-party Zigbee — see EnkiCapabilityProfile.is_boiler_switch.
_ENKI_NATIVE_DEVICE_TYPES = frozenset(
    {
        "access_and_motorizations",
        "boiler",
        "ceiling_fans",
        "inverters",
    }
)


def _normalize(value: str) -> str:
    return value.strip().lower().replace("_", " ")


def _normalize_device_type(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def manufacturer_in_enki_ecosystem(manufacturer: str) -> bool:
    """True when the referentiel/BFF manufacturer is an Enki ecosystem brand."""
    normalized = _normalize(manufacturer)
    if not normalized:
        return False
    if normalized in _ENKI_ECOSYSTEM_MANUFACTURERS:
        return True
    return any(brand in normalized for brand in _ENKI_ECOSYSTEM_MANUFACTURERS)


def device_in_enki_scope(
    *,
    manufacturer: str | None,
    device_type: str | None,
) -> bool:
    """Return True only for Enki ecosystem devices (not third-party Zigbee on the box)."""
    if device_type and _normalize_device_type(device_type) in _ENKI_NATIVE_DEVICE_TYPES:
        return True
    if not manufacturer:
        return False
    return manufacturer_in_enki_ecosystem(manufacturer)
