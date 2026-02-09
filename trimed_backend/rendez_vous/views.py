# views.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from datetime import datetime, timedelta, time
from .models import RendezVousType, RendezVousStatut, RendezVous
from .serializers import (
    RendezVousTypeSerializer, RendezVousStatutSerializer,
    RendezVousSerializer, CreneauDisponibleSerializer,
    ChangementStatutSerializer
)
from medical.models import Medecin
from medical.serializers import MedecinSerializer
from comptes.permissions import EstMedecin, EstPersonnel, EstPatient
from patients.permissions import PeutAccederPatient

class RendezVousViewSet(viewsets.ModelViewSet):
    """ViewSet pour les rendez-vous"""
    queryset = RendezVous.objects.all()
    serializer_class = RendezVousSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['tenant', 'medecin', 'type', 'statut']
    ordering_fields = ['date_heure', 'created_at']
    
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
            queryset = queryset.filter(date_heure__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date_heure__date__lte=date_to)
        
        # Filtrer par patient
        patient_id = self.request.query_params.get('patient_id')
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        
        # Filtrer par médecin
        medecin_id = self.request.query_params.get('medecin_id')
        if medecin_id:
            queryset = queryset.filter(medecin_id=medecin_id)
        
        # Filtrer par statut
        statut_id = self.request.query_params.get('statut_id')
        if statut_id:
            queryset = queryset.filter(statut_id=statut_id)
        
        # Les patients ne voient que leurs rendez-vous
        if user.role == 'patient' and hasattr(user, 'patient_lie'):
            queryset = queryset.filter(patient=user.patient_lie)
        
        # Les médecins ne voient que leurs rendez-vous
        elif user.role == 'medecin' and hasattr(user, 'medecin_lie'):
            queryset = queryset.filter(medecin=user.medecin_lie)
        
        # Filtrer les rendez-vous futurs seulement
        futurs_seulement = self.request.query_params.get('futurs_seulement')
        if futurs_seulement == 'true':
            queryset = queryset.filter(date_heure__gte=timezone.now())
        
        return queryset
    
    def perform_create(self, serializer):
        """Surcharge pour ajouter automatiquement le tenant"""
        serializer.save(tenant=self.request.user.hopital)
    
    @action(detail=False, methods=['get'])
    def creneaux_disponibles(self, request):
        """Obtenir les créneaux disponibles"""
        medecin_id = request.query_params.get('medecin_id')
        date_str = request.query_params.get('date')
        type_id = request.query_params.get('type_id')
        
        if not medecin_id or not date_str:
            return Response(
                {'error': 'medecin_id et date sont requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            medecin = Medecin.objects.get(pk=medecin_id, hopital=request.user.hopital)
            
            # Durée du rendez-vous (par défaut 30 minutes)
            duree = 30
            if type_id:
                try:
                    type_rdv = RendezVousType.objects.get(pk=type_id)
                    duree = type_rdv.duree_defaut
                except RendezVousType.DoesNotExist:
                    pass
            
            # Récupérer les rendez-vous du jour
            rendez_vous = RendezVous.objects.filter(
                tenant=request.user.hopital,
                medecin=medecin,
                date_heure__date=date,
                statut__est_annule=False
            ).order_by('date_heure')
            
            # Générer les créneaux disponibles (8h-18h)
            creneaux_disponibles = []
            heure_debut = datetime.combine(date, time(8, 0))
            heure_fin = datetime.combine(date, time(18, 0))
            
            current = heure_debut
            while current + timedelta(minutes=duree) <= heure_fin:
                # Vérifier si le créneau est disponible
                creneau_disponible = True
                creneau_fin = current + timedelta(minutes=duree)
                
                for rdv in rendez_vous:
                    rdv_fin = rdv.date_heure + timedelta(minutes=rdv.duree)
                    
                    # Vérifier si les créneaux se chevauchent
                    if (current < rdv_fin) and (creneau_fin > rdv.date_heure):
                        creneau_disponible = False
                        break
                
                if creneau_disponible:
                    creneaux_disponibles.append({
                        'heure': current.time().strftime('%H:%M'),
                        'date_heure': current,
                        'medecin_id': medecin_id,
                        'type_id': type_id
                    })
                
                current += timedelta(minutes=15)  # Incrément de 15 minutes
            
            return Response({
                'date': date_str,
                'medecin': MedecinSerializer(medecin).data,
                'duree_creneau': duree,
                'creneaux_disponibles': creneaux_disponibles,
                'nombre_creneaux': len(creneaux_disponibles)
            })
        
        except Medecin.DoesNotExist:
            return Response(
                {'error': 'Médecin non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError:
            return Response(
                {'error': 'Format de date invalide. Utilisez YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def changer_statut(self, request, pk=None):
        """Changer le statut d'un rendez-vous"""
        rendez_vous = self.get_object()
        
        # Vérifier les permissions
        if (request.user.role == 'patient' and 
            hasattr(request.user, 'patient_lie') and 
            request.user.patient_lie != rendez_vous.patient):
            return Response(
                {'error': 'Vous ne pouvez modifier que vos propres rendez-vous'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ChangementStatutSerializer(data=request.data)
        if serializer.is_valid():
            nouveau_statut = RendezVousStatut.objects.get(
                pk=serializer.validated_data['nouveau_statut_id']
            )
            raison = serializer.validated_data.get('raison', '')
            
            ancien_statut = rendez_vous.statut
            rendez_vous.statut = nouveau_statut
            
            # Si annulation, enregistrer la raison
            if nouveau_statut.est_annule:
                rendez_vous.raison_annulation = raison
            
            rendez_vous.save()
            
            # Log de l'action
            from django.contrib.admin.models import LogEntry, CHANGE
            from django.contrib.contenttypes.models import ContentType
            
            LogEntry.objects.log_action(
                user_id=request.user.pk,
                content_type_id=ContentType.objects.get_for_model(rendez_vous).pk,
                object_id=rendez_vous.pk,
                object_repr=str(rendez_vous),
                action_flag=CHANGE,
                change_message=f"Statut changé: {ancien_statut.nom} -> {nouveau_statut.nom}. Raison: {raison}"
            )
            
            return Response({
                'message': 'Statut mis à jour avec succès',
                'ancien_statut': ancien_statut.nom,
                'nouveau_statut': nouveau_statut.nom,
                'rendez_vous': RendezVousSerializer(rendez_vous).data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def agenda(self, request):
        """Agenda des rendez-vous"""
        user = request.user
        
        # Déterminer la période (par défaut: aujourd'hui)
        date_str = request.query_params.get('date')
        if date_str:
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Format de date invalide. Utilisez YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            date = timezone.now().date()
        
        # Récupérer les rendez-vous du jour
        rendez_vous = RendezVous.objects.filter(
            tenant=user.hopital,
            date_heure__date=date,
            statut__est_annule=False
        ).order_by('date_heure')
        
        # Filtrer selon le rôle
        if user.role == 'medecin' and hasattr(user, 'medecin_lie'):
            rendez_vous = rendez_vous.filter(medecin=user.medecin_lie)
        
        # Grouper par médecin
        agenda_par_medecin = {}
        for rdv in rendez_vous:
            medecin_nom = f"Dr {rdv.medecin.prenom} {rdv.medecin.nom}"
            if medecin_nom not in agenda_par_medecin:
                agenda_par_medecin[medecin_nom] = []
            
            agenda_par_medecin[medecin_nom].append(RendezVousSerializer(rdv).data)
        
        return Response({
            'date': date,
            'agenda': agenda_par_medecin,
            'total_rendez_vous': rendez_vous.count()
        })