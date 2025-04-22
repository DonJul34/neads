from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.core.exceptions import ValidationError
from .models import User, UserProfile
import re


class LoginForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Votre email'})
    )
    password = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Votre mot de passe'})
    )


class TemporaryLoginForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Votre email'})
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise ValidationError("L'adresse email est obligatoire.")
        return email.lower()


class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(
        label="Prénom",
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        label="Nom",
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = UserProfile
        fields = ['profile_picture', 'phone_number', 'company_name']
        widgets = {
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Téléphone'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Entreprise'}),
        }


class UserRoleForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['role']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        is_admin = kwargs.pop('is_admin', False)
        super().__init__(*args, **kwargs)
        
        # Seuls les admins peuvent attribuer le rôle d'admin
        if not is_admin:
            self.fields['role'].choices = [
                choice for choice in User.ROLE_CHOICES 
                if choice[0] != 'admin'
            ] 


class UserCreationForm(forms.ModelForm):
    """Formulaire pour créer un nouvel utilisateur. Inclut tous les champs requis
    plus un champ de mot de passe répété pour vérification."""
    password1 = forms.CharField(label='Mot de passe', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirmation', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'role')

    def clean_password2(self):
        # Vérifier que les deux mots de passe correspondent
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("Les mots de passe ne correspondent pas")
        return password2

    def save(self, commit=True):
        # Sauvegarder le mot de passe fourni au format hashé
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class AdminUserCreationForm(UserCreationForm):
    """Formulaire utilisé dans le backoffice admin pour créer un utilisateur avec
    gestion automatique du profil associé."""
    
    # Champs pour UserProfile
    phone_number = forms.CharField(max_length=15, required=False, label="Téléphone")
    company_name = forms.CharField(max_length=100, required=False, label="Entreprise")
    notes = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False, label="Notes")
    
    def save(self, commit=True):
        user = super().save(commit=True)  # On sauvegarde toujours l'utilisateur
        
        # Créer ou mettre à jour le profil
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.phone_number = self.cleaned_data.get('phone_number', '')
        profile.company_name = self.cleaned_data.get('company_name', '')
        profile.notes = self.cleaned_data.get('notes', '')
        profile.save()
        
        return user


class UserEditForm(forms.ModelForm):
    """Formulaire pour modifier un utilisateur existant."""
    
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'role', 'is_active')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs['readonly'] = True  # Email est en lecture seule
        

class AdminUserEditForm(UserEditForm):
    """Formulaire pour modifier un utilisateur avec son profil dans le backoffice."""
    
    # Champs pour UserProfile
    phone_number = forms.CharField(max_length=15, required=False, label="Téléphone")
    company_name = forms.CharField(max_length=100, required=False, label="Entreprise")
    notes = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False, label="Notes")
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Préremplir les champs du profil si l'utilisateur existe
        if self.instance and self.instance.pk:
            try:
                profile = self.instance.profile
                self.fields['phone_number'].initial = profile.phone_number
                self.fields['company_name'].initial = profile.company_name
                self.fields['notes'].initial = profile.notes
            except UserProfile.DoesNotExist:
                pass
    
    def save(self, commit=True):
        user = super().save(commit=True)  # On sauvegarde toujours l'utilisateur
        
        # Créer ou mettre à jour le profil
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.phone_number = self.cleaned_data.get('phone_number', '')
        profile.company_name = self.cleaned_data.get('company_name', '')
        profile.notes = self.cleaned_data.get('notes', '')
        profile.save()
        
        return user


class SendTempPasswordForm(forms.Form):
    """Formulaire pour envoyer un mot de passe temporaire à un utilisateur."""
    email = forms.EmailField(label="Email de l'utilisateur")
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if not User.objects.filter(email=email).exists():
            raise ValidationError("Aucun utilisateur avec cette adresse email n'existe.")
        return email


class SetPasswordForm(forms.Form):
    """Formulaire pour définir un nouveau mot de passe."""
    password1 = forms.CharField(
        label="Nouveau mot de passe",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        min_length=8,
    )
    password2 = forms.CharField(
        label="Confirmation du mot de passe",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    
    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise ValidationError("Les mots de passe ne correspondent pas.")
        return password2 