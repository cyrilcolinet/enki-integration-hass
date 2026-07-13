# Release — trunk + release-please

## Flow

```
feat/fix/* ──PR──► main ──► CI (ruff, pytest, HACS, Hassfest)
                    │
                    └──► release-please (PR "chore: release X.Y.Z")
                              │
                         merge ──► tag vX.Y.Z + GitHub Release + enki.zip
```

| Step | Trigger | Result |
|------|---------|--------|
| Integration | Merge PR → `main` | CI green |
| Version | Merge release-please PR | Tag + GitHub Release + `CHANGELOG.md` + `manifest.json` bump |
| HACS asset | Same workflow (`attach-hacs-zip` job) | `enki.zip` uploaded to the GitHub Release |

Uses the default `GITHUB_TOKEN` only — no CI App secrets. The zip is attached in the same workflow run because releases created by `GITHUB_TOKEN` do not trigger separate `on: release` workflows.

## Workflows

| Workflow | Role |
|----------|------|
| **CI** | Lint, tests, HACS validation, Hassfest on PR and push `main` |
| **Release please** | Release PR, tag, GitHub Release, and `enki.zip` |

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

## Manual zip re-upload

If `enki.zip` is missing from a release:

```bash
git checkout vX.Y.Z
cd custom_components/enki && zip -r enki.zip .
gh release upload vX.Y.Z enki.zip --clobber
```

## HACS

After the GitHub Release is published:

1. HACS shows an **Update** badge when a new release exists
2. Users click **Update**, then restart Home Assistant

See [HACS.md](HACS.md) and [MIGRATION.md](MIGRATION.md).
