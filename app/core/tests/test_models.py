"""
Test for models
"""

from django.test import TestCase
from django.contrib.auth import get_user_model


class ModelTest(TestCase):
    """ Test models """

    def test_create_user_with_email_successful(self):
        """ Testing creatinga new user with email succesfully """
        email = "test@example.com"
        password = "Test123123"
        user = get_user_model().objects.create_user(
            email=email,
            password=password,
        )

        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))

    def test_new_user_email_normalized(self):
        """ Test email is normalized for new users """
        sample_emails = [
            ['test1@EXAMPLE.com', 'test1@example.com', ],
            ['Test2@Example.com', 'Test2@example.com', ],
            ['TEST3@EXAMPLE.COM', 'TEST3@example.com', ],
            ['test4@example.COM', 'test4@example.com', ],
        ]

        for email, expected in sample_emails:
            user = get_user_model().objects.create_user(
                email,
                password="password"
            )

            self.assertTrue(user.email, expected)

    def test_new_user_with_email_raises_error(self):
        """ Creating an user without email raises value error"""
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user('', 'test123')

    def test_create_superuser(self):
        """ Test creating a superuser """
        user = get_user_model().objects.create_superuser(
            'Test@example.com',
            'Test123',
        )
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
