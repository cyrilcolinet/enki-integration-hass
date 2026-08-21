"""Constants for the Enki Home Assistant integration."""

from logging import Logger, getLogger

from . import gateway_keys_data

LOGGER: Logger = getLogger(__package__)

DOMAIN = "enki"
NAME = "Enki"

CONF_SCAN_INTERVAL = "scan_interval"
CONF_TELEMETRY = "telemetry"
CONF_TELEMETRY_ONBOARDING = "telemetry_onboarding_shown"

DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 10
MAX_SCAN_INTERVAL = 300

ENKI_OIDC_URL = "https://keycloak-prod.iot.leroymerlin.fr/realms/enki/protocol/openid-connect/token"
ENKI_BASE_URL = "https://enki.api.devportal.adeo.cloud"

# Mobile app version used for gateway key extraction and HTTP impersonation.
ENKI_APP_VERSION = "2.25.1"
ENKI_USER_AGENT = f"Enki/{ENKI_APP_VERSION} (iPhone; iOS 18.0; Scale/3.00) Enki"


# Re-export gateway keys (defined in gateway_keys_data.py — do not duplicate here).
def __getattr__(name: str) -> str:
    if name.endswith("_API_KEY"):
        return getattr(gateway_keys_data, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


FAN_ENDPOINT = 1
LIGHT_ENDPOINT = 2

AIRFLOW_MODE_MANUAL = "MANUAL"
AIRFLOW_MODE_BREEZE = "BREEZE"

PRESET_MODE_MANUAL = "manual"
PRESET_MODE_BREEZE = "breeze"

# Blade rotation (api-enki-airflow-prod; check/change-fan-rotation-direction).
AIRFLOW_ROTATION_CLOCKWISE = "CLOCKWISE"
AIRFLOW_ROTATION_COUNTERCLOCKWISE = "COUNTERCLOCKWISE"

DIRECTION_FORWARD = "forward"
DIRECTION_REVERSE = "reverse"

DEVICE_TYPE_LIGHTS = "lights"
DEVICE_TYPE_FANS = "ceiling_fans"
DEVICE_TYPE_INVERTERS = "inverters"
DEVICE_TYPE_ACCESS_MOTORIZATION = "access_and_motorizations"
DEVICE_TYPE_SENSORS = "sensors"
DEVICE_TYPE_CAMERAS = "cameras"
DEVICE_TYPE_BOILER = "boiler"

# Sent as ?version= on the referentiel endpoint. A stale value returns an older,
# thinner capability set — keep it in step with the Enki app (2.26.3 sends 2.26.0).
REFERENTIEL_VERSION = "2.26.0"

FAN_SPEED_MIN = 1
FAN_SPEED_MAX = 6
ORDERED_FAN_SPEEDS = list(range(FAN_SPEED_MIN, FAN_SPEED_MAX + 1))

# Device profile sharing (opt-in). See docs/TELEMETRY.md.
TELEMETRY_GITHUB_REPO = "cyrilcolinet/enki-integration-hass"
