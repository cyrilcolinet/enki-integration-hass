# Device profile sharing (opt-in)

Helps support new Enki hardware **without automatic uploads** and **without secrets** in the integration.

## For users

### Diagnostics (no opt-in)

**Settings** → **Devices & services** → **Enki** → ⋮ menu → **Download diagnostics**

Local JSON export: anonymized profiles (type, manufacturer, capabilities). Attach to an [issue](https://github.com/cyrilcolinet/enki-integration-hass/issues/new) if needed.

### Opt-in (notification + pre-filled issue)

**Enki** → **Configure** → enable:

> Notify me about new devices (GitHub issue link)

When a **new** profile is detected (unique fingerprint) **and support is missing** (unsupported device or unimplemented capabilities):

1. A **persistent notification** appears in Home Assistant
2. The link opens GitHub with a **pre-filled** title and body
3. You **confirm** issue creation — nothing is sent without that click

**Never included:** email, password, homeId, nodeId, room names.

**No notification** if the device is already fully supported (e.g. another Inspire fan variant already covered).

**Also skipped (no notification, no GitHub link):** Enki hub / gateway profiles, and third-party Zigbee (Sonoff, Tuya, Aqara, …) that the integration deliberately ignores at discovery.

### Enriched export

Diagnostics and GitHub prefill now include extra **English** context when available:

| Field | Meaning |
|-------|---------|
| `ha_platforms` | HA platforms that would be created (`climate`, `select`, …) |
| `uncovered_capabilities` | Referentiel capabilities not implemented yet |
| `api_read_errors` | Cloud read failures from the **last poll** (`heating/check_pilot_wire_state → HTTP 500`) — no node/home ids |
| `telemetry_reason` | Why a notification was suggested |

This helps reproduce cases like “entities exist but stay unavailable” without uploading full logs.

## For contributors

Local script (account required):

```bash
python3 scripts/discover_devices.py <email> <password> --export
```

See [DEVELOPMENT.md](DEVELOPMENT.md) for tests.

## Technical

- Deduplication by SHA256 fingerprint (local HA storage)
- URL: `github.com/.../issues/new?title=...&body=...&labels=device%20telemetry,unsupported`
- Three labels per issue: `device telemetry` + reason + device family (`motorization`, `climate`, …). Brand and model stay in the title/body. Sync repo labels with `scripts/sync_github_labels.sh` (also removes retired labels).
- No token, no `repository_dispatch`
