"""
Tests for the user API
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status


CREATE_USER_URL = reverse('user:create')


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
