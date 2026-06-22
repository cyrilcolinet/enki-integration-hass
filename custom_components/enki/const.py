"""Constants for the Enki Home Assistant integration."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "enki"
NAME = "Enki"

CONF_SCAN_INTERVAL = "scan_interval"
CONF_TELEMETRY = "telemetry"

DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 10
MAX_SCAN_INTERVAL = 300

ENKI_OIDC_URL = "https://keycloak-prod.iot.leroymerlin.fr/realms/enki/protocol/openid-connect/token"
ENKI_BASE_URL = "https://enki.api.devportal.adeo.cloud"

# Gateway API keys (reverse-engineered from the Enki mobile app traffic).
# They may change when the app updates — see docs/API.md.
ENKI_HOME_API_KEY = "FULsxyI3x1f7MtLVOsP6V1DeAPmBQJCB"
ENKI_BFF_API_KEY = "hTFx7uzWpn2JRpeylsZRRK00hd7lxH3V"
ENKI_NODE_API_KEY = "aMmVpSOOWjEGz7f99caaPdUPMNoAIabj"
ENKI_REFERENTIEL_API_KEY = "MiodFO5my5FR5U1aWHfiGMgFSuL6eOmB"
ENKI_LIGHTS_API_KEY = "9UO9gla4t7rJqkYgJNS0PzGFIWh9t9B5"
ENKI_POWER_API_KEY = "HaFUU0N7dDj1jIgMnrMAEdTWgKCH3Fhs"
ENKI_AIRFLOW_API_KEY = "6ex5WlshxPnnNsqHGoyN5u6dCIIdbFYG"

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

REFERENTIEL_VERSION = "2.23.0"

FAN_SPEED_MIN = 1
FAN_SPEED_MAX = 6
ORDERED_FAN_SPEEDS = list(range(FAN_SPEED_MIN, FAN_SPEED_MAX + 1))

# Device profile sharing (opt-in). See docs/TELEMETRY.md.
TELEMETRY_GITHUB_REPO = "cyrilcolinet/enki-integration-hass"
TELEMETRY_ISSUE_LABELS = ("device-telemetry", "enhancement")
