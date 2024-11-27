from django.db import models

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import EmailValidator
import math


class User(AbstractUser):
    id_user = models.AutoField(primary_key=True)
    role = models.CharField(max_length=50, default='user')  # 'admin' or other roles
    phone_number = models.CharField(max_length=20)
    
    # Override inherited fields to match your schema
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(
        unique=True,
        validators=[EmailValidator()]
    )
    
    # Required for custom user model
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name', 'phone_number']

    class Meta:
        db_table = 'user'



class Ride(models.Model):
    RIDE_STATUS_CHOICES = [
        ('en-route', 'En Route'),
        ('pickup', 'Pickup'),
        ('dropoff', 'Dropoff'),
    ]

    id_ride = models.AutoField(primary_key=True)
    status = models.CharField(max_length=20, choices=RIDE_STATUS_CHOICES)
    id_rider = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='rides_as_rider'
    )
    id_driver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='rides_as_driver'
    )
    pickup_latitude = models.FloatField()
    pickup_longitude = models.FloatField()
    dropoff_latitude = models.FloatField()
    dropoff_longitude = models.FloatField()
    pickup_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ride'

    def calculate_distance_to_point(self, lat, lon):
        """
        Calculate the distance between ride pickup location and given coordinates
        using the Haversine formula.
        """
        R = 6371  # Earth's radius in kilometers

        lat1 = math.radians(self.pickup_latitude)
        lon1 = math.radians(self.pickup_longitude)
        lat2 = math.radians(float(lat))
        lon2 = math.radians(float(lon))

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c

        return distance

class RideEvent(models.Model):
    id_ride_event = models.AutoField(primary_key=True)
    id_ride = models.ForeignKey(
        Ride,
        on_delete=models.CASCADE,
        related_name='ride_events'
    )
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ride_event'
        indexes = [
            models.Index(fields=['created_at']),  # Add index for filtering by date
        ]