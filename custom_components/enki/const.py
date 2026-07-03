"""Constants for the Enki Home Assistant integration."""

from logging import Logger, getLogger

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

# Gateway API keys (reverse-engineered from the Enki mobile app traffic).
# They may change when the app updates — see docs/API.md.
ENKI_HOME_API_KEY = "FULsxyI3x1f7MtLVOsP6V1DeAPmBQJCB"
ENKI_BFF_API_KEY = "hTFx7uzWpn2JRpeylsZRRK00hd7lxH3V"
ENKI_NODE_API_KEY = "aMmVpSOOWjEGz7f99caaPdUPMNoAIabj"
ENKI_REFERENTIEL_API_KEY = "MiodFO5my5FR5U1aWHfiGMgFSuL6eOmB"
ENKI_LIGHTS_API_KEY = "9UO9gla4t7rJqkYgJNS0PzGFIWh9t9B5"
ENKI_POWER_API_KEY = "HaFUU0N7dDj1jIgMnrMAEdTWgKCH3Fhs"
ENKI_AIRFLOW_API_KEY = "6ex5WlshxPnnNsqHGoyN5u6dCIIdbFYG"
ENKI_TEMPERATURE_HUMIDITY_API_KEY = "V6mMQHQAGNNVwjhuBXlVhQNYzZOxARJ3"
ENKI_BATTERY_HEALTH_API_KEY = "WcydJ76nQUo8AiwkV05kn3kiNyM31b3M"
ENKI_PRESENCE_DETECTOR_API_KEY = "bHEwVewJI2aNUiDX6KXt9ErzazfkarYp"
ENKI_CONTACT_SENSOR_API_KEY = "B2K2xlXnpVGEPylKq0Xn79LRuBG60w30"
ENKI_SIREN_API_KEY = "9jDuso0Im0tTAvj6Ecf0B1HWENeOykZa"

# api-enki-heating-prod (fil pilote, radiateurs Noirot/ACOVA, …).
# Capture X-Gateway-APIKey when controlling heating in the Enki app — see docs/API.md.
ENKI_HEATING_API_KEY = ""

# api-enki-water-sensor-prod (détecteurs de fuite Lexman, …).
ENKI_WATER_SENSOR_API_KEY = ""

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

# api-enki-access-motorizations-prod (Evology/Nodon roller shutters, …).
# Capture with mitmproxy when controlling a shutter in the Enki app (see docs/API.md).
ENKI_ACCESS_MOTORIZATION_API_KEY = ""

REFERENTIEL_VERSION = "2.23.0"

FAN_SPEED_MIN = 1
FAN_SPEED_MAX = 6
ORDERED_FAN_SPEEDS = list(range(FAN_SPEED_MIN, FAN_SPEED_MAX + 1))

# Device profile sharing (opt-in). See docs/TELEMETRY.md.
TELEMETRY_GITHUB_REPO = "cyrilcolinet/enki-integration-hass"
TELEMETRY_ISSUE_LABELS = ("device-telemetry", "enhancement")
