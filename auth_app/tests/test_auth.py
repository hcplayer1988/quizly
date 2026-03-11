"""Tests for authentication API endpoints."""
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class AuthTestCase(APITestCase):
    """Base setup shared across all auth tests."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')
        self.refresh_url = reverse('token_refresh')

    def _login(self):
        """Helper: login and return response with cookies set on client."""
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'testpassword123'
        })
        return response

    def _set_auth_cookies(self):
        """Helper: login and set cookies on client for authenticated requests."""
        refresh = RefreshToken.for_user(self.user)
        self.client.cookies['access_token'] = str(refresh.access_token)
        self.client.cookies['refresh_token'] = str(refresh)


class RegisterTests(AuthTestCase):

    def test_register_success(self):
        response = self.client.post(self.register_url, {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'newpassword123',
            'confirmed_password': 'newpassword123'
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['detail'], 'User created successfully!')

    def test_register_passwords_do_not_match(self):
        response = self.client.post(self.register_url, {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'password123',
            'confirmed_password': 'different123'
        })
        self.assertEqual(response.status_code, 400)

    def test_register_duplicate_email(self):
        response = self.client.post(self.register_url, {
            'username': 'anotheruser',
            'email': 'test@example.com',
            'password': 'password123',
            'confirmed_password': 'password123'
        })
        self.assertEqual(response.status_code, 400)

    def test_register_missing_fields(self):
        response = self.client.post(self.register_url, {
            'username': 'newuser'
        })
        self.assertEqual(response.status_code, 400)


class LoginTests(AuthTestCase):

    def test_login_success(self):
        response = self._login()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['detail'], 'Login successfully!')
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], 'testuser')
        self.assertIn('access_token', response.cookies)
        self.assertIn('refresh_token', response.cookies)

    def test_login_wrong_password(self):
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 401)

    def test_login_nonexistent_user(self):
        response = self.client.post(self.login_url, {
            'username': 'nobody',
            'password': 'password123'
        })
        self.assertEqual(response.status_code, 401)

    def test_login_missing_credentials(self):
        response = self.client.post(self.login_url, {})
        self.assertEqual(response.status_code, 400)


class LogoutTests(AuthTestCase):

    def test_logout_success(self):
        self._set_auth_cookies()
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Log-Out successfully!', response.data['detail'])

    def test_logout_no_refresh_token(self):
        self._set_auth_cookies()
        del self.client.cookies['refresh_token']
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data['detail'], 'Refresh token not found!')

    def test_logout_unauthenticated(self):
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, 401)

    def test_logout_invalid_refresh_token(self):
        self._set_auth_cookies()
        self.client.cookies['refresh_token'] = 'invalidtoken'
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, 401)


class TokenRefreshTests(AuthTestCase):

    def test_refresh_success(self):
        self._set_auth_cookies()
        response = self.client.post(self.refresh_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['detail'], 'Token refreshed')
        self.assertIn('access_token', response.cookies)

    def test_refresh_no_cookie(self):
        response = self.client.post(self.refresh_url)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data['detail'], 'Refresh token not found!')

    def test_refresh_invalid_token(self):
        self.client.cookies['refresh_token'] = 'invalidtoken'
        response = self.client.post(self.refresh_url)
        self.assertEqual(response.status_code, 401)
        
