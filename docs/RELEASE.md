# Release — trunk + release-please

## Flow

```
feat/fix/* ──PR──► main ──► CI (ruff, pytest, HACS, Hassfest)
                    │
                    └──► release-please (PR "chore: release X.Y.Z")
                              │
                         merge ──► tag vX.Y.Z + GitHub Release (CI App token)
                              │
                         GitHub Release published ──► enki.zip (release.yml)
```

| Step | Trigger | Result |
|------|---------|--------|
| Integration | Merge PR → `main` | CI green |
| Version | Merge release-please PR | Tag + GitHub Release + `CHANGELOG.md` + `manifest.json` bump |
| HACS asset | GitHub Release `published` | `enki.zip` attached by [`release.yml`](../.github/workflows/release.yml) |

release-please uses the **GitHub App CI** token (`CI_APP_*`), not `GITHUB_TOKEN`: a published release still triggers `on: release` so the HACS zip workflow runs.

## Workflows

| Workflow | Role |
|----------|------|
| **CI** | Lint, tests, HACS validation, Hassfest on PR and push `main` |
| **Release please** | Release PR + tag (CI App token) |
| **Release** | On `release: published` → build and upload `enki.zip` |

## Conventional Commits

PR titles / commits (English, imperative):

```
feat(light): add GDANSK BLE fallback
fix(telemetry): silence SDK admin capability gaps
```

release-please fills `CHANGELOG.md` and the GitHub Release body (Features / Bug Fixes sections).

Squash merges should keep a conventional PR title so the squash commit is parseable.

## release-please config

Files: `release-please-config.json`, `.release-please-manifest.json`.

| Option | Role |
|--------|------|
| `bootstrap-sha` | Start point for the changelog — only commits **after** this SHA are included |
| `exclude-paths` | Commits touching only `.github/`, `docs/`, `scripts/`, or `tests/` do not bump the version |
| `extra-files` | Bumps `custom_components/enki/manifest.json` → `version` |
| `label` / `release-label` | `pending release` → `released` after merge |

One-off version override: empty commit on `main` with `Release-As: 1.7.0` in the message (release-please honours the requested version).

After changing `bootstrap-sha`, close the open release PR and let release-please open a fresh one on the next `feat`/`fix`.

## GitHub secrets (repository)

| Secret | Usage |
|--------|--------|
| `CI_APP_ID` | GitHub App used by release-please (PR + tag + release) |
| `CI_APP_PRIVATE_KEY` | Private key for the CI App |

The App needs **Contents** read/write and **Pull requests** read/write on this repository.

Reuse the same CI App as [SyntaxLabsOrg/expert-crypto-ui](https://github.com/SyntaxLabsOrg/expert-crypto-ui) if it is installed on this repo; otherwise install it and add the secrets above.

## HACS

After the GitHub Release is published:

1. HACS shows an **Update** badge when a new release exists
2. Users click **Update**, then restart Home Assistant

See [HACS.md](HACS.md) and [MIGRATION.md](MIGRATION.md).
