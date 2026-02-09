from rest_framework import permissions

class PeutVoirConsultation(permissions.BasePermission):
    """
    Permission pour voir une consultation
    """
    
    def has_object_permission(self, request, view, obj):
        # Les patients ne voient que leurs consultations
        if request.user.role == 'patient':
            return hasattr(request.user, 'patient_lie') and request.user.patient_lie == obj.patient
        
        # Les médecins voient leurs consultations
        if request.user.role == 'medecin':
            return hasattr(request.user, 'medecin_lie') and request.user.medecin_lie == obj.medecin
        
        # Le personnel voit toutes les consultations de leur tenant
        if request.user.role in ['personnel', 'secretaire', 'infirmier']:
            return request.user.hopital == obj.tenant
        
        return False

class PeutCreerConsultation(permissions.BasePermission):
    """
    Permission pour créer une consultation
    """
    
    def has_permission(self, request, view):
        # Seuls les médecins et personnel peuvent créer des consultations
        return request.user.role in ['medecin', 'personnel', 'secretaire', 'infirmier']

class PeutVoirOrdonnance(permissions.BasePermission):
    """
    Permission pour voir une ordonnance
    """
    
    def has_object_permission(self, request, view, obj):
        # Les patients ne voient que leurs ordonnances
        if request.user.role == 'patient':
            return obj.patient.utilisateur == request.user
        
        # Les médecins voient leurs ordonnances
        if request.user.role == 'medecin':
            return obj.medecin.utilisateur == request.user
        
        # Le personnel voit toutes les ordonnances de leur tenant
        return request.user.hopital == obj.tenant