from django.shortcuts import render

# views.py
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ValidationError
from django.db.models import Prefetch, Q
from django.utils import timezone
from django.db.models import F
from datetime import timedelta
import logging


from .models import Ride, RideEvent, User
from .serializers import RideSerializer, UserSerializer, RideEventSerializer
from rest_framework import generics
from rest_framework.permissions import AllowAny

logger = logging.getLogger(__name__)

class IsAdminUser(IsAuthenticated):
    """Custom permission to only allow admin users"""
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == 'admin'

class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]


class RideViewSet(viewsets.ModelViewSet):
    serializer_class = RideSerializer
    permission_classes = [IsAdminUser]
    pagination_class = CustomPagination

    def get_queryset(self):
        try:
            # Base queryset
            queryset = Ride.objects.select_related('id_rider', 'id_driver')

            # Prefetch today's ride events
            twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
            recent_events_prefetch = Prefetch(
                'ride_events',
                queryset=RideEvent.objects.filter(created_at__gte=twenty_four_hours_ago),
                to_attr='recent_events'
            )
            queryset = queryset.prefetch_related(recent_events_prefetch)

            # Apply filters
            status_filter = self.request.query_params.get('status')
            rider_email = self.request.query_params.get('rider_email')
            
            if status_filter:
                if status_filter not in dict(Ride.RIDE_STATUS_CHOICES):
                    raise ValidationError({'status': 'Invalid status filter'})
                queryset = queryset.filter(status=status_filter)
            
            if rider_email:
                queryset = queryset.filter(id_rider__email=rider_email)

            # Apply sorting
            sort_by = self.request.query_params.get('sort_by', 'pickup_time')
            latitude = self.request.query_params.get('latitude')
            longitude = self.request.query_params.get('longitude')

            if sort_by == 'distance' and latitude and longitude:
                try:
                    # Convert coordinates to float
                    lat = float(latitude)
                    lon = float(longitude)
                    
                    # Validate coordinates
                    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                        raise ValidationError({'coordinates': 'Invalid coordinates range'})
                    
                    # Add distance annotation for sorting
                    # Using database-level distance calculation for efficiency
                    queryset = queryset.annotate(
                        distance=((F('pickup_latitude') - lat) * (F('pickup_latitude') - lat) +
                                (F('pickup_longitude') - lon) * (F('pickup_longitude') - lon))
                    ).order_by('distance')
                except ValueError:
                    raise ValidationError({'coordinates': 'Invalid coordinates format'})
            else:
                # Default sorting by pickup_time
                queryset = queryset.order_by('pickup_time')

            return queryset

        except Exception as e:
            logger.error(f"Error in get_queryset: {str(e)}")
            raise

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating ride: {str(e)}")
            return Response(
                {'error': 'An unexpected error occurred'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error updating ride: {str(e)}")
            return Response(
                {'error': 'An unexpected error occurred'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(f"Error deleting ride: {str(e)}")
            return Response(
                {'error': 'An unexpected error occurred'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        