# Application Map

## Vue d'ensemble

L'application Map gère la représentation géographique des créateurs sur une carte interactive. Elle permet de visualiser la distribution des créateurs, de les regrouper en clusters et d'effectuer des recherches géolocalisées.

## Modèles principaux

### MapPoint

Représente un créateur sur la carte:

```python
map_point = creator.map_point  # Accès au point sur la carte d'un créateur
map_point.latitude  # Latitude du point
map_point.longitude  # Longitude du point
```

Caractéristiques:
- Coordonnées géographiques (latitude, longitude)
- Informations pour le popup sur la carte (titre, contenu)
- Type d'icône pour la représentation visuelle
- Visibilité configurable

### MapCluster

Représente un regroupement de points sur la carte:

```python
cluster = MapCluster.objects.get(name="Paris Centre")
cluster.points_count  # Nombre de points dans le cluster
cluster.update_points_count()  # Mise à jour du nombre de points
```

Caractéristiques:
- Coordonnées du centre du cluster
- Niveau de zoom et rayon
- Nombre de points inclus
- Option pour clusters dynamiques ou fixes

## Relations avec les autres applications

### Avec l'application Creators

- Relation one-to-one entre `Creator` et `MapPoint`
- Utilisation du modèle `Location` de l'application Creators

## Fonctionnalités principales

- Affichage des créateurs sur une carte interactive
- Clustering automatique pour optimiser l'affichage
- Filtrages géographiques (zone, distance, région)
- Popups informatifs sur les créateurs
- Recherche par localisation

## Utilisation typique

```python
# Création automatique d'un point sur la carte lors de la création d'un créateur
creator = Creator.objects.create(...)
MapPoint.objects.create(
    creator=creator,
    latitude=creator.location.latitude,
    longitude=creator.location.longitude
)

# Recherche de créateurs dans une zone géographique
nearby_points = MapPoint.objects.filter(
    is_visible=True,
    latitude__gte=lat_min,
    latitude__lte=lat_max,
    longitude__gte=lng_min,
    longitude__lte=lng_max
)
nearby_creators = [point.creator for point in nearby_points]
```

## Intégration cartographique

L'application est conçue pour fonctionner avec des bibliothèques JavaScript de cartographie comme Leaflet ou Google Maps, avec les données servies via API REST.

## Configuration et personnalisation

Le comportement du clustering et de l'affichage peut être configuré via les paramètres des modèles ou via des variables d'environnement. 