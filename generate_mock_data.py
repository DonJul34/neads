#!/usr/bin/env python
import os
import sys
import random
import django
from decimal import Decimal

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neads.settings')
django.setup()

from django.utils import timezone
from django.core.files.base import ContentFile
from django.core.files import File
from django.db import transaction

from neads.core.models import User, UserProfile
from neads.creators.models import Creator, Domain, Location, Media, Rating, Favorite

# Import de Faker pour la génération de données réalistes
try:
    from faker import Faker
except ImportError:
    print("Le module 'faker' est requis. Installez-le avec: pip install faker")
    sys.exit(1)

# Initialisation de Faker
fake = Faker('fr_FR')

# Constantes de configuration
NUM_DOMAINS = 10
NUM_CLIENTS = 15
NUM_CONSULTANTS = 5
NUM_CREATORS = 25
NUM_RATINGS_PER_CREATOR = 8
NUM_FAVORITES_PER_USER = 5
DEFAULT_PASSWORD = "neads2025"  # Mot de passe par défaut pour tous les utilisateurs


def create_domains():
    """Crée plusieurs domaines d'expertise"""
    domains = [
        {'name': 'Mode', 'icon': 'fa-tshirt'},
        {'name': 'Beauté', 'icon': 'fa-magic'},
        {'name': 'Lifestyle', 'icon': 'fa-home'},
        {'name': 'Voyage', 'icon': 'fa-plane'},
        {'name': 'Food', 'icon': 'fa-utensils'},
        {'name': 'Fitness', 'icon': 'fa-dumbbell'},
        {'name': 'Tech', 'icon': 'fa-laptop'},
        {'name': 'Gaming', 'icon': 'fa-gamepad'},
        {'name': 'Musique', 'icon': 'fa-music'},
        {'name': 'Art', 'icon': 'fa-palette'},
        {'name': 'Danse', 'icon': 'fa-music'},
        {'name': 'Automobile', 'icon': 'fa-car'},
    ]
    
    created_domains = []
    for domain_data in domains:
        domain, created = Domain.objects.get_or_create(
            name=domain_data['name'],
            defaults={'icon': domain_data['icon']}
        )
        created_domains.append(domain)
    
    return created_domains


def create_locations(num_locations=50):
    """Crée plusieurs emplacements géographiques avec coordonnées"""
    locations = []
    
    # Villes françaises avec coordonnées approximatives
    cities = [
        {'city': 'Paris', 'country': 'France', 'postal_code': '75000', 'lat': 48.8566, 'lng': 2.3522},
        {'city': 'Lyon', 'country': 'France', 'postal_code': '69000', 'lat': 45.7640, 'lng': 4.8357},
        {'city': 'Marseille', 'country': 'France', 'postal_code': '13000', 'lat': 43.2965, 'lng': 5.3698},
        {'city': 'Bordeaux', 'country': 'France', 'postal_code': '33000', 'lat': 44.8378, 'lng': -0.5792},
        {'city': 'Lille', 'country': 'France', 'postal_code': '59000', 'lat': 50.6292, 'lng': 3.0573},
        {'city': 'Toulouse', 'country': 'France', 'postal_code': '31000', 'lat': 43.6047, 'lng': 1.4442},
        {'city': 'Nice', 'country': 'France', 'postal_code': '06000', 'lat': 43.7102, 'lng': 7.2620},
        {'city': 'Nantes', 'country': 'France', 'postal_code': '44000', 'lat': 47.2184, 'lng': -1.5536},
        {'city': 'Strasbourg', 'country': 'France', 'postal_code': '67000', 'lat': 48.5734, 'lng': 7.7521},
        {'city': 'Montpellier', 'country': 'France', 'postal_code': '34000', 'lat': 43.6108, 'lng': 3.8767},
        {'city': 'Rennes', 'country': 'France', 'postal_code': '35000', 'lat': 48.1173, 'lng': -1.6778},
        {'city': 'Reims', 'country': 'France', 'postal_code': '51100', 'lat': 49.2583, 'lng': 4.0317},
        {'city': 'Toulon', 'country': 'France', 'postal_code': '83000', 'lat': 43.1257, 'lng': 5.9304},
        {'city': 'Grenoble', 'country': 'France', 'postal_code': '38000', 'lat': 45.1885, 'lng': 5.7245},
        {'city': 'Angers', 'country': 'France', 'postal_code': '49000', 'lat': 47.4784, 'lng': -0.5632},
    ]
    
    for city_data in cities:
        # Ajoute une légère variation aux coordonnées pour créer plusieurs points dans la même ville
        for _ in range(num_locations // len(cities) + 1):
            lat_variation = random.uniform(-0.02, 0.02)
            lng_variation = random.uniform(-0.02, 0.02)
            
            location = Location.objects.create(
                city=city_data['city'],
                country=city_data['country'],
                postal_code=city_data['postal_code'],
                latitude=city_data['lat'] + lat_variation,
                longitude=city_data['lng'] + lng_variation
            )
            locations.append(location)
            
            if len(locations) >= num_locations:
                break
    
    return locations[:num_locations]


def create_users():
    """Crée des utilisateurs: admins, consultants et clients"""
    users = {
        'admins': [],
        'consultants': [],
        'clients': [],
    }
    
    # Admin
    admin_user, created = User.objects.get_or_create(
        email='admin@neads.com',
        defaults={
            'first_name': 'Admin',
            'last_name': 'NEADS',
            'role': 'admin',
            'is_staff': True,
            'is_superuser': True
        }
    )
    
    if created:
        admin_user.set_password(DEFAULT_PASSWORD)
        admin_user.save()
        UserProfile.objects.create(user=admin_user)
    
    users['admins'].append(admin_user)
    
    # Consultants
    for i in range(NUM_CONSULTANTS):
        first_name = fake.first_name()
        last_name = fake.last_name().upper()
        email = f"consultant{i+1}@neads.com"
        
        consultant, created = User.objects.get_or_create(
            email=email,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'role': 'consultant',
                'is_staff': True
            }
        )
        
        if created:
            consultant.set_password(DEFAULT_PASSWORD)
            consultant.save()
            
            profile = UserProfile.objects.create(
                user=consultant,
                phone_number=fake.phone_number(),
                company_name="NEADS Consulting",
                verified_email=True
            )
        
        users['consultants'].append(consultant)
    
    # Clients
    for i in range(NUM_CLIENTS):
        first_name = fake.first_name()
        last_name = fake.last_name().upper()
        email = f"client{i+1}@example.com"
        
        client, created = User.objects.get_or_create(
            email=email,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'role': 'client'
            }
        )
        
        if created:
            client.set_password(DEFAULT_PASSWORD)
            client.save()
            
            profile = UserProfile.objects.create(
                user=client,
                phone_number=fake.phone_number(),
                company_name=fake.company() if random.random() > 0.5 else None,
                verified_email=random.random() > 0.3
            )
        
        users['clients'].append(client)
    
    return users


def create_creators(domains, locations, users):
    """Crée des créateurs avec associations aux domaines et emplacements"""
    creators = []
    
    equipment_options = [
        "Canon EOS R5, iPhone 13 Pro",
        "Sony Alpha 7 III, GoPro Hero 10",
        "iPhone 14 Pro, Ring Light, Trépied",
        "Nikon Z6, DJI Osmo Mobile 5",
        "Canon EOS 90D, Studio d'enregistrement maison",
        "Appareil photo reflex, Drone DJI Mini 3",
        "Smartphone haut de gamme uniquement",
        "Studio photo complet, éclairage professionnel",
        "Matériel audio professionnel, caméra 4K",
        "iPhone, caméra Sony, micro Rode"
    ]
    
    delivery_options = [
        "24h à 48h",
        "3-5 jours",
        "Moins de 24h",
        "1 semaine",
        "2-3 jours",
        "24h (rush: +50%)",
        "48h garanties",
        "5 jours ouvrés",
        "Selon projet (3-7 jours)",
        "Express: 24h / Standard: 3 jours"
    ]
    
    content_types = [option[0] for option in Creator.CONTENT_TYPE_CHOICES]
    
    for i in range(NUM_CREATORS):
        first_name = fake.first_name()
        last_name = fake.last_name().upper()
        email = f"creator{i+1}@example.com"
        
        # Décide si ce créateur a un compte utilisateur associé
        has_user_account = random.random() > 0.3
        user = None
        
        if has_user_account:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'role': 'creator'
                }
            )
            
            if created:
                user.set_password(DEFAULT_PASSWORD)
                user.save()
                
                UserProfile.objects.create(
                    user=user,
                    phone_number=fake.phone_number(),
                    verified_email=random.random() > 0.2
                )
        
        # Créer le créateur
        creator = Creator.objects.create(
            user=user,
            first_name=first_name,
            last_name=last_name,
            age=random.randint(18, 45),
            gender=random.choice(['M', 'F', 'O']),
            location=random.choice(locations),
            email=email,
            phone=fake.phone_number() if random.random() > 0.3 else None,
            bio=fake.text(max_nb_chars=300) if random.random() > 0.2 else None,
            equipment=random.choice(equipment_options) if random.random() > 0.3 else None,
            delivery_time=random.choice(delivery_options) if random.random() > 0.3 else None,
            content_types=random.choice(content_types),
            mobility=random.random() > 0.5,
            can_invoice=random.random() > 0.4,
            previous_clients=", ".join(fake.company() for _ in range(random.randint(1, 5))) if random.random() > 0.5 else None,
            verified_by_neads=random.random() > 0.7,
            last_activity=timezone.now() - timezone.timedelta(days=random.randint(0, 30))
        )
        
        # Associer aléatoirement 1 à 3 domaines
        num_domains = random.randint(1, 3)
        selected_domains = random.sample(domains, num_domains)
        creator.domains.add(*selected_domains)
        
        creators.append(creator)
    
    return creators


def create_ratings(creators, users):
    """Crée des évaluations pour les créateurs"""
    
    comments = [
        "Très professionnel, livraison dans les délais.",
        "Excellent travail, je recommande vivement !",
        "Bonne qualité mais délais un peu longs.",
        "Résultat parfait, exactement ce que je cherchais.",
        "Communication facile et résultat de qualité.",
        "Un peu cher mais la qualité est au rendez-vous.",
        "Super créateur, travail soigné et rapide.",
        "Très créatif, a su comprendre parfaitement ma demande.",
        "Je suis très satisfait de notre collaboration.",
        "Léger retard de livraison mais le résultat en valait la peine.",
        "Excellente prestation, je ferai à nouveau appel à ses services.",
        "Qualité irréprochable, un vrai professionnel.",
        "Créativité et réactivité, que demander de plus ?",
        "A su s'adapter à mes demandes de modifications.",
        "Un plaisir de travailler avec ce créateur.",
        None  # Certains avis sans commentaire
    ]
    
    for creator in creators:
        # Nombre aléatoire de notes entre 0 et max
        num_ratings = random.randint(0, NUM_RATINGS_PER_CREATOR)
        
        # Utilisateurs qui vont noter (clients et consultants)
        potential_raters = users['clients'] + users['consultants']
        selected_raters = random.sample(potential_raters, min(num_ratings, len(potential_raters)))
        
        for user in selected_raters:
            # Les consultants donnent généralement de meilleures notes
            if user.role == 'consultant':
                rating_value = random.randint(3, 5)
                is_verified = True
                verified_by = user
            else:
                rating_value = random.randint(1, 5)
                # 50% de chances qu'un avis client soit vérifié par un consultant
                is_verified = random.random() > 0.5
                verified_by = random.choice(users['consultants']) if is_verified else None
            
            comment = random.choice(comments)
            
            Rating.objects.create(
                creator=creator,
                user=user,
                rating=rating_value,
                comment=comment,
                is_verified=is_verified,
                verified_by=verified_by,
                created_at=timezone.now() - timezone.timedelta(days=random.randint(0, 60))
            )


def create_favorites(creators, users):
    """Crée des favoris pour les utilisateurs"""
    for user in users['clients'] + users['consultants']:
        # Nombre aléatoire de favoris entre 0 et max
        num_favorites = random.randint(0, min(NUM_FAVORITES_PER_USER, len(creators)))
        
        if num_favorites > 0:
            selected_creators = random.sample(creators, num_favorites)
            
            for creator in selected_creators:
                notes = fake.text(max_nb_chars=100) if random.random() > 0.7 else None
                
                Favorite.objects.create(
                    creator=creator,
                    user=user,
                    notes=notes,
                    created_at=timezone.now() - timezone.timedelta(days=random.randint(0, 30))
                )


def create_media_for_creators(creators):
    """Crée des médias fictifs pour les créateurs"""
    # Comme nous n'avons pas accès aux fichiers réels, nous allons ajouter des entrées fictives
    # Dans un environnement réel, il faudrait télécharger ou générer des images/vidéos réelles
    
    media_titles = [
        "Projet commercial pour marque lifestyle",
        "Shooting produit cosmétique",
        "Contenu UGC pour réseau social",
        "Vidéo promotionnelle",
        "Présentation de produit",
        "Photo d'ambiance",
        "Collaboration avec marque",
        "Contenu éditorial",
        "Campagne publicitaire",
        "Projet personnel"
    ]
    
    media_descriptions = [
        "Réalisé en studio avec éclairage professionnel",
        "Shooting en extérieur, lumière naturelle",
        "Format vertical optimisé pour Instagram",
        "Montage réalisé avec Adobe Premiere Pro",
        "Shot avec iPhone dernière génération",
        "Retouches professionnelles sous Lightroom",
        "Prise de vue en 4K",
        "Style minimaliste et épuré",
        "Montage dynamique avec transitions",
        None
    ]
    
    total_media = 0
    
    for creator in creators:
        # Nombre aléatoire d'images entre 0 et 5
        num_images = random.randint(0, 5)
        
        for i in range(num_images):
            # Création d'entrées fictives pour les images
            Media.objects.create(
                creator=creator,
                title=random.choice(media_titles) if random.random() > 0.3 else None,
                description=random.choice(media_descriptions) if random.random() > 0.5 else None,
                media_type='image',
                file=None,  # Explicitement None pour éviter les erreurs
                order=i,
                is_verified=random.random() > 0.3,
                upload_date=timezone.now() - timezone.timedelta(days=random.randint(0, 90))
            )
            total_media += 1
        
        # Nombre aléatoire de vidéos entre 0 et 3
        num_videos = random.randint(0, 3)
        
        for i in range(num_videos):
            # Création d'entrées fictives pour les vidéos
            Media.objects.create(
                creator=creator,
                title=random.choice(media_titles) if random.random() > 0.3 else None,
                description=random.choice(media_descriptions) if random.random() > 0.5 else None,
                media_type='video',
                file=None,  # Explicitement None pour éviter les erreurs
                video_file=None,  # Explicitement None pour éviter les erreurs
                thumbnail=None,  # Explicitement None pour éviter les erreurs
                duration=random.randint(10, 180),  # Durée entre 10s et 3min
                order=i,
                is_verified=random.random() > 0.3,
                upload_date=timezone.now() - timezone.timedelta(days=random.randint(0, 90))
            )
            total_media += 1
    
    return total_media


@transaction.atomic
def run():
    """Fonction principale pour générer toutes les données"""
    print("Génération des données de test pour NEADS...")
    
    print("1. Création des domaines d'expertise...")
    domains = create_domains()
    print(f"   ✓ {len(domains)} domaines créés")
    
    print("2. Création des localisations...")
    locations = create_locations()
    print(f"   ✓ {len(locations)} emplacements créés")
    
    print("3. Création des utilisateurs...")
    users = create_users()
    print(f"   ✓ {len(users['admins'])} admin(s) créé(s)")
    print(f"   ✓ {len(users['consultants'])} consultant(s) créé(s)")
    print(f"   ✓ {len(users['clients'])} client(s) créé(s)")
    
    print("4. Création des créateurs...")
    creators = create_creators(domains, locations, users)
    print(f"   ✓ {len(creators)} créateurs créés")
    
    print("5. Création des évaluations...")
    create_ratings(creators, users)
    total_ratings = Rating.objects.count()
    print(f"   ✓ {total_ratings} évaluations créées")
    
    print("6. Création des favoris...")
    create_favorites(creators, users)
    total_favorites = Favorite.objects.count()
    print(f"   ✓ {total_favorites} favoris créés")
    
    print("7. Création des médias...")
    total_media = create_media_for_creators(creators)
    print(f"   ✓ {total_media} médias créés")
    
    print("\nGénération terminée avec succès!")
    print("\nComptes utilisateurs créés:")
    print(f"- Admin: admin@neads.com / {DEFAULT_PASSWORD}")
    print(f"- Consultants: consultant1@neads.com à consultant{NUM_CONSULTANTS}@neads.com / {DEFAULT_PASSWORD}")
    print(f"- Clients: client1@example.com à client{NUM_CLIENTS}@example.com / {DEFAULT_PASSWORD}")
    print(f"- Créateurs avec comptes: Vérifiez les emails creator*@example.com dans l'admin / {DEFAULT_PASSWORD}")


if __name__ == "__main__":
    run() 