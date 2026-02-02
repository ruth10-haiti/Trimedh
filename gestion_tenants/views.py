from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from .models import Tenant, ParametreHopital
from .serializers import TenantSerializer, ParametreHopitalSerializer
from comptes.permissions import EstAdminSysteme, EstProprietaireHopital

class TenantViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des tenants
    """
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nom', 'email_professionnel', 'directeur']
    ordering_fields = ['nom', 'cree_le', 'nombre_de_lits']
    
    def get_permissions(self):
        """
        Permissions personnalisées selon l'action
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated, EstAdminSysteme]
        elif self.action == 'retrieve':
            permission_classes = [IsAuthenticated]
        else:  # list
            permission_classes = [IsAuthenticated, EstAdminSysteme]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """
        Filtrer les tenants selon les permissions
        """
        queryset = super().get_queryset()
        user = self.request.user
        
        if user.role == 'admin-systeme':
            return queryset
        
        # Les propriétaires ne voient que leur tenant
        if user.role == 'proprietaire-hopital':
            return queryset.filter(proprietaire_utilisateur=user)
        
        # Les autres utilisateurs voient leur tenant
        if user.hopital:
            return queryset.filter(pk=user.hopital.pk)
        
        return Tenant.objects.none()
    
    @action(detail=True, methods=['patch'])
    def verifier_documents(self, request, pk=None):
        """Vérifier les documents d'un tenant"""
        tenant = self.get_object()
        action = request.data.get('action')
        commentaire = request.data.get('commentaire', '')
        
        if action == 'approuver':
            tenant.statut_verification_document = 'verifie'
            tenant.verifie_par = request.user
            tenant.date_verification = timezone.now()
            tenant.save()
            
            return Response({
                'status': 'success',
                'message': 'Documents approuvés avec succès'
            })
        
        elif action == 'rejeter':
            tenant.statut_verification_document = 'rejete'
            tenant.save()
            
            return Response({
                'status': 'success',
                'message': 'Documents rejetés',
                'commentaire': commentaire
            })
        
        return Response(
            {'error': 'Action invalide'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=True, methods=['get'])
    def statistiques(self, request, pk=None):
        """Statistiques d'un tenant"""
        tenant = self.get_object()
        
        from comptes.models import Utilisateur
        from patients.models import Patient
        from medical.models import Medecin, Consultation
        from rendez_vous.models import RendezVous
        
        data = {
            'utilisateurs': Utilisateur.objects.filter(hopital=tenant).count(),
            'patients': Patient.objects.filter(hopital=tenant).count(),
            'medecins': Medecin.objects.filter(hopital=tenant).count(),
            'consultations_mois': Consultation.objects.filter(
                tenant=tenant,
                date_consultation__month=timezone.now().month
            ).count(),
            'rdv_a_venir': RendezVous.objects.filter(
                tenant=tenant,
                date_heure__gte=timezone.now()
            ).count(),
        }
        
        return Response(data)

class ParametreHopitalViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des paramètres d'hôpital
    """
    queryset = ParametreHopital.objects.all()
    serializer_class = ParametreHopitalSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtrer par tenant de l'utilisateur"""
        queryset = super().get_queryset()
        user = self.request.user
        
        if user.role == 'admin-systeme':
            return queryset
        
        if user.hopital:
            return queryset.filter(tenant=user.hopital)
        
        return ParametreHopital.objects.none()