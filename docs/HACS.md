# HACS publication

Checklist aligned with the [official HACS documentation](https://www.hacs.xyz/docs/publish/).

## Custom repository (current install)

Until inclusion in the default store, users add the repo manually or via the **Open in HACS** badge.

1. **Public** GitHub repository
2. [`hacs.json`](../hacs.json) at the root with at least `name`
3. `custom_components/enki/` structure with `manifest.json`
4. Installation README
5. [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) workflow (lint, tests, HACS, Hassfest) **without errors**

### Quick install link (my.home-assistant.io)

After publishing the repo, generate a link:

[Create a HACS link](https://my.home-assistant.io/create-link/?redirect=hacs_repository&owner=cyrilcolinet&repository=enki-integration-hass&category=integration)

Example Markdown for the README:

```markdown
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=cyrilcolinet&repository=enki-integration-hass&category=integration)
```

## GitHub metadata (required for HACS)

Configure on the repository **Settings** page:

| Field | Example |
|-------|---------|
| **Description** | Home Assistant integration for the Enki / Leroy Merlin smart home cloud — lights, fans, switches, sensors, covers, climate, scenarios, and more. |
| **Topics** | `home-assistant`, `hacs`, `hacs-integration`, `enki`, `leroy-merlin`, `smart-home`, `home-automation`, `iot`, `lexman`, `edisio`, `equation` |
| **Issues** | Enabled |

## Releases (recommended)

HACS shows the last 5 releases when they exist.

Releases are automated via [release-please](../docs/RELEASE.md): merge the `chore: release X.Y.Z` PR on `main` — the workflow creates the GitHub Release and uploads `enki.zip`.

## Default HACS store

Procedure: [Include default repositories](https://www.hacs.xyz/docs/publish/include/)

**Repository status:** technical prerequisites are covered by CI on every push/PR:

| Prerequisite | Status |
|-----------|--------|
| **HACS** action (`hacs/action`, no `ignore: brands`) | ✅ [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) |
| **Hassfest** action | ✅ same |
| `hacs.json` + `country: FR` | ✅ [`hacs.json`](../hacs.json) |
| At least **one** GitHub release | ✅ [releases](https://github.com/cyrilcolinet/enki-integration-hass/releases) |
| Brand `custom_components/enki/brand/` | ✅ `icon.png` (256) + `icon@2x.png` (512) — served locally by HA **2026.3+** ([Brands Proxy API](https://developers.home-assistant.io/blog/2026/02/24/brands-proxy-api)); **no longer need** a PR on [home-assistant/brands](https://github.com/home-assistant/brands) (new custom integrations rejected since Feb 2026) |

**Remaining publication step:** PR on [hacs/default](https://github.com/hacs/default) (`integration` file), **alphabetical** entry: `cyrilcolinet/enki-integration-hass`.

## Local validation

Same checks as the **CI** workflow (ruff, pytest, Hassfest, HACS action) on every push/PR. On GitHub: **Actions** tab → **CI** workflow.
