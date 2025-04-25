"""
Modèles de l'application Creators du projet NEADS.

Cette application gère les profils des créateurs de contenu, leur portfolio, 
les évaluations et les favoris. Elle constitue le cœur fonctionnel de la plateforme
en permettant de mettre en relation les créateurs avec les clients potentiels.

Modèles principaux:
- Creator: Profil complet d'un créateur de contenu
- Domain: Domaines d'expertise des créateurs
- ContentType: Types de contenu proposés par les créateurs
- Location: Informations de localisation des créateurs
- Media: Fichiers médias (images/vidéos) constituant le portfolio
- Rating: Évaluations et commentaires sur les créateurs
- Favorite: Sauvegarde de créateurs favoris par utilisateur

Relations principales:
- Creator peut être lié à un User (relation one-to-one facultative)
- Creator est lié à une Location (relation many-to-one)
- Creator a plusieurs Domain et ContentType (relations many-to-many)
- Creator a plusieurs Media, Rating et Favorite (relations one-to-many)
- Creator est lié à un MapPoint dans l'application Map (relation one-to-one)

Voir README.md pour plus de détails sur l'architecture et l'utilisation.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from neads.core.models import User
from django.utils import timezone
import os


def image_upload_path(instance, filename):
    # Upload path avec timestamp pour éviter les collisions de noms
    creator_id = instance.creator.id
    ext = filename.split('.')[-1]
    filename = f"{timezone.now().timestamp()}_{creator_id}.{ext}"
    return os.path.join('creators', str(creator_id), 'images', filename)


def video_upload_path(instance, filename):
    # Upload path avec timestamp pour éviter les collisions de noms
    creator_id = instance.creator.id
    ext = filename.split('.')[-1]
    filename = f"{timezone.now().timestamp()}_{creator_id}.{ext}"
    return os.path.join('creators', str(creator_id), 'videos', filename)


class Domain(models.Model):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, blank=True, null=True)  # Classe CSS pour icône
    
    def __str__(self):
        return self.name


class ContentType(models.Model):
    name = models.CharField(max_length=50)
    
    def __str__(self):
        return self.name


class Location(models.Model):
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.city}, {self.country}"


class Creator(models.Model):
    GENDER_CHOICES = (
        ('M', 'Homme'),
        ('F', 'Femme'),
        ('O', 'Autre'),
    )
    
    CONTENT_TYPE_CHOICES = (
        ('video', 'Vidéo'),
        ('image', 'Image'),
        ('audio', 'Audio'),
        ('ugc_duo', 'UGC Duo'),
        ('animal', 'Animal'),
    )
    
    # Liens avec User (1-1 facultatif car peut exister sans compte)
    user = models.OneToOneField(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='creator_profile')
    
    # Informations personnelles
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    full_name = models.CharField(max_length=100, blank=True)  # Auto-généré
    age = models.PositiveIntegerField(validators=[MinValueValidator(13), MaxValueValidator(100)])
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    
    # Réseaux sociaux
    youtube_link = models.URLField(max_length=255, blank=True, null=True, verbose_name="Chaîne YouTube")
    tiktok_link = models.URLField(max_length=255, blank=True, null=True, verbose_name="Profil TikTok")
    instagram_link = models.URLField(max_length=255, blank=True, null=True, verbose_name="Profil Instagram")
    
    # Localisation
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, related_name='creators')
    
    # Contact
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)

    # Domaines d'expertise
    domains = models.ManyToManyField(Domain, related_name='creators')
    
    # Détails professionnels
    bio = models.TextField(blank=True, null=True)
    equipment = models.CharField(max_length=255, blank=True, null=True)
    delivery_time = models.CharField(max_length=50, blank=True, null=True)
    content_types = models.ManyToManyField(ContentType, related_name='creators', blank=True)
    mobility = models.BooleanField(default=False)
    can_invoice = models.BooleanField(default=False)
    previous_clients = models.TextField(blank=True, null=True)
    
    # Métriques et notation
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    total_ratings = models.PositiveIntegerField(default=0)
    verified_by_neads = models.BooleanField(default=False)
    
    # Timestamps et métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return self.full_name or f"{self.first_name} {self.last_name}"
    
    def save(self, *args, **kwargs):
        self.full_name = f"{self.first_name} {self.last_name}"
        super().save(*args, **kwargs)
    
    def update_ratings(self):
        # Prendre en compte tous les avis (plus de filtre is_verified)
        ratings = self.ratings.all()
        if ratings.exists():
            avg = ratings.aggregate(models.Avg('rating'))['rating__avg']
            count = ratings.count()
            self.average_rating = round(avg, 2)
            self.total_ratings = count
            self.save()
    
    def get_image_count(self):
        return self.media.filter(media_type='image').count()
    
    def get_video_count(self):
        return self.media.filter(media_type='video').count()
    
    def has_social_links(self):
        return bool(self.youtube_link or self.tiktok_link or self.instagram_link)


class Media(models.Model):
    MEDIA_TYPE_CHOICES = (
        ('image', 'Image'),
        ('video', 'Vidéo'),
    )
    
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name='media')
    title = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    media_type = models.CharField(max_length=5, choices=MEDIA_TYPE_CHOICES)
    file = models.FileField(upload_to=image_upload_path, blank=True, null=True)
    video_file = models.FileField(upload_to=video_upload_path, blank=True, null=True)
    thumbnail = models.ImageField(upload_to=image_upload_path, blank=True, null=True)
    
    # Pour les vidéos
    duration = models.PositiveIntegerField(blank=True, null=True)  # durée en secondes
    
    # Métadonnées
    upload_date = models.DateTimeField(auto_now_add=True)
    order = models.PositiveIntegerField(default=0)
    is_verified = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['order', '-upload_date']
    
    def __str__(self):
        return f"{self.get_media_type_display()} de {self.creator}"
    
    def save(self, *args, **kwargs):
        # Limitation du nombre de médias par créateur
        if self.media_type == 'image' and self.creator.get_image_count() >= 10 and not self.pk:
            raise ValueError("Le nombre maximum d'images (10) est atteint")
        if self.media_type == 'video' and self.creator.get_video_count() >= 10 and not self.pk:
            raise ValueError("Le nombre maximum de vidéos (10) est atteint")
        
        super().save(*args, **kwargs)


class Rating(models.Model):
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='ratings')
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Vérification (pour les avis clients)
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='verified_ratings')
    
    # Pour marquer si l'utilisateur déclare avoir eu une expérience avec le créateur
    has_experience = models.BooleanField(default=False, help_text="L'utilisateur a eu une expérience réelle avec ce créateur")
    
    class Meta:
        unique_together = ('creator', 'user')
    
    def __str__(self):
        return f"Note de {self.rating} pour {self.creator} par {self.user}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.creator.update_ratings()


class Favorite(models.Model):
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name='favorites')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ('creator', 'user')
    
    def __str__(self):
        return f"{self.creator} favori de {self.user}"
