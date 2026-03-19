from rest_framework import serializers
from django.utils import timezone
from datetime import datetime
from .models import (
    Patient, AdressePatient, PersonneAContacter,
    AssurancePatient, AllergiePatient, AntecedentMedical,
    SuiviPatient
)
from gestion_tenants.serializers import TenantSerializer

class AdressePatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdressePatient
        fields = '__all__'
        read_only_fields = ('adresse_id', 'cree_le', 'modifie_le')
    
    def validate_code_postal(self, value):
        """Validation du code postal français"""
        if value and not value.isdigit():
            raise serializers.ValidationError("Le code postal doit contenir uniquement des chiffres")
        return value

class PersonneAContacterSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonneAContacter
        fields = '__all__'
        read_only_fields = ('contact_id', 'cree_le')

class AssurancePatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssurancePatient
        fields = '__all__'
        read_only_fields = ('assurance_id', 'cree_le')
    
    def validate_date_expiration(self, value):
        if value and value < timezone.now().date():
            raise serializers.ValidationError("La date d'expiration ne peut pas être dans le passé")
        return value

class AllergiePatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = AllergiePatient
        fields = '__all__'
        read_only_fields = ('allergie_id', 'cree_le')

class AntecedentMedicalSerializer(serializers.ModelSerializer):
    class Meta:
        model = AntecedentMedical
        fields = '__all__'
        read_only_fields = ('antecedent_id', 'cree_le')
    
    def validate(self, data):
        """Validation des dates d'antécédent"""
        date_debut = data.get('date_debut')
        date_fin = data.get('date_fin')
        
        if date_debut and date_fin and date_fin < date_debut:
            raise serializers.ValidationError({
                'date_fin': 'La date de fin ne peut pas être antérieure à la date de début'
            })
        
        if date_fin and date_fin > timezone.now().date():
            raise serializers.ValidationError({
                'date_fin': 'La date de fin ne peut pas être dans le futur'
            })
        
        return data

class SuiviPatientSerializer(serializers.ModelSerializer):
    imc = serializers.SerializerMethodField()
    interpretation_imc = serializers.SerializerMethodField()
    
    class Meta:
        model = SuiviPatient
        fields = '__all__'
        read_only_fields = ('suivi_id', 'created_at', 'updated_at')
    
    def get_imc(self, obj):
        return obj.imc
    
    def get_interpretation_imc(self, obj):
        return obj.interpretation_imc
    
    def validate(self, data):
        """Validation des données de suivi"""
        # Validation tension artérielle
        systolique = data.get('tension_arterielle_systolique')
        diastolique = data.get('tension_arterielle_diastolique')
        
        if systolique and diastolique and systolique <= diastolique:
            raise serializers.ValidationError({
                'tension_arterielle_systolique': 'La pression systolique doit être supérieure à la diastolique'
            })
        
        # Validation date de suivi
        date_suivi = data.get('date_suivi')
        if date_suivi and date_suivi > timezone.now().date():
            raise serializers.ValidationError({
                'date_suivi': 'La date de suivi ne peut pas être dans le futur'
            })
        
        return data

class PatientSerializer(serializers.ModelSerializer):
    hopital_detail = TenantSerializer(source='hopital', read_only=True)
    adresses = AdressePatientSerializer(many=True, read_only=True)
    contacts = PersonneAContacterSerializer(many=True, read_only=True)
    assurances = AssurancePatientSerializer(many=True, read_only=True)
    allergies = AllergiePatientSerializer(many=True, read_only=True)
    antecedents = AntecedentMedicalSerializer(many=True, read_only=True)
    suivis = SuiviPatientSerializer(many=True, read_only=True)
    age = serializers.SerializerMethodField()
    
    class Meta:
        model = Patient
        fields = [
            'patient_id', 'hopital', 'hopital_detail', 'nom', 'prenom',
            'date_naissance', 'sexe', 'numero_dossier_medical',
            'numero_identification_nationale', 'telephone', 'email',
            'cree_le', 'modifie_le', 'utilisateur', 'adresses', 'contacts',
            'assurances', 'allergies', 'antecedents', 'suivis', 'age'
        ]
        read_only_fields = ('patient_id', 'cree_le', 'modifie_le')
    
    def get_age(self, obj):
        if obj.date_naissance:
            today = timezone.now().date()
            birth_date = obj.date_naissance
            age = today.year - birth_date.year
            
            # Ajuster si l'anniversaire n'est pas encore passé cette année
            if (today.month, today.day) < (birth_date.month, birth_date.day):
                age -= 1
            
            return age
        return None
    
    def validate_numero_dossier_medical(self, value):
        """Vérifier l'unicité du numéro de dossier"""
        if Patient.objects.filter(numero_dossier_medical=value).exists():
            raise serializers.ValidationError("Ce numéro de dossier médical existe déjà")
        return value
    
    def validate_numero_identification_nationale(self, value):
        if value and Patient.objects.filter(numero_identification_nationale=value).exists():
            raise serializers.ValidationError("Ce numéro d'identification nationale existe déjà")
        return value
    
    def validate_date_naissance(self, value):
        if value and value > timezone.now().date():
            raise serializers.ValidationError("La date de naissance ne peut pas être dans le futur")
        return value

class PatientListSerializer(serializers.ModelSerializer):
    age = serializers.SerializerMethodField()
    
    class Meta:
        model = Patient
        fields = [
            'patient_id', 'nom', 'prenom', 'date_naissance', 'sexe',
            'numero_dossier_medical', 'telephone', 'email', 'age'
        ]
    
    def get_age(self, obj):
        if obj.date_naissance:
            today = timezone.now().date()
            return today.year - obj.date_naissance.year - (
                (today.month, today.day) < (obj.date_naissance.month, obj.date_naissance.day)
            )
        return None