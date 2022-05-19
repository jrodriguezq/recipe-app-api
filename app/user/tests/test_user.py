"""
Tests for the user API
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status


CREATE_USER_URL = reverse('user:create')
TOKEN_URL = reverse('user:token')
ME_URL = reverse('user:me')


def create_user(**params):
    """ Helper to create new user """
    return get_user_model().objects.create_user(**params)


class PublicUserAPITest(TestCase):
    """ Test public features of user API """

    def setUp(self):
        self.client = APIClient()

    def test_create_user_success(self):
        """ Test creating a user is succesful """
        payload = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'name': 'Nombre',
        }
        res = self.client.post(CREATE_USER_URL, payload)
        user = get_user_model().objects.get(email=payload['email'])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(user.check_password(payload['password']))
        self.assertNotIn('password', res.data)

    def test_user_with_email_exist_error(self):
        """ Check that a new user with existing user throws ex """
        payload = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'name': 'Nombre',
        }
        create_user(**payload)

        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_too_short_error(self):
        """ Test ex when password is too short """
        payload = {
            'email': 'test@example.com',
            'password': 'pw',
            'name': 'Nombre',
        }

        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        user_exists = get_user_model().objects.filter(
            email=payload['email']
        ).exists()

        self.assertFalse(user_exists)

    def test_create_token_for_user(self):
        """ Create token for valid credentials """
        create_user_payload = {
            'email': 'test@example.com',
            'password': 'TestPassword123',
            'name': 'Nombre',
        }
        create_user(**create_user_payload)
        login_payload = {
            'email': create_user_payload['email'],
            'password': create_user_payload['password'],
        }
        res = self.client.post(TOKEN_URL, login_payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('token', res.data)

    def test_create_token_bad_user(self):
        """ Test token for invalid credentials """
        create_user_payload = {
            'email': 'test@example.com',
            'password': 'TestPassword123',
            'name': 'Nombre',
        }
        create_user(**create_user_payload)
        bad_login_payload = {
            'email': create_user_payload['email'],
            'password': '123123123',
        }
        res = self.client.post(TOKEN_URL, bad_login_payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('token', res.data)

    def test_create_token_blank_password(self):
        """ Test token for invalid credentials """
        create_user_payload = {
            'email': 'test2@example.com',
            'password': 'TestPassword123',
            'name': 'Nombre',
        }
        create_user(**create_user_payload)
        bad_login_payload = {
            'email': create_user_payload['email'],
            'password': '',
        }
        res = self.client.post(TOKEN_URL, bad_login_payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('token', res.data)

    def test_retrieve_user_unauthorized(self):
        """ Test authentication is required for users """
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateUserTest(TestCase):
    """ Test API request that require authentication """

    def setUp(self):
        self.user = create_user(
            email='test@example.com',
            password='TestPassword123',
            name='Nombre',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_profile_success(self):
        """ Test for retrieving authenticated user """
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, {
            'name': self.user.name,
            'email': self.user.email
        })

    def test_post_me_not_allowed(self):
        """ Test Post is not allowed at ME endpoint """
        res = self.client.post(ME_URL, {})

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_user_profile(self):
        """ Test authenticated user can update self """
        payload = {
            'name': 'UpdatedName',
            'password': 'newPassword123'
        }

        res = self.client.patch(ME_URL, payload)
        self.user.refresh_from_db()

        self.assertEqual(self.user.name, payload['name'])
        self.assertTrue(self.user.check_password(payload['password']))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
