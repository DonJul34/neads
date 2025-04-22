from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.views.decorators.csrf import csrf_exempt

from neads.core.models import User
from .models import Creator, Media, Rating, Domain, Favorite, Location
from .forms import CreatorForm, MediaUploadForm, RatingForm, CreatorSearchForm, FavoriteForm, LocationForm

import json
import requests
from typing import Dict, List, Any
from math import radians, cos, sin, asin, sqrt


# Fonction utilitaire pour vérifier si un fichier media est valide
def has_valid_file(media_obj):
    """
    Vérifie si un objet Media possède un fichier valide avec une URL.
    Évite les erreurs lorsqu'on tente d'accéder à media.file.url dans les templates.
    """
    try:
        return (media_obj is not None and 
                hasattr(media_obj, 'file') and 
                media_obj.file and 
                media_obj.file.name and 
                hasattr(media_obj.file, 'url'))
    except (ValueError, AttributeError):
        return False


@login_required
def gallery_view(request):
    """
    Vue principale de la galerie des créateurs avec filtres.
    """
    creators = Creator.objects.all().order_by('-average_rating', 'full_name')
    form = CreatorSearchForm(request.GET)
    
    # Appliquer les filtres si le formulaire est valide
    if form.is_valid():
        data = form.cleaned_data
        
        # Filtre par nom/prénom
        if data.get('query'):
            query = data['query']
            creators = creators.filter(
                Q(first_name__icontains=query) | 
                Q(last_name__icontains=query) | 
                Q(full_name__icontains=query)
            )
            
        # Filtre par domaines
        if data.get('domains'):
            creators = creators.filter(domains__in=data['domains']).distinct()
            
        # Filtres par âge
        if data.get('min_age'):
            creators = creators.filter(age__gte=data['min_age'])
        if data.get('max_age'):
            creators = creators.filter(age__lte=data['max_age'])
            
        # Filtre par genre
        if data.get('gender'):
            creators = creators.filter(gender=data['gender'])
            
        # Filtre par type de contenu
        if data.get('content_type'):
            creators = creators.filter(content_types=data['content_type'])
            
        # Filtres géographiques
        if data.get('country'):
            creators = creators.filter(location__country__icontains=data['country'])
        if data.get('city'):
            creators = creators.filter(location__city__icontains=data['city'])
            
        # Filtre par note minimale
        if data.get('min_rating'):
            creators = creators.filter(average_rating__gte=data['min_rating'])
            
        # Autres filtres spécifiques
        if data.get('can_invoice'):
            creators = creators.filter(can_invoice=True)
        if data.get('verified_only'):
            creators = creators.filter(verified_by_neads=True)
    
    # Pagination
    paginator = Paginator(creators, 12)  # 12 créateurs par page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Liste des domaines pour les filtres
    domains = Domain.objects.all()
    
    context = {
        'creators': page_obj,
        'form': form,
        'domains': domains,
        'total_creators': paginator.count,
    }
    
    # Retourner JSON pour les requêtes AJAX
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        creator_data = []
        for creator in page_obj:
            # Images pour la miniature
            thumbnail = None
            if creator.media.filter(media_type='image').exists():
                media_obj = creator.media.filter(media_type='image').first()
                # Vérifier si le fichier existe réellement
                if has_valid_file(media_obj):
                    thumbnail = media_obj.file.url
                
            # Domaines comme badges
            domains = [{'id': d.id, 'name': d.name} for d in creator.domains.all()]
            
            creator_data.append({
                'id': creator.id,
                'full_name': creator.full_name,
                'age': creator.age,
                'gender': creator.get_gender_display(),
                'location': str(creator.location) if creator.location else "",
                'rating': float(creator.average_rating),
                'total_ratings': creator.total_ratings,
                'thumbnail': thumbnail,
                'domains': domains,
                'verified': creator.verified_by_neads,
            })
            
        return JsonResponse({
            'creators': creator_data,
            'page': page_number,
            'total_pages': paginator.num_pages,
            'total_creators': paginator.count,
        })
        
    return render(request, 'creators/gallery.html', context)


@login_required
def creator_detail(request, creator_id):
    """
    Vue détaillée d'un créateur avec son portfolio et ses informations.
    Accès différenciés selon le rôle de l'utilisateur.
    """
    creator = get_object_or_404(Creator, id=creator_id)
    
    # Vérifier les restrictions d'accès pour les créateurs
    # Un créateur ne peut voir que sa propre fiche
    if request.user.role == 'creator':
        try:
            # Vérifier si l'utilisateur est lié au profil créateur consulté
            if not hasattr(request.user, 'creator_profile') or request.user.creator_profile.id != creator_id:
                return HttpResponseForbidden("Vous n'êtes pas autorisé à consulter ce profil.")
        except Exception as e:
            # Journaliser l'erreur et renvoyer une erreur d'accès
            print(f"Erreur de vérification d'accès créateur: {str(e)}")
            return HttpResponseForbidden("Vous n'avez pas accès à ce profil.")
    
    # Charger médias triés par type et ordre
    images = creator.media.filter(media_type='image').order_by('order')
    videos = creator.media.filter(media_type='video').order_by('order')
    
    # Filtrer les médias sans fichiers pour éviter les erreurs
    valid_images = []
    for image in images:
        if has_valid_file(image):
            valid_images.append(image)
            
    valid_videos = []
    for video in videos:
        if has_valid_file(video):
            valid_videos.append(video)
    
    # Informations de notation
    ratings = creator.ratings.filter(is_verified=True).order_by('-created_at')
    rating_breakdown = {
        5: ratings.filter(rating=5).count(),
        4: ratings.filter(rating=4).count(),
        3: ratings.filter(rating=3).count(),
        2: ratings.filter(rating=2).count(),
        1: ratings.filter(rating=1).count(),
    }
    
    # Vérifier si l'utilisateur a déjà noté ce créateur
    user_rating = None
    is_favorite = False
    if request.user.is_authenticated:
        user_rating = creator.ratings.filter(user=request.user).first()
        is_favorite = Favorite.objects.filter(user=request.user, creator=creator).exists()
    
    # Formulaires - conditions selon les rôles
    rating_form = None
    favorite_form = None
    
    # Les consultants et admins peuvent noter les créateurs
    if request.user.role in ['admin', 'consultant']:
        rating_form = RatingForm(instance=user_rating)
        favorite_form = FavoriteForm()
    
    # Déterminer si l'utilisateur peut modifier la fiche
    can_edit = False
    if request.user.role in ['admin', 'consultant'] or (request.user.role == 'creator' and hasattr(request.user, 'creator_profile') and request.user.creator_profile.id == creator_id):
        can_edit = True
    
    # Déterminer si l'utilisateur peut envoyer un message au créateur
    can_message = request.user.role in ['admin', 'consultant']
    
    # Déterminer si l'utilisateur peut voir les informations personnelles
    can_view_personal_info = request.user.role != 'client'
    
    # Pour les clients, masquer le nom de famille (sauf première lettre)
    if request.user.role == 'client':
        last_name_masked = creator.last_name[0] + '.' if creator.last_name else ''
    else:
        last_name_masked = creator.last_name
    
    context = {
        'creator': creator,
        'images': valid_images,
        'videos': valid_videos,
        'ratings': ratings,
        'rating_breakdown': rating_breakdown,
        'rating_form': rating_form,
        'favorite_form': favorite_form,
        'user_rating': user_rating,
        'is_favorite': is_favorite,
        'can_edit': can_edit,
        'can_message': can_message,
        'can_view_personal_info': can_view_personal_info,
        'is_client': request.user.role == 'client',
        'is_creator': request.user.role == 'creator',
        'is_admin': request.user.role == 'admin',
        'is_consultant': request.user.role == 'consultant',
        'last_name_masked': last_name_masked,
    }
    
    return render(request, 'creators/creator_detail.html', context)


@login_required
def creator_edit(request, creator_id):
    """
    Vue pour éditer les informations d'un créateur.
    """
    creator = get_object_or_404(Creator, id=creator_id)
    
    # Vérifier les permissions (propriétaire ou staff)
    if not (request.user == creator.user or request.user.is_staff):
        return HttpResponseForbidden("Vous n'avez pas les droits pour modifier ce profil.")
    
    # Si le créateur a déjà une localisation, l'utiliser, sinon en créer une nouvelle
    location = creator.location
    if location is None:
        location = Location()
    
    if request.method == 'POST':
        form = CreatorForm(request.POST, instance=creator)
        location_form = LocationForm(request.POST, instance=location)
        
        # Vérifier si les deux formulaires sont valides
        if form.is_valid() and location_form.is_valid():
            # Sauvegarder la localisation d'abord
            location = location_form.save()
            
            # Puis sauvegarder le créateur avec la référence à la localisation
            creator = form.save(commit=False)
            creator.location = location
            creator.save()
            
            # Enregistrer les relations ManyToMany
            form.save_m2m()
            
            return redirect('creator_detail', creator_id=creator.id)
    else:
        form = CreatorForm(instance=creator)
        location_form = LocationForm(instance=location)
    
    context = {
        'form': form,
        'location_form': location_form,
        'creator': creator,
    }
    
    return render(request, 'creators/creator_edit.html', context)


@login_required
@require_POST
def rate_creator(request, creator_id):
    """
    Vue pour noter un créateur.
    """
    creator = get_object_or_404(Creator, id=creator_id)
    
    # Vérifier les permissions (seuls les consultants/clients peuvent noter)
    if not (request.user.has_role('consultant') or request.user.has_role('client')):
        return HttpResponseForbidden("Vous n'avez pas les droits pour noter un créateur.")
    
    # Récupérer ou créer la note
    try:
        rating = Rating.objects.get(creator=creator, user=request.user)
    except Rating.DoesNotExist:
        rating = Rating(creator=creator, user=request.user)
    
    form = RatingForm(request.POST, instance=rating)
    if form.is_valid():
        rating = form.save(commit=False)
        
        # Auto-vérifier les notations des consultants
        if request.user.has_role('consultant'):
            rating.is_verified = True
            rating.verified_by = request.user
            
        rating.save()
        
        # Recalculer la note moyenne
        creator.update_ratings()
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True, 
                'rating': float(creator.average_rating),
                'total_ratings': creator.total_ratings
            })
            
        return redirect('creator_detail', creator_id=creator.id)
    
    # En cas d'erreur du formulaire
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)
        
    return redirect('creator_detail', creator_id=creator.id)


@login_required
@require_POST
def toggle_favorite(request, creator_id):
    """
    Vue pour ajouter/supprimer un créateur des favoris.
    """
    creator = get_object_or_404(Creator, id=creator_id)
    
    # Vérifier si déjà dans les favoris
    favorite, created = Favorite.objects.get_or_create(creator=creator, user=request.user)
    
    # Si on a des notes à ajouter
    if created and request.POST.get('notes'):
        favorite.notes = request.POST.get('notes')
        favorite.save()
    
    # Si on supprime des favoris
    if not created and request.POST.get('action') == 'remove':
        favorite.delete()
        is_favorite = False
    else:
        is_favorite = True
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'is_favorite': is_favorite})
        
    return redirect('creator_detail', creator_id=creator.id)


@login_required
def ajax_filter_results(request):
    """
    Endpoint AJAX pour les résultats filtrés.
    """
    if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'error': 'AJAX requests only'}, status=400)
    
    form = CreatorSearchForm(request.GET)
    if form.is_valid():
        # Cette fonction utilise la même logique de filtrage que gallery_view
        # mais retourne uniquement les données JSON
        return gallery_view(request)
    
    return JsonResponse({'error': 'Invalid form data'}, status=400)


@login_required
def ajax_map_data(request):
    """
    Endpoint AJAX pour les données de carte.
    """
    if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'error': 'AJAX requests only'}, status=400)
    
    # Filtres de base similaires à gallery_view
    creators = Creator.objects.filter(location__isnull=False)
    
    # Appliquer les filtres supplémentaires
    form = CreatorSearchForm(request.GET)
    if form.is_valid():
        data = form.cleaned_data
        
        # Appliquer les mêmes filtres que dans gallery_view
        # ...
    
    # Préparer les données pour la carte
    map_points = []
    for creator in creators:
        if creator.location and creator.location.latitude and creator.location.longitude:
            # Trouver une image pour l'aperçu
            thumbnail = None
            if creator.media.filter(media_type='image').exists():
                media = creator.media.filter(media_type='image').first()
                if has_valid_file(media):
                    thumbnail = media.file.url
                
            map_points.append({
                'id': creator.id,
                'name': creator.full_name,
                'lat': float(creator.location.latitude),
                'lng': float(creator.location.longitude),
                'rating': float(creator.average_rating),
                'thumbnail': thumbnail,
                'url': f"/creator/{creator.id}/",
            })
    
    return JsonResponse({'points': map_points})


@login_required
def media_upload(request, creator_id):
    """
    Vue pour l'upload de médias pour un créateur.
    """
    creator = get_object_or_404(Creator, id=creator_id)
    
    # Vérifier les permissions
    if not (request.user.has_role('admin') or request.user.has_role('consultant') or 
            (request.user.has_role('creator') and request.user.creator_profile == creator)):
        return HttpResponseForbidden("Vous n'avez pas les droits pour modifier ce créateur.")
    
    if request.method == 'POST':
        form = MediaUploadForm(request.POST, request.FILES)
        if form.is_valid():
            media = form.save(commit=False)
            media.creator = creator
            
            # Auto-valider les uploads des consultants/admins
            if request.user.has_role('admin') or request.user.has_role('consultant'):
                media.is_verified = True
                
            media.save()
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'media_id': media.id})
                
            return redirect('creator_detail', creator_id=creator.id)
            
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        form = MediaUploadForm()
    
    image_count = creator.get_image_count()
    video_count = creator.get_video_count()
    
    context = {
        'form': form,
        'creator': creator,
        'image_count': image_count,
        'video_count': video_count,
        'images_left': 10 - image_count,
        'videos_left': 10 - video_count,
    }
    
    return render(request, 'creators/media_upload.html', context)


@login_required
def search_view(request):
    """
    Vue dédiée à la recherche de créateurs.
    """
    # Initialiser le formulaire de recherche et la liste vide
    form = CreatorSearchForm(request.GET)
    creators = Creator.objects.none()
    is_search = False

    # N'effectuer la recherche que si le formulaire est soumis et valide
    if request.GET and form.is_valid():
        is_search = True
        creators = Creator.objects.all().order_by('-average_rating', 'full_name')
        data = form.cleaned_data
        
        # Filtre par nom/prénom
        if data.get('query'):
            query = data['query']
            creators = creators.filter(
                Q(first_name__icontains=query) | 
                Q(last_name__icontains=query) | 
                Q(full_name__icontains=query) |
                Q(bio__icontains=query)  # Recherche également dans la biographie
            )
            
        # Filtre par domaines
        if data.get('domains'):
            creators = creators.filter(domains__in=data['domains']).distinct()
            
        # Filtres par âge
        if data.get('min_age'):
            creators = creators.filter(age__gte=data['min_age'])
        if data.get('max_age'):
            creators = creators.filter(age__lte=data['max_age'])
            
        # Filtre par genre
        if data.get('gender'):
            creators = creators.filter(gender=data['gender'])
            
        # Filtre par type de contenu
        if data.get('content_type'):
            creators = creators.filter(content_types=data['content_type'])
            
        # Filtres géographiques
        if data.get('country'):
            creators = creators.filter(location__country__icontains=data['country'])
        if data.get('city'):
            creators = creators.filter(location__city__icontains=data['city'])
            
        # Filtre par note minimale
        if data.get('min_rating'):
            creators = creators.filter(average_rating__gte=data['min_rating'])
            
        # Autres filtres spécifiques
        if data.get('can_invoice'):
            creators = creators.filter(can_invoice=True)
        if data.get('verified_only'):
            creators = creators.filter(verified_by_neads=True)
    
    # Pagination
    paginator = Paginator(creators, 15)  # 15 créateurs par page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Liste des domaines pour le formulaire
    domains = Domain.objects.all().order_by('name')
    
    context = {
        'creators': page_obj,
        'form': form,
        'domains': domains,
        'is_search': is_search,
        'total_creators': paginator.count if is_search else 0,
        'search_query': request.GET.get('query', ''),
    }
    
    # Retourner JSON pour les requêtes AJAX
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        creator_data = []
        for creator in page_obj:
            # Images pour la miniature
            thumbnail = None
            if creator.media.filter(media_type='image').exists():
                media_obj = creator.media.filter(media_type='image').first()
                # Vérifier si le fichier existe réellement
                if has_valid_file(media_obj):
                    thumbnail = media_obj.file.url
                
            # Domaines comme badges
            domains = [{'id': d.id, 'name': d.name} for d in creator.domains.all()]
            
            creator_data.append({
                'id': creator.id,
                'full_name': creator.full_name,
                'age': creator.age,
                'gender': creator.get_gender_display(),
                'location': str(creator.location) if creator.location else "",
                'rating': float(creator.average_rating),
                'total_ratings': creator.total_ratings,
                'thumbnail': thumbnail,
                'domains': domains,
                'verified': creator.verified_by_neads,
            })
            
        return JsonResponse({
            'creators': creator_data,
            'page': page_number,
            'total_pages': paginator.num_pages,
            'total_creators': paginator.count,
        })
        
    return render(request, 'creators/search.html', context)


@login_required
def api_cities(request):
    """
    API endpoint pour récupérer les villes des créateurs.
    Retourne une liste de villes uniques présentes dans les emplacements des créateurs.
    """
    # Récupère le terme de recherche de la requête, s'il existe
    query = request.GET.get('q', '')
    
    # Récupère les villes uniques des emplacements des créateurs
    cities = Location.objects.filter(
        city__isnull=False,
        city__istartswith=query
    ).values_list('city', flat=True).distinct().order_by('city')[:10]
    
    # Convertit le queryset en liste
    cities_list = list(cities)
    
    return JsonResponse(cities_list, safe=False)


@login_required
def discover_view(request):
    """
    Vue pour découvrir de nouveaux créateurs via une recherche externe.
    Utilise SerpAPI et MistralAI pour enrichir les résultats.
    """
    query = request.GET.get('query', '')
    results = []
    error = None
    
    if query:
        try:
            # Recherche via SerpAPI (version simulée pour le moment)
            # En production, remplacer par un vrai appel à l'API SerpAPI
            results = search_creators_external(query)
            
            # Enrichir les résultats avec MistralAI (version simulée pour le moment)
            # En production, remplacer par un vrai appel à l'API MistralAI
            results = enrich_results_with_ai(results, query)
            
        except Exception as e:
            error = f"Erreur lors de la recherche: {str(e)}"
    
    context = {
        'query': query,
        'results': results,
        'error': error,
        'has_results': len(results) > 0
    }
    
    # Retourner JSON pour les requêtes AJAX
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'results': results,
            'error': error,
            'has_results': len(results) > 0
        })
    
    return render(request, 'creators/discover.html', context)


def search_creators_external(query: str) -> List[Dict[str, Any]]:
    """
    Fonction simulée pour rechercher des créateurs externes via SerpAPI.
    En production, utiliser l'API SerpAPI.
    """
    # Simulation de résultats pour démonstration
    mock_results = [
        {
            'name': 'Emma Beauté',
            'platform': 'Instagram',
            'followers': '120K',
            'profile_url': 'https://instagram.com/emmabeauty',
            'description': 'Créatrice de contenu beauté et lifestyle, spécialisée en skincare',
            'location': 'Paris, France',
            'profile_image': 'https://via.placeholder.com/150?text=Emma'
        },
        {
            'name': 'Thomas Tech',
            'platform': 'TikTok',
            'followers': '500K',
            'profile_url': 'https://tiktok.com/@thomastech',
            'description': 'Passionné de technologie, je teste les derniers gadgets!',
            'location': 'Lyon, France',
            'profile_image': 'https://via.placeholder.com/150?text=Thomas'
        },
        {
            'name': 'Marie Cuisine',
            'platform': 'Instagram',
            'followers': '80K',
            'profile_url': 'https://instagram.com/mariecuisine',
            'description': 'Recettes faciles et gourmandes pour tous les jours',
            'location': 'Bordeaux, France',
            'profile_image': 'https://via.placeholder.com/150?text=Marie'
        }
    ]
    
    # En production, remplacer par:
    # api_key = settings.SERPAPI_KEY
    # url = f"https://serpapi.com/search.json?engine=google&q={query}+influenceur+créateur+content&api_key={api_key}"
    # response = requests.get(url)
    # data = response.json()
    # ... traitement des résultats ...
    
    return mock_results


def enrich_results_with_ai(results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    """
    Fonction simulée pour enrichir les résultats avec MistralAI.
    En production, utiliser l'API MistralAI.
    """
    # Simulation d'enrichissement pour démonstration
    for result in results:
        # Ajouter des informations enrichies
        result['relevance_score'] = round(0.5 + 0.5 * (len(result['description']) % 5) / 5, 2)  # Score entre 0.5 et 1.0
        result['domain_match'] = True if query.lower() in result['description'].lower() else False
        result['potential_audience'] = f"{int(result['followers'].replace('K', '000')) // 100 * 100:,}".replace(',', ' ')
        result['engagement_rate'] = f"{3 + (hash(result['name']) % 7)}%"  # Entre 3% et 10%
        
    # Trier par pertinence (simulation)
    results.sort(key=lambda x: x['relevance_score'], reverse=True)
    
    # En production, remplacer par:
    # api_key = settings.MISTRAL_API_KEY
    # url = "https://api.mistral.ai/v1/chat/completions"
    # messages = [{"role": "user", "content": f"Analyze these creator profiles and enrich with additional info: {json.dumps(results)}"}]
    # data = {"model": "mistral-medium", "messages": messages}
    # headers = {"Authorization": f"Bearer {api_key}"}
    # response = requests.post(url, json=data, headers=headers)
    # enriched_data = response.json()
    # ... traitement des résultats ...
    
    return results


@login_required
def api_map_search(request):
    """
    API endpoint for searching creators on a map with distance filtering.
    Returns creators that are within the specified radius from the given coordinates.
    """
    # Get required parameters from request
    try:
        user_lat = float(request.GET.get('lat'))
        user_lng = float(request.GET.get('lng'))
        radius = float(request.GET.get('radius', 50))  # Default radius of 50km
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid location parameters'}, status=400)

    # Get creators with valid location data
    creators = Creator.objects.filter(
        location__latitude__isnull=False,
        location__longitude__isnull=False
    )

    # Apply standard filters if provided
    min_rating = request.GET.get('min_rating')
    if min_rating and min_rating.isdigit():
        creators = creators.filter(average_rating__gte=float(min_rating))
    
    min_age = request.GET.get('min_age')
    max_age = request.GET.get('max_age')
    if min_age and min_age.isdigit():
        creators = creators.filter(age__gte=int(min_age))
    if max_age and max_age.isdigit():
        creators = creators.filter(age__lte=int(max_age))
    
    city = request.GET.get('city')
    if city:
        creators = creators.filter(location__city__icontains=city)
    
    domain = request.GET.get('domain')
    if domain and domain.isdigit():
        creators = creators.filter(domains__id=int(domain))
    
    query = request.GET.get('query')
    if query:
        creators = creators.filter(
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query) | 
            Q(full_name__icontains=query)
        )

    # Prepare creator data with distances
    creators_data = []
    
    def haversine(lat1, lon1, lat2, lon2):
        """
        Calculate the great circle distance between two points 
        on the earth (specified in decimal degrees)
        """
        # Convert decimal degrees to radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371  # Radius of earth in kilometers
        return c * r
    
    for creator in creators:
        # Calculate distance
        distance = haversine(
            user_lat, user_lng, 
            float(creator.location.latitude), float(creator.location.longitude)
        )
        
        # Only include creators within the radius
        if distance <= radius:
            # Get a thumbnail image if available
            thumbnail = None
            if creator.media.filter(media_type='image').exists():
                media_obj = creator.media.filter(media_type='image').first()
                if has_valid_file(media_obj):
                    thumbnail = media_obj.file.url
            
            creator_data = {
                'id': creator.id,
                'name': f"{creator.first_name} {creator.last_name}",
                'rating': float(creator.average_rating),
                'age': creator.age,
                'distance': round(distance, 1),
                'image': thumbnail,
                'lat': float(creator.location.latitude),
                'lng': float(creator.location.longitude),
                'city': creator.location.city,
                'country': creator.location.country,
                'url': f"/creators/detail/{creator.id}/",
            }
            creators_data.append(creator_data)
    
    return JsonResponse({'creators': creators_data, 'total': len(creators_data)})
