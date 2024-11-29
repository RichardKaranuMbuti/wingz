from rest_framework import serializers
from .models import User, Ride, RideEvent

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import AuthenticationFailed
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
import logging


logger = logging.getLogger(__name__)

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = 'email'

    def validate(self, attrs):
        credentials = {
            'email': attrs.get('email'),
            'password': attrs.get('password')
        }
        
        if not credentials['email'] or not credentials['password']:
            raise AuthenticationFailed('Must include "email" and "password".')

        User = get_user_model()
        try:
            user = User.objects.get(email=credentials['email'])
            if user.check_password(credentials['password']):
                if not user.is_active:
                    raise AuthenticationFailed('User account is disabled.')
                
                refresh = RefreshToken.for_user(user)
                
                # Add custom claims
                refresh['email'] = user.email
                refresh['role'] = user.role
                refresh['user_id'] = user.id
                
                return {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            else:
                raise AuthenticationFailed('No active account found with the given credentials')
        except User.DoesNotExist:
            raise AuthenticationFailed('No active account found with the given credentials')
        
        
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        validators=[validate_password]
    )

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 
                 'phone_number', 'role', 'password']
        read_only_fields = ['id']

    def create(self, validated_data):
        # Remove the password from validated_data
        password = validated_data.pop('password')
        
        # Create the user instance
        user = User.objects.create(**validated_data)
        
        # Set the password properly (this will hash it)
        user.set_password(password)
        user.save()
        
        return user


class RideEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = RideEvent
        fields = ['id_ride_event', 'description', 'created_at']
        read_only_fields = ['id_ride_event', 'created_at']
        
class RideSerializer(serializers.ModelSerializer):
    rider = UserSerializer(source='id_rider', read_only=True)
    driver = UserSerializer(source='id_driver', read_only=True)
    todays_ride_events = serializers.SerializerMethodField()
    distance_to_pickup = serializers.SerializerMethodField()
    id_rider = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    id_driver = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = Ride
        fields = [
            'id_ride', 'status', 'rider', 'driver', 
            'id_rider', 'id_driver',
            'pickup_latitude', 'pickup_longitude',
            'dropoff_latitude', 'dropoff_longitude',
            'pickup_time', 'todays_ride_events',
            'distance_to_pickup'
        ]
        read_only_fields = ['id_ride', 'distance_to_pickup']

    def get_todays_ride_events(self, obj):
        recent_events = getattr(obj, 'recent_events', None)
        if recent_events is None:
            return []
        return RideEventSerializer(recent_events, many=True).data

    def get_distance_to_pickup(self, obj):
        request = self.context.get('request')
        if request and request.query_params.get('latitude') and request.query_params.get('longitude'):
            try:
                lat = float(request.query_params.get('latitude'))
                lon = float(request.query_params.get('longitude'))
                return obj.calculate_distance_to_point(lat, lon)
            except (ValueError, TypeError):
                return None
        return None

    def validate(self, data):
        if 'status' in data and data['status'] not in dict(Ride.RIDE_STATUS_CHOICES):
            raise serializers.ValidationError({'status': 'Invalid ride status'})
        
        # Validate coordinates
        for coord in ['pickup_latitude', 'pickup_longitude', 'dropoff_latitude', 'dropoff_longitude']:
            if coord in data:
                value = data[coord]
                if coord.endswith('latitude') and not -90 <= value <= 90:
                    raise serializers.ValidationError({coord: 'Latitude must be between -90 and 90'})
                if coord.endswith('longitude') and not -180 <= value <= 180:
                    raise serializers.ValidationError({coord: 'Longitude must be between -180 and 180'})
        
        return data
