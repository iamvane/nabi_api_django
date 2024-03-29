"""Test for affiliate registration"""
import json

from django.conf import settings
from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APITestCase

from ..models import Affiliate

User = get_user_model()


class CreateAffiliateTest(APITestCase):
    def setUp(self):
        self.url = '{}/v1/registration-affiliate/'.format(settings.HOSTNAME_PROTOCOL)
        self.payload = {
            "email": "affiliate020@yopmail.com",
            "password": "123456",
            "firstName": "Afiliado",
            "lastName": "Veinte",
            "birthday": "1992-05-24",
            "companyName": "Enterprise Inc",
        }
        self.payload_minimum = {
            "email": "affiliate020@yopmail.com",
            "password": "123456",
            "birthday": "1992-05-24",
        }
        self.payload_missing_birthdate = {
            "email": "affiliate021@yopmail.com",
            "password": "123456",
            "firstName": "Afiliado",
            "lastName": "Veinteyuno",
            "companyName": "Enterprise Inc",
        }
        self.payload_repeated = {
            "email": "affiliate020@yopmail.com",
            "password": "123456",
            "firstName": "Afiliado",
            "lastName": "OtroVeinte",
            "birthday": "1990-07-19",
            "companyName": "Enterprise Inc",
        }

    def test_create_affiliate(self):
        """Test affiliate creation"""
        response = self.client.post(self.url, data=json.dumps(self.payload), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertTrue(User.objects.filter(email=self.payload['email']).exists())
        self.assertTrue(User.objects.filter(username=self.payload['email']).exclude(referral_token='').exists())
        user_id = User.objects.get(username=self.payload['email']).id
        self.assertTrue(Affiliate.objects.filter(user_id=user_id, company_name=self.payload['companyName']).exists())

    def test_create_affiliate_minimum_data(self):
        """Test affiliate creation with minimun data"""
        response = self.client.post(self.url, data=json.dumps(self.payload_minimum), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertTrue(User.objects.filter(email=self.payload['email']).exists())
        self.assertTrue(User.objects.filter(username=self.payload['email']).exclude(referral_token='').exists())
        user_id = User.objects.get(username=self.payload['email']).id
        self.assertTrue(Affiliate.objects.filter(user_id=user_id).exists())

    def test_create_affiliate_missing_birthdate(self):
        """Test affiliate creation"""
        response = self.client.post(self.url, data=json.dumps(self.payload_missing_birthdate),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())

    def test_create_affiliate_twice(self):
        """Test affiliate creation twice (same email)"""
        response = self.client.post(self.url, data=json.dumps(self.payload), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        response = self.client.post(self.url, data=json.dumps(self.payload_repeated), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
