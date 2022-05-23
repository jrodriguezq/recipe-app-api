"""
Tests for the ingredient API
"""
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Ingredient
from recipe.serializers import IngredientSerializer


INGREDIENT_URL = reverse('recipe:ingredient-list')


def create_user(email='user@example.com', password='Testpass123'):
    return get_user_model().objects.create_user(email=email, password=password)


class PublicIngredientAPITest(TestCase):
    """ Test unauthenticated Ingredient request """

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """ Test auth is requried to retrieve ingredients """
        res = self.client.get(INGREDIENT_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientAPITest(TestCase):
    """ Test authenticated API request """

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredients(self):
        """ Retrieving a list of engridients """
        Ingredient.objects.create(user=self.user, name='Repollo')
        Ingredient.objects.create(user=self.user, name='Lechuga')

        res = self.client.get(INGREDIENT_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)

        self.assertEqual(res.data, serializer.data)

    def test_ingredient_limited_to_user(self):
        """ Test that list of ingredient is limited to user """
        user2 = create_user(email='test@example.com', password='SomePassword')
        Ingredient.objects.create(user=user2, name='Aji')

        ingredient = Ingredient.objects.create(user=self.user, name='Palta')

        res = self.client.get(INGREDIENT_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res[0]['name'], ingredient.name)
        self.assertEqual(res[0]['id'], ingredient.id)
