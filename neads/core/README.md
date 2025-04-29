# Application Core

## Vue d'ensemble

L'application Core est le cœur du projet NEADS. Elle gère l'authentification des utilisateurs, les rôles, les permissions et autres fonctionnalités fondamentales de la plateforme.

## Modèles

### User

Modèle utilisateur personnalisé basé sur `AbstractBaseUser` et `PermissionsMixin` avec:

- Authentification par email au lieu de nom d'utilisateur
- Système de rôles multiples (admin, consultant, client, creator)
- Mécanisme de connexion temporaire par token

```python
# Utilisation typique
user = User.objects.create_user(email="example@mail.com", password="secure_password", role="client")
user.has_role("client")  # True
token = user.generate_temp_login_token()  # Pour lien magique d'authentification
```

Rôles disponibles:
- `admin` : Administrateurs du système 
- `consultant` : Consultants internes
- `client` : Clients cherchant des créateurs
- `creator` : Créateurs de contenu

### UserProfile

Extension du modèle utilisateur pour stocker des informations supplémentaires:

- Photo de profil
- Numéro de téléphone
- Nom d'entreprise
- Méta-informations (IP de dernière connexion, vérifications)

## Middlewares

### CreatorRedirectMiddleware

Redirige automatiquement les utilisateurs avec le rôle "creator" vers leur profil de créateur ou vers le formulaire de création de profil s'ils n'en ont pas encore.

## Vues principales

- Authentification (login, logout, enregistrement)
- Gestion de profil utilisateur
- Pages d'administration pour les utilisateurs avec rôle admin/consultant

## Relations avec les autres applications

### Avec l'application Creators

- La relation one-to-one User → Creator permet de lier un compte utilisateur à un profil de créateur
- Les utilisateurs avec rôle "creator" sont automatiquement dirigés vers leur profil de créateur

## Configuration et personnalisation

```python
# settings.py
AUTH_USER_MODEL = 'core.User'
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
``` 