import os
from comptes.models import Utilisateur

def create_admin():
    email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
    password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
    nom = os.environ.get("DJANGO_SUPERUSER_NOM", "Trimedh")

    if email and password:
        if not Utilisateur.objects.filter(email=email).exists():
            print("Création du superuser...")
            Utilisateur.objects.create_superuser(
                email=email,
                nom_complet=nom,
                mot_de_passe=password
            )
            print("Superuser créé ")
        else:
            print("Superuser déjà existant")