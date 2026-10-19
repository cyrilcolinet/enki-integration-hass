# Security

## Reporting a vulnerability

**Do not** open a public issue for a security problem.

1. Open a [GitHub Security Advisory](https://github.com/cyrilcolinet/enki-integration-hass/security/advisories/new) (recommended)
2. Or contact the maintainer privately on GitHub

Target response time: 7 business days.

## Scope

- Integration `custom_components/enki/`
- Repository scripts and workflows

Out of scope: the Enki cloud API itself, the mobile app, the Enki hub.

## User best practices

- Do not commit `.env` or Enki credentials
- Use a dedicated Enki test account when possible
- The integration stores the password in HA config entries, protect your instance
