from rest_framework import serializers
from django.utils import timezone
from .models import (
    GroupeSanguin, Specialite, Medecin,
    Consultation, Ordonnance, ExamenMedical,
    Prescription, LignePrescription
)
from patients.models import Patient
from patients.serializers import PatientSerializer
from gestion_tenants.serializers import TenantSerializer
from gestion_medicaments.serializers import MedicamentSerializer

class GroupeSanguinSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupeSanguin
        fields = '__all__'
        read_only_fields = ('groupe_id',)

class SpecialiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialite
        fields = '__all__'
        read_only_fields = ('specialite_id',)

class MedecinSerializer(serializers.ModelSerializer):
    specialite_principale = SpecialiteSerializer(read_only=True)
    specialite_principale_id = serializers.PrimaryKeyRelatedField(
        queryset=Specialite.objects.all(),
        source='specialite_principale',
        write_only=True
    )
    hopital_detail = TenantSerializer(source='hopital', read_only=True)
    
    class Meta:
        model = Medecin
        fields = [
            'medecin_id', 'hopital', 'hopital_detail', 'nom', 'prenom',
            'sexe', 'date_naissance', 'telephone', 'email_professionnel',
            'numero_identification', 'numero_matricule_professionnel',
            'specialite_principale', 'specialite_principale_id',
            'cree_le', 'modifie_le', 'utilisateur'
        ]
        read_only_fields = ('medecin_id', 'cree_le', 'modifie_le')
    
    def validate_numero_identification(self, value):
        if value and Medecin.objects.filter(numero_identification=value).exists():
            raise serializers.ValidationError("Ce numéro d'identification existe déjà")
        return value

class ConsultationSerializer(serializers.ModelSerializer):
    patient_detail = PatientSerializer(source='patient', read_only=True)
    patient_id = serializers.PrimaryKeyRelatedField(
        queryset=Patient.objects.all(),
        source='patient',
        write_only=True
    )
    medecin_detail = MedecinSerializer(source='medecin', read_only=True)
    medecin_id = serializers.PrimaryKeyRelatedField(
        queryset=Medecin.objects.all(),
        source='medecin',
        write_only=True
    )
    
    class Meta:
        model = Consultation
        fields = [
            'consultation_id', 'tenant', 'patient', 'patient_detail',
            'patient_id', 'medecin', 'medecin_detail', 'medecin_id',
            'rendez_vous', 'date_consultation', 'motif',
            'diagnostic_principal', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ('consultation_id', 'created_at', 'updated_at')
    
    def validate_date_consultation(self, value):
        if value > timezone.now():
            raise serializers.ValidationError("La date de consultation ne peut pas être dans le futur")
        return value

class OrdonnanceSerializer(serializers.ModelSerializer):
    consultation_detail = ConsultationSerializer(source='consultation', read_only=True)
    consultation_id = serializers.PrimaryKeyRelatedField(
        queryset=Consultation.objects.all(),
        source='consultation',
        write_only=True
    )
    prescriptions = serializers.SerializerMethodField()
    
    def get_prescriptions(self, obj):
        from .serializers import PrescriptionSerializer
        return PrescriptionSerializer(obj.prescriptions.all(), many=True).data
    
    class Meta:
        model = Ordonnance
        fields = [
            'ordonnance_id', 'tenant', 'consultation', 'consultation_detail',
            'consultation_id', 'patient', 'medecin', 'date_ordonnance',
            'recommandations', 'created_at', 'updated_at', 'prescriptions'
        ]
        read_only_fields = ('ordonnance_id', 'created_at', 'updated_at')

class ExamenMedicalSerializer(serializers.ModelSerializer):
    patient_detail = PatientSerializer(source='patient', read_only=True)
    consultation_detail = ConsultationSerializer(source='consultation', read_only=True)
    medecin_prescripteur_detail = MedecinSerializer(source='medecin_prescripteur', read_only=True)
    
    class Meta:
        model = ExamenMedical
        fields = [
            'examen_id', 'tenant', 'patient', 'patient_detail',
            'consultation', 'consultation_detail', 'medecin_prescripteur',
            'medecin_prescripteur_detail', 'nom_examen', 'type_examen',
            'resultat', 'notes', 'fichier_resultat', 'date_examen',
            'date_resultat', 'created_at', 'updated_at'
        ]
        read_only_fields = ('examen_id', 'created_at', 'updated_at')
    
    def validate_date_examen(self, value):
        if value > timezone.now():
            raise serializers.ValidationError("La date d'examen ne peut pas être dans le futur")
        return value

class PrescriptionSerializer(serializers.ModelSerializer):
    medicament_detail = MedicamentSerializer(source='medicament', read_only=True)
    ordonnance_detail = OrdonnanceSerializer(source='ordonnance', read_only=True)
    
    class Meta:
        model = Prescription
        fields = [
            'prescription_id', 'ordonnance', 'ordonnance_detail',
            'medicament', 'medicament_detail', 'dosage', 'frequence',
            'duree', 'quantite', 'instructions', 'created_at', 'updated_at'
        ]
        read_only_fields = ('prescription_id', 'created_at', 'updated_at')