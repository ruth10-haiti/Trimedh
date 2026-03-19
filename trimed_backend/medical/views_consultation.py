from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Count, Q
from .models import Consultation, Medecin
from patients.models import Patient
from .serializers import ConsultationSerializer
from comptes.permissions import EstMedecin, EstPersonnel

class ConsultationViewSet(viewsets.ModelViewSet):
    """ViewSet pour les consultations"""
    queryset = Consultation.objects.all()
    serializer_class = ConsultationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['tenant', 'patient', 'medecin', 'rendez_vous']
    search_fields = ['motif', 'diagnostic_principal', 'patient__nom', 'medecin__nom']
    ordering_fields = ['date_consultation', 'created_at']
    ordering = ['-date_consultation']
    
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
        
        # Les médecins voient leurs consultations
        if user.role == 'medecin' and hasattr(user, 'medecin_lie'):
            queryset = queryset.filter(medecin=user.medecin_lie)
        
        return queryset
    
    def perform_create(self, serializer):
        """Créer une consultation"""
        serializer.save(tenant=self.request.user.hopital)
    
    @action(detail=False, methods=['get'])
    def mes_consultations(self, request):
        """Consultations du médecin connecté"""
        if request.user.role != 'medecin' or not hasattr(request.user, 'medecin_lie'):
            return Response(
                {'error': 'Vous devez être médecin'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        consultations = self.get_queryset().filter(medecin=request.user.medecin_lie)
        serializer = self.get_serializer(consultations, many=True)
        
        return Response({
            'total': consultations.count(),
            'consultations': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def aujourd_hui(self, request):
        """Consultations du jour"""
        today = timezone.now().date()
        consultations = self.get_queryset().filter(date_consultation__date=today)
        serializer = self.get_serializer(consultations, many=True)
        
        return Response({
            'date': today,
            'total': consultations.count(),
            'consultations': serializer.data
        })
    
    @action(detail=True, methods=['get'])
    def historique_patient(self, request, pk=None):
        """Historique des consultations d'un patient"""
        consultation = self.get_object()
        historique = Consultation.objects.filter(
            tenant=consultation.tenant,
            patient=consultation.patient
        ).order_by('-date_consultation')
        
        serializer = self.get_serializer(historique, many=True)
        
        return Response({
            'patient': consultation.patient.nom,
            'total_consultations': historique.count(),
            'consultations': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def statistiques(self, request):
        """Statistiques des consultations"""
        queryset = self.get_queryset()
        
        # Consultations du jour
        today = timezone.now().date()
        consultations_jour = queryset.filter(date_consultation__date=today).count()
        
        # Consultations du mois
        debut_mois = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        consultations_mois = queryset.filter(date_consultation__gte=debut_mois).count()
        
        # Par médecin
        par_medecin = queryset.values('medecin__nom', 'medecin__prenom').annotate(
            total=Count('consultation_id')
        ).order_by('-total')[:5]
        
        # Motifs fréquents
        motifs = queryset.values('motif').annotate(
            total=Count('consultation_id')
        ).order_by('-total')[:10]
        
        return Response({
            'consultations_jour': consultations_jour,
            'consultations_mois': consultations_mois,
            'top_medecins': list(par_medecin),
            'motifs_frequents': list(motifs),
            'total': queryset.count()
        })