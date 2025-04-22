from django import forms
from django.core.exceptions import ValidationError
from .models import Creator, Media, Rating, Domain, Location, Favorite


class LocationForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = ['city', 'country', 'postal_code', 'latitude', 'longitude']
        
    def clean(self):
        cleaned_data = super().clean()
        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')
        
        if (latitude is None or longitude is None) and cleaned_data.get('city') and cleaned_data.get('country'):
            # Ici on pourrait implémenter un appel à une API de géocodage
            # pour obtenir automatiquement les coordonnées à partir de la ville et du pays
            pass
            
        return cleaned_data


class CreatorForm(forms.ModelForm):
    domains = forms.ModelMultipleChoiceField(
        queryset=Domain.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    
    class Meta:
        model = Creator
        fields = [
            'first_name', 'last_name', 'age', 'gender', 
            'email', 'phone', 'bio', 'equipment', 'delivery_time', 
            'content_types', 'mobility', 'can_invoice', 'previous_clients',
            'domains'
        ]
        
    def clean_age(self):
        age = self.cleaned_data.get('age')
        if age < 13:
            raise ValidationError("L'âge minimum est de 13 ans.")
        return age


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
        
    def clean(self):
        cleaned_data = super().clean()
        media_type = cleaned_data.get('media_type')
        file = cleaned_data.get('file')
        video_file = cleaned_data.get('video_file')
        
        if media_type == 'image' and not file:
            self.add_error('file', "Le fichier image est requis pour ce type de média.")
        
        if media_type == 'video' and not video_file:
            self.add_error('video_file', "Le fichier vidéo est requis pour ce type de média.")
            
        return cleaned_data


class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.RadioSelect(choices=[(i, i) for i in range(1, 6)]),
            'comment': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Votre commentaire (facultatif)'})
        }


class FavoriteForm(forms.ModelForm):
    class Meta:
        model = Favorite
        fields = ['notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Notes personnelles (facultatif)'})
        } 