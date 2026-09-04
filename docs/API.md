# Enki cloud API — engineering notes

This integration talks to the **unofficial** Enki REST API used by the Leroy Merlin / Adeo mobile app. There is no public developer portal for end users; behaviour was inferred from network traffic and [CyrilP/hass-enki-component](https://github.com/CyrilP/hass-enki-component).

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

Gateway keys are bundled in `custom_components/enki/const.py`. They are **embedded in the Enki mobile APK** (one key per micro-service), not fetched from a central API. Refresh them after an app update with `scripts/extract_gateway_keys.py` (see [DEVELOPMENT.md](DEVELOPMENT.md)). Requests failing with `401`/`403` usually mean outdated credentials or gateway keys — Home Assistant shows a **persistent notification** with guidance.

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
    HA->>Ref: GET /v1/devices/{deviceId}?version={REFERENTIEL_VERSION}
```

`REFERENTIEL_VERSION` is defined in [`const.py`](../custom_components/enki/const.py) and tracks the value the Enki app sends — a stale value returns a thinner capability set.

## Supported device types (this integration)

Detection is **capability-based** (referentiel metadata + BFF dashboard), not limited to a fixed list of model names.

| Referentiel / BFF type | HA platforms | Backend services |
|------------------------|--------------|------------------|
| `ceiling_fans` (+ fan capabilities) | `fan` + `light` | `api-enki-airflow-prod`, `api-enki-lighting-prod`, `api-enki-power-prod` |
| `lights` (+ light capabilities) | `light` | `api-enki-lighting-prod` |
| Switches / outlets (Edisio, …) | `light` (ON/OFF) | `api-enki-power-prod` (`switch-electrical-power`) |
| `inverters` (Envertech-Lexman solar) | `sensor` (power W) | BFF dashboard `description.value` |
| `access_and_motorizations` (Evology, Nodon, …) | `cover` (beta) | `api-enki-rolling-prod` — `shutter/{nodeId}/…` (key in `const.py`) |
| `sensors` (motion, contact, temperature, …) | `binary_sensor`, `sensor`, `switch`, `number` | presence, contact, temperature-humidity, battery-health, siren micro-services |
| Heating / pilot wire / thermostat | `select`, `climate`, `switch`, `number`, `binary_sensor` | `api-enki-thermostat-prod` (setpoint, pilot wire, window/presence, offset, child-lock, preheating), `api-enki-presence-detector-prod` (occupancy); `ENKI_HEATING_API_KEY`/`ENKI_THERMOSTAT_API_KEY` in `const.py`; if cleared, reads are skipped silently and writes raise an error |
| Water leak sensors | `binary_sensor`, `sensor` (battery) | `api-enki-water-leak-detector-prod` + `api-enki-battery-health-prod` — keys in `const.py`; same fallback if a key is missing |
| `cameras` (Lexman / Meari) | `camera`, `sensor`, `binary_sensor` | `api-enki-lexman-camera-prod` (`/events?nodeId=…`) for events; config controls on `api-enki-lexman-camera-meari-prod`; **no live video** (TUTK Kalay P2P native SDK) |

Sensor capability paths: `GET/POST …/v1/sensors/{node_id}/{kebab-case-capability}` (siren uses `/v1/siren/`).

Multi-endpoint lights (several circuits on one node) create one HA light entity per BFF `mainChangeCapability` endpoint.

### Ceiling fan (Inspire Siroco+, ESDK)

State is split across services:

| Field | Endpoint | Notes |
|-------|----------|-------|
| `fan_speed` | `GET …/check-fan-speed` | `0` = off, `1–6` = speed levels |
| `airflow_mode` | `GET …/check-airflow-mode` | `MANUAL`, `BREEZE` |
| `airflow_rotation` | `GET …/check-fan-rotation-direction` | `CLOCKWISE` / `COUNTERCLOCKWISE` when supported |
| Light on/off (`light_power`) | `api-enki-lighting-prod` | `check-light-state` → `lastReportedValue.power` |
| Light `brightness`, `colorTemperature` | `api-enki-lighting-prod` | `change-light-state` (full `lastReportedValue` payload) |

Commands:

- `POST …/change-fan-speed` — body `{"value": <0-6>}`, expect `202`
- `POST …/change-airflow-mode` — body `{"value": "MANUAL"|"BREEZE"}`, expect `202` or `204` (mode brise)
- `POST …/change-fan-rotation-direction` — body `{"value": "CLOCKWISE"|"COUNTERCLOCKWISE"}`, expect `202` or `204` (Inspire; enables `fan.set_direction` in HA)
- `POST …/change-light-state` — full `lastReportedValue` object; `power` ON/OFF for the fan light kit
- `POST …/switch-electrical-power?endpoints=1|2` — fan motor only in practice; light kit uses lighting `power`

Fan motor and light kit are **independent** (turning the fan on does not switch the light on).

### Roller shutters (Evology SIN2RS1, …) — beta

**Base URL:** `https://enki.api.devportal.adeo.cloud/api-enki-rolling-prod/v1/shutter/{nodeId}/`

| Field | Endpoint | Notes |
|-------|----------|-------|
| `shutter_position` | `GET …/check-shutter-position` | `0–100` (% open) |
| `shutter_opening` | `GET …/check-shutter-opening` | `OPEN` / `CLOSED` |
| `roller_shutter_state` | `GET …/check-roller-shutter-state` | e.g. `OPENING` / `CLOSING` / `STOPPED` |
| `roller_shutter_mode` | `GET …/check-roller-shutter-mode` | `NORMAL` / `INVERTED` |

Commands:

- `POST …/change-shutter-position` — body `{"value": <0-100>}`, expect `202` or `204`
- `POST …/stop-change-shutter-position` — stop mid-travel (no body)
- `POST …/change-roller-shutter-mode` — body `{"value": "NORMAL"|"INVERTED"}`
- `POST …/execute-preset` — body `{"value": "<preset>"}` when referentiel lists presets
- `POST …/switch-roller-shutter` — body `{"value": "OPEN"|"CLOSED"}` for RTS motorizations

RTS models (Somfy, `tr_device_rts_roller_shutter_motorization_label`) expose only
`switch_roller_shutter` and `stop_change_shutter_position`: one-way radio, so no
position and no `check-*` feedback. The cover entity reports `assumed_state`.
Path segment unconfirmed against real hardware — see #96.

Gateway key: `ENKI_ACCESS_MOTORIZATION_API_KEY` in `const.py`. Legacy path `api-enki-access-and-motorizations-prod` is obsolete. See [DEVELOPMENT.md](DEVELOPMENT.md#capturing-a-gateway-key-with-mitmproxy-fallback) for validating a key with mitmproxy.

### Dry-contact gate / garage receiver (Lexman 83424576, Nodon SIN-4-1-20)

**Referentiel capability:** `power_on_with_timer` only (Mpulse mode — timed impulse, no state read).

**HA entity:** `button` “Trigger”

| Command | Endpoint | Notes |
|---------|----------|-------|
| Impulse | `POST …/power-on-with-timer` | **No body** — `api-enki-power-prod` (APK `mbj.e`) |

Gateway key: `ENKI_POWER_API_KEY` (same as outlets). Distinct from roller shutters (`api-enki-rolling-prod`).

### Standard lights (Eglo V-Link, Lexman, etc.)

| Capability | Parameter | Wire format |
|------------|-----------|-------------|
| On/off | `power` | `"ON"` / `"OFF"` |
| Brightness | `brightness` | float, device-specific max (often `100`) |
| Colour temperature | `colorTemperature` | `"T3500K"` style strings |
| Hue (RGB bulbs) | `hue` | normalized float `0.0`–`1.0` (HA hue ÷ 360) |
| Saturation (RGB bulbs) | `saturation` | normalized float `0.0`–`1.0` (HA sat ÷ 100) |

RGB bulbs (e.g. Lexman) advertise `change_hue` + `change_saturation` and map to
HA's `ColorMode.HS`. When the bulb also advertises `change_color_temperature`,
the integration exposes both `hs` and `color_temp`; the reported `colorMode`
field (`hs` vs `ct`) indicates which mode is active.

## Heating and water sensors (manifest ≥ 1.5.0)

**Heating base URL:** `https://enki.api.devportal.adeo.cloud/api-enki-heating-prod/v1/heating/{nodeId}/`

| Capability | Platform | Notes |
|------------|----------|-------|
| `check_pilot_wire_state` / `switch_pilot_wire_mode` | `select` | COMFORT, ECO, OFF, … |
| `check_thermostat_target_temperature` / `change_thermostat_target_temperature` | `climate` | °C setpoint |
| `check_thermostat_running_state` | `climate` | HEAT / IDLE → `hvac_action` |
| `check_window_open_detection` | `binary_sensor` | WINDOW_OPEN / NO_WINDOW_OPEN |
| `check_occupancy` | `binary_sensor` | OCCUPIED / UNOCCUPIED |

**Water leak base URL:** `https://enki.api.devportal.adeo.cloud/api-enki-water-leak-detector-prod/v1/detectors/{nodeId}/`

| Capability | Platform |
|------------|----------|
| `check-water-sensor-state` | `binary_sensor` (moisture) |

Gateway keys (`ENKI_HEATING_API_KEY`, `ENKI_WATER_SENSOR_API_KEY`, …) are in `const.py`. Refresh with `scripts/extract_gateway_keys.py` after an app update — see [DEVELOPMENT.md](DEVELOPMENT.md). If a key is cleared, reads are skipped silently and writes raise a clear error.

## Operational notifications

Home Assistant shows **persistent notifications** (French or English) when:

| Situation | What you see |
|-----------|----------------|
| Invalid Enki credentials | Link to reconfigure the integration |
| HTTP 403 (gateway key) | Hint to refresh keys from the APK |
| Network / cloud unreachable | Check Internet and `enki` logs |
| Enki cloud maintenance (`mobile-config`) | Shown while `maintenance: true`; cleared on the next poll when it ends |

Notifications clear automatically after the next successful poll (maintenance is re-checked every poll; auth/gateway/connection clear after a successful device poll).

## Scenarios (api-enki-scenario-prod)

Base: `https://enki.api.devportal.adeo.cloud/api-enki-scenario-prod/v1/scenarios`

| Method | Path | Notes |
|--------|------|-------|
| GET | `/scenarios?homeId={homeId}` | List (`items[]` with `id`, `label`, `enabled`, `status`) |
| POST | `/scenarios/{scenarioId}/activate` | Run scenario (`homeId` header) |

Gateway key: `ENKI_SCENARIO_API_KEY` in `gateway_keys_data.py`.

## Instant consumption (api-enki-consumption-prod)

Base: `https://enki.api.devportal.adeo.cloud/api-enki-consumption-prod/v1/consumption`

| Method | Path | Notes |
|--------|------|-------|
| GET | `/{nodeId}/check-instant-consumption?homeId={homeId}` | `lastReportedValue` (W), `unit` |

Used for Edisio / Equation devices with `check_electrical_consumption` in referentiel. Gateway key: `ENKI_CONSUMPTION_API_KEY`.

## Lexman cameras (api-enki-lexman-camera-meari-prod)

Base: `https://enki.api.devportal.adeo.cloud/api-enki-lexman-camera-meari-prod/v1/`
Gateway key: `ENKI_LEXMAN_CAMERA_MEARI_API_KEY`. Headers: `Authorization`, `X-Gateway-APIKey`, `homeId`.

Two camera generations coexist:

| Generation | Backing service | Live video |
|------------|-----------------|------------|
| meari (solar / outdoor, 2K…) | `api-enki-lexman-camera-meari-prod` | WebRTC over the meari signaling WebSocket (documented below) |
| earlier Lexman cameras | `api-enki-lexman-camera-prod` | TUTK Kalay P2P — node payload carries `p2pId` / `p2pAuthKey` / `p2pPassword`, and the app drives them through the native `com.tutk.IOTC` SDK |

Only the meari generation is reachable without a native SDK. A camera that is not in the
meari backend answers `404 NOT_FOUND` on **every** meari route — including all `change-*`
writes — while an unknown enum value answers `400 BAD_REQUEST` first (values are validated
before the device lookup). `check-camera-status` is therefore the cheapest way to tell a
"wrong value" from a "wrong service".

### REST

| Method | Path | Notes |
|--------|------|-------|
| GET | `camera/{nodeId}/check-camera-status` | battery, wifi, sd card, firmware and every current setting |
| GET | `camera/{nodeId}/check-camera-events?day=…` | event list (thumbnails) |
| GET | `camera/{nodeId}/check-camera-connect-wss` | signaling credentials (see below) |
| GET | `camera/{nodeId}/check-detection-zone` / `check-firmware-update-status` | |
| POST | `camera/{nodeId}/wake-up` | wakes a dormant (battery) camera |
| POST | `camera/{nodeId}/change-night-vision-mode` | `{"value": "SMART" \| "FULL_COLOR" \| "BLACK_AND_WHITE"}` |
| POST | `camera/{nodeId}/change-motion-detection-mode` | `{"value": "ON" \| "OFF" \| "HUMAN_FORM"}` |
| POST | `camera/{nodeId}/change-indicator-light-mode` | `{"value": "ON" \| "OFF"}` |
| POST | `camera/{nodeId}/change-flip-screen-mode` | `{"value": "FLIP_HORIZONTAL" \| "FLIP_VERTICAL" \| "FLIP_ALL" \| …}` |
| POST | `camera/{nodeId}/change-motion-detection-sensitivity-level` | `{"value": <int>}` |
| POST | `camera/{nodeId}/change-humanoid-detection-sensitivity-level` | `{"value": <int>}` |
| POST | `camera/{nodeId}/change-light-mode`, `change-recording-duration`, `change-detection-zone` | |
| POST | `camera/{nodeId}/format-sd-card`, `update-firmware-version` | destructive — not exposed |

### Live video — meari WebRTC signaling

`check-camera-connect-wss` returns `webSocketServerUrl`, `accessId`, `signature`, `token`,
`expires`, `callee`, `deviceCode`. Open that WebSocket (no extra header) and exchange JSON
frames; every frame shares the same envelope:

```json
{"sid": "<uuid uppercase>", "method": "<option|offer|answer|candidate|settings>",
 "action": "req", "cmd": "mts", "params": { }}
```

`caller` is a client id (16 hex chars), `callee` and `devicecode` come from the REST call.

1. **Authenticate** — `method: "option"`, with `"auth": {accessId, signature, token}` and
   `params: {caller, callee, devicecode, expires, continent: "Europe", country: "France"}`.
   The reply (`method: "option"`) carries the relay: `coturn_host`, `coturn_ip`,
   `coturn_port`, `username`, `pwd`.
2. **Offer** — `method: "offer"`, `params: {caller, callee, devicecode, sdp,
   settings: {method: "preview"}}`. The app offers audio `sendrecv` (two-way talk) plus
   video `recvonly`, ICE **relay-only** through that coturn server.
3. **Answer** — inbound `method: "answer"`, `params.sdp`.
4. **ICE** — `method: "candidate"` both ways, `params: {caller, callee,
   candidate: {candidate, sdpMid, sdpMLineIndex}}`.
5. **Start the stream** — `method: "settings"`, `params: {caller, callee,
   settings: {sid, method: "preview", streams: [{channel: 0, stream: 1, stop: 0}]}}`.
   Recorded playback uses the same shape with `method: "playback"`.

Errors arrive as `{sid, method, action, cmd, errid, errstr}` (plus `desc` when the camera is
asleep). `errstr` values `device dormancy`, `device awaken timeout`, `device offline` and
`session not found` mean "wake the camera and retry", not "wrong request".

`scripts/probe_camera_stream.py` replays the whole sequence and prints, per camera, whether
it is a meari device, whether signaling authenticates and whether the camera answers an SDP
offer.

## Future device families

The Enki app also controls alarms via other microservices. Use `scripts/discover_devices.py` to dump unknown `deviceType` values from your account before adding new platforms.

## References

- [CyrilP/hass-enki-component](https://github.com/CyrilP/hass-enki-component) (lights)
- Product docs: [Enki support — Inspire](https://support.enki-home.com/)
