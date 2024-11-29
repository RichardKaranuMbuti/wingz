from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from .models import User, Ride, RideEvent
from rest_framework_simplejwt.tokens import RefreshToken

class RideAPITests(APITestCase):
    def setUp(self):
        # Create admin user
        self.admin_user = User.objects.create_user(
            username='admin@test.com',
            email='admin@test.com',
            password='testpass123',
            role='admin',
            first_name='Admin',
            last_name='User',
            phone_number='1234567890'
        )
        
        # Create regular user
        self.regular_user = User.objects.create_user(
            username='user@test.com',
            email='user@test.com',
            password='testpass123',
            role='user',
            first_name='Regular',
            last_name='User',
            phone_number='0987654321'
        )
        
        # Create test ride
        self.ride = Ride.objects.create(
            status='pickup',
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

    def get_tokens_for_user(self, user):
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

    def test_user_registration(self):
        """Test user registration endpoint"""
        url = reverse('user-register')
        data = {
            'email': 'newuser@test.com',
            'role': 'user',
            'password': 'newpass123!',
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'User',
            'phone_number': '1234567899'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email='newuser@test.com').exists())

    def test_user_login(self):
        """Test user login and token generation"""
        url = reverse('token_obtain_pair')
        data = {
            'email': 'admin@test.com',
            'password': 'testpass123'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_unauthorized_access(self):
        """Test that unauthorized users cannot access the API"""
        response = self.client.get(reverse('ride-list'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_admin_access(self):
        """Test that non-admin users cannot access the API"""
        tokens = self.get_tokens_for_user(self.regular_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = self.client.get(reverse('ride-list'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_access(self):
        """Test that admin users can access the API"""
        tokens = self.get_tokens_for_user(self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = self.client.get(reverse('ride-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ride_list_pagination(self):
        """Test ride list pagination"""
        tokens = self.get_tokens_for_user(self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = self.client.get(f"{reverse('ride-list')}?page=1&page_size=10")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', response.data)
        self.assertIn('results', response.data)

    def test_ride_filtering(self):
        """Test ride filtering by status and rider email"""
        tokens = self.get_tokens_for_user(self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        
        # Test status filter
        response = self.client.get(f"{reverse('ride-list')}?status=pickup")
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
        tokens = self.get_tokens_for_user(self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = self.client.get(
            f"{reverse('ride-list')}?sort_by=distance&latitude=37.7749&longitude=-122.4194"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_recent_events_only(self):
        """Test that only recent events are included"""
        tokens = self.get_tokens_for_user(self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = self.client.get(reverse('ride-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        ride_data = response.data['results'][0]
        self.assertIn('todays_ride_events', ride_data)
        events = ride_data['todays_ride_events']
        self.assertEqual(len(events), 1)  # Only the recent event
        self.assertEqual(events[0]['description'], 'Recent event')

    def test_create_ride(self):
        """Test ride creation"""
        tokens = self.get_tokens_for_user(self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        ride_data = {
            'status': 'pickup',
            'id_rider': self.regular_user.id,
            'id_driver': self.admin_user.id,
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
        tokens = self.get_tokens_for_user(self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = self.client.get(
            f"{reverse('ride-list')}?sort_by=distance&latitude=invalid&longitude=-122.4194"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_ride(self):
        """Test ride update"""
        tokens = self.get_tokens_for_user(self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        update_data = {
            'status': 'en-route'
        }
        response = self.client.patch(
            reverse('ride-detail', kwargs={'pk': self.ride.pk}),
            update_data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'en-route')

    def test_delete_ride(self):
        """Test ride deletion"""
        tokens = self.get_tokens_for_user(self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = self.client.delete(
            reverse('ride-detail', kwargs={'pk': self.ride.pk})
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Ride.objects.filter(pk=self.ride.pk).exists())