from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q, Count, Min, Max
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from functools import wraps
from django.template.loader import render_to_string

from neads.core.models import User
from .models import Creator, Media, Rating, Domain, Favorite, Location
from .forms import CreatorSearchForm, RatingForm, FavoriteForm, CreatorForm, LocationForm, MediaUploadForm

import json
import requests
from typing import Dict, List, Any
from math import radians, cos, sin, asin, sqrt
import logging
import re

from py_countries_states_cities_database import get_all_countries_and_cities_nested

logger = logging.getLogger(__name__)


# Custom decorator to check user roles
def role_required(allowed_roles):
    """
    Decorator to restrict views based on user roles.
    Takes a list of allowed roles as argument.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            
            if request.user.role not in allowed_roles:
                return HttpResponseForbidden("Vous n'avez pas les permissions nécessaires pour accéder à cette page.")
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# Fonction utilitaire pour vérifier si un fichier media est valide
def has_valid_file(media_obj):
    """
    Vérifie si un objet Media possède un fichier valide avec une URL.
    Évite les erreurs lorsqu'on tente d'accéder à media.file.url dans les templates.
    """
    try:
        if media_obj is None:
            logger.debug("has_valid_file: media_obj is None")
            return False
        
        logger.debug(f"has_valid_file: Vérification du media {media_obj.id}, type: {media_obj.media_type}")
        
        if media_obj.media_type == 'image':
            # Validation d'image
            if not hasattr(media_obj, 'file'):
                logger.debug(f"has_valid_file: media_obj n'a pas d'attribut 'file'")
                return False
            
            if not media_obj.file:
                logger.debug(f"has_valid_file: media_obj.file est vide")
                return False
            
            # Vérifier si le fichier existe physiquement
            try:
                if not media_obj.file.storage.exists(media_obj.file.name):
                    logger.warning(f"has_valid_file: Le fichier {media_obj.file.name} n'existe pas physiquement")
                    return False
            except Exception as e:
                logger.error(f"has_valid_file: Erreur lors de la vérification du fichier physique: {str(e)}")
                
            # Vérifier l'attribut name et url
            if not media_obj.file.name:
                logger.debug(f"has_valid_file: media_obj.file.name est vide")
                return False
                
            if not hasattr(media_obj.file, 'url'):
                logger.debug(f"has_valid_file: media_obj.file n'a pas d'attribut 'url'")
                return False
                
            logger.debug(f"has_valid_file: Image valide trouvée: {media_obj.file.url}")
            return True
        
        elif media_obj.media_type == 'video':
            # Validation de vidéo
            valid_video = (hasattr(media_obj, 'video_file') and 
                         media_obj.video_file and 
                         media_obj.video_file.name and 
                         hasattr(media_obj.video_file, 'url'))
                         
            valid_thumbnail = (hasattr(media_obj, 'thumbnail') and 
                              media_obj.thumbnail and 
                              media_obj.thumbnail.name and 
                              hasattr(media_obj.thumbnail, 'url'))
            
            if not valid_video:
                logger.debug(f"has_valid_file: Vidéo invalide: {media_obj.id}")
                
            if not valid_thumbnail:
                logger.debug(f"has_valid_file: Miniature invalide pour la vidéo: {media_obj.id}")
            
            if valid_video and valid_thumbnail:
                logger.debug(f"has_valid_file: Vidéo et miniature valides pour: {media_obj.id}")
                
            return valid_video and valid_thumbnail
        
        logger.warning(f"has_valid_file: Type de média non reconnu: {media_obj.media_type}")
        return False
        
    except Exception as e:
        logger.error(f"has_valid_file: Exception non gérée: {str(e)}")
        return False


def get_creator_thumbnail(creator):
    """
    Récupère une miniature pour un créateur en suivant cet ordre de priorité:
    1. Image mise en avant (featured_image)
    2. Première image valide du portfolio
    3. Null si aucune image n'est disponible
    """
    try:
        # 1. D'abord, vérifier si une image mise en avant est définie
        if creator.featured_image and creator.featured_image.name:
            return creator.featured_image.url
        
        # 2. Ensuite, chercher la première image valide dans le portfolio
        if creator.media.filter(media_type='image').exists():
            image = creator.media.filter(media_type='image').first()
            if has_valid_file(image):
                return image.file.url
        
        # 3. Aucune image disponible
        return None
    except Exception:
        # En cas d'erreur, retourner None pour éviter de casser le template
        return None


@login_required
def gallery_view(request):
    """
    Vue principale de la galerie des créateurs avec filtres.
    """
    # Vérifier si l'utilisateur est un créateur
    if request.user.has_role('creator'):
        try:
            if hasattr(request.user, 'creator_profile') and request.user.creator_profile:
                return redirect('creator_detail', creator_id=request.user.creator_profile.id)
            else:
                messages.warning(request, "Votre profil de créateur n'est pas encore configuré. Veuillez le créer pour être visible dans la galerie.")
                return redirect('creator_add')
        except Exception as e:
            messages.error(request, f"Erreur d'accès au profil de créateur: {str(e)}")
            return redirect('creator_add')

    creators = Creator.objects.all().order_by('-average_rating', 'full_name')
    
    # Nettoyer les paramètres de l'URL pour éviter l'accumulation des paramètres 'page'
    current_params = request.GET.copy()
    if 'page' in current_params:
        # Supprime tous les paramètres 'page' sauf le dernier
        current_params.pop('page')
    
    # Créer le formulaire avec les paramètres GET
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
            
        # Filtres géographiques
        if data.get('country'):
            creators = creators.filter(location__full_address__icontains=data['country'])
        if data.get('city'):
            creators = creators.filter(location__full_address__icontains=data['city'])
            
        # Filtre par note minimale
        if data.get('min_rating'):
            creators = creators.filter(average_rating__gte=data['min_rating'])
            
        # Autres filtres spécifiques
        if data.get('can_invoice'):
            creators = creators.filter(can_invoice=True)
        if data.get('verified_only'):
            creators = creators.filter(verified_by_neads=True)
        
        # Filtre des favoris
        if data.get('favorites_only') and request.user.is_authenticated:
            # Récupérer les IDs des créateurs favoris de l'utilisateur
            favorite_creator_ids = Favorite.objects.filter(user=request.user).values_list('creator_id', flat=True)
            creators = creators.filter(id__in=favorite_creator_ids)
    
    # Pagination
    paginator = Paginator(creators, 12)  # 12 créateurs par page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Récupérer tous les domaines
    all_domains = Domain.objects.all().order_by('name')
    
    # Récupérer les 6 domaines les plus utilisés
    top_domains = Domain.objects.annotate(
        creator_count=Count('creators')
    ).order_by('-creator_count')[:6]
    
    # Obtenir les statistiques d'âge pour le slider
    min_creator_age = Creator.objects.aggregate(Min('age'))['age__min'] or 18
    max_creator_age = Creator.objects.aggregate(Max('age'))['age__max'] or 65
    
    # Construire l'URL des paramètres sans le paramètre page
    clean_params = current_params.urlencode()
    
    # Préparer les données des domaines en JSON pour JavaScript
    domains_json = []
    for domain in all_domains:
        creator_count = domain.creators.count()
        domains_json.append({
            'id': domain.id,
            'name': domain.name,
            'count': creator_count
        })
    all_countries = get_all_countries_and_cities_nested()
    
    context = {
        'creators': page_obj,
        'form': form,
        'domains': all_domains,
        'all_domains': all_domains,
        'top_domains': top_domains,
        'total_creators': paginator.count,
        'clean_params': clean_params,
        'min_creator_age': min_creator_age,
        'max_creator_age': max_creator_age,
        'domains_json': json.dumps(domains_json),
        'countries':all_countries,
        'country_city_map': json.dumps({
            entry["iso2"]: entry["cities"]
            for entry in all_countries
        })
    }
    
    # Retourner JSON pour les requêtes AJAX
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        creator_data = []
        for creator in page_obj:
            # Images pour la miniature
            thumbnail = get_creator_thumbnail(creator)
            
            # Domaines comme badges
            domains = [{'id': d.id, 'name': d.name} for d in creator.domains.all()]
            
            creator_data.append({
                'id': creator.id,
                'full_name': creator.full_name,
                'first_name': creator.first_name,
                'last_name': creator.last_name,
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
    Affiche la fiche détaillée d'un créateur.
    """
    creator = get_object_or_404(Creator, id=creator_id)
    
    # Log de l'accès
    if request.user.is_authenticated:
        logger.info(f"Vue creator_detail: Accès au profil {creator_id} par {request.user.email} (role: {request.user.role})")
    
    # Vérifier si le créateur est dans les favoris de l'utilisateur
    is_favorite = False
    if request.user.is_authenticated and not request.user.role == 'client':
        is_favorite = Favorite.objects.filter(creator=creator, user=request.user).exists()
    
    # Vérifier les permissions d'accès
    # Restriction pour les créateurs: peuvent uniquement voir leur propre profil
    if request.user.is_authenticated and request.user.role == 'creator':
        if not hasattr(request.user, 'creator_profile') or request.user.creator_profile.id != creator_id:
            messages.error(request, "En tant que créateur, vous ne pouvez accéder qu'à votre propre profil.")
            return redirect('gallery_view')
    
    # Pour le développement uniquement
    # Pour la production, cette vérification doit être décommentée
    # if not creator.verified_by_neads and not (request.user.is_authenticated and (request.user.role == 'admin' or request.user.role == 'consultant')):
    #     raise Http404("Ce créateur n'est pas encore vérifié.")
    
    # Récupérer les médias du créateur
    videos = creator.media.filter(media_type='video').order_by('-upload_date')
    photos = creator.media.filter(media_type='image').order_by('-upload_date')
    
    # Debug des médias pour identifier les problèmes
    logger.debug(f"creator_detail: Nombre de vidéos: {videos.count()}")
    logger.debug(f"creator_detail: Nombre de photos: {photos.count()}")
    
    for photo in photos:
        logger.debug(f"Photo ID: {photo.id}, Valide: {has_valid_file(photo)}")
    
    for video in videos:
        logger.debug(f"Vidéo ID: {video.id}, Valide: {has_valid_file(video)}")
    
    # Récupérer les avis sur le créateur
    ratings = Rating.objects.filter(creator=creator).order_by('-created_at')
    rating_form = None
    
    # Afficher le formulaire d'avis uniquement pour les consultants et admin
    if request.user.is_authenticated and (request.user.role == 'admin' or request.user.role == 'consultant'):
        # Vérifie si l'utilisateur a déjà donné un avis
        user_rating = Rating.objects.filter(creator=creator, user=request.user).first()
        if user_rating:
            rating_form = RatingForm(instance=user_rating)
        else:
            rating_form = RatingForm()
    
    # Formulaire d'ajout aux favoris pour les consultants et admin
    favorite_form = None
    favorite = None
    if request.user.is_authenticated and (request.user.role == 'admin' or request.user.role == 'consultant'):
        favorite = Favorite.objects.filter(creator=creator, user=request.user).first()
        if favorite:
            favorite_form = FavoriteForm(instance=favorite)
        else:
            favorite_form = FavoriteForm()
    
    # Le contexte à passer au template
    context = {
        'creator': creator,
        'videos': videos,
        'photos': photos,
        'domains': creator.domains.all(),
        'ratings': ratings,
        'rating_form': rating_form,
        'favorite_form': favorite_form,
        'is_favorite': is_favorite,
        'favorite': favorite,
        'nominatim_url': settings.NOMINATIM_URL,
    }
    
    return render(request, 'creators/creator_detail.html', context)


@login_required
def creator_edit(request, creator_id):
    """Vue pour modifier un créateur existant."""
    creator = get_object_or_404(Creator, id=creator_id)
    
    # Vérifier que l'utilisateur a le droit de modifier ce créateur
    if not request.user.is_superuser and not request.user.has_role('consultant') and not (request.user.is_authenticated and request.user == creator.user):
        messages.error(request, "Vous n'avez pas l'autorisation de modifier ce profil.")
        return redirect('creator_detail', creator_id=creator.id)
    
    if request.method == 'POST':
        creator_form = CreatorForm(request.POST, instance=creator)
        location_form = LocationForm(request.POST, instance=creator.location)
        
        if creator_form.is_valid() and location_form.is_valid():
            location = location_form.save()
            creator = creator_form.save()
            
            messages.success(request, "Le profil de créateur a été mis à jour avec succès!")
            return redirect('creator_detail', creator_id=creator.id)
    else:
        creator_form = CreatorForm(instance=creator)
        location_form = LocationForm(instance=creator.location)
    
    return render(request, 'creators/edit_creator.html', {
        'creator': creator,
        'form': creator_form,
        'location_form': location_form,
        'nominatim_url': settings.NOMINATIM_URL,
    })


@login_required
@require_POST
def rate_creator(request, creator_id):
    """
    Vue pour noter un créateur.
    """
    # Les clients ne peuvent pas noter les créateurs
    if request.user.role == 'client':
        messages.error(request, "En tant que client, vous ne pouvez pas noter les créateurs.")
        return redirect('creator_detail', creator_id=creator_id)
    
    creator = get_object_or_404(Creator, id=creator_id)
    
    # Vérifier les permissions (seuls les consultants/admins peuvent noter)
    if not (request.user.has_role('consultant') or request.user.has_role('admin')):
        return HttpResponseForbidden("Vous n'avez pas les droits pour noter un créateur.")
    
    # Récupérer ou créer la note
    try:
        rating = Rating.objects.get(creator=creator, user=request.user)
    except Rating.DoesNotExist:
        rating = Rating(creator=creator, user=request.user)
    
    form = RatingForm(request.POST, instance=rating)
    
    # Pour les administrateurs et consultants, on rend le champ has_experience facultatif
    if request.user.has_role('admin') or request.user.has_role('consultant'):
        form.fields['has_experience'].required = False
    
    if form.is_valid():
        rating = form.save(commit=False)
        
        # Tous les avis sont automatiquement vérifiés pour apparaître immédiatement
        rating.is_verified = True
        
        # Si c'est un admin ou consultant qui vérifie
        if request.user.has_role('consultant') or request.user.has_role('admin'):
            rating.verified_by = request.user
            # Si le champ n'est pas rempli par un admin/consultant, on le met à True par défaut
            if not rating.has_experience:
                rating.has_experience = True
            
        rating.save()
        
        # Recalculer la note moyenne
        creator.update_ratings()
        
        # Message de succès simple
        messages.success(request, "Votre avis a été publié avec succès !")
        
        # Ajouter un message de journalisation
        logger.info(f"Nouvelle note de {request.user.email} pour le créateur {creator.id} : {rating.rating}/5 (has_experience: {rating.has_experience}, is_verified: {rating.is_verified})")
        
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
    
    messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")
    return redirect('creator_detail', creator_id=creator.id)


@login_required
@require_POST
def toggle_favorite(request, creator_id):
    """
    Vue pour ajouter/supprimer un créateur des favoris.
    """
    # Les clients ne peuvent pas ajouter de favoris
    if request.user.role == 'client':
        messages.error(request, "En tant que client, vous ne pouvez pas ajouter de créateurs aux favoris.")
        return redirect('creator_detail', creator_id=creator_id)
    
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
                'url': reverse('creator_detail', kwargs={'creator_id': creator.id}),
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
        logger.warning(f"Tentative d'accès non autorisée à media_upload par {request.user} pour le créateur {creator}")
        return HttpResponseForbidden("Vous n'avez pas les droits pour modifier ce créateur.")
    
    logger.info(f"Début de l'upload de média par {request.user} pour le créateur {creator}")
    
    if request.method == 'POST':
        form = MediaUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                media = form.save(commit=False)
                media.creator = creator
                
                # Vérifier les fichiers avant la sauvegarde
                if media.media_type == 'image':
                    if not media.file:
                        raise ValueError("Le fichier image est manquant")
                    
                    logger.info(f"Fichier image: {media.file.name}, taille: {media.file.size} octets")
                    
                elif media.media_type == 'video':
                    if not media.video_file:
                        raise ValueError("Le fichier vidéo est manquant")
                    if not media.thumbnail:
                        raise ValueError("La miniature de la vidéo est manquante")
                        
                    logger.info(f"Fichier vidéo: {media.video_file.name}, taille: {media.video_file.size} octets")
                    logger.info(f"Miniature: {media.thumbnail.name}, taille: {media.thumbnail.size} octets")
                
                # Auto-valider les uploads des consultants/admins
                if request.user.has_role('admin') or request.user.has_role('consultant'):
                    media.is_verified = True
                    logger.info(f"Media auto-validé par {request.user} (admin/consultant)")
                
                # Sauvegarde du média
                media.save()
                logger.info(f"Media {media.id} sauvegardé avec succès pour le créateur {creator}")
                
                # Vérifier après la sauvegarde si le média est bien accessible
                is_valid = has_valid_file(media)
                logger.info(f"Vérification post-sauvegarde du média {media.id}: {'Valide' if is_valid else 'INVALIDE'}")
                
                if not is_valid:
                    logger.warning(f"Le média {media.id} a été sauvegardé mais n'est pas valide selon has_valid_file")
                    # On continue quand même car le problème peut être temporaire
                
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': True, 'media_id': media.id})
                    
                return redirect('creator_detail', creator_id=creator.id)
                
            except Exception as e:
                logger.error(f"Erreur lors de la sauvegarde du média pour {creator}: {str(e)}")
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'errors': {'general': f'Une erreur est survenue lors de la sauvegarde: {str(e)}'}}, status=500)
                messages.error(request, f"Une erreur est survenue lors de la sauvegarde du média: {str(e)}")
                
        else:
            logger.warning(f"Formulaire invalide pour l'upload de média par {request.user}: {form.errors}")
            # Log détaillé des erreurs de formulaire
            for field, errors in form.errors.items():
                for error in errors:
                    logger.warning(f"Erreur de formulaire - {field}: {error}")
                    
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")
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
            
        # Filtres géographiques
        if data.get('country'):
            creators = creators.filter(location__full_address__icontains=data['country'])
        if data.get('city'):
            creators = creators.filter(location__full_address__icontains=data['city'])
            
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
            thumbnail = get_creator_thumbnail(creator)
            
            # Domaines comme badges
            domains = [{'id': d.id, 'name': d.name} for d in creator.domains.all()]
            
            creator_data.append({
                'id': creator.id,
                'full_name': creator.full_name,
                'first_name': creator.first_name,
                'last_name': creator.last_name,
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

    # Apply search filters, identiques à la galerie
    query = request.GET.get('query')
    if query:
        creators = creators.filter(
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query) | 
            Q(full_name__icontains=query)
        )
    
    # Filtres par domaines
    domains_param = request.GET.get('domains')
    if domains_param:
        domain_ids = domains_param.split(',')
        # Si plusieurs domaines, on exige qu'ils soient tous présents (AND)
        for domain_id in domain_ids:
            if domain_id.isdigit():
                creators = creators.filter(domains__id=int(domain_id))
    
    # Filtre par genre
    gender = request.GET.get('gender')
    if gender:
        creators = creators.filter(gender=gender)
    
    # Filtres d'âge
    min_age = request.GET.get('min_age')
    max_age = request.GET.get('max_age')
    if min_age and min_age.isdigit():
        creators = creators.filter(age__gte=int(min_age))
    if max_age and max_age.isdigit():
        creators = creators.filter(age__lte=int(max_age))
    
    # Filtres additionnels
    can_invoice = request.GET.get('can_invoice')
    if can_invoice == 'on':
        creators = creators.filter(can_invoice=True)
    
    verified_only = request.GET.get('verified_only')
    if verified_only == 'on':
        creators = creators.filter(verified_by_neads=True)
    
    min_rating = request.GET.get('min_rating')
    if min_rating and min_rating.isdigit():
        creators = creators.filter(average_rating__gte=float(min_rating))
    
    # Filtre des favoris
    favorites_only = request.GET.get('favorites_only')
    if favorites_only == 'on' and request.user.is_authenticated:
        # Récupérer les IDs des créateurs favoris de l'utilisateur
        favorite_creator_ids = Favorite.objects.filter(user=request.user).values_list('creator_id', flat=True)
        creators = creators.filter(id__in=favorite_creator_ids)
    
    # Filtres géographiques
    city = request.GET.get('city')
    if city:
        creators = creators.filter(location__full_address__icontains=city)
    
    country = request.GET.get('country')
    if country:
        creators = creators.filter(location__full_address__icontains=country)

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
            # Get a thumbnail image
            thumbnail = get_creator_thumbnail(creator)
            
            # Format name based on user role
            if request.user.role == 'client':
                creator_name = f"{creator.first_name} {creator.last_name[0]}."
            else:
                creator_name = creator.full_name
            
            # Récupérer les domaines du créateur
            domains = [{'id': d.id, 'name': d.name} for d in creator.domains.all()]
            
            creator_data = {
                'id': creator.id,
                'name': creator_name,
                'first_name': creator.first_name,
                'last_name': creator.last_name,
                'rating': float(creator.average_rating),
                'total_ratings': creator.total_ratings,
                'age': creator.age,
                'gender': creator.get_gender_display(),
                'domains': domains,
                'can_invoice': creator.can_invoice,
                'distance': round(distance, 1),
                'thumbnail': thumbnail,
                'latitude': float(creator.location.latitude),
                'longitude': float(creator.location.longitude),
                'city': creator.location.full_address.split(',')[0] if creator.location.full_address else '',
                'country': creator.location.full_address.split(',')[-1].strip() if creator.location.full_address and ',' in creator.location.full_address else '',
                'url': reverse('creator_detail', kwargs={'creator_id': creator.id}),
            }
            creators_data.append(creator_data)
    
    # Trier les créateurs par distance
    creators_data.sort(key=lambda x: x['distance'])
    
    return JsonResponse({'creators': creators_data, 'total': len(creators_data)})


@login_required
@role_required(['admin'])
def delete_rating(request, rating_id):
    """
    Vue permettant aux administrateurs de supprimer un avis sur un créateur.
    Seuls les administrateurs peuvent utiliser cette fonctionnalité.
    """
    try:
        rating = get_object_or_404(Rating, id=rating_id)
        creator_id = rating.creator.id
        
        # Journaliser la suppression
        logger.info(f"Admin {request.user.email} a supprimé l'avis #{rating_id} sur le créateur #{creator_id}")
        
        # Supprimer l'avis
        rating.delete()
        
        # Mettre à jour les moyennes
        rating.creator.update_ratings()
        
        messages.success(request, "L'avis a été supprimé avec succès.")
        return redirect('creator_detail', creator_id=creator_id)
    except Exception as e:
        logger.error(f"Erreur lors de la suppression de l'avis: {str(e)}")
        messages.error(request, "Une erreur est survenue lors de la suppression de l'avis.")
        return redirect('creator_detail', creator_id=creator_id)


@login_required
@role_required(['admin'])
def creator_delete(request, creator_id):
    """
    Vue permettant aux administrateurs de supprimer un profil créateur complet.
    Cette action est irréversible et supprime toutes les données associées.
    """
    try:
        creator = get_object_or_404(Creator, id=creator_id)
        creator_name = creator.full_name
        
        if request.method == 'POST':
            # Journaliser la suppression
            logger.warning(f"Admin {request.user.email} a supprimé le profil du créateur {creator_name} (ID: {creator_id})")
            
            # Supprimer les médias associés
            media_count = Media.objects.filter(creator=creator).count()
            Media.objects.filter(creator=creator).delete()
            
            # Supprimer les évaluations
            rating_count = Rating.objects.filter(creator=creator).count()
            Rating.objects.filter(creator=creator).delete()
            
            # Supprimer les favoris
            favorite_count = Favorite.objects.filter(creator=creator).count()
            Favorite.objects.filter(creator=creator).delete()
            
            # Supprimer la localisation si elle existe
            if creator.location:
                creator.location.delete()
            
            # Supprimer le créateur
            creator.delete()
            
            # Message récapitulatif
            messages.success(
                request, 
                f"Le profil de {creator_name} a été supprimé avec succès. "
                f"({media_count} médias, {rating_count} avis et {favorite_count} favoris supprimés)"
            )
            
            # Rediriger vers la liste des créateurs
            return redirect('creator_list')
        
        # Si ce n'est pas une requête POST, rediriger vers la page de détail
        return redirect('creator_detail', creator_id=creator_id)
    except Exception as e:
        logger.error(f"Erreur lors de la suppression du créateur: {str(e)}")
        messages.error(request, "Une erreur est survenue lors de la suppression du créateur.")
        return redirect('creator_detail', creator_id=creator_id)


@login_required
@role_required(['admin', 'consultant'])
def creators_list(request):
    """
    Vue pour l'administration des créateurs - liste avec actions avancées.
    Réservée aux administrateurs et consultants.
    """
    creators = Creator.objects.all().order_by('-created_at')
    
    # Filtres
    query = request.GET.get('q')
    if query:
        creators = creators.filter(
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query) | 
            Q(email__icontains=query)
        )
    
    # Pagination
    paginator = Paginator(creators, 20)  # 20 créateurs par page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'creators': page_obj,
        'total_creators': paginator.count,
        'q': query,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': page_obj,
        'paginator': paginator,
    }
    
    return render(request, 'creators/creators_list.html', context)


@login_required
def creator_add(request):
    """
    Vue pour ajouter un nouveau créateur.
    """
    if request.method == 'POST':
        creator_form = CreatorForm(request.POST)
        location_form = LocationForm(request.POST)
        
        if creator_form.is_valid() and location_form.is_valid():
            # Créer un objet Location
            location = location_form.save()
            
            # Créer un objet Creator avec la relation vers Location
            creator = creator_form.save(commit=False)
            creator.location = location
            
            # Si l'utilisateur est authentifié, associer le créateur à l'utilisateur
            if request.user.is_authenticated:
                creator.user = request.user
            
            creator.save()
            
            # Enregistrer les relations ManyToMany
            creator_form.save_m2m()
            
            # Rediriger vers la page de détail du créateur
            messages.success(request, "Votre profil de créateur a été créé avec succès!")
            return redirect('creator_detail', creator_id=creator.id)
    else:
        creator_form = CreatorForm()
        location_form = LocationForm()
    
    return render(request, 'creators/create_creator.html', {
        'form': creator_form,
        'location_form': location_form,
        'nominatim_url': settings.NOMINATIM_URL,
    })


@login_required
def favorites_view(request):
    """
    Affiche la liste des créateurs favoris de l'utilisateur.
    """
    # Les clients ne peuvent pas avoir de favoris
    if request.user.role == 'client':
        messages.error(request, "En tant que client, vous n'avez pas accès aux favoris.")
        return redirect('gallery_view')
    
    favorites = Favorite.objects.filter(user=request.user).select_related('creator')
    total_favorites = favorites.count()
    
    # Extraire les créateurs à partir des favorites
    creators = [favorite.creator for favorite in favorites]
    
    context = {
        'favorites': favorites,
        'creators': creators,
        'total_favorites': total_favorites,
        'total_creators': total_favorites,
    }
    
    return render(request, 'creators/favorites.html', context)


@login_required
def contact_creator(request, creator_id):
    """
    Vue pour envoyer un email à un créateur via le formulaire de contact.
    """
    # Les clients ne peuvent pas contacter les créateurs
    if request.user.role == 'client':
        messages.error(request, "En tant que client, vous ne pouvez pas contacter directement les créateurs.")
        return redirect('creator_detail', creator_id=creator_id)
    
    creator = get_object_or_404(Creator, id=creator_id)
    
    if request.method == 'POST':
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        copy_me = request.POST.get('copy_me') == 'on'
        
        # Préparation du message avec les informations du client
        html_message = render_to_string('core/emails/contact_creator_email.html', {
            'creator': creator,
            'user': request.user,
            'subject': subject,
            'message': message,
        })
        
        # Envoi de l'email au créateur
        send_mail(
            subject=f"NEADS - Contact: {subject}",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[creator.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        # Copie à l'expéditeur si demandée
        if copy_me and request.user.email:
            send_mail(
                subject=f"NEADS - Copie de votre message à {creator.full_name}",
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[request.user.email],
                html_message=html_message,
                fail_silently=False,
            )
        
        messages.success(request, f"Votre message a été envoyé à {creator.full_name}")
        return redirect('creator_detail', creator_id=creator_id)


@login_required
def api_domains(request):
    """
    API endpoint pour récupérer tous les domaines avec leur nombre d'utilisations.
    """
    domains = Domain.objects.all()
    domains_data = []
    
    for domain in domains:
        # Compter le nombre de créateurs qui utilisent ce domaine
        count = Creator.objects.filter(domains=domain).count()
        domains_data.append({
            'id': domain.id,
            'name': domain.name,
            'count': count
        })
    
    # Trier par nom
    domains_data.sort(key=lambda x: x['name'])
    
    return JsonResponse(domains_data, safe=False)


# Fonction utilitaire pour normaliser les adresses et codes postaux
def normalize_address(address_data):
    """
    Normalise les adresses et codes postaux pour être cohérent avec les pratiques françaises.
    Corrige notamment les codes postaux administratifs vs couramment utilisés.
    """
    if not address_data:
        return address_data
    
    # Dictionnaire des corrections spécifiques de codes postaux
    postal_corrections = {
        'Montpellier': '34000',  # Au lieu de 34062 (administratif)
        'Marseille': {
            # Arrondissements de Marseille
            'Marseille 1er Arrondissement': '13001',
            'Marseille 2e Arrondissement': '13002',
            'Marseille 3e Arrondissement': '13003',
            'Marseille 4e Arrondissement': '13004',
            'Marseille 5e Arrondissement': '13005',
            'Marseille 6e Arrondissement': '13006',
            'Marseille 7e Arrondissement': '13007',
            'Marseille 8e Arrondissement': '13008',
            'Marseille 9e Arrondissement': '13009',
            'Marseille 10e Arrondissement': '13010',
            'Marseille 11e Arrondissement': '13011',
            'Marseille 12e Arrondissement': '13012',
            'Marseille 13e Arrondissement': '13013',
            'Marseille 14e Arrondissement': '13014',
            'Marseille 15e Arrondissement': '13015',
            'Marseille 16e Arrondissement': '13016',
            # Fallback général pour Marseille
            'Marseille': '13000',
        },
        'Lyon': {
            # Arrondissements de Lyon
            'Lyon 1er Arrondissement': '69001',
            'Lyon 2e Arrondissement': '69002',
            'Lyon 3e Arrondissement': '69003',
            'Lyon 4e Arrondissement': '69004',
            'Lyon 5e Arrondissement': '69005',
            'Lyon 6e Arrondissement': '69006',
            'Lyon 7e Arrondissement': '69007',
            'Lyon 8e Arrondissement': '69008',
            'Lyon 9e Arrondissement': '69009',
            # Fallback général pour Lyon
            'Lyon': '69000',
        },
        'Toulouse': '31000',  # Au lieu de 31500 (administratif)
        'Bordeaux': '33000',  # Au lieu de 33063 (administratif)
        'Nantes': '44000',    # Au lieu de 44109 (administratif)
        'Strasbourg': '67000', # Au lieu de 67482 (administratif)
        'Lille': '59000',     # Au lieu de 59350 (administratif)
    }
    
    try:
        # Vérifier si l'adresse contient une ville connue pour avoir des problèmes de code postal
        for city, correction in postal_corrections.items():
            if isinstance(correction, dict):
                # Pour les villes avec des arrondissements
                for district, code in correction.items():
                    if district in address_data and re.search(r'\b\d{5}\b', address_data):
                        # Remplacer le code postal existant par celui corrigé
                        address_data = re.sub(r'\b\d{5}\b', code, address_data)
                        logger.debug(f"Code postal corrigé pour {district}: {code}")
                        break
                if city in address_data and re.search(r'\b\d{5}\b', address_data) and not any(district in address_data for district in correction.keys()):
                    # Utiliser le code par défaut si aucun arrondissement n'est trouvé
                    address_data = re.sub(r'\b\d{5}\b', correction['Lyon' if city == 'Lyon' else 'Marseille'], address_data)
                    logger.debug(f"Code postal général corrigé pour {city}")
            else:
                # Pour les villes sans arrondissements
                if city in address_data and re.search(r'\b\d{5}\b', address_data):
                    address_data = re.sub(r'\b\d{5}\b', correction, address_data)
                    logger.debug(f"Code postal corrigé pour {city}: {correction}")
    except Exception as e:
        logger.error(f"Erreur lors de la normalisation de l'adresse: {str(e)}")
    
    return address_data
