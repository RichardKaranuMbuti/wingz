from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from .models import User, Ride, RideEvent

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id_user', 'first_name', 'last_name', 'email', 'phone_number', 'role']
        read_only_fields = ['id_user']

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

    class Meta:
        model = Ride
        fields = [
            'id_ride', 'status', 'rider', 'driver', 
            'pickup_latitude', 'pickup_longitude',
            'dropoff_latitude', 'dropoff_longitude',
            'pickup_time', 'todays_ride_events',
            'distance_to_pickup'
        ]
        read_only_fields = ['id_ride', 'distance_to_pickup']

    def get_todays_ride_events(self, obj):
        # Get only events from the last 24 hours
        # This will be prefetched in the viewset
        return RideEventSerializer(obj.recent_events, many=True).data

    def get_distance_to_pickup(self, obj):
        # Calculate distance if coordinates are provided in context
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
        return data