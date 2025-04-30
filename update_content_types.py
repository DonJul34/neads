#!/usr/bin/env python
import os
import django
import re

# Configurer l'environnement Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neads.settings')
django.setup()

# Importer les modèles après la configuration de Django
from neads.creators.models import ContentType

def update_content_types():
    """
    Met à jour les types de contenu existants avec des noms descriptifs 
    au lieu des noms génériques comme "Type X".
    """
    # Mapping des anciens noms vers les nouveaux noms descriptifs
    content_type_mapping = {
        'Type 8': 'Vidéo',
        'Type 9': 'Audio',
        'Type 10': 'Image',
        'Type 11': 'UGC',
        'Type 12': 'Animation',
        'Type 13': 'Story',
        'Type 15': 'Reel',
        'Type 16': 'Live',
        'Type 17': 'Podcast',
        'Type 77': 'Tutoriel',
        'Type 186': 'Vlog',
        'Type 309': 'Short',
    }
    
    print("Mise à jour des types de contenu...")
    
    updated_count = 0
    for content_type in ContentType.objects.all():
        old_name = content_type.name
        # Vérifier si le nom actuel correspond à un pattern "Type X"
        if old_name in content_type_mapping:
            # Mettre à jour avec le nouveau nom descriptif
            content_type.name = content_type_mapping[old_name]
            content_type.save()
            updated_count += 1
            print(f"  - Mis à jour: '{old_name}' -> '{content_type.name}'")
        else:
            # Si c'est un pattern "Type X" mais pas dans notre mapping
            match = re.match(r'Type (\d+)', old_name)
            if match:
                print(f"  - Non mis à jour (pas dans le mapping): '{old_name}'")
    
    print(f"\nTerminé: {updated_count} types de contenu mis à jour.")

if __name__ == "__main__":
    update_content_types() 