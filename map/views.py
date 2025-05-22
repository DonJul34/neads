from django.shortcuts import render
from django.http import JsonResponse
from django.views.generic import TemplateView
from creators.models import Creator, Domain
from django.db.models import Q, Avg
from creators.forms import CreatorFilterForm
from neads.creator.models import CreatorDomain

class MapView(TemplateView):
    template_name = 'map/map_view.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Initialiser le formulaire de filtrage avec les paramètres de requête
        form = CreatorFilterForm(self.request.GET)
        
        # Obtenir tous les domaines pour le filtrage
        domains = Domain.objects.all().order_by('name')
        
        # Filtrer les créateurs
        creators = Creator.objects.filter(is_active=True)
        filtered_creators = self.apply_filters(creators, form)
        
        context.update({
            'form': form,
            'domains': domains,
            'total_creators': filtered_creators.count(),
        })
        
        return context
    
    def apply_filters(self, queryset, form):
        """Applique les filtres à partir du formulaire à la queryset des créateurs"""
        if form.is_valid():
            data = form.cleaned_data
            
            # Filtrage par texte
            if data.get('query'):
                query = data['query']
                queryset = queryset.filter(
                    Q(user__first_name__icontains=query) | 
                    Q(user__last_name__icontains=query) |
                    Q(biography__icontains=query) |
                    Q(city__icontains=query)
                )
            
            # Filtrage par domaines
            if data.get('domains'):
                queryset = queryset.filter(domains__in=data['domains']).distinct()
            
            # Filtrage par pays
            if data.get('country'):
                queryset = queryset.filter(country=data['country'])
            
            # Filtrage par ville
            if data.get('city'):
                queryset = queryset.filter(city__icontains=data['city'])
            
            # Filtrage par genre
            if data.get('gender'):
                queryset = queryset.filter(gender=data['gender'])
            
            # Filtrage par âge
            if data.get('min_age'):
                queryset = queryset.filter(age__gte=data['min_age'])
            if data.get('max_age'):
                queryset = queryset.filter(age__lte=data['max_age'])
            
            # Filtrage par capacité de facturation
            if data.get('can_invoice'):
                queryset = queryset.filter(can_invoice=True)
            
            # Filtrage par vérification
            if data.get('verified_only'):
                queryset = queryset.filter(is_verified=True)
            
            # Filtrage par note minimale
            if data.get('min_rating'):
                queryset = queryset.annotate(
                    avg_rating=Avg('ratings__rating')
                ).filter(avg_rating__gte=data['min_rating'])
        
        return queryset

def map_data(request):
    """Vue AJAX pour récupérer les données des créateurs pour la carte"""
    # Initialiser le formulaire avec les paramètres de requête
    form = CreatorFilterForm(request.GET)
    
    # Obtenir les créateurs de base
    creators = Creator.objects.filter(is_active=True)
    
    # Appliquer les filtres
    if form.is_valid():
        data = form.cleaned_data
        
        # Filtrage par texte
        if data.get('query'):
            query = data['query']
            creators = creators.filter(
                Q(user__first_name__icontains=query) | 
                Q(user__last_name__icontains=query) |
                Q(biography__icontains=query) |
                Q(city__icontains=query)
            )
        
        # Filtrage par domaines
        if data.get('domains'):
            creators = creators.filter(domains__in=data['domains']).distinct()
        
        # Filtrage par pays
        if data.get('country'):
            creators = creators.filter(country=data['country'])
        
        # Filtrage par ville
        if data.get('city'):
            creators = creators.filter(city__icontains=data['city'])
        
        # Filtrage par genre
        if data.get('gender'):
            creators = creators.filter(gender=data['gender'])
        
        # Filtrage par âge
        if data.get('min_age'):
            creators = creators.filter(age__gte=data['min_age'])
        if data.get('max_age'):
            creators = creators.filter(age__lte=data['max_age'])
        
        # Filtrage par capacité de facturation
        if data.get('can_invoice'):
            creators = creators.filter(can_invoice=True)
        
        # Filtrage par vérification
        if data.get('verified_only'):
            creators = creators.filter(is_verified=True)
        
        # Filtrage par note minimale
        if data.get('min_rating'):
            creators = creators.annotate(
                avg_rating=Avg('ratings__rating')
            ).filter(avg_rating__gte=data['min_rating'])
    
    # Préparer les données pour la carte
    points = []
    for creator in creators.filter(latitude__isnull=False, longitude__isnull=False):
        # Calculer la note moyenne
        avg_rating = creator.ratings.aggregate(Avg('rating'))['rating__avg'] or 0
        
        # Obtenir le nom complet
        full_name = f"{creator.user.first_name} {creator.user.last_name}"
        
        # Ajouter le point à la liste
        points.append({
            'lat': float(creator.latitude),
            'lng': float(creator.longitude),
            'name': full_name,
            'rating': round(avg_rating, 1),
            'thumbnail': creator.profile_picture.url if creator.profile_picture else None,
            'url': f'/creators/{creator.id}/'
        })
    
    # Retourner les données au format JSON
    return JsonResponse({
        'total': creators.count(),
        'points': points
    })

def map_view(request):
    """Vue principale de la carte des créateurs"""
    
    # Récupération des domaines pour les filtres
    domains = CreatorDomain.objects.all().order_by('name')
    
    # Formulaire de filtrage
    form = CreatorFilterForm(request.GET or None)
    
    # Application des filtres
    creators = Creator.objects.select_related('user').all()
    
    # Total des créateurs (avant filtrage)
    total_creators = creators.count()
    
    context = {
        'domains': domains,
        'form': form,
        'total_creators': total_creators,
    }
    
    return render(request, 'map/map_view.html', context)

def map_data_ajax(request):
    """Vue Ajax pour renvoyer les données des créateurs au format JSON"""
    
    # Initialiser le formulaire de filtrage avec les paramètres GET
    form = CreatorFilterForm(request.GET or None)
    
    # Appliquer les filtres si le formulaire est valide
    creators = Creator.objects.select_related('user').filter(
        latitude__isnull=False, 
        longitude__isnull=False
    )
    
    if form.is_valid():
        filters = form.get_filters()
        if filters:
            creators = creators.filter(**filters)
    
    # Préparation des données pour la carte
    data = {
        'total': creators.count(),
        'points': []
    }
    
    # Récupérer les créateurs avec leurs coordonnées
    for creator in creators:
        if creator.latitude and creator.longitude:
            # Calcul de la note moyenne
            avg_rating = creator.reviews.aggregate(avg=Avg('rating'))['avg'] or 0
            
            data['points'].append({
                'id': creator.id,
                'name': creator.user.get_full_name() or creator.user.username,
                'lat': float(creator.latitude),
                'lng': float(creator.longitude),
                'rating': round(avg_rating, 1),
                'thumbnail': creator.profile_image.url if creator.profile_image else None,
                'url': creator.get_absolute_url(),
                'city': creator.city,
                'country': creator.country,
                'domains': list(creator.domains.values_list('name', flat=True)),
            })
    
    return JsonResponse(data) 