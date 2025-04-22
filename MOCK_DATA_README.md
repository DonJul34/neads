# Génération de données factices pour NEADS

Ce dossier contient des scripts pour générer des données factices pour l'application NEADS, incluant des utilisateurs, des créateurs, des évaluations et des médias.

## Contenu des données générées

Les scripts génèrent les données suivantes:

- **Utilisateurs**
  - 1 admin (email: admin@neads.com, password: neads2025)
  - 5 consultants (email: consultant1@neads.com à consultant5@neads.com, password: neads2025)
  - 15 clients (email: client1@example.com à client15@example.com, password: neads2025)
  - ~18 créateurs avec comptes utilisateurs (email: creator*@example.com, password: neads2025)

- **Données métier**
  - 25 créateurs avec profils complets
  - 12 domaines d'expertise (Mode, Beauté, Lifestyle, etc.)
  - ~50 localisations géographiques en France (avec coordonnées pour la carte)
  - ~150-200 évaluations de créateurs
  - ~100 médias (images et vidéos, sans fichiers réels)
  - ~50-80 favoris

## Prérequis

- Python 3.8+ installé
- Django 4.2+
- Base de données NEADS initialisée (migrations appliquées)

## Installation

### Windows

1. Double-cliquez sur le fichier `setup_mock_data.bat`
2. Attendez que le script se termine

### Linux/Mac

1. Ouvrez un terminal dans ce dossier
2. Rendez le script exécutable: `chmod +x setup_mock_data.sh`
3. Exécutez le script: `./setup_mock_data.sh`
4. Attendez que le script se termine

## Installation manuelle

Si les scripts automatiques ne fonctionnent pas:

1. Installez Faker: `pip install faker`
2. Exécutez le script Python: `python generate_mock_data.py`

## Connexion

Après avoir généré les données, vous pouvez vous connecter avec les comptes suivants:

- **Admin**: admin@neads.com / neads2025
- **Consultants**: consultant1@neads.com à consultant5@neads.com / neads2025
- **Clients**: client1@example.com à client15@example.com / neads2025
- **Créateurs**: creator1@example.com à creator25@example.com / neads2025 (certains créateurs n'ont pas de compte)

## Notes importantes

- Les mots de passe sont visibles dans le panneau d'administration (en texte clair dans ce README)
- Aucun fichier média réel n'est généré (images/vidéos)
- Ces données sont uniquement destinées à des fins de test et de démonstration

## Personnalisation

Pour modifier le nombre ou le contenu des données générées, vous pouvez éditer les constantes au début du fichier `generate_mock_data.py`:

```python
NUM_DOMAINS = 10
NUM_CLIENTS = 15
NUM_CONSULTANTS = 5
NUM_CREATORS = 25
NUM_RATINGS_PER_CREATOR = 8
NUM_FAVORITES_PER_USER = 5
DEFAULT_PASSWORD = "neads2025"
``` 