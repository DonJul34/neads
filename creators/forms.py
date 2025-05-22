from django import forms
from .models import Domain
from django.db.models import Count

class CreatorFilterForm(forms.Form):
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Rechercher un créateur par nom ou prénom...',
            'class': 'form-control'
        })
    )
    
    # On récupérera les 6 domaines les plus utilisés dans la vue
    domains = forms.ModelMultipleChoiceField(
        queryset=Domain.objects.all().order_by('name'),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'domain-checkbox'
        })
    )
    
    # Champ de recherche de domaine
    domain_search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Rechercher un domaine...',
            'class': 'form-control domain-search',
            'autocomplete': 'off'
        })
    )
    
    # Suppression des champs de localisation
    # country et city sont supprimés
    
    GENDER_CHOICES = (
        ('', 'Tous'),
        ('M', 'Homme'),
        ('F', 'Femme'),
        ('O', 'Autre')
    )
    
    gender = forms.ChoiceField(
        choices=GENDER_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    CONTENT_TYPE_CHOICES = (
        ('', 'Tous'),
        ('photo', 'Photo'),
        ('video', 'Vidéo'),
        ('article', 'Article'),
        ('podcast', 'Podcast'),
        ('livestream', 'Livestream')
    )
    
    # Les champs min_age et max_age ne sont plus des NumberInput
    # mais seront gérés par un curseur à double point (RangeSlider)
    # Les valeurs min_age et max_age seront définies dans le HTML
    # en fonction de l'âge minimum et maximum des créateurs
    min_age = forms.IntegerField(
        required=False,
        min_value=16,
        widget=forms.HiddenInput()
    )
    
    max_age = forms.IntegerField(
        required=False,
        min_value=16,
        widget=forms.HiddenInput()
    )
    
    can_invoice = forms.BooleanField(
        required=False,
        label='Peut facturer',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    verified_only = forms.BooleanField(
        required=False,
        label='Profils vérifiés uniquement',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    # La note minimum sera sélectionnée avec des étoiles
    # nous utilisons un champ caché qui sera mis à jour par JavaScript
    min_rating = forms.DecimalField(
        required=False,
        min_value=0,
        max_value=5,
        widget=forms.HiddenInput(attrs={'id': 'min_rating_input'})
    )
    
    def clean_min_rating(self):
        min_rating = self.cleaned_data.get('min_rating')
        if min_rating is not None:
            return float(min_rating)
        return None 