from django.db import models
from neads.creators.models import Creator, Location


class MapPoint(models.Model):
    creator = models.OneToOneField(Creator, on_delete=models.CASCADE, related_name='map_point')
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, related_name='map_points')
    
    # Coordonnées (peuvent être différentes de celles de Location pour le clustering)
    latitude = models.FloatField()
    longitude = models.FloatField()
    
    # Informations pour l'affichage sur la carte
    popup_title = models.CharField(max_length=100, blank=True, null=True)
    popup_content = models.TextField(blank=True, null=True)
    icon_type = models.CharField(max_length=50, default='default')
    
    # Métadonnées
    is_visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Point sur la carte pour {self.creator}"
    
    def save(self, *args, **kwargs):
        # Auto-générer le titre du popup s'il n'existe pas
        if not self.popup_title and self.creator:
            self.popup_title = str(self.creator)
            
        # Utiliser les coordonnées de la location si elles ne sont pas définies
        if not self.latitude and self.location and self.location.latitude:
            self.latitude = self.location.latitude
            
        if not self.longitude and self.location and self.location.longitude:
            self.longitude = self.location.longitude
            
        super().save(*args, **kwargs)


class MapCluster(models.Model):
    name = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()
    zoom_level = models.PositiveIntegerField(default=10)
    radius = models.PositiveIntegerField(default=50)  # rayon en km
    points_count = models.PositiveIntegerField(default=0)
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    is_dynamic = models.BooleanField(default=True)  # Si True, généré dynamiquement, sinon fixe
    
    def __str__(self):
        return f"Cluster {self.name} ({self.points_count} points)"
    
    def update_points_count(self):
        # Cette méthode serait normalement implémentée avec une requête géospatiale
        # Simplifiée ici pour l'exemple
        self.points_count = MapPoint.objects.filter(
            is_visible=True,
            latitude__gte=self.latitude - 0.5,
            latitude__lte=self.latitude + 0.5,
            longitude__gte=self.longitude - 0.5,
            longitude__lte=self.longitude + 0.5
        ).count()
        self.save()
