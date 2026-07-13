# Development

Technical documentation for contributing, testing, and releasing the integration.

## Prerequisites

- Python 3.12+
- Home Assistant 2024.12+ (for testing on a real instance)

```bash
git clone https://github.com/cyrilcolinet/enki-integration-hass.git
cd enki-integration-hass
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

## Unit tests

Without an Enki account or hardware:

```bash
pytest tests/unit -v
```

## Lint and format

```bash
ruff check .
ruff format --check .   # or ruff format . to fix
```

## Local scripts (outside Home Assistant)

Scripts in `scripts/` run **on your dev machine**, not inside the HA container. They talk directly to the Enki cloud API (or parse an APK). Home Assistant is not required — only Python 3 and `pip install -r requirements-dev.txt`.

| Script | Usage |
|--------|--------|
| `scripts/fetch_gateway_keys.py` | Verify login and read `mobile-config` `/settings` (not gateway keys) |
| `scripts/extract_gateway_keys.py` | Extract gateway keys from an APK (jadx + DI module); `--apply` updates `const.py` |
| `scripts/discover_devices.py` | Export anonymized device profiles from the account |

```bash
source .venv/bin/activate
python3 scripts/fetch_gateway_keys.py
python3 scripts/extract_gateway_keys.py path/to/enki.apk
python3 scripts/extract_gateway_keys.py path/to/enki.apk --apply --update-known
python3 scripts/discover_devices.py your@email.com 'password'
```

Gateway keys are embedded in the APK (one per micro-service). Run `extract_gateway_keys.py --apply` after each Enki app update.

## Repository language

- **Python code** (comments, docstrings): English — see [CONTRIBUTING.md](../CONTRIBUTING.md#language)
- **Markdown** (`docs/`, `README.md`, …): English
- **Home Assistant UI** (`strings.json`, translations): French and English via translation files

## Real API tests (optional)

1. Copy `.env.example` to `.env`
2. Fill in `ENKI_USERNAME`, `ENKI_PASSWORD`, `ENKI_HOME_ID`, `ENKI_NODE_ID`
3. Retrieve IDs with:

```bash
python3 scripts/discover_devices.py <email> <password>
```

4. Run tests:

```bash
set -a && source .env && set +a
pytest tests/integration -v -m integration
```

Live tests restore the fan and light to off at the end of the session.

## Testing in Home Assistant

Copy `custom_components/enki/` into your dev instance `config/custom_components/`, restart, add the integration via the UI.

## CI

Single workflow: [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)

Triggered on every push to `main` and every pull request:

| Job | Role |
|-----|------|
| Lint | Ruff check + format |
| Unit tests | `pytest tests/unit` |
| Hassfest | HA integration validation |
| HACS | Repository validation (default store eligibility) |

Live tests: only via `workflow_dispatch` with `ENKI_*` secrets configured on the repo.

## GitHub labels

Workflow triage labels (`next release`, `beta`, `stale`, …) and telemetry labels are defined in [`scripts/github_labels.py`](../scripts/github_labels.py). Sync them to the repository:

```bash
./scripts/sync_github_labels.sh
```

| Label | Use |
|-------|-----|
| `next release` | Planned for the upcoming tag |
| `release blocker` | Must ship before the next release |
| `beta` | Experimental feature or device; needs testers |
| `stale` | No recent activity (also applied weekly by CI) |
| `blocked` | Waiting on hardware, upstream API, or third party |
| `needs info` | Waiting on reporter feedback |
| `confirmed` | Reproduced or accepted by a maintainer |
| `regression` | Worked before, broken recently |
| `breaking change` | Intentional breaking change for users |

Telemetry-specific labels (`device telemetry`, `unsupported`, `motorization`, …) are pre-filled on opt-in device profile issues — see [TELEMETRY.md](TELEMETRY.md).

## Publishing a release

Releases are driven by [release-please](https://github.com/googleapis/release-please). See [RELEASE.md](RELEASE.md).

1. Merge `feat`/`fix` PRs to `main` with [Conventional Commits](https://www.conventionalcommits.org/) titles.
2. **Release please** opens or updates a draft PR `chore: release X.Y.Z` (`CHANGELOG.md` + `manifest.json`).
3. Review the release PR, then merge — release-please creates tag `vX.Y.Z` and the GitHub Release.
4. [`release.yml`](../.github/workflows/release.yml) attaches `enki.zip` when the release is published.

Requires repository secrets `CI_APP_ID` and `CI_APP_PRIVATE_KEY` (GitHub App token so `on: release` still runs).

APK validation in CI release is **disabled for now**. Locally, after an Enki app update: `python3 scripts/extract_gateway_keys.py path/to/enki.apk --check` then `--apply --update-known` if needed.

## Technical documentation

| Document | Content |
|----------|---------|
| [RELEASE.md](RELEASE.md) | release-please workflow and secrets |
| [API.md](API.md) | Enki cloud endpoints (reverse engineering) |
| [HACS.md](HACS.md) | HACS publication checklist |
| [SUPPORTED_DEVICES.md](SUPPORTED_DEVICES.md) | Hardware and per-device status |

## Code structure

Home Assistant requires **platform loaders** and `config_flow.py` at the root of `custom_components/enki/`. Everything else is organized by layer:

```
custom_components/enki/
├── __init__.py, manifest.json, config_flow.py, coordinator.py, entity.py
├── binary_sensor.py, climate.py, cover.py, fan.py, light.py
├── number.py, select.py, sensor.py, switch.py, diagnostics.py
├── const.py, exceptions.py, strings.json, translations/, brand/
│
├── api/                    # cloud layer
│   ├── client.py           # discovery + REST commands
│   ├── auth.py             # OAuth Keycloak
│   ├── transport.py        # HTTP per micro-service
│   ├── gateway_registry.py # APK micro-service catalogue
│   └── gateway_keys.py     # runtime key store + mobile-config settings path
│
├── domain/                 # business model (no HA import)
│   ├── models.py, capabilities.py, state.py, profile.py
│
├── platforms/              # shared internal logic
│   ├── light/behavior.py
│   └── fan/airflow.py
│
├── telemetry/
│   ├── reporter.py
│   └── nudge.py
│
└── lib/                    # pure functions (0 HA import)
    ├── conversion.py, bff.py, battery.py, capability_path.py
    ├── heating.py, shutter.py, enki_scope.py
```

Platforms registered in `__init__.py` → `PLATFORMS`: `binary_sensor`, `climate`, `cover`, `fan`, `light`, `number`, `select`, `sensor`, `switch`.

### Import conventions

| Package | Role | Example |
|---------|------|---------|
| `enki.api` | Public cloud client | `from enki.api import EnkiAPI` |
| `enki.domain` | Model and capabilities | `from enki.domain.models import EnkiDevice` |
| `enki.lib` | Helpers testable without HA | `from enki.lib.conversion import speed_to_percentage` |
| `enki.platforms.fan` | Fan logic | `from enki.platforms.fan.airflow import preset_to_enki_airflow_mode` |
| `enki.telemetry` | Opt-in telemetry | `from enki.telemetry import EnkiTelemetryReporter` |

See also [CONTRIBUTING.md](../CONTRIBUTING.md) for PR conventions.
