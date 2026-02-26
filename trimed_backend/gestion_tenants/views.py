from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny  
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from .models import Tenant, ParametreHopital
from .serializers import TenantSerializer, ParametreHopitalSerializer
from comptes.permissions import EstAdminSysteme, EstProprietaireHopital
from rest_framework import generics, permissions
from rest_framework.response import Response
from .models import Tenant
from .serializers import TenantSerializer  

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
            # Les actions d'écriture nécessitent admin système
            permission_classes = [IsAuthenticated, EstAdminSysteme]
        elif self.action == 'retrieve':
            # Consulter un hôpital spécifique nécessite juste authentification
            permission_classes = [IsAuthenticated]
        elif self.action == 'list':
            # La liste des hôpitaux est publique (pour l'inscription)
            permission_classes = [AllowAny]
        else:
            # Pour les actions personnalisées (verifier_documents, statistiques)
            permission_classes = [IsAuthenticated, EstAdminSysteme]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """
        Filtrer les tenants selon les permissions
        """
        queryset = super().get_queryset()
        user = self.request.user
        
        # Pour l'action 'list' (publique), retourner tous les tenants
        if self.action == 'list':
            return queryset
        
        # Si l'utilisateur n'est pas authentifié, retourner queryset vide
        if not user or not user.is_authenticated:
            return Tenant.objects.none()
        
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

class TenantListView(generics.ListAPIView):
    """Vue pour lister les hôpitaux actifs"""
    permission_classes = [permissions.AllowAny] 
    serializer_class = TenantSerializer
    
    def get_queryset(self):
        # Ne retourner que les hôpitaux actifs
        return Tenant.objects.filter(statut='actif').order_by('nom')