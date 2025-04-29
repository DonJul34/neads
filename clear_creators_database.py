#!/usr/bin/env python
import os
import django

# Configurer l'environnement Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neads.settings')
django.setup()

# Importer les modèles après la configuration de Django
from neads.creators.models import Creator, Domain, ContentType, Location, Media

def clear_creators_database():
    """
    Supprime tous les créateurs et leurs données associées de la base de données,
    mais préserve les utilisateurs superutilisateurs.
    """
    print("Nettoyage de la base de données des créateurs...")
    
    # Supprimer d'abord les médias (pour éviter les contraintes d'intégrité)
    media_count = Media.objects.all().count()
    Media.objects.all().delete()
    print(f"- {media_count} médias supprimés")
    
    # Supprimer les créateurs
    creator_count = Creator.objects.all().count()
    Creator.objects.all().delete()
    print(f"- {creator_count} créateurs supprimés")
    
    # Supprimer les locations non utilisées
    location_count = Location.objects.all().count()
    Location.objects.all().delete()
    print(f"- {location_count} localisations supprimées")
    
    # Optionnel: supprimer les domaines et types de contenu
    # Décommenter si vous souhaitez les garder
    domain_count = Domain.objects.all().count()
    Domain.objects.all().delete()
    print(f"- {domain_count} domaines supprimés")
    
    content_type_count = ContentType.objects.all().count()
    ContentType.objects.all().delete()
    print(f"- {content_type_count} types de contenu supprimés")
    
    print("Nettoyage terminé avec succès!")

if __name__ == "__main__":
    clear_creators_database() 