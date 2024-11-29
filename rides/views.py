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
from django.db.models.expressions import ExpressionWrapper, Window
from django.db.models.functions import RowNumber

logger = logging.getLogger(__name__)

from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

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


from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

# @method_decorator(csrf_exempt, name='dispatch')

from django.db.models import F
from django.db.models.expressions import RawSQL


class RideViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Ride operations.
    Supports CRUD operations with optimized queries and pagination.
    Only accessible by admin users.
    """
    serializer_class = RideSerializer
    permission_classes = [IsAdminUser]
    pagination_class = CustomPagination

    def get_queryset(self):
        """
        Returns an optimized queryset for rides with related data.
        Implements filtering and sorting with efficient SQL queries.
        """
        try:
            # Base queryset with related fields - Query 1
            queryset = Ride.objects.select_related('id_rider', 'id_driver')
            
            # Prefetch today's ride events - Query 2
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
            latitude = self.request.query_params.get('latitude')
            longitude = self.request.query_params.get('longitude')
            
            if status_filter:
                if status_filter not in dict(Ride.RIDE_STATUS_CHOICES):
                    raise ValidationError({
                        'status': f'Invalid status. Must be one of: {", ".join(dict(Ride.RIDE_STATUS_CHOICES).keys())}'
                    })
                queryset = queryset.filter(status=status_filter)
            
            if rider_email:
                queryset = queryset.filter(id_rider__email=rider_email)

            # Apply sorting
            sort_by = self.request.query_params.get('sort_by', 'pickup_time')
            
            if sort_by == 'distance' and latitude and longitude:
                try:
                    lat = float(latitude)
                    lon = float(longitude)
                    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                        raise ValidationError({'coordinates': 'Invalid latitude/longitude values'})
                    
                    # Calculate distance using SQL for efficiency
                    distance_formula = """
                        6371 * acos(
                            cos(radians(%s)) * 
                            cos(radians(pickup_latitude)) * 
                            cos(radians(pickup_longitude) - radians(%s)) + 
                            sin(radians(%s)) * 
                            sin(radians(pickup_latitude))
                        )
                    """
                    queryset = queryset.annotate(
                        distance=RawSQL(distance_formula, params=[lat, lon, lat])
                    ).order_by('distance')
                except (ValueError, TypeError):
                    raise ValidationError({'coordinates': 'Invalid coordinate format'})
            else:
                queryset = queryset.order_by('pickup_time')

            return queryset

        except Exception as e:
            logger.error(f"Error in get_queryset: {str(e)}")
            raise

    def get_serializer_context(self):
        """
        Add coordinates to serializer context for distance calculations.
        """
        context = super().get_serializer_context()
        context.update({
            'latitude': self.request.query_params.get('latitude'),
            'longitude': self.request.query_params.get('longitude')
        })
        return context

    def create(self, request, *args, **kwargs):
        """
        Create a new ride with validated data.
        Calculates distance if coordinates are provided.
        """
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # Create the ride instance
            ride = serializer.save()
            
            # Calculate initial distance if coordinates provided
            latitude = request.query_params.get('latitude')
            longitude = request.query_params.get('longitude')
            if latitude and longitude:
                try:
                    distance = ride.calculate_distance_to_point(
                        float(latitude),
                        float(longitude)
                    )
                    ride.distance_to_pickup = distance
                    ride.save()
                except (ValueError, TypeError):
                    pass  # Skip distance calculation if coordinates are invalid
            
            return Response(
                self.get_serializer(ride).data,
                status=status.HTTP_201_CREATED
            )
            
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error creating ride: {str(e)}")
            return Response(
                {'error': 'An unexpected error occurred'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update(self, request, *args, **kwargs):
        """
        Update a ride instance.
        Recalculates distance if coordinates are updated.
        """
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(
                instance,
                data=request.data,
                partial=partial
            )
            serializer.is_valid(raise_exception=True)
            
            # Check if location-related fields are being updated
            location_fields = {
                'pickup_latitude', 'pickup_longitude',
                'dropoff_latitude', 'dropoff_longitude'
            }
            
            if any(field in request.data for field in location_fields):
                # Save the updated instance
                instance = serializer.save()
                
                # Recalculate distance if coordinates are provided
                latitude = request.query_params.get('latitude')
                longitude = request.query_params.get('longitude')
                if latitude and longitude:
                    try:
                        distance = instance.calculate_distance_to_point(
                            float(latitude),
                            float(longitude)
                        )
                        instance.distance_to_pickup = distance
                        instance.save()
                    except (ValueError, TypeError):
                        pass
            else:
                instance = serializer.save()
            
            return Response(self.get_serializer(instance).data)
            
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error updating ride: {str(e)}")
            return Response(
                {'error': 'An unexpected error occurred'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def destroy(self, request, *args, **kwargs):
        """
        Delete a ride instance.
        """
        try:
            instance = self.get_object()
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(f"Error deleting ride: {str(e)}")
            return Response(
                {'error': 'An unexpected error occurred'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )