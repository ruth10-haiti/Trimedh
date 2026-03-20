from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PatientViewSet,
    AdressePatientViewSet,
    PersonneAContacterViewSet,
    AssurancePatientViewSet,
    AllergiePatientViewSet,
    AntecedentMedicalViewSet,
    SuiviPatientViewSet
)

router = DefaultRouter()
router.register(r'patients', PatientViewSet)
router.register(r'adresses', AdressePatientViewSet)
router.register(r'contacts', PersonneAContacterViewSet)
router.register(r'assurances', AssurancePatientViewSet)
router.register(r'allergies', AllergiePatientViewSet)
router.register(r'antecedents', AntecedentMedicalViewSet)
router.register(r'suivis', SuiviPatientViewSet)

urlpatterns = [
    path('', include(router.urls)),
]