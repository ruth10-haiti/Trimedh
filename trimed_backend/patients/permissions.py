from rest_framework import permissions

class PeutAccederPatient(permissions.BasePermission):
    """
    Permission pour accéder à un patient
    """
    
    def has_object_permission(self, request, view, obj):
        # Les patients ne voient que leur propre dossier
        if request.user.role == 'patient':
            return hasattr(request.user, 'patient_lie') and request.user.patient_lie == obj
        
        # Les médecins et personnel voient les patients de leur tenant
        if request.user.hopital:
            return obj.hopital == request.user.hopital
        
        return False

class PeutModifierPatient(permissions.BasePermission):
    """
    Permission pour modifier un patient
    """
    
    def has_object_permission(self, request, view, obj):
        # Seuls les médecins et personnel peuvent modifier
        if request.user.role not in ['medecin', 'personnel', 'infirmier', 'secretaire']:
            return False
        
        # Doit être du même tenant
        return request.user.hopital == obj.hopital