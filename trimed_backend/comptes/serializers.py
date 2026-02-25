# serializers.py
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils import timezone
from .models import Utilisateur

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
    # Accepter un dictionnaire de données d'hôpital au lieu d'un ID
    hopital = serializers.DictField(required=False, allow_null=True)
    class Meta:
        model = Utilisateur
        fields = ['nom_complet', 'email', 'password', 'confirm_password', 'role', 'hopital']
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({
                'password': 'Les mots de passe ne correspondent pas'
            })
        return data
    def create(self, validated_data):
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        hopital_data = validated_data.pop('hopital', None)
        # Créer le Tenant (hôpital) si des données sont fournies
        tenant = None
        if hopital_data:
            from gestion_tenants.models import Tenant
            try:
                nombre_de_lits = int(hopital_data.get('nombre_de_lits', 1))
            except (ValueError, TypeError):
                nombre_de_lits = 1
            tenant = Tenant.objects.create(
                nom=hopital_data.get('nom', ''),
                adresse=hopital_data.get('adresse', ''),
                telephone=hopital_data.get('telephone', ''),
                email_professionnel=hopital_data.get('email_professionnel', ''),
                directeur=hopital_data.get('directeur', ''),
                nombre_de_lits=nombre_de_lits,
                numero_enregistrement=hopital_data.get('numero_enregistrement', ''),
                statut='inactif',
                statut_verification_document='en_attente',
            )
        # Créer l'utilisateur lié au tenant (ou sans tenant si non fourni)
        utilisateur = Utilisateur.objects.creer_utilisateur(
            email=validated_data['email'],
            nom_complet=validated_data['nom_complet'],
            mot_de_passe=password,
            role=validated_data.get('role', 'proprietaire-hopital'),
            hopital=tenant
        )
        # Lier l'utilisateur comme propriétaire du tenant
        if tenant:
            tenant.proprietaire_utilisateur = utilisateur
            tenant.cree_par_utilisateur = utilisateur
            tenant.save(update_fields=['proprietaire_utilisateur', 'cree_par_utilisateur'])
        return utilisateur

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