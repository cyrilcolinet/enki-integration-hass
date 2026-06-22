# Sécurité

## Signaler une vulnérabilité

**Ne pas** ouvrir d’issue publique pour un problème de sécurité.

1. Ouvrir un [GitHub Security Advisory](https://github.com/cyrilcolinet/enki-integration-hass/security/advisories/new) (recommandé)
2. Ou contacter le mainteneur via GitHub en privé

Délai de réponse visé : 7 jours ouvrés.

## Périmètre

- Intégration `custom_components/enki/`
- Scripts et workflows du dépôt

Hors périmètre : l’API cloud Enki elle-même, l’application mobile, la box Enki.

## Bonnes pratiques utilisateur

- Ne pas committer `.env` ou identifiants Enki
- Utiliser un compte Enki dédié aux tests si possible
- L’intégration stocke le mot de passe dans les entrées de configuration HA — protégez votre instance
