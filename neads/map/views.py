from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from django.urls import reverse
import logging

from neads.creators.models import Creator
from neads.creators.forms import CreatorSearchForm


@login_required
def map_view(request):
    """
    Vue principale de la carte des créateurs.
    """
    # Récupérer tous les créateurs avec coordonnées de localisation
    creators = Creator.objects.filter(
        location__isnull=False,
        location__latitude__isnull=False,
        location__longitude__isnull=False
    )
    
    # Formulaire de recherche pour les filtres
    form = CreatorSearchForm(request.GET)
    
    context = {
        'form': form,
        'total_creators': creators.count(),
    }
    
    return render(request, 'map/map_view.html', context)


@login_required
def ajax_map_data(request):
    """
    Endpoint AJAX pour les données de carte avec filtres.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Ajax map data request with params: {request.GET}")
    
    if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'error': 'AJAX requests only'}, status=400)
    
    # Filtres de base - uniquement créateurs avec coordonnées
    creators = Creator.objects.filter(
        location__isnull=False,
        location__latitude__isnull=False, 
        location__longitude__isnull=False
    )
    
    try:
        # Appliquer les filtres supplémentaires
        form = CreatorSearchForm(request.GET)
        if form.is_valid():
            data = form.cleaned_data
            logger.info(f"Form is valid with data: {data}")
            
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
    except Exception as e:
        logger.error(f"Error applying filters: {e}")
        return JsonResponse({'error': str(e), 'points': []}, status=500)
    
    # Préparer les données pour la carte
    map_points = []
    try:
        for creator in creators:
            if creator.location and creator.location.latitude and creator.location.longitude:
                # Trouver une image pour l'aperçu
                thumbnail = None
                try:
                    if creator.media.filter(media_type='image').exists():
                        media_obj = creator.media.filter(media_type='image').first()
                        # Vérifier si le fichier existe réellement
                        if media_obj.file and hasattr(media_obj.file, 'name') and media_obj.file.name:
                            thumbnail = media_obj.file.url
                except Exception as media_error:
                    logger.warning(f"Error getting media for creator {creator.id}: {media_error}")
                    
                # Utiliser la fonction reverse pour générer une URL correcte
                creator_url = reverse('creator_detail', kwargs={'creator_id': creator.id})
                
                map_points.append({
                    'id': creator.id,
                    'name': creator.full_name,
                    'lat': float(creator.location.latitude),
                    'lng': float(creator.location.longitude),
                    'rating': float(creator.average_rating),
                    'thumbnail': thumbnail,
                    'url': creator_url,
                })
    except Exception as e:
        logger.error(f"Error preparing map points: {e}")
        return JsonResponse({'error': str(e), 'points': []}, status=500)
        
    logger.info(f"Returning {len(map_points)} map points")
    return JsonResponse({
        'points': map_points,
        'total': len(map_points)
    })


@login_required
def map_search_view(request):
    """
    Vue de recherche sur la carte des créateurs.
    """
    # Récupérer tous les créateurs avec coordonnées de localisation
    creators = Creator.objects.filter(
        location__isnull=False,
        location__latitude__isnull=False,
        location__longitude__isnull=False
    )
    
    # Formulaire de recherche pour les filtres
    form = CreatorSearchForm(request.GET)
    
    context = {
        'form': form,
        'total_creators': creators.count(),
    }
    
    return render(request, 'map/map_search.html', context)


@login_required
def api_creators(request):
    """
    API endpoint for retrieving creators with valid location data.
    Returns a list of creators with their location and profile information.
    """
    # Get creators with valid location data
    creators = Creator.objects.filter(
        location__latitude__isnull=False,
        location__longitude__isnull=False
    )

    # Apply filters if provided
    min_rating = request.GET.get('min_rating')
    if min_rating and min_rating.isdigit():
        creators = creators.filter(avg_rating__gte=float(min_rating))
    
    min_age = request.GET.get('min_age')
    max_age = request.GET.get('max_age')
    if min_age and min_age.isdigit():
        creators = creators.filter(age__gte=int(min_age))
    if max_age and max_age.isdigit():
        creators = creators.filter(age__lte=int(max_age))
    
    city = request.GET.get('city')
    if city:
        creators = creators.filter(location__city__icontains=city)

    # Prepare the creator data
    creators_data = []
    for creator in creators:
        creator_data = {
            'id': creator.id,
            'name': f"{creator.first_name} {creator.last_name}",
            'rating': creator.avg_rating,
            'age': creator.age,
            'image': creator.profile_image.url if creator.profile_image else None,
            'lat': creator.location.latitude,
            'lng': creator.location.longitude,
            'city': creator.location.city,
            'country': creator.location.country,
            'url': reverse('creator_detail', args=[creator.id])
        }
        creators_data.append(creator_data)
    
    return JsonResponse(creators_data, safe=False)
