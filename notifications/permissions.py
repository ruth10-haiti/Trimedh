from rest_framework import permissions

class PeutVoirNotifications(permissions.BasePermission):
    """
    Permission pour voir les notifications
    """
    
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Chacun ne peut voir que ses propres notifications
        return obj.utilisateur == request.user

class PeutGererTypesNotification(permissions.BasePermission):
    """
    Permission pour gérer les types de notifications
    """
    
    def has_permission(self, request, view):
        # Seuls les admins et propriétaires peuvent gérer les types
        return request.user.role in ['admin-systeme', 'proprietaire-hopital']