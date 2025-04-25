# NEADS - Plateforme de Connexion Créateurs/Clients

## Vue d'ensemble

NEADS est une plateforme Django permettant de connecter des créateurs de contenu avec des clients potentiels. Le projet est structuré en trois applications principales qui travaillent ensemble pour offrir une expérience complète.

## Structure du Projet

Le projet est organisé en trois applications principales:

1. **Core** (`neads/core/`) - Système d'authentification et fonctionnalités de base
2. **Creators** (`neads/creators/`) - Gestion des profils de créateurs et de leurs contenus
3. **Map** (`neads/map/`) - Affichage cartographique des créateurs

## Installation et Configuration

### Prérequis
- Python 3.8+
- Django 4.2+
- Autres dépendances listées dans `requirements.txt`

### Installation

```bash
# Cloner le dépôt
git clone [URL_DU_REPO]

# Installer les dépendances
pip install -r requirements.txt

# Configurer la base de données
python manage.py migrate

# Créer un superutilisateur
python manage.py createsuperuser

# Lancer le serveur de développement
python manage.py runserver
```

Pour générer des données fictives de test:
```bash
# Sur Windows
setup_mock_data.bat

# Sur Linux/Mac
./setup_mock_data.sh
```

## Documentation Détaillée

Chaque application possède sa propre documentation détaillée:

- [Documentation Core](neads/core/README.md)
- [Documentation Creators](neads/creators/README.md)
- [Documentation Map](neads/map/README.md)

## Environnement de Développement

Le projet inclut des scripts pour configurer l'environnement de développement:

```bash
# Sur Windows
setup_django_env.bat

# Sur Linux/Mac
./setup_django_linux.sh
```

## Licence

[Licence du projet] 