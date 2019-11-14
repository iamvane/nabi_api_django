"""Tests for fetch-profile API"""
from django.conf import settings

from rest_framework import status

from .base_test_class import BaseTest


class FetchProfileInstructor(BaseTest):
    fixtures = ['01_core_users.json', '02_accounts_instructors.json']
    login_data = {
        'email': 'luisinstruct@yopmail.com',
        'password': 'T3st11ng'
    }

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/fetch-profile/'.format(settings.HOSTNAME_PROTOCOL)

    def test_instructor(self):
        """Test request to fetch profile API (instructor)"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(response.json(), {"bioTitle": "Music instructor",
                                           "bioDescription": "I'm a professional music instructor",
                                           "music": ["piano", "guitar"]}
                         )


class FetchProfileInstructorEmpty(BaseTest):
    fixtures = ['01_core_users.json', '02_accounts_instructors.json']
    login_data = {
        'email': 'luisinstruct2@yopmail.com',
        'password': 'T3st11ng'
    }

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/fetch-profile/'.format(settings.HOSTNAME_PROTOCOL)

    def test_instructor(self):
        """Test request to fetch profile API, for an instructor without data"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(response.json(), {"bioTitle": None, "bioDescription": None, "music": None})
