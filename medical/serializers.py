from rest_framework import serializers
from django.utils import timezone
from .models import (
    Medecin, Specialite, GroupeSanguin, Consultation, 
    Ordonnance, ExamenMedical, Prescription, LignePrescription
)

class SpecialiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialite
        fields = '__all__'
        read_only_fields = ['specialite_id']

class GroupeSanguinSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupeSanguin
        fields = '__all__'
        read_only_fields = ['groupe_id']

class MedecinListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour la liste des médecins"""
    specialite_nom = serializers.CharField(source='specialite_principale.nom_specialite', read_only=True)
    
    class Meta:
        model = Medecin
        fields = [
            'medecin_id', 'nom', 'prenom', 'sexe', 'specialite_nom',
            'telephone', 'email_professionnel'
        ]

class MedecinSerializer(serializers.ModelSerializer):
    """Serializer complet pour les médecins"""
    specialite_detail = SpecialiteSerializer(source='specialite_principale', read_only=True)
    utilisateur_detail = serializers.SerializerMethodField()
    
    def get_utilisateur_detail(self, obj):
        if obj.utilisateur:
            return {
                'utilisateur_id': obj.utilisateur.utilisateur_id,
                'nom_complet': obj.utilisateur.nom_complet,
                'email': obj.utilisateur.email,
                'role': obj.utilisateur.role
            }
        return None
    
    class Meta:
        model = Medecin
        fields = '__all__'
        read_only_fields = ['medecin_id', 'cree_le', 'modifie_le']

class ConsultationListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour la liste des consultations"""
    patient_nom = serializers.CharField(source='patient.nom', read_only=True)
    patient_prenom = serializers.CharField(source='patient.prenom', read_only=True)
    medecin_nom = serializers.CharField(source='medecin.nom', read_only=True)
    medecin_prenom = serializers.CharField(source='medecin.prenom', read_only=True)
    
    class Meta:
        model = Consultation
        fields = [
            'consultation_id', 'date_consultation', 'motif', 'diagnostic_principal',
            'patient_nom', 'patient_prenom', 'medecin_nom', 'medecin_prenom'
        ]

class ConsultationSerializer(serializers.ModelSerializer):
    """Serializer complet pour les consultations"""
    patient_detail = serializers.SerializerMethodField()
    medecin_detail = serializers.SerializerMethodField()
    rendez_vous_detail = serializers.SerializerMethodField()
    ordonnances = serializers.SerializerMethodField()
    examens = serializers.SerializerMethodField()
    
    def get_patient_detail(self, obj):
        if obj.patient:
            return {
                'patient_id': obj.patient.patient_id,
                'nom': obj.patient.nom,
                'prenom': obj.patient.prenom,
                'date_naissance': obj.patient.date_naissance,
                'sexe': obj.patient.sexe
            }
        return None
    
    def get_medecin_detail(self, obj):
        if obj.medecin:
            return {
                'medecin_id': obj.medecin.medecin_id,
                'nom': obj.medecin.nom,
                'prenom': obj.medecin.prenom,
                'specialite': obj.medecin.specialite_principale.nom_specialite if obj.medecin.specialite_principale else None
            }
        return None
    
    def get_rendez_vous_detail(self, obj):
        if obj.rendez_vous:
            return {
                'rendez_vous_id': obj.rendez_vous.rendez_vous_id,
                'date_heure': obj.rendez_vous.date_heure,
                'motif': obj.rendez_vous.motif
            }
        return None
    
    def get_ordonnances(self, obj):
        ordonnances = obj.ordonnance_set.all()
        return OrdonnanceListSerializer(ordonnances, many=True).data
    
    def get_examens(self, obj):
        examens = obj.examenmedical_set.all()
        return ExamenMedicalListSerializer(examens, many=True).data
    
    class Meta:
        model = Consultation
        fields = '__all__'
        read_only_fields = ['consultation_id', 'created_at', 'updated_at']

class LignePrescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LignePrescription
        fields = '__all__'
        read_only_fields = ['ligne_id']

class PrescriptionSerializer(serializers.ModelSerializer):
    """Serializer pour les prescriptions"""
    medicament_detail = serializers.SerializerMethodField()
    lignes = LignePrescriptionSerializer(source='ligneprescription_set', many=True, read_only=True)
    
    def get_medicament_detail(self, obj):
        if obj.medicament:
            return {
                'medicament_id': obj.medicament.medicament_id,
                'nom': obj.medicament.nom,
                'forme_pharmaceutique': obj.medicament.forme_pharmaceutique,
                'dosage_standard': obj.medicament.dosage_standard
            }
        return None
    
    class Meta:
        model = Prescription
        fields = '__all__'
        read_only_fields = ['prescription_id', 'created_at', 'updated_at']

class OrdonnanceListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour la liste des ordonnances"""
    medecin_nom = serializers.CharField(source='medecin.nom', read_only=True)
    medecin_prenom = serializers.CharField(source='medecin.prenom', read_only=True)
    nb_prescriptions = serializers.SerializerMethodField()
    
    def get_nb_prescriptions(self, obj):
        return obj.prescription_set.count()
    
    class Meta:
        model = Ordonnance
        fields = [
            'ordonnance_id', 'date_ordonnance', 'recommandations',
            'medecin_nom', 'medecin_prenom', 'nb_prescriptions'
        ]

class OrdonnanceSerializer(serializers.ModelSerializer):
    """Serializer complet pour les ordonnances"""
    consultation_detail = serializers.SerializerMethodField()
    patient_detail = serializers.SerializerMethodField()
    medecin_detail = serializers.SerializerMethodField()
    prescriptions = PrescriptionSerializer(source='prescription_set', many=True, read_only=True)
    
    def get_consultation_detail(self, obj):
        if obj.consultation:
            return {
                'consultation_id': obj.consultation.consultation_id,
                'date_consultation': obj.consultation.date_consultation,
                'motif': obj.consultation.motif
            }
        return None
    
    def get_patient_detail(self, obj):
        if obj.patient:
            return {
                'patient_id': obj.patient.patient_id,
                'nom': obj.patient.nom,
                'prenom': obj.patient.prenom
            }
        return None
    
    def get_medecin_detail(self, obj):
        if obj.medecin:
            return {
                'medecin_id': obj.medecin.medecin_id,
                'nom': obj.medecin.nom,
                'prenom': obj.medecin.prenom
            }
        return None
    
    class Meta:
        model = Ordonnance
        fields = '__all__'
        read_only_fields = ['ordonnance_id', 'created_at', 'updated_at']

class ExamenMedicalListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour la liste des examens"""
    patient_nom = serializers.CharField(source='patient.nom', read_only=True)
    patient_prenom = serializers.CharField(source='patient.prenom', read_only=True)
    medecin_nom = serializers.CharField(source='medecin_prescripteur.nom', read_only=True)
    
    class Meta:
        model = ExamenMedical
        fields = [
            'examen_id', 'nom_examen', 'type_examen', 'date_examen', 'date_resultat',
            'patient_nom', 'patient_prenom', 'medecin_nom'
        ]

class ExamenMedicalSerializer(serializers.ModelSerializer):
    """Serializer complet pour les examens médicaux"""
    patient_detail = serializers.SerializerMethodField()
    consultation_detail = serializers.SerializerMethodField()
    medecin_detail = serializers.SerializerMethodField()
    
    def get_patient_detail(self, obj):
        if obj.patient:
            return {
                'patient_id': obj.patient.patient_id,
                'nom': obj.patient.nom,
                'prenom': obj.patient.prenom
            }
        return None
    
    def get_consultation_detail(self, obj):
        if obj.consultation:
            return {
                'consultation_id': obj.consultation.consultation_id,
                'date_consultation': obj.consultation.date_consultation,
                'motif': obj.consultation.motif
            }
        return None
    
    def get_medecin_detail(self, obj):
        if obj.medecin_prescripteur:
            return {
                'medecin_id': obj.medecin_prescripteur.medecin_id,
                'nom': obj.medecin_prescripteur.nom,
                'prenom': obj.medecin_prescripteur.prenom
            }
        return None
    
    class Meta:
        model = ExamenMedical
        fields = '__all__'
        read_only_fields = ['examen_id', 'created_at', 'updated_at']

class ConsultationCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création de consultations"""
    class Meta:
        model = Consultation
        fields = ['patient', 'medecin', 'rendez_vous', 'date_consultation', 'motif', 'diagnostic_principal', 'notes']
    
    def create(self, validated_data):
        # Ajouter le tenant automatiquement
        validated_data['tenant'] = self.context['request'].user.hopital
        return super().create(validated_data)

class OrdonnanceCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création d'ordonnances"""
    prescriptions = PrescriptionSerializer(many=True, required=False)
    
    class Meta:
        model = Ordonnance
        fields = ['consultation', 'patient', 'medecin', 'date_ordonnance', 'recommandations', 'prescriptions']
    
    def create(self, validated_data):
        prescriptions_data = validated_data.pop('prescriptions', [])
        validated_data['tenant'] = self.context['request'].user.hopital
        
        ordonnance = Ordonnance.objects.create(**validated_data)
        
        # Créer les prescriptions
        for prescription_data in prescriptions_data:
            Prescription.objects.create(ordonnance=ordonnance, **prescription_data)
        
        return ordonnance