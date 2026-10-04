"""HTTP verbs are read out of the APK, not hardcoded (#285)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from extract_api_routes import http_verbs  # noqa: E402

# Retrofit's own dispatch, as jadx renders it. The annotation names are
# obfuscated and change every build; the verb strings next to them do not.
RETROFIT_DISPATCH = """
            Annotation annotation2 = annotationArr[i6];
            if (annotation2 instanceof gi6) {
                rukVar.b("DELETE", ((gi6) annotation2).value(), false);
            } else if (annotation2 instanceof qva) {
                rukVar.b("GET", ((qva) annotation2).value(), false);
            } else if (annotation2 instanceof fki) {
                rukVar.b("PATCH", ((fki) annotation2).value(), true);
            } else if (annotation2 instanceof hki) {
                rukVar.b("POST", ((hki) annotation2).value(), true);
            } else if (annotation2 instanceof iki) {
                rukVar.b("PUT", ((iki) annotation2).value(), true);
            }
"""


def test_verbs_are_read_from_retrofits_dispatch(tmp_path: Path) -> None:
    (tmp_path / "rzd.java").write_text(RETROFIT_DISPATCH, encoding="utf-8")

    assert http_verbs(tmp_path) == {
        "gi6": "DELETE",
        "qva": "GET",
        "fki": "PATCH",
        "hki": "POST",
        "iki": "PUT",
    }


def test_a_dump_without_the_dispatch_fails_loudly(tmp_path: Path) -> None:
    """Silently returning nothing is how the catalogue went stale for two releases."""
    (tmp_path / "noise.java").write_text("class noise { int a = 1; }", encoding="utf-8")

    with pytest.raises(RuntimeError, match="empty"):
        http_verbs(tmp_path)
