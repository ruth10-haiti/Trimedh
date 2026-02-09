from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db import models
from .models import MedicamentCategorie, Medicament
from .serializers import (
    MedicamentCategorieSerializer, MedicamentSerializer,
    MedicamentListSerializer, StockUpdateSerializer
)
from comptes.permissions import EstMedecin, EstPersonnel

class MedicamentCategorieViewSet(viewsets.ModelViewSet):
    """ViewSet pour les catégories de médicaments"""
    queryset = MedicamentCategorie.objects.all()
    serializer_class = MedicamentCategorieSerializer
    permission_classes = [IsAuthenticated, EstPersonnel]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['tenant']
    search_fields = ['nom', 'description']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Filtrer par tenant
        if user.hopital:
            queryset = queryset.filter(tenant=user.hopital)
        
        return queryset
    
    def perform_create(self, serializer):
        """Surcharge pour ajouter automatiquement le tenant"""
        serializer.save(tenant=self.request.user.hopital)

class MedicamentViewSet(viewsets.ModelViewSet):
    """ViewSet pour les médicaments"""
    queryset = Medicament.objects.all()
    serializer_class = MedicamentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['tenant', 'categorie', 'forme_pharmaceutique', 'actif']
    search_fields = ['nom', 'description', 'code_atc', 'dci']
    ordering_fields = ['nom', 'stock_actuel', 'prix_unitaire', 'created_at']
    
    def get_serializer_class(self):
        """Utiliser un serializer différent pour la liste"""
        if self.action == 'list':
            return MedicamentListSerializer
        return super().get_serializer_class()
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Filtrer par tenant
        if user.hopital:
            queryset = queryset.filter(tenant=user.hopital)
        
        # Filtrer par besoin de réapprovisionnement
        besoin_reappro = self.request.query_params.get('besoin_reapprovisionnement')
        if besoin_reappro == 'true':
            queryset = queryset.filter(stock_actuel__lte=models.F('stock_minimum'))
        elif besoin_reappro == 'false':
            queryset = queryset.filter(stock_actuel__gt=models.F('stock_minimum'))
        
        # Filtrer par médicaments nécessitant une ordonnance
        necessite_ordonnance = self.request.query_params.get('necessite_ordonnance')
        if necessite_ordonnance == 'true':
            queryset = queryset.filter(necessite_ordonnance=True)
        elif necessite_ordonnance == 'false':
            queryset = queryset.filter(necessite_ordonnance=False)
        
        return queryset
    
    def perform_create(self, serializer):
        """Surcharge pour ajouter automatiquement le tenant"""
        serializer.save(tenant=self.request.user.hopital)
    
    @action(detail=True, methods=['post'])
    def mettre_a_jour_stock(self, request, pk=None):
        """Mettre à jour le stock d'un médicament"""
        medicament = self.get_object()
        
        # Vérifier que l'utilisateur est autorisé
        if request.user.role not in ['personnel', 'secretaire', 'infirmier']:
            return Response(
                {'error': 'Seul le personnel peut modifier le stock'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = StockUpdateSerializer(data=request.data)
        if serializer.is_valid():
            quantite = serializer.validated_data['quantite']
            operation = serializer.validated_data['operation']
            motif = serializer.validated_data.get('motif', '')
            
            ancien_stock = medicament.stock_actuel
            
            if operation == 'ajouter':
                medicament.stock_actuel += quantite
            elif operation == 'retirer':
                if medicament.stock_actuel < quantite:
                    return Response(
                        {'error': f'Stock insuffisant. Stock actuel: {medicament.stock_actuel}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                medicament.stock_actuel -= quantite
            elif operation == 'definir':
                medicament.stock_actuel = quantite
            
            medicament.save()
            
            # Log de l'opération
            from django.contrib.admin.models import LogEntry, CHANGE
            from django.contrib.contenttypes.models import ContentType
            
            LogEntry.objects.log_action(
                user_id=request.user.pk,
                content_type_id=ContentType.objects.get_for_model(medicament).pk,
                object_id=medicament.pk,
                object_repr=str(medicament),
                action_flag=CHANGE,
                change_message=f"Stock mis à jour: {ancien_stock} -> {medicament.stock_actuel}. Motif: {motif}"
            )
            
            return Response({
                'message': 'Stock mis à jour avec succès',
                'ancien_stock': ancien_stock,
                'nouveau_stock': medicament.stock_actuel,
                'medicament': MedicamentSerializer(medicament).data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def statistiques_stock(self, request):
        """Statistiques sur le stock de médicaments"""
        user = request.user
        
        # Filtrer par tenant
        if not user.hopital:
            return Response(
                {'error': 'Aucun tenant associé'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        medicaments = Medicament.objects.filter(tenant=user.hopital, actif=True)
        
        total_medicaments = medicaments.count()
        medicaments_bas_stock = medicaments.filter(stock_actuel__lte=models.F('stock_minimum')).count()
        valeur_stock_total = sum(m.prix_unitaire * m.stock_actuel for m in medicaments if m.prix_unitaire)
        
        # Médicaments par catégorie
        categories = MedicamentCategorie.objects.filter(tenant=user.hopital)
        medicaments_par_categorie = []
        
        for categorie in categories:
            count = medicaments.filter(categorie=categorie).count()
            if count > 0:
                medicaments_par_categorie.append({
                    'categorie': categorie.nom,
                    'nombre': count
                })
        
        data = {
            'total_medicaments': total_medicaments,
            'medicaments_bas_stock': medicaments_bas_stock,
            'valeur_stock_total': round(float(valeur_stock_total), 2),
            'medicaments_par_categorie': medicaments_par_categorie,
            'date_analyse': timezone.now().date()
        }
        
        return Response(data)