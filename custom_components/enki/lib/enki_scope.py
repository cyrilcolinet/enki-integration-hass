"""Which devices belong in the Enki cloud integration vs Zigbee2MQTT / ZHA."""

from __future__ import annotations

# Marques de l'écosystème Enki / Leroy Merlin (catalogue officiel).
# Beaucoup utilisent Zigbee en radio — ce n'est pas un critère d'exclusion.
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

# Types référentiel réservés au catalogue Enki (fabricant parfois absent côté API).
_ENKI_NATIVE_DEVICE_TYPES = frozenset(
    {
        "access_and_motorizations",
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
