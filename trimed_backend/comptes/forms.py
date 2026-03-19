from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from .models import Utilisateur

class UtilisateurCreationForm(forms.ModelForm):
    """Formulaire pour créer un superuser avec mot de passe"""
    password1 = forms.CharField(label='Mot de passe', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirmer le mot de passe', widget=forms.PasswordInput)

    class Meta:
        model = Utilisateur
        fields = ('email', 'nom_complet', 'role', 'hopital')

    def clean_password2(self):
        # Vérifie que les deux mots de passe correspondent
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Les mots de passe ne correspondent pas")
        return password2

    def save(self, commit=True):
        utilisateur = super().save(commit=False)
        utilisateur.set_password(self.cleaned_data["password1"])
        if commit:
            utilisateur.save()
        return utilisateur

class UtilisateurChangeForm(forms.ModelForm):
    """Formulaire pour modifier un utilisateur existant dans l’admin"""
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = Utilisateur
        fields = ('email', 'nom_complet', 'password', 'role', 'hopital', 'is_active', 'is_staff', 'is_superuser')
