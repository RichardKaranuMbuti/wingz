# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RideViewSet, UserRegistrationView

router = DefaultRouter()
router.register(r'rides', RideViewSet, basename='ride')

urlpatterns = [
    path('users/', include(router.urls)),
    path('register/', UserRegistrationView.as_view(), name='user-register'),
]