"""Tests for forgot password API"""

import json

from django.conf import settings

from rest_framework import status
from rest_framework.test import APITestCase

from core.models import User, UserToken


class ResetPasswordInstructorTest(APITestCase):
    fixtures = ['01_core_users.json', '02_accounts_instructors.json']

    def setUp(self):
        self.url = '{}/v1/forgot-password/'.format(settings.HOSTNAME_PROTOCOL)
        self.data = {
            'email': 'luisinstruct@yopmail.com'
        }
        self.data_non_existent = {
            'email': 'luisinstruct88@yopmail.com'
        }

    def test_forgot_password(self):
        """Test request to reset password for instructor"""
        response = self.client.post(self.url, data=json.dumps(self.data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertTrue(User.objects.filter(email=self.data['email']).exists())
        self.assertTrue(UserToken.objects.filter(user=User.objects.get(email=self.data['email'])).exists())

    def test_forgot_password_non_existent(self):
        """Test request to reset password for non existent instructor"""
        response = self.client.post(self.url, data=json.dumps(self.data_non_existent), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertFalse(User.objects.filter(email=self.data_non_existent['email']).exists())


class SetPasswordInstructorTest(APITestCase):
    fixtures = ['01_core_users.json', '02_accounts_instructors.json']

    def setUp(self):
        self.data = {'email': 'luisinstruct@yopmail.com'}
        url = '{}/v1/forgot-password/'.format(settings.HOSTNAME_PROTOCOL)
        response = self.client.post(url, data=json.dumps(self.data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertTrue(UserToken.objects.filter(user=User.objects.get(email=self.data['email'])).exists())
        token = UserToken.objects.get(user=User.objects.get(email=self.data['email'])).token
        self.url = '{}/v1/forgot-password/?token={}'.format(settings.HOSTNAME_PROTOCOL, token)

    def test_set_password(self):
        """Test request to set password for instructor"""
        new_pass_dic = {'password': 'Prueba12345'}
        response = self.client.put(self.url, data=json.dumps(new_pass_dic), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        login_url = '{}/v1/login/'.format(settings.HOSTNAME_PROTOCOL)
        login_data = self.data.copy()
        login_data.update(new_pass_dic)
        response = self.client.post(login_url, data=json.dumps(login_data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())

    def test_failed_set_password(self):
        """Test failed request to set password for instructor"""
        new_pass_dic = {'password': 'Prueba12345'}
        url = self.url[:-4]
        response = self.client.put(url, data=json.dumps(new_pass_dic), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
