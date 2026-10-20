# HACS publication

Checklist aligned with the [official HACS documentation](https://www.hacs.xyz/docs/publish/).

## Marketplace, from Home Assistant 2026.11

HACS moves into Home Assistant as the **Marketplace** integration
([hacs/integration#5590](https://github.com/hacs/integration/issues/5590)). Read
from its source on `dev`, nothing here has to change:

- it still reads **`hacs.json`** at the root, and `manifest.json` for the domain,
  the name, `codeowners` and `config_flow`;
- it refuses an install whose `manifest.json` carries no version the loader
  accepts, CALVER, SEMVER, SIMPLEVER, BUILDVER or PEP440. Ours is release-please's
  semver, so it qualifies;
- its update entity points at **`/api/brands/integration/{domain}/icon.png`**,
  the local proxy, which prefers the icon an integration ships. That is
  `custom_components/enki/brand/`, already in place, and it is what HACS could
  not do: it hardcoded the brands CDN, which answers 200 with an "icon not
  available" placeholder for anything unregistered
  ([#346](https://github.com/cyrilcolinet/enki-integration-hass/issues/346)).

Two keys of our `hacs.json` are **ignored** by Marketplace, which accepts only
`content_in_root`, `filename`, `hacs`, `hide_default_branch`, `homeassistant`,
`name`, `persistent_directory` and `zip_release`:

| Key | Marketplace |
|-----|-------------|
| `country` | ignored |
| `render_readme` | ignored |

They stay for now because the HACS everyone is running today still uses them.
Drop them once 2026.11 is the floor.

**Status: published in the default HACS store.** Users install Enki straight from
HACS (search **Enki**), no custom repository needed. The custom-repository flow
below is only a fallback while a HACS instance catches up with the default-store
sync.

## Custom repository (fallback)

If the default-store entry hasn't synced to a given instance yet, add the repo
manually or via the **Open in HACS** badge.

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
| **Description** | Home Assistant integration for the Enki / Leroy Merlin smart home cloud: lights, fans, switches, sensors, covers, climate, scenarios, and more. |
| **Topics** | `home-assistant`, `hacs`, `hacs-integration`, `enki`, `leroy-merlin`, `smart-home`, `home-automation`, `iot`, `lexman`, `edisio`, `equation` |
| **Issues** | Enabled |

## Releases (recommended)

HACS shows the last 5 releases when they exist.

Releases are automated via [release-please](../docs/RELEASE.md): merge the `chore: release X.Y.Z` PR on `main`, the workflow creates the GitHub Release and uploads `enki.zip`.

## Default HACS store, done ✅

Procedure: [Include default repositories](https://www.hacs.xyz/docs/publish/include/)

The [hacs/default](https://github.com/hacs/default) PR adding
`cyrilcolinet/enki-integration-hass` to the `integration` file is **merged**, so
the integration ships in the default store. The technical prerequisites below are
kept green by CI on every push/PR:

| Prerequisite | Status |
|-----------|--------|
| **HACS** action (`hacs/action`, no `ignore: brands`) | ✅ [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) |
| **Hassfest** action | ✅ same |
| `hacs.json` + `country: FR` | ✅ [`hacs.json`](../hacs.json) |
| At least **one** GitHub release | ✅ [releases](https://github.com/cyrilcolinet/enki-integration-hass/releases) |
| Brand `custom_components/enki/brand/` | ✅ `icon.png` (256) + `icon@2x.png` (512): served locally by HA **2026.3+** ([Brands Proxy API](https://developers.home-assistant.io/blog/2026/02/24/brands-proxy-api)); **no longer need** a PR on [home-assistant/brands](https://github.com/home-assistant/brands) (new custom integrations rejected since Feb 2026) |

The `integration` entry is alphabetical: `cyrilcolinet/enki-integration-hass`. If the repo is ever renamed or moved, update that entry (and open a new PR) to keep the default-store listing valid.

## Local validation

Same checks as the **CI** workflow (ruff, pytest, Hassfest, HACS action) on every push/PR. On GitHub: **Actions** tab → **CI** workflow.
