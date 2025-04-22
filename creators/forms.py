from django import forms
from .models import Domain

class CreatorFilterForm(forms.Form):
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Rechercher un créateur...'})
    )
    
    domains = forms.ModelMultipleChoiceField(
        queryset=Domain.objects.all().order_by('name'),
        required=False,
        widget=forms.CheckboxSelectMultiple
    )
    
    country = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Pays'})
    )
    
    city = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Ville'})
    )
    
    GENDER_CHOICES = (
        ('', 'Tous'),
        ('M', 'Homme'),
        ('F', 'Femme'),
        ('O', 'Autre')
    )
    
    gender = forms.ChoiceField(
        choices=GENDER_CHOICES,
        required=False
    )
    
    CONTENT_TYPE_CHOICES = (
        ('', 'Tous'),
        ('photo', 'Photo'),
        ('video', 'Vidéo'),
        ('article', 'Article'),
        ('podcast', 'Podcast'),
        ('livestream', 'Livestream')
    )
    
    content_type = forms.ChoiceField(
        choices=CONTENT_TYPE_CHOICES,
        required=False
    )
    
    min_age = forms.IntegerField(
        required=False,
        min_value=16,
        widget=forms.NumberInput(attrs={'placeholder': 'Âge minimum'})
    )
    
    max_age = forms.IntegerField(
        required=False,
        min_value=16,
        widget=forms.NumberInput(attrs={'placeholder': 'Âge maximum'})
    )
    
    can_invoice = forms.BooleanField(
        required=False,
        label='Peut facturer'
    )
    
    verified_only = forms.BooleanField(
        required=False,
        label='Profils vérifiés uniquement'
    )
    
    RATING_CHOICES = (
        ('', 'Toutes notes'),
        ('3', '3 étoiles et plus'),
        ('4', '4 étoiles et plus'),
        ('5', '5 étoiles uniquement')
    )
    
    min_rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        required=False
    )
    
    def clean_min_rating(self):
        min_rating = self.cleaned_data.get('min_rating')
        if min_rating and min_rating.isdigit():
            return float(min_rating)
        return None 