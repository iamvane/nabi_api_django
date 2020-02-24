"""Tests for ReferralDashboard"""
from decimal import Decimal

from django.conf import settings

from rest_framework import status

from .base_test_class import BaseTest


class ReferralDashboardTest(BaseTest):
    fixtures = ['01_core_users.json', '02_accounts_instructors.json', '03_accounts_parents.json',
                '04_accounts_students.json', '17_core_benefits.json']

    def setUp(self):
        self.url = '{}/v1/referral-dashboard/'.format(settings.HOSTNAME_PROTOCOL)

    def test_success(self):
        self.login_data = {'email': 'luisinstruct@yopmail.com', 'password': 'T3st11ng'}
        super().setUp()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        response_json = response.json()
        self.assertIsInstance(response_json, dict, response_json)
        self.assertEqual(response_json.get('totalAmount'), Decimal('10.0'), response_json)
        self.assertIsInstance(response_json.get('provider_list'), list, response_json)
        self.assertEqual(len(response_json.get('provider_list')), 2, response_json)
        for provider in response_json.get('provider_list'):
            self.assertIsNotNone(provider.get('name'), response_json)
            self.assertIsNotNone(provider.get('date'), response_json)
            self.assertIsNotNone(provider.get('source'), response_json)

    def test_empty_only_discount(self):
        """Test for user without amount benefits, only discount"""
        self.login_data = {'email': 'luisstudent@yopmail.com', 'password': 'T3st11ng'}
        super().setUp()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        response_json = response.json()
        self.assertIsInstance(response_json, dict, response_json)
        self.assertEqual(response_json.get('totalAmount'), Decimal('0.0'), response_json)
        self.assertIsInstance(response_json.get('provider_list'), list, response_json)
        self.assertEqual(len(response_json.get('provider_list')), 0, response_json)

    def test_empty_no_benefits(self):
        """Test for user without any benefit"""
        self.login_data = {'email': 'luisstudent2@yopmail.com', 'password': 'T3st11ng'}
        super().setUp()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        response_json = response.json()
        self.assertIsInstance(response_json, dict, response_json)
        self.assertEqual(response_json.get('totalAmount'), Decimal('0.0'), response_json)
        self.assertIsInstance(response_json.get('provider_list'), list, response_json)
        self.assertEqual(len(response_json.get('provider_list')), 0, response_json)
