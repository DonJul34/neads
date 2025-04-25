# Application Creators

## Vue d'ensemble

L'application Creators est le cœur fonctionnel de NEADS, permettant de gérer les profils des créateurs de contenu, leur portfolio, leurs évaluations et favoris. Cette application fournit toutes les fonctionnalités nécessaires pour mettre en relation les créateurs avec les clients potentiels.

## Modèles principaux

### Creator

Modèle central représentant un créateur de contenu avec toutes ses caractéristiques professionnelles:

```python
creator = Creator.objects.get(id=1)
creator.full_name  # Nom complet du créateur
creator.domains.all()  # Domaines d'expertise
creator.content_types.all()  # Types de contenu proposés
creator.average_rating  # Note moyenne
creator.update_ratings()  # Recalcule la note moyenne
creator.total_clients  # Nombre total de clients engagés
```

Caractéristiques principales:
- Informations personnelles (nom, âge, genre)
- Localisation géographique
- Liens réseaux sociaux (YouTube, TikTok, Instagram)
- Informations professionnelles (bio, équipement, délais de livraison)
- Domaines d'expertise et types de contenu
- Métriques de performance (notation, clients)

### Domain

Représente les domaines d'expertise des créateurs:

```python
domain = Domain.objects.get(name="Voyage")
domain.creators.all()  # Tous les créateurs dans le domaine Voyage
```

### ContentType

Types de contenu que les créateurs peuvent produire:

```python
content_type = ContentType.objects.get(name="Vidéo")
content_type.creators.all()  # Tous les créateurs proposant des vidéos
```

### Location

Gère les informations de localisation des créateurs:

```python
location = Location.objects.get(city="Paris")
location.creators.all()  # Tous les créateurs basés à Paris
```

### Media

Gère les fichiers médias (images et vidéos) du portfolio des créateurs:

```python
medias = creator.media.filter(media_type="image")  # Images du portfolio
```

Caractéristiques:
- Support pour images et vidéos
- Génération de chemins d'upload sécurisés
- Limitation du nombre de médias par créateur
- Possibilité de vérification des médias

### Rating

Gère les évaluations et commentaires sur les créateurs:

```python
ratings = creator.ratings.all()  # Toutes les évaluations
```

### Favorite

Gestion des créateurs favoris par utilisateur:

```python
favorites = user.favorites.all()  # Tous les créateurs favoris d'un utilisateur
```

## Relations principales

### Relations One-to-One
- `Creator` ↔ `User` (facultatif) : Lien avec le compte utilisateur
- `Creator` ↔ `MapPoint` : Représentation du créateur sur la carte

### Relations One-to-Many
- `Location` → `Creator` : Une localisation peut avoir plusieurs créateurs
- `Creator` → `Media` : Un créateur peut avoir plusieurs médias
- `Creator` → `Rating` : Un créateur peut avoir plusieurs évaluations
- `Creator` → `Favorite` : Un créateur peut être favori de plusieurs utilisateurs

### Relations Many-to-Many
- `Creator` ↔ `Domain` : Un créateur peut avoir plusieurs domaines
- `Creator` ↔ `ContentType` : Un créateur peut proposer plusieurs types de contenu

## Fonctionnalités

- Création et gestion de profil créateur
- Upload et gestion de portfolio avec images et vidéos
- Système d'évaluation et notation
- Gestion des favoris
- Recherche et filtrage de créateurs par critères
- Métriques et statistiques de performance

## Utilitaires

- Fonctions personnalisées pour l'upload de fichiers (`image_upload_path`, `video_upload_path`)
- Méthodes de calcul et mise à jour des statistiques (`update_ratings`)
- Validation et limitation des médias 