# serializers.py
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils import timezone
from .models import Utilisateur

from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils import timezone
from .models import Utilisateur
from gestion_tenants.models import Tenant  # Ajouter cet import

class UtilisateurSerializer(serializers.ModelSerializer):
    hopital_detail = serializers.SerializerMethodField()
    
    def get_hopital_detail(self, obj):
        if obj.hopital:
            from gestion_tenants.serializers import TenantSerializer
            return TenantSerializer(obj.hopital).data
        return None
    
    class Meta:
        model = Utilisateur
        fields = [
            'utilisateur_id', 'nom_complet', 'email', 'role',
            'hopital', 'hopital_detail', 'cree_le', 'derniere_connexion',
            'is_active', 'is_staff', 'last_login'
        ]
        read_only_fields = [
            'utilisateur_id', 'cree_le', 'derniere_connexion',
            'last_login', 'is_staff'
        ]
        extra_kwargs = {
            'email': {'required': True},
            'nom_complet': {'required': True},
            'role': {'required': True}
        }
    
    def validate_email(self, value):
        """Validation de l'email"""
        if Utilisateur.objects.filter(email=value).exists():
            raise serializers.ValidationError("Cet email est déjà utilisé")
        return value
    
    def validate_role(self, value):
        """Validation du rôle"""
        roles_autorises = [choice[0] for choice in Utilisateur.Role.choices]
        if value not in roles_autorises:
            raise serializers.ValidationError(f"Rôle invalide. Choix: {roles_autorises}")
        return value

class InscriptionSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, required=True)
    # MODIFICATION: On attend un ID d'hôpital (IntegerField) au lieu d'un dictionnaire
    hopital = serializers.IntegerField(required=True)  # Rendre obligatoire pour l'app mobile
    
    class Meta:
        model = Utilisateur
        fields = ['nom_complet', 'email', 'password', 'confirm_password', 'role', 'hopital']
    
    def validate(self, data):
        # Vérifier que les mots de passe correspondent
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({
                'password': 'Les mots de passe ne correspondent pas'
            })
        
        # MODIFICATION: Vérifier que l'hôpital existe et est actif
        hopital_id = data.get('hopital')
        if hopital_id:
            try:
                tenant = Tenant.objects.get(tenant_id=hopital_id)
                # Optionnel: Vérifier que l'hôpital est actif
                if tenant.statut != 'actif':
                    raise serializers.ValidationError({
                        'hopital': "Cet hôpital n'est pas actif. Veuillez contacter l'administrateur."
                    })
            except Tenant.DoesNotExist:
                raise serializers.ValidationError({
                    'hopital': "L'hôpital sélectionné n'existe pas"
                })
        
        return data
    
    def create(self, validated_data):
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        
        # Récupérer l'ID de l'hôpital
        hopital_id = validated_data.pop('hopital')
        
        # Récupérer l'instance de l'hôpital
        try:
            tenant = Tenant.objects.get(tenant_id=hopital_id)
        except Tenant.DoesNotExist:
            raise serializers.ValidationError({
                'hopital': "L'hôpital sélectionné n'existe pas"
            })
        
        # MODIFICATION: Utiliser create_user (qui existe déjà via votre manager)
        utilisateur = Utilisateur.objects.create_user(
            email=validated_data['email'],
            nom_complet=validated_data['nom_complet'],
            mot_de_passe=password,
            role=validated_data.get('role', 'patient'),
            hopital=tenant
        )
        
        return utilisateur

# Le reste des serializers reste identique (LoginSerializer, ChangePasswordSerializer, UpdateProfileSerializer)
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        
        if email and password:
            utilisateur = authenticate(email=email, password=password)
            
            if not utilisateur:
                raise serializers.ValidationError("Email ou mot de passe incorrect")
            
            if not utilisateur.is_active:
                raise serializers.ValidationError("Ce compte est désactivé")
            
            # Mettre à jour la dernière connexion
            utilisateur.derniere_connexion = timezone.now()
            utilisateur.save(update_fields=['derniere_connexion'])
            
            data['utilisateur'] = utilisateur
        else:
            raise serializers.ValidationError("Email et mot de passe requis")
        
        return data

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    confirm_password = serializers.CharField(required=True)
    
    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': 'Les nouveaux mots de passe ne correspondent pas'
            })
        return data

class UpdateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Utilisateur
        fields = ['nom_complet', 'email', 'role', 'hopital']
        read_only_fields = ['email', 'role']
    
    def validate_nom_complet(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Le nom complet doit contenir au moins 3 caractères")
        return value

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        
        if email and password:
            utilisateur = authenticate(email=email, password=password)
            
            if not utilisateur:
                raise serializers.ValidationError("Email ou mot de passe incorrect")
            
            if not utilisateur.is_active:
                raise serializers.ValidationError("Ce compte est désactivé")
            
            # Mettre à jour la dernière connexion
            utilisateur.derniere_connexion = timezone.now()
            utilisateur.save(update_fields=['derniere_connexion'])
            
            data['utilisateur'] = utilisateur
        else:
            raise serializers.ValidationError("Email et mot de passe requis")
        
        return data

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    confirm_password = serializers.CharField(required=True)
    
    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': 'Les nouveaux mots de passe ne correspondent pas'
            })
        return data

class UpdateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Utilisateur
        fields = ['nom_complet', 'email', 'role', 'hopital']
        read_only_fields = ['email', 'role']  # Email et rôle ne peuvent pas être modifiés
    
    def validate_nom_complet(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Le nom complet doit contenir au moins 3 caractères")
        return value