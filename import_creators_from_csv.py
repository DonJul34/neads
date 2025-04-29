#!/usr/bin/env python
import os
import sys
import csv
import django
from django.utils import timezone
from django.core.files.base import ContentFile
import requests
from urllib.parse import urlparse
import re
import random
import time
import string

# Configurer l'environnement Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neads.settings')
django.setup()

# Importer les modèles après la configuration de Django
from neads.creators.models import Creator, Domain, ContentType, Location, Media
from neads.core.models import User
from django.contrib.auth.models import Group

# Cache pour les coordonnées géographiques (évite les requêtes répétées à l'API)
GEOCODE_CACHE = {}

def generate_random_password(length=12):
    """
    Génère un mot de passe aléatoire sécurisé.
    """
    # Caractères pour le mot de passe (lettres, chiffres, caractères spéciaux)
    chars = string.ascii_letters + string.digits + '!@#$%^&*()_+'
    # Générer le mot de passe
    return ''.join(random.choice(chars) for _ in range(length))

def get_or_create_creator_user(email, first_name, last_name):
    """
    Crée un utilisateur pour un créateur si nécessaire.
    Retourne un tuple (user, password) où password est None si l'utilisateur existait déjà.
    """
    if not email:
        return None, None
        
    try:
        # Essayer de récupérer un utilisateur existant
        user = User.objects.get(email=email)
        return user, None  # Utilisateur existant, pas de nouveau mot de passe
    except User.DoesNotExist:
        # Générer un mot de passe aléatoire
        password = generate_random_password()
        
        # Créer l'utilisateur (notre modèle User utilise l'email comme identifiant unique)
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        # Par défaut, définir le rôle comme "creator" si le champ existe
        if hasattr(User, 'role'):
            user.role = 'creator'
            user.save()
        
        # Ajouter l'utilisateur au groupe "creators" s'il existe
        try:
            creators_group = Group.objects.get(name='creators')
            user.groups.add(creators_group)
        except Group.DoesNotExist:
            # Créer le groupe s'il n'existe pas
            creators_group = Group.objects.create(name='creators')
            user.groups.add(creators_group)
        
        return user, password

def geocode_address(address, city, postal_code, country):
    """
    Utilise l'API Nominatim pour géocoder une adresse internationale.
    Ajoute une légère variation aléatoire pour éviter des points exacts superposés.
    Inclut un cache pour éviter les requêtes répétées.
    """
    # S'assurer que le pays est spécifié, sinon utiliser France par défaut
    if not country or country.strip() == '':
        country = 'France'
        
    # Normaliser l'adresse pour la clé de cache
    cache_key = f"{city.lower() if city else ''}, {postal_code}, {country}"
    
    # Vérifier le cache
    if cache_key in GEOCODE_CACHE:
        base_lat, base_lng = GEOCODE_CACHE[cache_key]
    else:
        # Construire l'adresse de recherche
        search_address = f"{city}, {postal_code}, {country}"
        
        # Utiliser l'API Nominatim (OpenStreetMap)
        nominatim_url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': search_address,
            'format': 'json',
            'limit': 1,
            'addressdetails': 1
        }
        
        # Ajouter un header d'agent utilisateur (requis par Nominatim)
        headers = {
            'User-Agent': 'NEADS Creators Import Script (contact@neads.io)'
        }
        
        try:
            # Attendre pour respecter la limitation de l'API (1 requête/seconde max)
            time.sleep(1)
            
            response = requests.get(nominatim_url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if data and len(data) > 0:
                # Extraire les coordonnées
                base_lat = float(data[0]['lat'])
                base_lng = float(data[0]['lon'])
                
                # Mettre en cache les résultats
                GEOCODE_CACHE[cache_key] = (base_lat, base_lng)
                print(f"Coordonnées trouvées pour {search_address}: {base_lat}, {base_lng}")
            else:
                # Essayons juste avec la ville et le pays si l'adresse complète échoue
                search_address = f"{city}, {country}"
                params['q'] = search_address
                
                # Attendre à nouveau avant une nouvelle requête
                time.sleep(1)
                
                response = requests.get(nominatim_url, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                if data and len(data) > 0:
                    # Extraire les coordonnées
                    base_lat = float(data[0]['lat'])
                    base_lng = float(data[0]['lon'])
                    
                    # Mettre en cache les résultats
                    GEOCODE_CACHE[cache_key] = (base_lat, base_lng)
                    print(f"Coordonnées trouvées pour {search_address}: {base_lat}, {base_lng}")
                else:
                    # Si tout échoue, utiliser des coordonnées par défaut selon le pays
                    print(f"Échec de géocodage pour {search_address}, utilisation des coordonnées par défaut")
                    
                    # Dictionnaire des centres approximatifs des pays
                    country_fallbacks = {
                        'France': (46.603354, 1.888334),
                        'Switzerland': (46.8182, 8.2275),
                        'Suisse': (46.8182, 8.2275),
                        'Belgium': (50.5039, 4.4699),
                        'Belgique': (50.5039, 4.4699),
                        'Canada': (56.1304, -106.3468),
                        'USA': (37.0902, -95.7129),
                        'États-Unis': (37.0902, -95.7129),
                        'United Kingdom': (55.3781, -3.4360),
                        'Royaume-Uni': (55.3781, -3.4360),
                        'Germany': (51.1657, 10.4515),
                        'Allemagne': (51.1657, 10.4515),
                        'Spain': (40.4637, -3.7492),
                        'Espagne': (40.4637, -3.7492),
                        'Italy': (41.8719, 12.5674),
                        'Italie': (41.8719, 12.5674)
                    }
                    
                    # Utiliser les coordonnées du pays spécifié ou un point au centre de l'Europe
                    base_lat, base_lng = country_fallbacks.get(country, (48.8566, 2.3522))
        except Exception as e:
            print(f"Erreur lors du géocodage de {search_address}: {str(e)}")
            # Utiliser des coordonnées par défaut selon le pays (même mapping que ci-dessus)
            country_fallbacks = {
                'France': (46.603354, 1.888334),
                'Switzerland': (46.8182, 8.2275),
                'Suisse': (46.8182, 8.2275),
                'Belgium': (50.5039, 4.4699),
                'Belgique': (50.5039, 4.4699),
                'Canada': (56.1304, -106.3468),
                'USA': (37.0902, -95.7129),
                'États-Unis': (37.0902, -95.7129),
                'United Kingdom': (55.3781, -3.4360),
                'Royaume-Uni': (55.3781, -3.4360),
                'Germany': (51.1657, 10.4515),
                'Allemagne': (51.1657, 10.4515),
                'Spain': (40.4637, -3.7492),
                'Espagne': (40.4637, -3.7492),
                'Italy': (41.8719, 12.5674),
                'Italie': (41.8719, 12.5674)
            }
            base_lat, base_lng = country_fallbacks.get(country, (48.8566, 2.3522))
    
    # Ajouter une légère variation aléatoire (±500 mètres environ)
    # 0.005 degré ≈ 500 mètres à cette latitude
    lat_variation = random.uniform(-0.005, 0.005)
    lng_variation = random.uniform(-0.005, 0.005)
    
    return base_lat + lat_variation, base_lng + lng_variation

def clean_url(url):
    """Nettoie les URLs pour n'en extraire qu'une seule."""
    if not url:
        return None
    # Prendre la première URL si plusieurs sont présentes (séparées par '|')
    if '|' in url:
        url = url.split('|')[0]
    return url.strip()

def extract_filename_from_url(url):
    """Extrait le nom du fichier depuis une URL."""
    if not url:
        return None
    parsed_url = urlparse(url)
    path = parsed_url.path
    filename = os.path.basename(path)
    return filename

def download_file_from_url(url, creator_id, file_type='image', is_featured=False):
    """
    Télécharge un fichier depuis une URL et le prépare pour Django.
    Retourne un tuple (nom_fichier, contenu_fichier).
    """
    try:
        # S'assurer que l'URL est valide
        if not url or not url.startswith('http'):
            return None, None

        # Créer le chemin pour le stockage du fichier
        media_dir = 'creators'
        creator_dir = f"{creator_id}"
        
        # Déterminer le dossier de destination selon le type et si c'est une image mise en avant
        if is_featured:
            type_dir = 'featured'
        else:
            type_dir = 'images' if file_type == 'image' else 'videos'
        
        # Assurer que le répertoire existe
        os.makedirs(os.path.join('media', media_dir, creator_dir, type_dir), exist_ok=True)
        
        # Extraire le nom du fichier original
        original_filename = extract_filename_from_url(url)
        if not original_filename:
            # Générer un nom si l'extraction échoue
            ext = '.jpg' if file_type == 'image' else '.mp4'
            original_filename = f"{timezone.now().timestamp()}_{creator_id}{ext}"
            
        # Préfixer le nom pour les images mises en avant
        if is_featured:
            original_filename = f"featured_{original_filename}"
        
        # Télécharger le fichier
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()  # Lève une exception pour les erreurs HTTP
        
        # Créer le fichier sur le disque
        file_path = os.path.join('media', media_dir, creator_dir, type_dir, original_filename)
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Chemin relatif pour la base de données
        db_path = os.path.join(media_dir, creator_dir, type_dir, original_filename)
        
        print(f"Fichier téléchargé: {file_path}")
        return db_path, original_filename
        
    except Exception as e:
        print(f"Erreur lors du téléchargement de {url}: {str(e)}")
        return None, None

def parse_gender(gender_value):
    """Convertit le genre au format attendu par le modèle."""
    gender_map = {
        'Homme': 'M',
        'Femme': 'F',
        'Autre': 'O'
    }
    return gender_map.get(gender_value, 'O')

def calculate_age(birth_year):
    """Calcule l'âge à partir de l'année de naissance."""
    if not birth_year or not birth_year.isdigit():
        return 25  # Valeur par défaut si l'année n'est pas valide
    birth_year = int(birth_year)
    current_year = timezone.now().year
    return current_year - birth_year

def clean_duplicate_media(creator_id=None):
    """
    Nettoie les médias en double pour un créateur ou tous les créateurs.
    Les doublons sont identifiés par des noms de fichiers similaires.
    """
    from django.db.models import Count
    
    print("Nettoyage des médias en double...")
    
    # Filtrer par créateur si spécifié
    media_query = Media.objects
    if creator_id:
        media_query = media_query.filter(creator_id=creator_id)
        print(f"Nettoyage pour le créateur ID: {creator_id}")
    
    # Compter les médias avant nettoyage
    total_before = media_query.count()
    
    # Pour les images
    images = media_query.filter(media_type='image')
    
    # Identifier les doublons d'images en regroupant par créateur et nom de fichier
    image_duplicates = []
    for creator in Creator.objects.all():
        creator_images = images.filter(creator=creator)
        seen_filenames = set()
        
        for media in creator_images:
            if not media.file:
                continue
                
            filename = os.path.basename(media.file.name)
            
            # Si on a déjà vu ce nom de fichier, c'est un doublon
            if filename in seen_filenames:
                image_duplicates.append(media.id)
            else:
                seen_filenames.add(filename)
    
    # Pour les vidéos
    videos = media_query.filter(media_type='video')
    
    # Identifier les doublons de vidéos
    video_duplicates = []
    for creator in Creator.objects.all():
        creator_videos = videos.filter(creator=creator)
        seen_filenames = set()
        
        for media in creator_videos:
            if not media.video_file:
                continue
                
            filename = os.path.basename(media.video_file.name)
            
            # Si on a déjà vu ce nom de fichier, c'est un doublon
            if filename in seen_filenames:
                video_duplicates.append(media.id)
            else:
                seen_filenames.add(filename)
    
    # Supprimer les doublons
    if image_duplicates:
        Media.objects.filter(id__in=image_duplicates).delete()
        print(f"Suppression de {len(image_duplicates)} images en double")
    
    if video_duplicates:
        Media.objects.filter(id__in=video_duplicates).delete()
        print(f"Suppression de {len(video_duplicates)} vidéos en double")
    
    # Compter les médias après nettoyage
    total_after = media_query.count()
    print(f"Nettoyage terminé: {total_before - total_after} médias supprimés")

def import_creators_from_csv(csv_path, clean_duplicates=True):
    print(f"Importation des créateurs depuis {csv_path}")
    
    # Créer un fichier pour stocker les mots de passe générés
    passwords_file = "creators_passwords.txt"
    with open(passwords_file, 'w', encoding='utf-8') as pwd_file:
        pwd_file.write("Email,Mot de passe\n")
    
    with open(csv_path, 'r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file)
        
        # Compteurs
        total_rows = 0
        imported_count = 0
        error_count = 0
        users_created = 0
        
        # Liste des IDs des créateurs mis à jour pour nettoyage ultérieur
        updated_creator_ids = []
        
        for row in csv_reader:
            total_rows += 1
            try:
                # Récupérer ou créer les domaines
                domains_list = []
                if 'Domaines' in row and row['Domaines']:
                    domain_names = row['Domaines'].split('|')
                    for domain_name in domain_names:
                        domain, created = Domain.objects.get_or_create(name=domain_name.strip())
                        domains_list.append(domain)
                
                # Récupérer ou créer les types de contenu
                content_types_list = []
                content_types_fields = ['connaitre_connaitre_domaines', 'propos_propos_adresse_pays']
                for field in content_types_fields:
                    if field in row and row[field]:
                        # Extraire les IDs des types de contenu
                        content_type_ids = re.findall(r'"(\d+)"', row[field])
                        for content_type_id in content_type_ids:
                            # Correspondance des IDs vers des noms de type (à adapter)
                            content_type_name = f"Type {content_type_id}"
                            content_type, created = ContentType.objects.get_or_create(name=content_type_name)
                            content_types_list.append(content_type)
                
                # Récupérer les données d'adresse
                address = row.get('propos_propos_adresse', '')
                city = row.get('propos_propos_adresse_ville', '')
                postal_code = row.get('propos_propos_adresse_cp', '')
                country = row.get('Pays', 'France')
                
                # Informations personnelles du créateur
                first_name = row.get('propos_propos_prenom', '')
                last_name = row.get('propos_propos_nom', '')
                email = row.get('propos_propos_email', '')
                
                # Créer un utilisateur pour le créateur
                user, password = get_or_create_creator_user(email, first_name, last_name)
                
                # Si un nouvel utilisateur a été créé avec un mot de passe, l'enregistrer dans le fichier
                if user and password:
                    users_created += 1
                    with open(passwords_file, 'a', encoding='utf-8') as pwd_file:
                        pwd_file.write(f"{email},{password}\n")
                    print(f"Utilisateur créé pour {first_name} {last_name} ({email})")
                
                # Générer les coordonnées approximatives en utilisant le pays exact
                latitude, longitude = geocode_address(address, city, postal_code, country)
                
                # Créer ou récupérer la localisation
                location_data = {
                    'full_address': f"{address} {city} {postal_code} {country}".strip(),
                    'latitude': latitude,
                    'longitude': longitude
                }
                location, created = Location.objects.get_or_create(**location_data)
                
                # Créer le créateur
                creator_data = {
                    'first_name': first_name,
                    'last_name': last_name,
                    'age': calculate_age(row.get('propos_propos_naissance', '')),
                    'gender': parse_gender(row.get('propos_propos_genre', '')),
                    'email': email,
                    'phone': row.get('propos_propos_telephone', ''),
                    'location': location,
                    'bio': row.get('connaitre_connaitre_propos', ''),
                    'equipment': row.get('connaitre_connaitre_materiel', ''),
                    'youtube_link': row.get('connaitre_connaitre_youtube', ''),
                    'tiktok_link': row.get('connaitre_connaitre_tiktok', ''),
                    'instagram_link': row.get('connaitre_connaitre_instagram', ''),
                    'previous_clients': row.get('connaitre_connaitre_marques', ''),
                    'can_invoice': row.get('propos_propos_statut', '') == 'Oui',
                    'verified_by_neads': True,  # Par défaut, considérons-les comme vérifiés
                    'user': user  # Lier l'utilisateur au créateur
                }
                
                # Nettoyer les champs vides
                creator_data = {k: v for k, v in creator_data.items() if v}
                
                # Créer ou mettre à jour le créateur
                creator, created = Creator.objects.update_or_create(
                    email=creator_data['email'], 
                    defaults=creator_data
                )
                
                # Ajouter les domaines et types de contenu
                creator.domains.set(domains_list)
                creator.content_types.set(content_types_list)
                
                # Stocker les URLs déjà traitées pour éviter les doublons
                processed_urls = set()
                
                # Gestion de l'image mise en avant
                if 'Featured Image URL' in row and row['Featured Image URL']:
                    featured_img_url = clean_url(row['Featured Image URL'])
                    if featured_img_url:
                        processed_urls.add(featured_img_url)  # Ajouter aux URLs traitées
                        
                        # Vérifier si le créateur a déjà une image mise en avant
                        if not creator.featured_image:
                            # Télécharger l'image mise en avant
                            file_path, filename = download_file_from_url(
                                featured_img_url, creator.id, 'image', is_featured=True
                            )
                            if file_path:
                                # Assigner l'image mise en avant au créateur
                                creator.featured_image = file_path
                                creator.save()
                                print(f"  - Image mise en avant ajoutée: {file_path}")
                        else:
                            print(f"  - Le créateur a déjà une image mise en avant, ignoré")
                
                # Gestion des médias (images et vidéos)
                media_fields = {
                    'Image URL': 'image', 
                    'Attachment URL': 'video'
                }
                
                # Variables pour suivre la première image trouvée
                first_image_path = None
                
                for field_name, media_type in media_fields.items():
                    if field_name in row and row[field_name]:
                        media_urls = row[field_name].split('|')
                        for i, url in enumerate(media_urls):
                            url = url.strip()
                            if not url or url in processed_urls:
                                continue
                                
                            # Marquer cette URL comme traitée
                            processed_urls.add(url)
                                
                            # Télécharger le fichier
                            file_path, filename = download_file_from_url(url, creator.id, media_type)
                            if not file_path:
                                print(f"  - Échec du téléchargement pour {url}")
                                continue
                                
                            # Capturer la première image pour l'utiliser comme image mise en avant si nécessaire
                            if media_type == 'image' and first_image_path is None:
                                first_image_path = file_path
                                
                            # Vérifier si un média avec cette URL existe déjà
                            existing_media = None
                            if media_type == 'image':
                                existing_media = Media.objects.filter(
                                    creator=creator, 
                                    media_type=media_type,
                                    file__contains=os.path.basename(file_path)
                                ).first()
                            else:
                                existing_media = Media.objects.filter(
                                    creator=creator, 
                                    media_type=media_type,
                                    video_file__contains=os.path.basename(file_path)
                                ).first()
                                
                            if existing_media:
                                print(f"  - Média déjà existant pour {url}, ignoré")
                                continue
                                
                            # Créer l'objet Media
                            media = Media(
                                creator=creator,
                                title=f"{creator.full_name} Media {i+1}",
                                media_type=media_type,
                                order=i,
                                is_verified=True
                            )
                            
                            # Définir le fichier selon le type
                            if media_type == 'image':
                                media.file = file_path
                            else:  # video
                                media.video_file = file_path
                                # Pour les vidéos, utiliser la première image comme miniature si disponible
                                # sinon laisser vide pour que le front puisse générer une miniature
                                if first_image_path:
                                    media.thumbnail = first_image_path
                            
                            # Enregistrer pour obtenir un ID
                            media.save()
                            
                            print(f"  - Média ajouté: {media.title} ({file_path})")
                
                # Si aucune image mise en avant n'a été trouvée mais qu'on a une première image, l'utiliser
                if not creator.featured_image and first_image_path:
                    creator.featured_image = first_image_path
                    creator.save()
                    print(f"  - Image mise en avant définie automatiquement: {first_image_path}")
                
                # Ajouter l'ID du créateur à la liste pour nettoyage ultérieur
                updated_creator_ids.append(creator.id)
                
                imported_count += 1
                print(f"Créateur importé: {creator.full_name} - Localisation: {latitude:.6f}, {longitude:.6f}")
                
            except Exception as e:
                error_count += 1
                print(f"Erreur lors de l'importation de la ligne {total_rows}: {str(e)}")
        
        # Nettoyage des médias en double
        if clean_duplicates and updated_creator_ids:
            print("\nNettoyage des médias en double...")
            for creator_id in updated_creator_ids:
                clean_duplicate_media(creator_id)
        
        print(f"\nImportation terminée:")
        print(f"  - Total des lignes traitées: {total_rows}")
        print(f"  - Créateurs importés avec succès: {imported_count}")
        print(f"  - Utilisateurs créés: {users_created}")
        print(f"  - Erreurs: {error_count}")
        print(f"\nLes mots de passe ont été enregistrés dans le fichier: {passwords_file}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    else:
        csv_path = "Createurs-Export-2025-April-08-1940.csv"
    
    # Option pour nettoyer ou non les doublons
    clean_duplicates = True
    
    # Si un deuxième argument est fourni et qu'il est 'no-clean', désactiver le nettoyage
    if len(sys.argv) > 2 and sys.argv[2].lower() == 'no-clean':
        clean_duplicates = False
    
    import_creators_from_csv(csv_path, clean_duplicates) 