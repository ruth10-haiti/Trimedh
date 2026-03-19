# views.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from datetime import timedelta, datetime
from .models import (
    Specialite, Medecin, Consultation, Ordonnance,
    ExamenMedical, Prescription
)
from .serializers import (
    SpecialiteSerializer, MedecinSerializer,
    ConsultationSerializer, OrdonnanceSerializer,
    ExamenMedicalSerializer, PrescriptionSerializer
)
from comptes.permissions import EstMedecin, EstPersonnel, EstPatient
from patients.permissions import PeutAccederPatient

class MedecinViewSet(viewsets.ModelViewSet):
    """ViewSet pour les médecins"""
    queryset = Medecin.objects.all()
    serializer_class = MedecinSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['hopital', 'specialite_principale', 'sexe']
    search_fields = ['nom', 'prenom', 'email_professionnel']
    ordering_fields = ['nom', 'prenom', 'cree_le']
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Filtrer par tenant
        if user.hopital:
            queryset = queryset.filter(hopital=user.hopital)
        
        # Filtrer par spécialité
        specialite_id = self.request.query_params.get('specialite_id')
        if specialite_id:
            queryset = queryset.filter(specialite_principale_id=specialite_id)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def disponibilites(self, request):
        """Obtenir les disponibilités des médecins"""
        medecin_id = request.query_params.get('medecin_id')
        date = request.query_params.get('date')
        
        if not medecin_id or not date:
            return Response(
                {'error': 'medecin_id et date sont requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            medecin = Medecin.objects.get(pk=medecin_id)
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
            
            # Récupérer les rendez-vous du jour
            from rendez_vous.models import RendezVous
            rendez_vous = RendezVous.objects.filter(
                medecin=medecin,
                date_heure__date=date_obj
            ).order_by('date_heure')
            
            # Générer les créneaux disponibles
            creneaux_disponibles = []
            heure_debut = datetime.combine(date_obj, datetime.min.time().replace(hour=8))
            heure_fin = datetime.combine(date_obj, datetime.min.time().replace(hour=18))
            
            current = heure_debut
            while current < heure_fin:
                # Vérifier si le créneau est pris
                est_occupe = rendez_vous.filter(
                    date_heure__range=(current, current + timedelta(minutes=30))
                ).exists()
                
                if not est_occupe:
                    creneaux_disponibles.append(current.strftime('%H:%M'))
                
                current += timedelta(minutes=30)
            
            return Response({
                'medecin': MedecinSerializer(medecin).data,
                'date': date,
                'creneaux_disponibles': creneaux_disponibles
            })
        
        except Medecin.DoesNotExist:
            return Response(
                {'error': 'Médecin non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )

class ConsultationViewSet(viewsets.ModelViewSet):
    """ViewSet pour les consultations"""
    queryset = Consultation.objects.all()
    serializer_class = ConsultationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = ['date_consultation', 'created_at']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Filtrer par tenant
        if user.hopital:
            queryset = queryset.filter(tenant=user.hopital)
        
        # Filtrer par date
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        if date_from:
            queryset = queryset.filter(date_consultation__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date_consultation__date__lte=date_to)
        
        # Filtrer par patient
        patient_id = self.request.query_params.get('patient_id')
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        
        # Filtrer par médecin
        medecin_id = self.request.query_params.get('medecin_id')
        if medecin_id:
            queryset = queryset.filter(medecin_id=medecin_id)
        
        # Les patients ne voient que leurs consultations
        if user.role == 'patient' and hasattr(user, 'patient_lie'):
            queryset = queryset.filter(patient=user.patient_lie)
        
        # Les médecins ne voient que leurs consultations
        elif user.role == 'medecin' and hasattr(user, 'medecin_lie'):
            queryset = queryset.filter(medecin=user.medecin_lie)
        
        return queryset
    
    def perform_create(self, serializer):
        """Surcharge pour ajouter automatiquement le tenant"""
        serializer.save(tenant=self.request.user.hopital)
    
    @action(detail=True, methods=['post'])
    def creer_ordonnance(self, request, pk=None):
        """Créer une ordonnance pour cette consultation"""
        consultation = self.get_object()
        
        # Vérifier que l'utilisateur est le médecin de la consultation
        if (request.user.role == 'medecin' and 
            hasattr(request.user, 'medecin_lie') and 
            request.user.medecin_lie != consultation.medecin):
            return Response(
                {'error': 'Seul le médecin de la consultation peut créer une ordonnance'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        ordonnance_data = request.data.copy()
        ordonnance_data['consultation'] = consultation.pk
        ordonnance_data['patient'] = consultation.patient.pk
        ordonnance_data['medecin'] = consultation.medecin.pk
        ordonnance_data['tenant'] = consultation.tenant.pk
        
        serializer = OrdonnanceSerializer(data=ordonnance_data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def ajouter_examen(self, request, pk=None):
        """Ajouter un examen médical pour cette consultation"""
        consultation = self.get_object()
        
        examen_data = request.data.copy()
        examen_data['consultation'] = consultation.pk
        examen_data['patient'] = consultation.patient.pk
        examen_data['tenant'] = consultation.tenant.pk
        
        # Si le médecin prescripteur n'est pas spécifié, utiliser le médecin de la consultation
        if not examen_data.get('medecin_prescripteur'):
            examen_data['medecin_prescripteur'] = consultation.medecin.pk
        
        serializer = ExamenMedicalSerializer(data=examen_data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)