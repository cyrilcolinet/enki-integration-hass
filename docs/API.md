# Enki cloud API — engineering notes

This integration talks to the **unofficial** Enki REST API used by the Leroy Merlin / Adeo mobile app. There is no public developer portal for end users; behaviour was inferred from network traffic and existing community work.

## Authentication

| Item | Value |
|------|-------|
| OIDC token URL | `https://keycloak-prod.iot.leroymerlin.fr/realms/enki/protocol/openid-connect/token` |
| Grant | `password` (resource owner) |
| Client ID | `enki-front` |
| API gateway | `https://enki.api.devportal.adeo.cloud` |

Every microservice call sends:

- `Authorization: Bearer <access_token>`
- `X-Gateway-APIKey: <service-specific key>`
- `homeId: <uuid>` when the node belongs to a home

Gateway keys are bundled in `custom_components/enki/const.py`. They can change when the mobile app updates; capture fresh keys with mitmproxy if requests start failing with `401`/`403`.

## Discovery flow

```mermaid
sequenceDiagram
    participant HA as Home Assistant
    participant Auth as Keycloak
    participant Home as api-enki-home-prod
    participant BFF as api-enki-mobile-bff-prod
    participant Ref as api-enki-referentiel-agg-prod
    participant Node as api-enki-node-agg-prod

    HA->>Auth: POST /token (password grant)
    Auth-->>HA: access_token
    HA->>Home: GET /v1/homes
    Home-->>HA: home ids
    HA->>BFF: GET /dashboard/homes/{id}?hasGroups=true
    BFF-->>HA: sections / items (nodeId, deviceId, deviceType)
    HA->>Node: GET /v1/nodes/{nodeId}
    HA->>Ref: GET /v1/devices/{deviceId}?version=2.23.0
```

## Supported device types (this integration)

| BFF / referentiel type | HA platforms | Backend services |
|------------------------|--------------|------------------|
| `ceiling_fans` | `fan` + `light` | `api-enki-airflow-prod`, `api-enki-lighting-prod`, `api-enki-power-prod` |
| `lights` | `light` | `api-enki-lighting-prod` |

### Ceiling fan (Inspire Siroco+, ESDK)

State is split across services:

| Field | Endpoint | Notes |
|-------|----------|-------|
| `fan_speed` | `GET …/check-fan-speed` | `0` = off, `1–6` = speed levels |
| `airflow_mode` | `GET …/check-airflow-mode` | `MANUAL`, `BREEZE` |
| Light on/off (`light_power`) | `api-enki-power-prod` endpoint `2` | `check-electrical-power` / `switch-electrical-power` |
| Light `brightness`, `colorTemperature` | `api-enki-lighting-prod` | `change-light-state` (lighting `power` field is not the relay) |

Commands:

- `POST …/change-fan-speed` — body `{"value": <0-6>}`, expect `202`
- `POST …/change-light-state` — full `lastReportedValue` object, expect `202`
- `POST …/switch-electrical-power?endpoints=1|2` — optional direct power switch per endpoint

Fan motor and light kit are **independent** (turning the fan on does not switch the light on).

### Standard lights (Eglo V-Link, Lexman, etc.)

| Capability | Parameter | Wire format |
|------------|-----------|-------------|
| On/off | `power` | `"ON"` / `"OFF"` |
| Brightness | `brightness` | float, device-specific max (often `100`) |
| Colour temperature | `colorTemperature` | `"T3500K"` style strings |

## Future device families (not implemented yet)

The Enki app also controls heating, shutters, sockets, and alarms via other microservices (`api-enki-heating-prod`, motorisation APIs, etc.). Use `scripts/discover_devices.py` to dump unknown `deviceType` values from your account before adding new platforms.

## References

- Fork base: [CyrilP/hass-enki-component](https://github.com/CyrilP/hass-enki-component) (lights)
- Fan / airflow research: community reverse engineering of ESDK ceiling fans
- Product docs: [Enki support — Inspire](https://support.enki-home.com/)
