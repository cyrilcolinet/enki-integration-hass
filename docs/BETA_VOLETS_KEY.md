# Cover gateway keys — contributor guide

This document is for **people comfortable with networking / mobile debugging**. Casual testers do not need it: see [Beta covers — for testers](SUPPORTED_DEVICES.md#for-testers-covers) in `SUPPORTED_DEVICES.md`.

## Current state

For **roller shutters** (`api-enki-rolling-prod`), the **`ENKI_ACCESS_MOTORIZATION_API_KEY`** is already included in `const.py` (extracted from the Enki APK — version tracked in `const.py`). The legacy micro-service `api-enki-access-and-motorizations-prod` is no longer used.

Users **configure nothing**: the **“Shutter (beta)”** entity appears if the cover is active in the Enki app and the integration is **v1.5.0+**.

## When to read this guide

- **Enki app update** — gateway keys may change; the recommended method is `scripts/extract_gateway_keys.py` (see [DEVELOPMENT.md](DEVELOPMENT.md)).
- **HTTP 403** on `api-enki-rolling-prod` — validate the embedded key vs real app traffic (mitmproxy below).
- **APK extraction failure** — capture `X-Gateway-APIKey` manually and open an issue or PR.

**This is not:**

- the Enki account password;
- a personal secret tied to a home;
- data to share publicly on social media (it is a Leroy Merlin / Adeo app key, reusable for the whole integration once merged in the repo).

## What to capture (manual validation)

When controlling a cover in the Enki app, look for an HTTP request to:

```text
…/api-enki-rolling-prod/v1/shutter/{nodeId}/…
```

Copy the header value:

```text
X-Gateway-APIKey: <value to compare or send to maintainer>
```

Typical actions in the URL: `check-shutter-position`, `change-shutter-position`, `check-shutter-opening`.

## Recommended method — APK extraction

On the dev machine:

```bash
python3 scripts/extract_gateway_keys.py path/to/enki.apk --apply --update-known
```

The script updates `custom_components/enki/const.py` (including `ENKI_ACCESS_MOTORIZATION_API_KEY`). Details: [DEVELOPMENT.md](DEVELOPMENT.md).

## Alternative — mitmproxy (network validation)

### Prerequisites

- PC and phone on the **same Wi‑Fi network**
- [mitmproxy](https://mitmproxy.org/) installed on the PC
- **Enki** app on the phone, with at least one working cover

### Steps

1. **Start mitmproxy** on the PC:
   ```bash
   mitmweb
   ```
   Web UI: http://127.0.0.1:8081 — proxy listens on port **8080**.

2. **Configure Wi‑Fi proxy on the phone**  
   Wi‑Fi settings → current network → manual proxy → PC IP, port **8080**.

3. **Install the mitmproxy certificate** on the phone  
   On the phone, open http://mitm.it and follow instructions (iOS or Android). Without the certificate, the app HTTPS traffic will not be visible.

4. **Control a cover in the Enki app**  
   Open, close, or set position.

5. **Filter traffic** in mitmweb  
   Search for `rolling-prod` or `change-shutter`.

6. **Copy `X-Gateway-APIKey`** from the request headers and compare to `ENKI_ACCESS_MOTORIZATION_API_KEY` in `const.py`.

7. **Disable the proxy** on the phone when done.

### Reporting to the project

If the key differs from the repo, open an [issue](https://github.com/cyrilcolinet/enki-integration-hass/issues/new) or comment on an existing cover issue with:

- the `X-Gateway-APIKey` value (text only);
- cover model tested (e.g. Evology SIN2RS1);
- Enki app (APK) version;
- confirmation the command worked in the app at capture time.

**Never attach:** email, password, Bearer tokens, homeId, nodeId.

## Alternative — HTTP Toolkit

[HTTP Toolkit](https://httptoolkit.com/) provides a GUI (Android via ADB, or manual proxy like mitmproxy). Same principle: intercept an `api-enki-rolling-prod` / `shutter/…` request and read `X-Gateway-APIKey`.

## Repository integration

1. **Preferred:** `extract_gateway_keys.py --apply --update-known` (see above).
2. **Otherwise:** maintainer updates manually:

```python
# custom_components/enki/const.py
ENKI_ACCESS_MOTORIZATION_API_KEY = "…"
```

Then publish a new version. Users change nothing manually if they use HACS.

## References

- Cover API notes: [API.md](API.md#roller-shutters-evology-sin2rs1--beta)
- Testers (no proxy): [SUPPORTED_DEVICES.md](SUPPORTED_DEVICES.md#for-testers-covers)
