"""Tests for referral-email API"""
import json

from django.conf import settings

from rest_framework import status

from .base_test_class import BaseTest


class ReferralEmailTest(BaseTest):
    fixtures = ['01_core_users.json', '02_accounts_instructors.json']
    login_data = {
        'email': 'luisinstruct@yopmail.com',
        'password': 'T3st11ng'
    }

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/referral-email/'.format(settings.HOSTNAME_PROTOCOL)

    def test_instructor(self):
        """Test request to referral-email from current instructor"""
        response = self.client.post(self.url, data=json.dumps({'email': 'luistest1@yopmail.com'}),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())

    def test_instructor_wrong_email(self):
        """Test request to referral-email from logged instructor"""
        response = self.client.post(self.url, data=json.dumps({'email': 'luistest1-yopmail-com'}),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
