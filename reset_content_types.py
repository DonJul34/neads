#!/usr/bin/env python
import os
import django

# Configurer l'environnement Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neads.settings')
django.setup()

# Importer les modèles après la configuration de Django
from neads.creators.models import ContentType, Creator

def reset_content_types():
    """
    Réinitialise complètement les types de contenu en:
    1. Supprimant tous les types de contenu existants
    2. Créant de nouveaux types avec des noms descriptifs
    3. Réinitialisant les relations des créateurs avec les types de contenu
    """
    print("Réinitialisation des types de contenu...")
    
    # Étape 1: Détacher tous les types de contenu des créateurs
    print("1. Suppression des relations content_types pour tous les créateurs...")
    for creator in Creator.objects.all():
        creator.content_types.clear()
    print("   Relations content_types supprimées.")
    
    # Étape 2: Supprimer tous les types de contenu existants
    print("2. Suppression de tous les types de contenu existants...")
    old_count = ContentType.objects.count()
    ContentType.objects.all().delete()
    print(f"   {old_count} types de contenu supprimés.")
    
    # Étape 3: Créer de nouveaux types de contenu avec des noms descriptifs
    print("3. Création de nouveaux types de contenu descriptifs...")
    
    new_content_types = [
        'Vidéo',
        'Audio',
        'Image',
        'UGC',
        'Animation',
        'Story',
        'Reel',
        'Live',
        'Podcast',
        'Tutoriel',
        'Vlog',
        'Short',
        'Texte'
    ]
    
    for name in new_content_types:
        ContentType.objects.create(name=name)
    
    print(f"   {len(new_content_types)} nouveaux types de contenu créés:")
    for i, name in enumerate(new_content_types, 1):
        print(f"     {i}. {name}")
    
    print("\nRéinitialisation terminée avec succès!")

if __name__ == "__main__":
    confirmation = input("Cette opération va supprimer TOUS les types de contenu existants et réinitialiser les relations. Êtes-vous sûr? (oui/non): ")
    if confirmation.lower() == 'oui':
        reset_content_types()
    else:
        print("Opération annulée.") 