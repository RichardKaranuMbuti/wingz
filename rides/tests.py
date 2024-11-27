from django.test import TestCase

# tests.py
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from .models import User, Ride, RideEvent

class RideAPITests(APITestCase):
    def setUp(self):
        # Create admin user
        self.admin_user = User.objects.create_user(
            username='admin@test.com',
            email='admin@test.com',
            password='testpass123',
            role='admin',
            first_name='Admin',
            last_name='User'
        )
        
        # Create regular user
        self.regular_user = User.objects.create_user(
            username='user@test.com',
            email='user@test.com',
            password='testpass123',
            role='user',
            first_name='Regular',
            last_name='User'
        )
        
        # Create test ride
        self.ride = Ride.objects.create(
            status='en-route',
            id_rider=self.regular_user,
            id_driver=self.admin_user,
            pickup_latitude=37.7749,
            pickup_longitude=-122.4194,
            dropoff_latitude=37.7750,
            dropoff_longitude=-122.4195,
            pickup_time=timezone.now()
        )
        
        # Create ride events
        self.event_recent = RideEvent.objects.create(
            id_ride=self.ride,
            description='Recent event',
            created_at=timezone.now() - timedelta(hours=1)
        )
        
        self.event_old = RideEvent.objects.create(
            id_ride=self.ride,
            description='Old event',
            created_at=timezone.now() - timedelta(days=2)
        )
        
        # Set up API client
        self.client = APIClient()

    def test_unauthorized_access(self):
        """Test that unauthorized users cannot access the API"""
        response = self.client.get(reverse('ride-list'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_admin_access(self):
        """Test that non-admin users cannot access the API"""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(reverse('ride-list'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_access(self):
        """Test that admin users can access the API"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(reverse('ride-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ride_list_pagination(self):
        """Test ride list pagination"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(reverse('ride-list'))
        self.assertIn('count', response.data)
        self.assertIn('results', response.data)

    def test_ride_filtering(self):
        """Test ride filtering by status and rider email"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Test status filter
        response = self.client.get(f"{reverse('ride-list')}?status=en-route")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        
        # Test email filter
        response = self.client.get(
            f"{reverse('ride-list')}?rider_email={self.regular_user.email}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_distance_sorting(self):
        """Test sorting by distance to coordinates"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(
            f"{reverse('ride-list')}?sort_by=distance&latitude=37.7749&longitude=-122.4194"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_recent_events_only(self):
        """Test that only recent events are included"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(reverse('ride-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that only recent events are included
        ride_data = response.data['results'][0]
        events = ride_data['todays_ride_events']
        self.assertEqual(len(events), 1)  # Only the recent event
        self.assertEqual(events[0]['description'], 'Recent event')

    def test_create_ride(self):
        """Test ride creation"""
        self.client.force_authenticate(user=self.admin_user)
        ride_data = {
            'status': 'pickup',
            'id_rider': self.regular_user.id_user,
            'id_driver': self.admin_user.id_user,
            'pickup_latitude': 37.7749,
            'pickup_longitude': -122.4194,
            'dropoff_latitude': 37.7750,
            'dropoff_longitude': -122.4195,
            'pickup_time': timezone.now().isoformat()
        }
        response = self.client.post(reverse('ride-list'), ride_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_invalid_coordinates(self):
        """Test invalid coordinates handling"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(
            f"{reverse('ride-list')}?sort_by=distance&latitude=invalid&longitude=-122.4194"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)