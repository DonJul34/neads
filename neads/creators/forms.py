from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from .models import Creator, Media, Rating, Domain, Location, Favorite
import datetime


class LocationForm(forms.ModelForm):
    """
    Formulaire pour la localisation avec autocomplétion de ville.
    Les champs latitude et longitude sont cachés et seront remplis automatiquement
    par le JavaScript côté client.
    """
    city = forms.CharField(
        label="Ville",
        widget=forms.TextInput(attrs={
            'class': 'form-control location-autocomplete',
            'placeholder': 'Commencez à taper une ville...',
            'id': 'location-input'
        })
    )
    
    class Meta:
        model = Location
        fields = ['city', 'country', 'postal_code', 'latitude', 'longitude']
        widgets = {
            'country': forms.HiddenInput(),
            'postal_code': forms.HiddenInput(),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        # Pas besoin de validation ici, les champs cachés sont remplis par JS
        return cleaned_data


class CreatorForm(forms.ModelForm):
    """
    Formulaire pour la création/édition d'un profil de créateur.
    """
    # Champs personnalisés
    age = forms.IntegerField(
        validators=[MinValueValidator(13)],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '13',
            'max': '100',
        }),
        help_text="Vous devez avoir au moins 13 ans pour utiliser cette plateforme."
    )
    
    gender = forms.ChoiceField(
        choices=Creator.GENDER_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    
    bio = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 5,
            'placeholder': 'Décrivez-vous, votre expérience, et votre style...'
        }),
        required=False
    )
    
    equipment = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 3,
            'placeholder': 'Caméras, logiciels, matériel...'
        }),
        required=False
    )
    
    content_types = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 2, 
            'placeholder': 'Photos, vidéos, podcasts...'
        }),
        required=False
    )
    
    previous_clients = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 2,
            'placeholder': 'Clients avec lesquels vous avez déjà travaillé...'
        }),
        required=False
    )
    
    # Override des champs standards
    first_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    last_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    
    phone = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=False
    )
    
    birth_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'max': datetime.date.today().isoformat()
        }),
        required=False
    )
    
    # Champs avancés
    mobility = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        required=False
    )
    
    can_invoice = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        required=False
    )
    
    # Champs ManyToMany
    domains = forms.ModelMultipleChoiceField(
        queryset=None,  # Sera défini dans __init__
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'domains-checkbox'}),
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Domain
        self.fields['domains'].queryset = Domain.objects.all().order_by('name')
        
        # Ajouter des classes Bootstrap à tous les champs
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.RadioSelect)):
                if not field.widget.attrs.get('class'):
                    field.widget.attrs['class'] = 'form-control'
    
    class Meta:
        model = Creator
        exclude = ['user', 'created_at', 'updated_at', 'location', 'average_rating', 
                  'total_ratings', 'verified_by_neads', 'verified_by', 'verified_at',
                  'last_activity', 'full_name']


class CreatorSearchForm(forms.Form):
    query = forms.CharField(required=False, label="Recherche par nom")
    domains = forms.ModelMultipleChoiceField(
        queryset=Domain.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Domaines"
    )
    min_age = forms.IntegerField(required=False, min_value=13, max_value=100, label="Âge minimum")
    max_age = forms.IntegerField(required=False, min_value=13, max_value=100, label="Âge maximum")
    gender = forms.ChoiceField(
        choices=[('', 'Tous')] + list(Creator.GENDER_CHOICES),
        required=False,
        label="Genre"
    )
    content_type = forms.ChoiceField(
        choices=[('', 'Tous')] + list(Creator.CONTENT_TYPE_CHOICES),
        required=False,
        label="Type de contenu"
    )
    country = forms.CharField(required=False, label="Pays")
    city = forms.CharField(required=False, label="Ville")
    min_rating = forms.DecimalField(
        required=False, 
        min_value=0, 
        max_value=5,
        decimal_places=1,
        label="Note minimum"
    )
    can_invoice = forms.BooleanField(required=False, label="Peut facturer")
    verified_only = forms.BooleanField(required=False, label="Vérifiés NEADS uniquement")
    
    def clean(self):
        cleaned_data = super().clean()
        min_age = cleaned_data.get('min_age')
        max_age = cleaned_data.get('max_age')
        
        if min_age and max_age and min_age > max_age:
            raise ValidationError("L'âge minimum ne peut pas être supérieur à l'âge maximum.")
            
        return cleaned_data


class MediaUploadForm(forms.ModelForm):
    class Meta:
        model = Media
        fields = ['title', 'description', 'media_type', 'file', 'video_file', 'thumbnail']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Titre du média'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': '3', 'placeholder': 'Description du contenu...'}),
            'media_type': forms.Select(attrs={'class': 'form-select'}),
            'file': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/jpeg,image/png,image/gif'}),
            'video_file': forms.FileInput(attrs={'class': 'form-control', 'accept': 'video/mp4'}),
            'thumbnail': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/jpeg,image/png,image/gif'}),
        }
        
    def clean(self):
        cleaned_data = super().clean()
        media_type = cleaned_data.get('media_type')
        file = cleaned_data.get('file')
        video_file = cleaned_data.get('video_file')
        thumbnail = cleaned_data.get('thumbnail')
        
        # Validation selon le type de média
        if media_type == 'image':
            if not file:
                self.add_error('file', "Une image est requise pour ce type de média.")
            if video_file:
                self.add_error('video_file', "Un fichier vidéo n'est pas autorisé pour une publication de type image.")
            if thumbnail:
                self.add_error('thumbnail', "Une miniature n'est pas nécessaire pour une publication de type image.")
                
        elif media_type == 'video':
            if not video_file:
                self.add_error('video_file', "Une vidéo est requise pour ce type de média.")
            if file:
                self.add_error('file', "Un fichier image n'est pas autorisé pour une publication de type vidéo.")
            if not thumbnail:
                self.add_error('thumbnail', "Une miniature est requise pour les vidéos afin d'afficher un aperçu dans la galerie.")
        
        # Validation des images
        if file:
            # Validation de la taille
            if file.size > 5 * 1024 * 1024:  # 5 Mo
                self.add_error('file', "L'image ne doit pas dépasser 5 Mo.")
            
            # Validation du type de fichier
            valid_image_types = ['image/jpeg', 'image/png', 'image/gif']
            if file.content_type not in valid_image_types:
                self.add_error('file', "Le format de l'image n'est pas valide. Utilisez uniquement JPG, PNG ou GIF.")
            
            # Validation de l'extension
            file_name = file.name.lower()
            if not (file_name.endswith('.jpg') or file_name.endswith('.jpeg') or 
                    file_name.endswith('.png') or file_name.endswith('.gif')):
                self.add_error('file', "L'extension du fichier n'est pas valide. Utilisez .jpg, .jpeg, .png ou .gif.")
        
        # Validation des vidéos
        if video_file:
            # Validation de la taille
            if video_file.size > 50 * 1024 * 1024:  # 50 Mo
                self.add_error('video_file', "La vidéo ne doit pas dépasser 50 Mo.")
            
            # Validation du type de fichier
            if video_file.content_type != 'video/mp4':
                self.add_error('video_file', "Le format de la vidéo n'est pas valide. Utilisez uniquement MP4.")
            
            # Validation de l'extension
            if not video_file.name.lower().endswith('.mp4'):
                self.add_error('video_file', "L'extension du fichier n'est pas valide. Utilisez uniquement .mp4.")
            
            # On pourrait ajouter ici une validation de la durée avec une bibliothèque comme moviepy
            # Cette fonctionnalité nécessiterait l'installation de dépendances supplémentaires
        
        # Validation des miniatures
        if thumbnail:
            # Validation de la taille
            if thumbnail.size > 5 * 1024 * 1024:  # 5 Mo
                self.add_error('thumbnail', "La miniature ne doit pas dépasser 5 Mo.")
            
            # Validation du type de fichier
            valid_image_types = ['image/jpeg', 'image/png', 'image/gif']
            if thumbnail.content_type not in valid_image_types:
                self.add_error('thumbnail', "Le format de la miniature n'est pas valide. Utilisez uniquement JPG, PNG ou GIF.")
            
            # Validation de l'extension
            thumbnail_name = thumbnail.name.lower()
            if not (thumbnail_name.endswith('.jpg') or thumbnail_name.endswith('.jpeg') or 
                    thumbnail_name.endswith('.png') or thumbnail_name.endswith('.gif')):
                self.add_error('thumbnail', "L'extension du fichier n'est pas valide. Utilisez .jpg, .jpeg, .png ou .gif.")
        
        return cleaned_data


class RatingForm(forms.ModelForm):
    has_experience = forms.BooleanField(
        required=True,
        label="J'ai déjà travaillé avec ce créateur",
        help_text="Pour garantir la qualité des avis, seuls les utilisateurs ayant eu une expérience réelle avec le créateur peuvent le noter. Les avis non vérifiés pourront être supprimés.",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = Rating
        fields = ['rating', 'comment', 'has_experience']
        widgets = {
            'rating': forms.RadioSelect(choices=[(i, i) for i in range(1, 6)], attrs={'class': 'form-check-input'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Votre commentaire (facultatif)'})
        }


class FavoriteForm(forms.ModelForm):
    class Meta:
        model = Favorite
        fields = ['notes']
        widgets = {
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Notes personnelles (facultatif)'})
        } 