# Partage de profils appareils (opt-in)

Aide à supporter de nouveaux matériels Enki **sans envoi automatique** et **sans secret** dans l’intégration.

## Pour l’utilisateur

### Diagnostics (sans opt-in)

**Paramètres** → **Appareils et services** → **Enki** → menu ⋮ → **Télécharger les diagnostics**

Export JSON local : profils anonymisés (type, fabricant, capabilities). À joindre à une [issue](https://github.com/cyrilcolinet/enki-integration-hass/issues/new) si besoin.

### Opt-in (notification + issue pré-remplie)

**Enki** → **Configurer** → activer :

> M’avertir des nouveaux appareils (lien issue GitHub)

Quand un **nouveau** profil est détecté (empreinte unique) :

1. Une **notification persistante** apparaît dans Home Assistant
2. Le lien ouvre GitHub avec titre et description **pré-remplis**
3. Vous **validez** la création de l’issue — rien n’est envoyé sans ce clic

**Jamais inclus :** e-mail, mot de passe, homeId, nodeId, noms de pièces.

## Pour les contributeurs

Script local (compte requis) :

```bash
python3 scripts/discover_devices.py <email> <password> --export
```

Voir [DEVELOPMENT.md](DEVELOPMENT.md) pour les tests.

## Technique

- Déduplication par empreinte SHA256 (stockage local HA)
- URL : `github.com/.../issues/new?title=...&body=...&labels=device-telemetry`
- Aucun token, aucun `repository_dispatch`
