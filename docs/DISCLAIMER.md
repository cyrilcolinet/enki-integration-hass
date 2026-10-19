# Disclaimer

## Unofficial project

This Home Assistant integration is a **community project**. It is **not** an official Enki / Leroy Merlin product or service.

- **Not affiliated** with Leroy Merlin, ADEO, or the Enki brand
- **Not endorsed or sponsored** by Leroy Merlin, ADEO, or Enki
- **Not maintained by Enki**: support for this integration comes from the open-source community via GitHub issues, not from Enki / Leroy Merlin customer support

For official product support, use [Enki support](https://support.enki-home.com/) and the Enki mobile app.

## Author and maintainers

The integration was created and is maintained by independent contributors ([@cyrilcolinet](https://github.com/cyrilcolinet) and others). **None of them are Enki, Leroy Merlin, or ADEO employees** unless explicitly stated otherwise in a given contribution.

## How it works

The integration talks to the **Enki cloud API**: the same Adeo / Leroy Merlin cloud the mobile app uses, authenticating with **your own Enki account** (email + password, via Keycloak). It is **not** an official SDK: the endpoints and per-service gateway keys were documented by observing the mobile app, and Enki has neither published nor certified this integration. No credentials or data are sent anywhere other than the Enki cloud your app already talks to.

## Legal basis

This is not legal advice, and none of the maintainers is a lawyer. It is a statement of what this
project does and on what footing, so that a rightsholder reading it knows where we stand.

The integration exists to make Enki devices work with Home Assistant. Nothing in it reproduces,
redistributes or re-implements the Enki app: it speaks to the same cloud, with the user's own
account, from an independently written program.

The endpoints and per-service gateway keys are documented by **observing the mobile app**: its
network traffic, and its code where that was the only way to see which address a device's commands
go to. In the European Union, [Directive 2009/24/EC](https://eur-lex.europa.eu/LexUriServ/LexUriServ.do?uri=OJ%3AL%3A2009%3A111%3A0016%3A0022%3AEN%3APDF)
permits exactly that, without the rightsholder's authorisation, where it is indispensable to obtain
the information needed for the **interoperability** of an independently created program, in France,
through article L122-6-1 of the *code de la propriété intellectuelle*. The directive also makes
contractual provisions to the contrary null and void.

We hold ourselves to the conditions that come with it:

- **Interoperability only.** What is learnt is used to talk to the Enki cloud and for nothing else.
  No part of this project competes with, substitutes for or reproduces the Enki app.
- **Lawful users.** The app is installed from its official store, and every request is made with the
  user's own Enki account against their own devices.
- **No information that was available otherwise.** Adeo publishes no API documentation. Nothing here
  was taken from a source we were not entitled to read.
- **No circumvention.** No protection measure is defeated. Where the app pins its certificate, we
  stop and look for another way rather than breaking it; where a route refuses our key, we treat
  that as our bug and verify the key against the app rather than working around the refusal.
- **Only what interoperability needs.** The gateway keys shipped here are application keys embedded
  in a public app, not anyone's personal secret, and they are the one thing without which no
  independent client can reach the service at all. No user data, no account, no credential of any
  person is published.
- **Nothing of the app is redistributed.** No APK, no decompiled source and no extracted resource is
  committed to this repository, and none is accepted in a contribution.

## If you are a rightsholder

If Adeo, Leroy Merlin or Enki consider that something here goes beyond the above, we would rather
hear it than be guessed at. Open an issue titled **"Rightsholder contact"** on
[the tracker](https://github.com/cyrilcolinet/enki-integration-hass/issues/new), or write to
**cyril@syntax-labs.fr** for anything you would rather keep off a public tracker.

Say which file or behaviour you mean and we will look at it on its merits and answer. That offer is
not an admission that anything here is unlawful, and a request is not a court order. But a concrete
objection is worth acting on, and we would rather fix it than argue about it.

## Trademarks

"Enki", "Leroy Merlin", "ADEO", and device brand names (Lexman, Equation, Inspire, Eglo, Sedea, Edisio, Evology, Nodon, EssentielB, …) are trademarks of their respective owners. Their use in this repository is for **identification only** (compatible hardware and services). No affiliation or endorsement is implied.

## No warranty

This software is provided **as is** under the [MIT License](../LICENSE). The Enki cloud API is unofficial and may change, break, or disable this integration without notice; gateway keys may rotate on app updates. Use at your own risk, with your own account.
