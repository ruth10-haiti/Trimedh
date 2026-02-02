# permissions.py
from rest_framework import permissions
from django.utils import timezone
from datetime import timedelta

class PeutCreerRendezVous(permissions.BasePermission):
    """
    Permission pour créer un rendez-vous
    """
    
    def has_permission(self, request, view):
        # Tout utilisateur authentifié peut créer un rendez-vous
        return request.user.is_authenticated

class PeutModifierRendezVous(permissions.BasePermission):
    """
    Permission pour modifier un rendez-vous
    """
    
    def has_object_permission(self, request, view, obj):
        # Les patients ne peuvent modifier que leurs propres rendez-vous
        if request.user.role == 'patient':
            return hasattr(request.user, 'patient_lie') and request.user.patient_lie == obj.patient
        
        # Les médecins ne peuvent modifier que leurs propres rendez-vous
        if request.user.role == 'medecin':
            return hasattr(request.user, 'medecin_lie') and request.user.medecin_lie == obj.medecin
        
        # Le personnel peut modifier tous les rendez-vous de leur tenant
        if request.user.role in ['personnel', 'secretaire', 'infirmier']:
            return request.user.hopital == obj.tenant
        
        return False

class PeutAnnulerRendezVous(permissions.BasePermission):
    """
    Permission pour annuler un rendez-vous
    """
    
    def has_object_permission(self, request, view, obj):
        # Les patients peuvent annuler leurs rendez-vous jusqu'à 24h avant
        if request.user.role == 'patient':
            if hasattr(request.user, 'patient_lie') and request.user.patient_lie == obj.patient:
                # Vérifier que le rendez-vous est dans plus de 24h
                return obj.date_heure > timezone.now() + timedelta(hours=24)
            return False
        
        # Les médecins et personnel peuvent annuler à tout moment
        return request.user.role in ['medecin', 'personnel', 'secretaire', 'infirmier']