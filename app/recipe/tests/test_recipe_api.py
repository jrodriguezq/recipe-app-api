"""
Tests for Recipe API
"""

from decimal import Decimal
import tempfile
import os

from PIL import Image

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Tag, Ingredient
from recipe.serializers import RecipeSerializer, RecipeDetailSerializer, IngredientSerializer


RECIPES_URL = reverse('recipe:recipe-list')


def detailt_url(recipe_id):
    """ Create and return a recipe detail url """

    return reverse('recipe:recipe-detail', args=[recipe_id])


def image_upload_url(recipe_id):
    """ Create and return an image upload URL """
    return reverse('recipe:recipe-upload-image', args=[recipe_id])


def create_recipe(user, **params):
    """ Create and return a sample recipe """
    defaults = {
        'title': 'Sample Title',
        'time_minutes': '22',
        'price': Decimal('10.69'),
        'description': 'Sample description long long long',
        'link': 'https://google.com',
    }
    defaults.update(params)

    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe


def create_user(**params):
    """ Create and return a new user """
    return get_user_model().objects.create_user(**params)


class PublicRecipeAPITests(TestCase):
    """ Test unauthenticated API request """

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """ Test auth is required to use API """
        res = self.client.get(RECIPES_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeAPITests(TestCase):
    """ Test authenticated API request """

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            email='test@example.com',
            password='TestPass123'
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        """ Test retriving a list of recipes """
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipe_list_limited_to_user(self):
        """ Test list of recipes is limited to authenticated user """
        other_user = create_user(
            email='second@example.com',
            password='pass123'
        )
        create_recipe(user=other_user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_recipe_detail(self):
        """ Test get recipe details """
        recipe = create_recipe(user=self.user)

        url = detailt_url(recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):
        """ Test creating a recipe """
        payload = {
            'title': 'Sample Title',
            'time_minutes': 22,
            'price': Decimal('10.69')
        }
        res = self.client.post(RECIPES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_partial_update(self):
        """ Test partial update of a recipe """
        original_link = 'https://link1.com'
        recipe = create_recipe(
            user=self.user,
            title='Sample Title',
            link=original_link,
        )
        payload = {'title': 'Another Recipe Title'}
        url = detailt_url(recipe.id)

        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        """ Test full update of recipe"""
        recipe = create_recipe(
            user=self.user,
            title='Sample Title',
            link='Sample title',
            description='Sample description'
        )
        payload = {
            'title': 'Best Title ever',
            'link': 'https://hackerrank.com',
            'description': 'new description :D',
            'time_minutes': 10,
            'price': Decimal('8.0')
        }
        me_url = detailt_url(recipe.id)
        res = self.client.put(me_url, payload)
        recipe.refresh_from_db()

        for key, value in payload.items():
            self.assertEqual(getattr(recipe, key), value)
            self.assertEqual(recipe.user, self.user)

    def test_update_user_returns_error(self):
        """ Test changing user in recipe returns in error """
        new_user = create_user(
            email='new_user@example.com',
            password='password'
        )
        recipe = create_recipe(
            user=self.user,
            title='title',
            description='desc'
        )
        url = detailt_url(recipe.id)

        res = self.client.patch(url, {'user': new_user.id})
        recipe.refresh_from_db()

        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        """ Test deleting a recipe sucessful """
        recipe = create_recipe(user=self.user)
        url = detailt_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_other_user_recipe_error(self):
        """ Another user trying to delete throw error """
        new_user = create_user(email='asd@example.com', password='123')
        recipe = create_recipe(new_user)
        url = detailt_url(recipe.id)

        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_create_recipe_with_new_tags(self):
        """ Test creating a recipe with new tags """
        payload = {
            'title': 'Thai pad',
            'time_minutes': 30,
            'price': Decimal('99.99'),
            'tags': [
                {'name': 'Thai'},
                {'name': 'Wok'}
            ]
        }

        res = self.client.post(RECIPES_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                user=self.user, name=tag['name']
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_tags(self):
        """ Tests creating a recipe with existing tags """
        tag = Tag.objects.create(user=self.user, name='Vintage')
        payload = {
            'title': 'Old school burger',
            'time_minutes': 15,
            'price': Decimal('99.99'),
            'tags': [
                {'name': 'Vintage'},
                {'name': 'Wok'},
            ],
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag, recipe.tags.all())
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_tag_on_update(self):
        """ Test creating a tag when updating recipe """
        recipe = create_recipe(user=self.user)
        payload = {
            'tags': [
                {'name': 'lunch'}
            ]
        }
        url = detailt_url(recipe.id)

        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user=self.user, name='lunch')

        self.assertIn(new_tag, recipe.tags.all())

    def test_update_recipe_asign_tag(self):
        """ Asigning an existing tag when updating recipe """
        tag_breakfast = Tag.objects.create(user=self.user, name='Breakfast')
        recipe = create_recipe(user=self.user)

        recipe.tags.add(tag_breakfast)

        tag_lunch = Tag.objects.create(user=self.user, name='Lunch')

        payload = {'tags': [{'name': 'Lunch'}]}

        url = detailt_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(tag_lunch, recipe.tags.all())
        self.assertNotIn(tag_breakfast, recipe.tags.all())

    def test_clear_recipe_tags(self):
        """ Test clearing a recipe tags """
        tag = Tag.objects.create(user=self.user, name='Dessert')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag)

        payload = {'tags': []}
        url = detailt_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)

    def test_create_recipe_with_new_ingredient(self):
        """ Test creating a recipe with new ingredients """
        payload = {
            'title': 'My tacos',
            'time_minutes': 60,
            'price': Decimal('9.99'),
            'ingredients': [
                {'name': 'Meat'},
                {'name': 'Tortilla'}
            ]
        }
        res = self.client.post(RECIPES_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingredient['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_ingredent(self):
        """ Test creating a new recipe with existing ingredient """
        ingredient = Ingredient.objects.create(user=self.user, name='Avocado')
        payload = {
            'title': 'Avocado toast',
            'time_minutes': 5,
            'price': Decimal('9.99'),
            'ingredients': [
                {'name': 'Avocado'},
                {'name': 'Toast'}
            ]
        }
        res = self.client.post(RECIPES_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertIn(ingredient, recipe.ingredients.all())
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingredient['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_ingredient_on_update(self):
        """ Test creating an ingredient when updating recipe """
        recipe = create_recipe(user=self.user)
        payload = {'ingredients': [{'name': 'Avocado'}]}
        url = detailt_url(recipe.id)

        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        new_ingredient = Ingredient.objects.get(user=self.user, name='Avocado')
        self.assertIn(new_ingredient, recipe.ingredients.all())

    def test_update_recipe_asign_ingredient(self):
        """ Test asigning an eisting ingredient when creating a recipe """
        ingredient1 = Ingredient.objects.create(user=self.user, name='Salt')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient1)

        ingredient2 = Ingredient.objects.create(user=self.user, name='Chilly')
        payload = {'ingredients': [{'name': 'Chilly'}]}
        url = detailt_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(ingredient2, recipe.ingredients.all())
        self.assertNotIn(ingredient1, recipe.ingredients.all())

    def test_clear_recipe_ingredients(self):
        """ Test clearing a recipe ingredients """
        ingredient = Ingredient.objects.create(user=self.user, name='Bread')
        recipe = create_recipe(self.user)
        recipe.ingredients.add(ingredient)

        payload = {'ingredients': []}
        url = detailt_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 0)

    def test_filter_by_tags(self):
        """ Test filtering recipes by tag """
        r1 = create_recipe(user=self.user, title='Plain rice')
        r2 = create_recipe(user=self.user, title='Curry')
        tag1 = Tag.objects.create(user=self.user, name='Spicy')
        tag2 = Tag.objects.create(user=self.user, name='Mild')
        r1.tags.add(tag1)
        r2.tags.add(tag2)
        r3 = create_recipe(user=self.user, title='Fish and Chips')

        params = {'tags': f'{tag1.id},{tag2.id}'}
        res = self.client.get(RECIPES_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)

        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)

    def test_filter_by_ingredients(self):
        """ Test filtering recipes by ingredients """
        r1 = create_recipe(user=self.user, title='Fried Chicken')
        r2 = create_recipe(user=self.user, title='Boil Goose')
        r3 = create_recipe(user=self.user, title='Not Chicken')
        ingredient1 = Ingredient.objects.create(user=self.user, name='Chicken')
        ingredient2 = Ingredient.objects.create(user=self.user, name='Goose')
        r1.ingredients.add(ingredient1)
        r2.ingredients.add(ingredient2)

        params = {'ingredients': f'{ingredient1.id},{ingredient2.id}'}
        res = self.client.get(RECIPES_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)

        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)


class ImageUploadTests(TestCase):
    """ Tests for upload image API """

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'user@example.com',
            'password'
        )
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user=self.user)

    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_image(self):
        """ Test uploading an image to a recipe """
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            img = Image.new('RGB', (10, 10))
            img.save(image_file, format='JPEG')
            image_file.seek(0)
            payload = {'image': image_file}
            res = self.client.post(url, payload, format='multipart')

        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):
        """ Test uploading invalid image """
        url = image_upload_url(self.recipe.id)
        payload = {'image': 'not an image'}

        res = self.client.post(url, payload, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
