# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RideViewSet, UserRegistrationView,CustomTokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView


router = DefaultRouter()
router.register(r'rides', RideViewSet, basename='ride')

urlpatterns = [
    path('', include(router.urls)),
    path('register/', UserRegistrationView.as_view(), name='user-register'),
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]