# serializers.py
from rest_framework import serializers
from django.utils import timezone
from datetime import datetime, timedelta, time
from .models import RendezVousType, RendezVousStatut, RendezVous
from patients.models import Patient
from medical.models import Medecin
from patients.serializers import PatientSerializer
from medical.serializers import MedecinSerializer

class RendezVousTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RendezVousType
        fields = '__all__'
        read_only_fields = ('type_id', 'created_at', 'updated_at')
    
    def validate_nom(self, value):
        """Vérifier l'unicité du nom dans le tenant"""
        tenant = self.context['request'].user.hopital
        if RendezVousType.objects.filter(tenant=tenant, nom=value).exists():
            raise serializers.ValidationError("Ce type de rendez-vous existe déjà")
        return value

class RendezVousStatutSerializer(serializers.ModelSerializer):
    class Meta:
        model = RendezVousStatut
        fields = '__all__'
        read_only_fields = ('statut_id', 'created_at', 'updated_at')

class RendezVousSerializer(serializers.ModelSerializer):
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
    type_detail = RendezVousTypeSerializer(source='type', read_only=True)
    statut_detail = RendezVousStatutSerializer(source='statut', read_only=True)
    
    duree = serializers.ReadOnlyField()
    date_fin = serializers.ReadOnlyField()
    est_dans_futur = serializers.ReadOnlyField()
    est_dans_passe = serializers.ReadOnlyField()
    est_aujourdhui = serializers.ReadOnlyField()
    
    class Meta:
        model = RendezVous
        fields = [
            'rendez_vous_id', 'tenant', 'patient', 'patient_detail', 'patient_id',
            'medecin', 'medecin_detail', 'medecin_id', 'date_heure', 'type',
            'type_detail', 'statut', 'statut_detail', 'motif', 'notes',
            'raison_annulation', 'rappel_envoye', 'date_rappel',
            'duree', 'date_fin', 'est_dans_futur', 'est_dans_passe',
            'est_aujourdhui', 'created_at', 'updated_at'
        ]
        read_only_fields = (
            'rendez_vous_id', 'created_at', 'updated_at',
            'rappel_envoye', 'date_rappel'
        )
    
    def validate_date_heure(self, value):
        """Validation de la date du rendez-vous"""
        if value < timezone.now():
            raise serializers.ValidationError("La date du rendez-vous ne peut pas être dans le passé")
        
        # Vérifier que c'est pendant les heures ouvrables (8h-18h)
        heure = value.time()
        if heure < time(8, 0) or heure > time(18, 0):
            raise serializers.ValidationError("Les rendez-vous sont disponibles de 8h à 18h")
        
        # Vérifier que ce n'est pas un week-end
        if value.weekday() >= 5:  # 5 = samedi, 6 = dimanche
            raise serializers.ValidationError("Les rendez-vous ne sont pas disponibles le week-end")
        
        return value
    
    def validate(self, data):
        """Validation globale du rendez-vous"""
        date_heure = data.get('date_heure')
        medecin = data.get('medecin')
        tenant = data.get('tenant', self.context['request'].user.hopital)
        
        if date_heure and medecin and tenant:
            # Vérifier la disponibilité du médecin
            rdv = RendezVous(
                tenant=tenant,
                medecin=medecin,
                date_heure=date_heure,
                type=data.get('type')
            )
            
            if not rdv.verifier_disponibilite():
                raise serializers.ValidationError({
                    'date_heure': 'Ce créneau n\'est pas disponible pour ce médecin'
                })
        
        return data

class CreneauDisponibleSerializer(serializers.Serializer):
    """Serializer pour les créneaux disponibles"""
    
    date = serializers.DateField()
    heure = serializers.TimeField()
    medecin_id = serializers.IntegerField()
    
    def validate(self, data):
        """Validation du créneau"""
        date_heure = datetime.combine(data['date'], data['heure'])
        
        # Vérifier que c'est dans le futur
        if date_heure < timezone.now():
            raise serializers.ValidationError("Le créneau ne peut pas être dans le passé")
        
        # Vérifier que c'est pendant les heures ouvrables
        heure = data['heure']
        if heure < time(8, 0) or heure > time(17, 30):  # Dernier créneau à 17h30
            raise serializers.ValidationError("Créneau en dehors des heures ouvrables")
        
        # Vérifier que ce n'est pas un week-end
        if data['date'].weekday() >= 5:
            raise serializers.ValidationError("Créneau le week-end non disponible")
        
        return data

class ChangementStatutSerializer(serializers.Serializer):
    """Serializer pour changer le statut d'un rendez-vous"""
    
    nouveau_statut_id = serializers.IntegerField(required=True)
    raison = serializers.CharField(required=False, allow_blank=True)
    
    def validate_nouveau_statut_id(self, value):
        try:
            statut = RendezVousStatut.objects.get(pk=value)
        except RendezVousStatut.DoesNotExist:
            raise serializers.ValidationError("Statut invalide")
        
        return value