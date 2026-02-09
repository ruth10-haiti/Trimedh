from rest_framework import permissions

class PeutModifierTenant(permissions.BasePermission):
    """
    Permission pour modifier un tenant
    """
    def has_object_permission(self, request, view, obj):
        # Seuls les admins système peuvent modifier
        return request.user.role == 'admin-systeme'

class PeutVoirTenant(permissions.BasePermission):
    """
    Permission pour voir un tenant
    """
    def has_object_permission(self, request, view, obj):
        # Les admins système voient tout
        if request.user.role == 'admin-systeme':
            return True
        
        # Les propriétaires voient leur tenant
        if request.user.role == 'proprietaire-hopital':
            return obj.proprietaire_utilisateur == request.user
        
        # Les autres utilisateurs voient leur tenant assigné
        return request.user.hopital == obj