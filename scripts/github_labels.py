"""GitHub repository label definitions (workflow triage + telemetry)."""

from __future__ import annotations

from enki.lib.telemetry_labels import (
    TELEMETRY_GITHUB_LABEL_DEFINITIONS,
    TELEMETRY_GITHUB_ORPHAN_LABELS,
)

WORKFLOW_GITHUB_LABEL_DEFINITIONS: tuple[tuple[str, str, str], ...] = (
    ("pending release", "0075ca", "Open release-please PR awaiting merge"),
    ("released", "0e8a16", "Tagged by release-please"),
    ("next release", "0075ca", "Target for the upcoming tagged release"),
    ("release blocker", "b60205", "Must be resolved before the next release"),
    ("beta", "fbca04", "Beta or experimental; needs real-world testing"),
    ("stale", "cfd3d7", "No recent activity"),
    ("blocked", "e99695", "Blocked by external dependency or missing hardware"),
    ("needs info", "d876e3", "Waiting on reporter feedback"),
    ("confirmed", "0e8a16", "Reproduced or accepted by a maintainer"),
    ("regression", "d73a4a", "Worked before, broken in a recent version"),
    ("breaking change", "5319e7", "Breaking change for existing users"),
)

WORKFLOW_GITHUB_ORPHAN_LABELS: tuple[str, ...] = (
    "next-release",
    "release-blocker",
    "breaking-change",
    "needs-info",
)

GITHUB_LABEL_ORPHAN_LABELS: tuple[str, ...] = (
    WORKFLOW_GITHUB_ORPHAN_LABELS + TELEMETRY_GITHUB_ORPHAN_LABELS
)


def github_label_definitions() -> tuple[tuple[str, str, str], ...]:
    return WORKFLOW_GITHUB_LABEL_DEFINITIONS + TELEMETRY_GITHUB_LABEL_DEFINITIONS


def github_label_orphans() -> tuple[str, ...]:
    return GITHUB_LABEL_ORPHAN_LABELS
