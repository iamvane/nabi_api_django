"""Tests for Minimal Instructor Rate Lesson"""
from django.conf import settings

from rest_framework import status

from .base_test_class import BaseTest


class MinimalRateTest(BaseTest):
    fixtures = ['01_core_users.json', '02_accounts_instructors.json', '12_accounts_instructorlessonrates.json']
    login_data = {
        'email': 'luisstudent@yopmail.com',
        'password': 'T3st11ng'
    }

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/minimal-rate/'.format(settings.HOSTNAME_PROTOCOL)

    def test_get_data(self):
        """Test getting data"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        data_dict = response.json()
        self.assertDictEqual(data_dict, {'minRate': 20.0})


class MinimalRateEmptyTest(BaseTest):
    fixtures = ['01_core_users.json', '02_accounts_instructors.json']
    login_data = {
        'email': 'luisstudent@yopmail.com',
        'password': 'T3st11ng'
    }

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/minimal-rate/'.format(settings.HOSTNAME_PROTOCOL)

    def test_get_data(self):
        """Test getting data"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        data_dict = response.json()
        self.assertDictEqual(data_dict, {'minRate': None})
