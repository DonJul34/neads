from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
import uuid
import os


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('L\'adresse email est obligatoire')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('admin', 'Administrateur'),
        ('consultant', 'Consultant'),
        ('client', 'Client'),
        ('creator', 'Créateur'),
    )
    
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='client')
    
    # Champs pour connexion temporaire
    temp_login_token = models.CharField(max_length=100, blank=True, null=True)
    temp_login_expiry = models.DateTimeField(blank=True, null=True)
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    def has_role(self, role_name):
        return self.role == role_name
    
    def generate_temp_login_token(self):
        token = uuid.uuid4().hex
        self.temp_login_token = token
        self.temp_login_expiry = timezone.now() + timezone.timedelta(hours=24)
        self.save()
        return token
        
    def is_temp_token_valid(self, token):
        return (
            self.temp_login_token == token and
            self.temp_login_expiry and 
            self.temp_login_expiry > timezone.now()
        )


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    company_name = models.CharField(max_length=100, blank=True, null=True)
    
    # Timestamps et métadonnées
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    verified_email = models.BooleanField(default=False)
    verified_phone = models.BooleanField(default=False)
    
    # Pour les consultants/clients
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Profil de {self.user.email}"
