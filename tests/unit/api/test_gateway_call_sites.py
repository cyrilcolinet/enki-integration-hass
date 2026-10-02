"""Following a gateway key to the interface it signs (#275)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from gateway_call_sites import (  # noqa: E402
    declared_routes,
    interfaces_by_key,
    interfaces_by_slug,
    keys_for_slug,
)

CONSUMPTION_KEY = "63NAgKMjnVEkRwVpoRS78vQUBR0uNwkF"
OTHER_KEY = "zh3jMokVoRrRmJ0LrVANkJCsNt30YEV7"

# The retrofit interface: the only class that says which service it talks to.
NN5 = """
public interface nn5 {
    @qva("consumption/{nodeId}/check-instant-consumption")
    Object d(@z2d("X-Gateway-APIKey") String str, @q1j("nodeId") String str2);
}
"""

# A holder: takes the key as a parameter and hands it to the interface it casts.
BP1 = """
public final class bp1 {
    public Object O(String str, String str2) {
        nn5 nn5Var = (nn5) this.c;
        return nn5Var.d(str, str2);
    }
}
"""

# The caller holding the literal. It also holds another service's key, which is
# what made the old proximity heuristic a coin toss (fdr.java holds five).
FDR = f"""
public final class fdr {{
    public Object a() {{
        bp1 bp1Var = (bp1) this.c;
        return bp1Var.O("{CONSUMPTION_KEY}", strG);
    }}
    public Object b() {{
        q7x q7xVar = (q7x) this.d;
        return q7xVar.z("{OTHER_KEY}", strG);
    }}
}}
"""

# The interface the other key belongs to, so the two must not be confused.
Q7X = """
public interface q7x {
    @qva("alexa/{nodeId}/check-mapping")
    Object z(@z2d("X-Gateway-APIKey") String str);
}
"""

DI_MODULE = """
public final class ui6 {
    public final Object a() {
        return new fdr(new bp1((nn5) i75.h(this,
            "https://enki.api.devportal.adeo.cloud/api-enki-consumption-prod/v1/", nn5.class)), 17);
    }
}
"""

SOURCES = {"nn5": NN5, "bp1": BP1, "fdr": FDR, "q7x": Q7X, "ui6": DI_MODULE}


def test_a_key_handed_through_a_holder_reaches_its_interface() -> None:
    by_key = interfaces_by_key(SOURCES, SOURCES)

    assert set(by_key[CONSUMPTION_KEY]) == {"nn5"}
    assert set(by_key[OTHER_KEY]) == {"q7x"}


def test_the_di_module_says_which_interface_serves_a_slug() -> None:
    assert interfaces_by_slug([DI_MODULE]) == {"api-enki-consumption-prod": {"nn5"}}


def test_a_service_resolves_to_exactly_one_key() -> None:
    """The neighbour's key sits in the same file and must not come along."""
    by_key = interfaces_by_key(SOURCES, SOURCES)

    assert keys_for_slug(SOURCES, by_key, {"nn5"}) == {CONSUMPTION_KEY}
    assert keys_for_slug(SOURCES, by_key, {"q7x"}) == {OTHER_KEY}


def test_an_interface_cast_at_the_call_site_is_enough() -> None:
    """`((rt9) pz7Var.c).d("key", …)` — no holder to walk through."""
    sources = {
        "rt9": 'interface rt9 {\n    @qva("states/{nodeId}")\n    Object d(String str);\n}',
        "u39": f'class u39 {{\n  void a() {{ ((rt9) pz7Var.c).d("{OTHER_KEY}", strG); }}\n}}',
    }

    by_key = interfaces_by_key(sources, sources)

    assert keys_for_slug(sources, by_key, {"rt9"}) == {OTHER_KEY}


def test_a_pass_through_holder_with_no_methods() -> None:
    """The siren's shape: `this.a.a.i("key", …)`, the holder only stores the interface."""
    sources = {
        "f9n": (
            'interface f9n {\n    @qva("siren/{nodeId}/check-siren-state")\n'
            "    Object i(String s);\n}"
        ),
        "u8n": "public final class u8n {\n    public final f9n a;\n}",
        "e9n": (
            "public final class e9n {\n    public final u8n a;\n"
            f'    void x() {{ this.a.a.i("{OTHER_KEY}", strG); }}\n}}'
        ),
    }

    by_key = interfaces_by_key(sources, sources)

    assert keys_for_slug(sources, by_key, {"f9n"}) == {OTHER_KEY}


def test_a_holder_is_not_mistaken_for_an_interface() -> None:
    """Only classes that declare routes count: a holder signs nothing."""
    by_key = interfaces_by_key(SOURCES, SOURCES)

    assert keys_for_slug(SOURCES, by_key, {"bp1", "fdr"}) == set()


def test_routes_are_read_from_the_interface() -> None:
    assert declared_routes(NN5) == {"consumption/{nodeId}/check-instant-consumption"}
    assert declared_routes(BP1) == set()


def test_every_wired_key_matches_its_recorded_call_site() -> None:
    """The same gate CI runs, so a swapped key fails here too (#275)."""
    import enki.gateway_keys_data as keys_module
    from enki.api.gateway_registry import ENKI_MICRO_SERVICES

    recorded = json.loads(
        (REPO_ROOT / "scripts" / "gateway_key_evidence.json").read_text(encoding="utf-8")
    )["services"]

    for svc in ENKI_MICRO_SERVICES:
        if not svc.wired:
            continue
        assert svc.const_key in recorded, f"{svc.const_key} has no recorded call site"
        assert recorded[svc.const_key]["key"] == getattr(keys_module, svc.const_key)
