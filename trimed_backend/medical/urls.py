from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views_consultation import ConsultationViewSet

router = DefaultRouter()
router.register(r'consultations', ConsultationViewSet, basename='consultation')

urlpatterns = [
    path('', include(router.urls)),
]