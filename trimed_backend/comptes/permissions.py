from rest_framework import permissions
from .models import Utilisateur

class EstAdminSysteme(permissions.BasePermission):
    """Permission pour les administrateurs système"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin-systeme'

class EstProprietaireHopital(permissions.BasePermission):
    """Permission pour les propriétaires d'hôpital"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'proprietaire-hopital'

class EstMedecin(permissions.BasePermission):
    """Permission pour les médecins"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'medecin'

class EstPersonnel(permissions.BasePermission):
    """Permission pour le personnel"""
    
    def has_permission(self, request, view):
        roles_personnel = ['personnel', 'secretaire', 'infirmier']
        return request.user.is_authenticated and request.user.role in roles_personnel

class EstPatient(permissions.BasePermission):
    """Permission pour les patients"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'patient'

class PeutModifierUtilisateur(permissions.BasePermission):
    """
    Permission pour modifier un utilisateur
    """
    def has_object_permission(self, request, view, obj):
        # L'utilisateur peut modifier son propre profil
        if obj == request.user:
            return True
        
        # Les admins système peuvent modifier tous les utilisateurs
        if request.user.role == 'admin-systeme':
            return True
        
        # Les propriétaires peuvent modifier les utilisateurs de leur tenant
        if (request.user.role == 'proprietaire-hopital' and 
            request.user.hopital and 
            obj.hopital == request.user.hopital):
            return True
        
        return False

class EstDansMemesTenant(permissions.BasePermission):
    """
    Permission pour s'assurer que l'utilisateur accède uniquement 
    aux ressources de son propre tenant
    """
    
    def has_object_permission(self, request, view, obj):
        # Vérifier si l'objet a un attribut tenant
        if hasattr(obj, 'tenant'):
            return obj.tenant == request.user.hopital
        # Vérifier si l'objet a un attribut hopital
        elif hasattr(obj, 'hopital'):
            return obj.hopital == request.user.hopital
        # Pour les utilisateurs
        elif isinstance(obj, Utilisateur):
            return obj.hopital == request.user.hopital
        return False