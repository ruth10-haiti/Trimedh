# models.py
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.core.validators import EmailValidator

class GestionnaireUtilisateur(BaseUserManager):
    
    def create_user(self, email, nom_complet, mot_de_passe=None, **extra_fields):
        if not email:
            raise ValueError('L\'email est obligatoire')
        
        email = self.normalize_email(email)
        utilisateur = self.model(
            email=email,
            nom_complet=nom_complet,
            **extra_fields
        )
        utilisateur.set_password(mot_de_passe)
        utilisateur.save(using=self._db)
        return utilisateur
    
    def create_superuser(self, email, nom_complet, mot_de_passe=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin-systeme')
        
        return self.create_user(email, nom_complet, mot_de_passe, **extra_fields)

class Utilisateur(AbstractBaseUser, PermissionsMixin):
    
    
    class Role(models.TextChoices):
        ADMIN_SYSTEME = 'admin-systeme', 'Administrateur Système'
        PROPRIETAIRE_HOPITAL = 'proprietaire-hopital', 'Propriétaire Hôpital'
        MEDECIN = 'medecin', 'Médecin'
        INFIRMIER = 'infirmier', 'Infirmier'
        SECRETAIRE = 'secretaire', 'Secrétaire'
        PERSONNEL = 'personnel', 'Personnel'
        PATIENT = 'patient', 'Patient'
    
    utilisateur_id = models.AutoField(primary_key=True)
    nom_complet = models.CharField(max_length=255)
    email = models.EmailField(
        max_length=100,
        unique=True,
        validators=[EmailValidator()]
    )

    role = models.CharField(
        max_length=50,
        choices=Role.choices,
        default=Role.PATIENT
    )
    
    hopital = models.ForeignKey(
        'gestion_tenants.Tenant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='hopital_id',
        related_name='utilisateurs'
    )
    
    cree_le = models.DateTimeField(default=timezone.now)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    derniere_connexion = models.DateTimeField(null=True, blank=True)
    
    derniere_modification = models.DateTimeField(auto_now=True)
    modifie_par = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='utilisateurs_modifies'
    )
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nom_complet']
    
    objects = GestionnaireUtilisateur()
    
    def __str__(self):
        return f"{self.nom_complet} ({self.get_role_display()})"
    
    def save(self, *args, **kwargs):
        if not self.pk:
            self.cree_le = timezone.now()
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'utilisateur'
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['hopital']),
        ]