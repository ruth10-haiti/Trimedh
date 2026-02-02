from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import datetime, timedelta
from .models import (
    Medecin, Specialite, GroupeSanguin, Consultation,
    Ordonnance, ExamenMedical, Prescription
)
from .serializers import (
    MedecinSerializer, MedecinListSerializer, SpecialiteSerializer,
    GroupeSanguinSerializer, ConsultationSerializer, ConsultationListSerializer,
    ConsultationCreateSerializer, OrdonnanceSerializer, OrdonnanceListSerializer,
    OrdonnanceCreateSerializer, ExamenMedicalSerializer, ExamenMedicalListSerializer,
    PrescriptionSerializer
)
from comptes.permissions import EstMedecin, EstPersonnel, EstPatient

class SpecialiteViewSet(viewsets.ModelViewSet):
    """ViewSet pour les spécialités médicales"""
    queryset = Specialite.objects.all()
    serializer_class = SpecialiteSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['nom_specialite', 'description']
    filterset_fields = ['actif']

class GroupeSanguinViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les groupes sanguins (lecture seule)"""
    queryset = GroupeSanguin.objects.all()
    serializer_class = GroupeSanguinSerializer
    permission_classes = [IsAuthenticated]

class MedecinViewSet(viewsets.ModelViewSet):
    """ViewSet pour les médecins"""
    queryset = Medecin.objects.all()
    serializer_class = MedecinSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['specialite_principale', 'sexe']
    search_fields = ['nom', 'prenom', 'email_professionnel', 'numero_matricule_professionnel']
    ordering_fields = ['nom', 'prenom', 'cree_le']
    ordering = ['nom', 'prenom']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return MedecinListSerializer
        return super().get_serializer_class()
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated, EstMedecin]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Filtrage par tenant
        if user.hopital:
            queryset = queryset.filter(hopital=user.hopital)
        
        return queryset.select_related('specialite_principale', 'utilisateur')
    
    def perform_create(self, serializer):
        serializer.save(
            hopital=self.request.user.hopital,
            cree_par_utilisateur=self.request.user
        )
    
    @action(detail=True, methods=['get'])
    def consultations(self, request, pk=None):
        """Récupérer les consultations d'un médecin"""
        medecin = self.get_object()
        consultations = Consultation.objects.filter(medecin=medecin).order_by('-date_consultation')
        
        # Filtrage par date
        date_debut = request.query_params.get('date_debut')
        date_fin = request.query_params.get('date_fin')
        
        if date_debut:
            try:
                date_debut = datetime.strptime(date_debut, '%Y-%m-%d').date()
                consultations = consultations.filter(date_consultation__date__gte=date_debut)
            except ValueError:
                pass
        
        if date_fin:
            try:
                date_fin = datetime.strptime(date_fin, '%Y-%m-%d').date()
                consultations = consultations.filter(date_consultation__date__lte=date_fin)
            except ValueError:
                pass
        
        page = self.paginate_queryset(consultations)
        if page is not None:
            serializer = ConsultationListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ConsultationListSerializer(consultations, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def statistiques(self, request, pk=None):
        """Statistiques d'un médecin"""
        medecin = self.get_object()
        
        # Consultations
        total_consultations = Consultation.objects.filter(medecin=medecin).count()
        consultations_mois = Consultation.objects.filter(
            medecin=medecin,
            date_consultation__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        # Ordonnances
        total_ordonnances = Ordonnance.objects.filter(medecin=medecin).count()
        
        # Examens prescrits
        total_examens = ExamenMedical.objects.filter(medecin_prescripteur=medecin).count()
        
        return Response({
            'consultations_total': total_consultations,
            'consultations_ce_mois': consultations_mois,
            'ordonnances_total': total_ordonnances,
            'examens_prescrits': total_examens
        })

class ConsultationViewSet(viewsets.ModelViewSet):
    """ViewSet pour les consultations"""
    queryset = Consultation.objects.all()
    serializer_class = ConsultationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['patient', 'medecin', 'rendez_vous']
    search_fields = ['patient__nom', 'patient__prenom', 'medecin__nom', 'motif', 'diagnostic_principal']
    ordering_fields = ['date_consultation', 'created_at']
    ordering = ['-date_consultation']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ConsultationListSerializer
        elif self.action == 'create':
            return ConsultationCreateSerializer
        return super().get_serializer_class()
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update']:
            permission_classes = [IsAuthenticated, EstMedecin]
        elif self.action == 'destroy':
            permission_classes = [IsAuthenticated, EstMedecin]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Filtrage par tenant
        if user.hopital:
            queryset = queryset.filter(tenant=user.hopital)
        
        # Filtrage par rôle
        if user.role == 'patient' and hasattr(user, 'patient_lie'):
            queryset = queryset.filter(patient=user.patient_lie)
        elif user.role == 'medecin' and hasattr(user, 'medecin_lie'):
            queryset = queryset.filter(medecin=user.medecin_lie)
        
        # Filtres par date
        date_debut = self.request.query_params.get('date_debut')
        date_fin = self.request.query_params.get('date_fin')
        
        if date_debut:
            try:
                date_debut = datetime.strptime(date_debut, '%Y-%m-%d').date()
                queryset = queryset.filter(date_consultation__date__gte=date_debut)
            except ValueError:
                pass
        
        if date_fin:
            try:
                date_fin = datetime.strptime(date_fin, '%Y-%m-%d').date()
                queryset = queryset.filter(date_consultation__date__lte=date_fin)
            except ValueError:
                pass
        
        return queryset.select_related('patient', 'medecin', 'rendez_vous')
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.hopital)
    
    @action(detail=True, methods=['post'])
    def creer_ordonnance(self, request, pk=None):
        """Créer une ordonnance pour cette consultation"""
        consultation = self.get_object()
        
        # Vérifier que l'utilisateur est le médecin de la consultation
        if request.user.role != 'medecin' or not hasattr(request.user, 'medecin_lie'):
            return Response(
                {'error': 'Seul le médecin de la consultation peut créer une ordonnance'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if request.user.medecin_lie != consultation.medecin:
            return Response(
                {'error': 'Vous ne pouvez créer une ordonnance que pour vos propres consultations'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Préparer les données
        ordonnance_data = request.data.copy()
        ordonnance_data['consultation'] = consultation.consultation_id
        ordonnance_data['patient'] = consultation.patient.patient_id
        ordonnance_data['medecin'] = consultation.medecin.medecin_id
        ordonnance_data['date_ordonnance'] = timezone.now()
        
        serializer = OrdonnanceCreateSerializer(data=ordonnance_data, context={'request': request})
        if serializer.is_valid():
            ordonnance = serializer.save()
            return Response(OrdonnanceSerializer(ordonnance).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def prescrire_examen(self, request, pk=None):
        """Prescrire un examen médical"""
        consultation = self.get_object()
        
        # Vérifier les permissions
        if request.user.role != 'medecin' or not hasattr(request.user, 'medecin_lie'):
            return Response(
                {'error': 'Seuls les médecins peuvent prescrire des examens'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if request.user.medecin_lie != consultation.medecin:
            return Response(
                {'error': 'Vous ne pouvez prescrire des examens que pour vos propres consultations'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Préparer les données
        examen_data = request.data.copy()
        examen_data['tenant'] = consultation.tenant.tenant_id
        examen_data['patient'] = consultation.patient.patient_id
        examen_data['consultation'] = consultation.consultation_id
        examen_data['medecin_prescripteur'] = consultation.medecin.medecin_id
        examen_data['date_examen'] = request.data.get('date_examen', timezone.now())
        
        serializer = ExamenMedicalSerializer(data=examen_data)
        if serializer.is_valid():
            examen = serializer.save()
            return Response(ExamenMedicalSerializer(examen).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class OrdonnanceViewSet(viewsets.ModelViewSet):
    """ViewSet pour les ordonnances"""
    queryset = Ordonnance.objects.all()
    serializer_class = OrdonnanceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['patient', 'medecin', 'consultation']
    search_fields = ['patient__nom', 'patient__prenom', 'medecin__nom', 'recommandations']
    ordering_fields = ['date_ordonnance', 'created_at']
    ordering = ['-date_ordonnance']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return OrdonnanceListSerializer
        elif self.action == 'create':
            return OrdonnanceCreateSerializer
        return super().get_serializer_class()
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update']:
            permission_classes = [IsAuthenticated, EstMedecin]
        elif self.action == 'destroy':
            permission_classes = [IsAuthenticated, EstMedecin]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Filtrage par tenant
        if user.hopital:
            queryset = queryset.filter(tenant=user.hopital)
        
        # Filtrage par rôle
        if user.role == 'patient' and hasattr(user, 'patient_lie'):
            queryset = queryset.filter(patient=user.patient_lie)
        elif user.role == 'medecin' and hasattr(user, 'medecin_lie'):
            queryset = queryset.filter(medecin=user.medecin_lie)
        
        return queryset.select_related('patient', 'medecin', 'consultation')
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.hopital)

class ExamenMedicalViewSet(viewsets.ModelViewSet):
    """ViewSet pour les examens médicaux"""
    queryset = ExamenMedical.objects.all()
    serializer_class = ExamenMedicalSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['patient', 'consultation', 'medecin_prescripteur', 'type_examen']
    search_fields = ['patient__nom', 'patient__prenom', 'nom_examen', 'resultat']
    ordering_fields = ['date_examen', 'date_resultat', 'created_at']
    ordering = ['-date_examen']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ExamenMedicalListSerializer
        return super().get_serializer_class()
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update']:
            permission_classes = [IsAuthenticated, EstMedecin | EstPersonnel]
        elif self.action == 'destroy':
            permission_classes = [IsAuthenticated, EstMedecin]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Filtrage par tenant
        if user.hopital:
            queryset = queryset.filter(tenant=user.hopital)
        
        # Filtrage par rôle
        if user.role == 'patient' and hasattr(user, 'patient_lie'):
            queryset = queryset.filter(patient=user.patient_lie)
        elif user.role == 'medecin' and hasattr(user, 'medecin_lie'):
            queryset = queryset.filter(medecin_prescripteur=user.medecin_lie)
        
        return queryset.select_related('patient', 'consultation', 'medecin_prescripteur')
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.hopital)
    
    @action(detail=True, methods=['post'])
    def ajouter_resultat(self, request, pk=None):
        """Ajouter le résultat d'un examen"""
        examen = self.get_object()
        
        # Vérifier les permissions
        if request.user.role not in ['medecin', 'infirmier', 'personnel']:
            return Response(
                {'error': 'Vous n\'avez pas la permission d\'ajouter des résultats'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        resultat = request.data.get('resultat')
        notes = request.data.get('notes', '')
        
        if not resultat:
            return Response(
                {'error': 'Le résultat est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        examen.resultat = resultat
        examen.notes = notes
        examen.date_resultat = timezone.now()
        examen.save()
        
        serializer = self.get_serializer(examen)
        return Response(serializer.data)

class PrescriptionViewSet(viewsets.ModelViewSet):
    """ViewSet pour les prescriptions"""
    queryset = Prescription.objects.all()
    serializer_class = PrescriptionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['ordonnance', 'medicament']
    search_fields = ['medicament__nom', 'dosage', 'instructions']
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated, EstMedecin]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Filtrage par tenant via l'ordonnance
        if user.hopital:
            queryset = queryset.filter(ordonnance__tenant=user.hopital)
        
        # Filtrage par rôle
        if user.role == 'patient' and hasattr(user, 'patient_lie'):
            queryset = queryset.filter(ordonnance__patient=user.patient_lie)
        elif user.role == 'medecin' and hasattr(user, 'medecin_lie'):
            queryset = queryset.filter(ordonnance__medecin=user.medecin_lie)
        
        return queryset.select_related('ordonnance', 'medicament')