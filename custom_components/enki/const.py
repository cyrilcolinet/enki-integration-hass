"""Constants for the Enki Home Assistant integration."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "enki"
NAME = "Enki"

CONF_SCAN_INTERVAL = "scan_interval"
CONF_TELEMETRY = "telemetry"
CONF_TELEMETRY_ONBOARDING = "telemetry_onboarding_shown"
# An account that signs in with Google or Apple has no password in the Enki realm,
# so its entry stores the refresh token as its credential instead (#325).
CONF_REFRESH_TOKEN = "refresh_token"
CONF_AUTH_PROVIDER = "auth_provider"

DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 10
MAX_SCAN_INTERVAL = 300

ENKI_OIDC_URL = "https://keycloak-prod.iot.leroymerlin.fr/realms/enki/protocol/openid-connect/token"
# Spelled out rather than derived from the token URL: both appear verbatim in the
# app, and deriving one from the other breaks quietly when a realm moves.
ENKI_OIDC_AUTH_URL = (
    "https://keycloak-prod.iot.leroymerlin.fr/realms/enki/protocol/openid-connect/auth"
)
ENKI_OIDC_CLIENT_ID = "enki-front"
# Where Keycloak sends the authorization code back. It is the mobile app's own
# deep link, registered in its manifest, and the only redirect the client takes.
ENKI_SSO_REDIRECT_URI = "enki://oauth/callback"
# `kc_idp_hint` on the authorize call, `provider_type` on the token exchange
# the app sends the lowercase name to one and the uppercase to the other (APK sfn).
SSO_PROVIDERS = {"google": "GOOGLE", "apple": "APPLE"}
ENKI_BASE_URL = "https://enki.api.devportal.adeo.cloud"

# Mobile app version used for gateway key extraction and HTTP impersonation.
ENKI_APP_VERSION = "2.26.3"
ENKI_USER_AGENT = f"Enki/{ENKI_APP_VERSION} (iPhone; iOS 18.0; Scale/3.00) Enki"


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
DEVICE_TYPE_VIDEOPHONES = "videophones"
DEVICE_TYPE_BOILER = "boiler"

# Sent as ?version= on the referentiel endpoint. A stale value returns an older,
# thinner capability set, keep it in step with the Enki app (2.26.3 sends 2.26.0).
REFERENTIEL_VERSION = "2.26.0"

FAN_SPEED_MIN = 1
FAN_SPEED_MAX = 6
ORDERED_FAN_SPEEDS = list(range(FAN_SPEED_MIN, FAN_SPEED_MAX + 1))

# Device profile sharing (opt-in). See docs/TELEMETRY.md.
TELEMETRY_GITHUB_REPO = "cyrilcolinet/enki-integration-hass"
