from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MedicamentViewSet, MedicamentCategorieViewSet
)

router = DefaultRouter()
router.register(r'', MedicamentViewSet, basename='medicament')
router.register(r'categories', MedicamentCategorieViewSet, basename='medicament-categorie')

urlpatterns = [
    path('', include(router.urls)),
]
