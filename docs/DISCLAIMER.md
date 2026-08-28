# Disclaimer

## Unofficial project

This Home Assistant integration is a **community project**. It is **not** an official Enki / Leroy Merlin product or service.

- **Not affiliated** with Leroy Merlin, ADEO, or the Enki brand
- **Not endorsed or sponsored** by Leroy Merlin, ADEO, or Enki
- **Not maintained by Enki** — support for this integration comes from the open-source community via GitHub issues, not from Enki / Leroy Merlin customer support

For official product support, use [Enki support](https://support.enki-home.com/) and the Enki mobile app.

## Author and maintainers

The integration was created and is maintained by independent contributors ([@cyrilcolinet](https://github.com/cyrilcolinet) and others). **None of them are Enki, Leroy Merlin, or ADEO employees** unless explicitly stated otherwise in a given contribution.

## How it works

The integration talks to the **Enki cloud API** — the same Adeo / Leroy Merlin cloud the mobile app uses — authenticating with **your own Enki account** (email + password, via Keycloak). It is **not** an official SDK: the endpoints and per-service gateway keys were documented by observing the mobile app, and Enki has neither published nor certified this integration. No credentials or data are sent anywhere other than the Enki cloud your app already talks to.

## Trademarks

"Enki", "Leroy Merlin", "ADEO", and device brand names (Lexman, Equation, Inspire, Eglo, Sedea, Edisio, Evology, Nodon, …) are trademarks of their respective owners. Their use in this repository is for **identification only** (compatible hardware and services). No affiliation or endorsement is implied.

## No warranty

This software is provided **as is** under the [MIT License](../LICENSE). The Enki cloud API is unofficial and may change, break, or disable this integration without notice; gateway keys may rotate on app updates. Use at your own risk, with your own account.
