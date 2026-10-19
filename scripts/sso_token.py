#!/usr/bin/env python3
"""Sign in with Google or Apple and print the refresh token, for the probe scripts.

The probes ask for an email and a password. An account created with Google or
Apple has no password in the Enki realm (#325), so its owner could not run any of
them — which is backwards, since those are the accounts we most need reports
from.

This does the same browser dance the integration does: open the link, sign in,
and paste back the ``enki://`` address your browser cannot open. What comes out
is a refresh token the probes take with ``--refresh-token``.

Two things to know. Do it **on a computer** — on a phone with the Enki app
installed, the app opens instead and swallows the address. And the code lasts
about a minute, so paste it straight away.

The token it prints is a credential for your account: keep it like a password,
and do not paste it into an issue.

Usage:
    python3 scripts/sso_token.py google
    python3 scripts/sso_token.py apple
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from enki_bootstrap import bootstrap, load_module  # noqa: E402

bootstrap("enki.api.auth", "enki.const", "enki.exceptions")
auth_mod = load_module("enki.api.auth")
const_mod = load_module("enki.const")

SSO_PROVIDERS = const_mod.SSO_PROVIDERS
account_from_claims = auth_mod.account_from_claims
claims_from_token = auth_mod.claims_from_token
exchange_sso_code = auth_mod.exchange_sso_code
sso_authorize_url = auth_mod.sso_authorize_url
sso_code_from_callback = auth_mod.sso_code_from_callback


async def sign_in(provider: str) -> int:
    import aiohttp

    print(f"\n1. Open this link and sign in with {provider.title()}:\n")
    print(f"   {sso_authorize_url(provider)}\n")
    print("2. Your browser will fail to open an address starting with enki://.")
    print("   That is expected. Copy that whole address from the address bar.\n")
    pasted = input("3. Paste it here: ")

    async with aiohttp.ClientSession() as session:
        payload = await exchange_sso_code(session, sso_code_from_callback(pasted), provider)

    claims = claims_from_token(payload["access_token"])
    print(f"\nSigned in as {account_from_claims(claims) or 'an account with no email claim'}.")
    print("\nRefresh token — treat it like a password, do not post it anywhere:\n")
    print(f"   {payload['refresh_token']}\n")
    print("Pass it to a probe, for example:")
    print("   python3 scripts/probe_capability.py check_child_lock --refresh-token <the token>\n")
    # Names only, no values: this is what a capability report can safely include,
    # and it answers whether a federated token carries the same claims as a
    # password one (#325).
    print(f"Claims this token carries (names only): {sorted(claims)}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("provider", choices=sorted(SSO_PROVIDERS))
    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(asyncio.run(sign_in(parse_args().provider)))
