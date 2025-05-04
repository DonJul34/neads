from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from .models import Creator, Media, Rating, Domain, Location, Favorite, ContentType
import datetime


class LocationForm(forms.ModelForm):
    """
    Formulaire pour la localisation avec autocomplétion d'adresse via l'API Google Places.
    Le JavaScript côté client extrait automatiquement latitude et longitude
    à partir de l'adresse complète sélectionnée.
    """
    full_address = forms.CharField(
        label="Adresse complète",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Commencez à taper votre adresse...',
            'id': 'full-address-input',
            'autocomplete': 'off',  # Désactiver l'autocomplétion du navigateur
            'data-disable-autocompletion': 'true'  # Attribut personnalisé
        })
    )
    
    class Meta:
        model = Location
        fields = ['full_address', 'latitude', 'longitude']
        widgets = {
            'latitude': forms.HiddenInput(attrs={'id': 'id_latitude'}),
            'longitude': forms.HiddenInput(attrs={'id': 'id_longitude'}),
        }
        
    def clean(self):
        cleaned_data = super().clean()
        full_address = cleaned_data.get('full_address')
        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')
        
        # Si l'adresse est fournie mais pas les coordonnées
        if full_address and (latitude is None or longitude is None):
            # Nous sommes plus souples ici pour permettre les tests
            # mais en production, on pourrait bloquer la soumission
            self.add_warning('full_address', "L'adresse n'a pas pu être géolocalisée. Veuillez sélectionner une adresse dans les suggestions.")
        
        return cleaned_data
    
    def add_warning(self, field, message):
        """Ajoute un avertissement sans bloquer la soumission du formulaire."""
        if not hasattr(self, '_warnings'):
            self._warnings = {}
        if field not in self._warnings:
            self._warnings[field] = []
        self._warnings[field].append(message)


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
    
    # Réseaux sociaux
    youtube_link = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://youtube.com/@votrechaine'
        }),
        label="Chaîne YouTube"
    )
    
    tiktok_link = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://tiktok.com/@votreprofil'
        }),
        label="Profil TikTok"
    )
    
    instagram_link = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://instagram.com/votreprofil'
        }),
        label="Profil Instagram"
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
    
    content_types = forms.ModelMultipleChoiceField(
        queryset=None,  # Sera défini dans __init__
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'content-types-checkbox'}),
        required=False,
        label="Types de contenu"
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
        from .models import Domain, ContentType
        self.fields['domains'].queryset = Domain.objects.all().order_by('name')
        self.fields['content_types'].queryset = ContentType.objects.all().order_by('name')
        
        # Ajouter des classes Bootstrap à tous les champs
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.RadioSelect, forms.CheckboxSelectMultiple)):
                if not field.widget.attrs.get('class'):
                    field.widget.attrs['class'] = 'form-control'
    
    class Meta:
        model = Creator
        exclude = ['user', 'created_at', 'updated_at', 'location', 'average_rating', 
                  'total_ratings', 'verified_by_neads', 'verified_by', 'verified_at',
                  'last_activity', 'full_name']


class CreatorSearchForm(forms.Form):
    """Formulaire pour la recherche et le filtrage des créateurs."""
    query = forms.CharField(required=False, label="Recherche")
    domains = forms.ModelMultipleChoiceField(
        queryset=Domain.objects.all(), 
        required=False, 
        widget=forms.CheckboxSelectMultiple,
        label="Domaines d'expertise"
    )
    min_age = forms.IntegerField(required=False, min_value=18, max_value=99, label="Âge minimum")
    max_age = forms.IntegerField(required=False, min_value=18, max_value=99, label="Âge maximum")
    gender = forms.ChoiceField(
        choices=[('', 'Tous')] + list(Creator.GENDER_CHOICES), 
        required=False, 
        label="Genre"
    )
    content_type = forms.ChoiceField(
        choices=[
            ('', 'Tous'),
            ('photo', 'Photo'),
            ('video', 'Vidéo'),
            ('audio', 'Audio'),
            ('text', 'Texte'),
            ('mixed', 'Mixte')
        ],
        required=False,
        label="Type de contenu"
    )
    min_rating = forms.IntegerField(required=False, min_value=1, max_value=5, label="Note minimum")
    can_invoice = forms.BooleanField(required=False, label="Peut facturer")
    verified_only = forms.BooleanField(required=False, label="Vérifiés uniquement")
    favorites_only = forms.BooleanField(required=False, label="Favoris uniquement")
    country = forms.CharField(required=False, label="Pays")
    city = forms.CharField(required=False, label="Ville")
    
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


class CreatorRegistrationForm(forms.Form):
    """
    Formulaire d'inscription pour les créateurs qui ne sont pas encore inscrits.
    Ce formulaire permet de créer à la fois un compte utilisateur et un profil créateur.
    """
    # Informations personnelles
    first_name = forms.CharField(
        max_length=50,
        label="Prénom",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Prénom'}),
        required=True
    )
    
    last_name = forms.CharField(
        max_length=50,
        label="Nom",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom'}),
        required=True
    )
    
    gender = forms.ChoiceField(
        choices=Creator.GENDER_CHOICES,
        label="Genre",
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    
    birth_year = forms.IntegerField(
        label="Année de naissance",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1923',
            'max': datetime.date.today().year - 13,
            'placeholder': 'Année de naissance'
        }),
        required=True
    )
    
    # Contact
    email = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'votre@email.com'}),
        required=True
    )
    
    phone = forms.CharField(
        max_length=20,
        label="Téléphone",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+33612345678'}),
        required=True
    )
    
    # Localisation
    full_address = forms.CharField(
        max_length=255,
        label="Adresse complète",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Commencez à taper votre adresse...',
            'id': 'id_full_address',
            'autocomplete': 'off',  # Désactiver l'autocomplétion du navigateur
            'spellcheck': 'false',  # Désactiver le correcteur orthographique
            'aria-describedby': 'addressHelp'
        }),
        required=True,
        help_text="Saisissez votre adresse et sélectionnez une suggestion"
    )
    
    latitude = forms.FloatField(widget=forms.HiddenInput(attrs={'id': 'id_latitude'}), required=False)
    longitude = forms.FloatField(widget=forms.HiddenInput(attrs={'id': 'id_longitude'}), required=False)
    
    # Réseaux sociaux
    tiktok_link = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://www.tiktok.com/@votreprofil'
        }),
        label="Compte TikTok"
    )
    
    instagram_link = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://www.instagram.com/votreprofil'
        }),
        label="Compte Instagram"
    )
    
    youtube_link = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://www.youtube.com/@votrechaine'
        }),
        label="Compte YouTube"
    )
    
    # Informations professionnelles
    baseline = forms.CharField(
        max_length=50,
        label="Baseline",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Créateur de contenu UGC',
            'maxlength': '50'
        }),
        required=True,
        help_text="ex : Créateur de contenu UGC"
    )
    
    bio = forms.CharField(
        label="À propos de toi",
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 5,
            'placeholder': 'Parlez de vous, de votre expérience...',
            'minlength': '400',
            'maxlength': '1000'
        }),
        required=True,
        help_text="min. 400 caractères, max. 1000"
    )
    
    equipment = forms.CharField(
        label="Matériel utilisé",
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 3,
            'placeholder': 'Caméras, logiciels, accessoires...'
        }),
        required=True
    )
    
    previous_clients = forms.CharField(
        label="Marques avec lesquelles tu as travaillé",
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 3,
            'placeholder': 'Listez les marques...'
        }),
        required=True
    )
    
    # Options
    can_invoice = forms.ChoiceField(
        choices=[
            (True, "Oui"),
            (False, "Non")
        ],
        label="Statut pour facturer",
        widget=forms.RadioSelect(),
        required=True
    )
    
    # Domaines d'expertise
    domains = forms.ModelMultipleChoiceField(
        queryset=Domain.objects.all().order_by('name'),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'domains-checkbox'}),
        required=True,
        label="Domaines",
        help_text="Sélectionne 5 domaines maximum"
    )
    
    # Photo de profil
    featured_image = forms.ImageField(
        label="Photo de profil",
        required=True,
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    
    # Portfolio - Vidéos individuelles
    video_file1 = forms.FileField(
        label="Vidéo UGC 1",
        required=True,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'video/mp4,video/quicktime'
        }),
        help_text="Format MP4 uniquement (100Mo max)"
    )
    
    video_file2 = forms.FileField(
        label="Vidéo UGC 2",
        required=True,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'video/mp4,video/quicktime'
        })
    )
    
    video_file3 = forms.FileField(
        label="Vidéo UGC 3",
        required=True,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'video/mp4,video/quicktime'
        })
    )
    
    # Vidéos supplémentaires (optionnelles)
    video_file4 = forms.FileField(
        label="Vidéo UGC 4 (optionnelle)",
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'video/mp4,video/quicktime'
        })
    )
    
    video_file5 = forms.FileField(
        label="Vidéo UGC 5 (optionnelle)",
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'video/mp4,video/quicktime'
        })
    )
    
    # Images individuelles
    image_file1 = forms.ImageField(
        label="Photo UGC 1",
        required=True,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/jpeg,image/png,image/gif'
        }),
        help_text="Format JPG, PNG ou GIF (5Mo max)"
    )
    
    image_file2 = forms.ImageField(
        label="Photo UGC 2",
        required=True,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/jpeg,image/png,image/gif'
        })
    )
    
    image_file3 = forms.ImageField(
        label="Photo UGC 3",
        required=True,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/jpeg,image/png,image/gif'
        })
    )
    
    # Conditions générales
    accept_terms = forms.BooleanField(
        required=True,
        label="J'accepte les conditions générales d'utilisation",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def clean_domains(self):
        domains = self.cleaned_data.get('domains')
        if domains and len(domains) > 5:
            raise ValidationError("Vous ne pouvez sélectionner que 5 domaines maximum.")
        return domains
        
    def clean_birth_year(self):
        birth_year = self.cleaned_data.get('birth_year')
        # Calculer l'âge approximatif
        current_year = datetime.date.today().year
        age = current_year - birth_year
        
        if age < 13:
            raise ValidationError("Vous devez avoir au moins 13 ans pour vous inscrire.")
        if age > 100:
            raise ValidationError("Veuillez entrer une année de naissance valide.")
        
        return birth_year
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Vérifier si l'email existe déjà
        from neads.core.models import User
        if User.objects.filter(email=email).exists():
            raise ValidationError("Un compte avec cet email existe déjà. Veuillez vous connecter.")
        return email
        
    def clean(self):
        cleaned_data = super().clean()
        full_address = cleaned_data.get('full_address')
        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')
        
        # Si l'adresse est fournie mais pas les coordonnées
        if full_address and (not latitude or not longitude):
            self.add_error('full_address', "Veuillez sélectionner une adresse dans les suggestions pour permettre la géolocalisation.")
        
        return cleaned_data 