"""Tests for login with existing account"""
import json

from django.conf import settings

from rest_framework import status
from rest_framework.test import APITestCase


class LoginInstructorTest(APITestCase):
    fixtures = ['01_core_users.json', '02_accounts_instructors.json']

    def setUp(self):
        self.url = '{}/v1/login/'.format(settings.HOSTNAME_PROTOCOL)
        self.payload = {
            "email": "luisinstruct@yopmail.com",
            "password": "T3st11ng",
        }
        self.payload_wrong_pass = {
            "email": "luisinstruct@yopmail.com",
            "password": "probando",
        }

    def test_login(self):
        """Test login instructor"""
        response = self.client.post(self.url, data=json.dumps(self.payload), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())

    def test_failed_login(self):
        """Test failed login instructor"""
        response = self.client.post(self.url, data=json.dumps(self.payload_wrong_pass), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())


class LoginStudentTest(APITestCase):
    fixtures = ['01_core_users.json', '04_accounts_students.json']

    def setUp(self):
        self.url = '{}/v1/login/'.format(settings.HOSTNAME_PROTOCOL)
        self.payload = {
            "email": "luisstudent@yopmail.com",
            "password": "T3st11ng",
        }
        self.payload_wrong_pass = {
            "email": "luisstudent@yopmail.com",
            "password": "probando",
        }

    def test_login(self):
        """Test login student"""
        response = self.client.post(self.url, data=json.dumps(self.payload), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())

    def test_failed_login(self):
        """Test failed login student"""
        response = self.client.post(self.url, data=json.dumps(self.payload_wrong_pass), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())


class LoginParentTest(APITestCase):
    fixtures = ['01_core_users.json', '03_accounts_parents.json']

    def setUp(self):
        self.url = '{}/v1/login/'.format(settings.HOSTNAME_PROTOCOL)
        self.payload = {
            "email": "luisparent@yopmail.com",
            "password": "T3st11ng",
        }
        self.payload_wrong_pass = {
            "email": "luisparent@yopmail.com",
            "password": "probando",
        }

    def test_login(self):
        """Test login parent"""
        response = self.client.post(self.url, data=json.dumps(self.payload), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())

    def test_failed_login(self):
        """Test failed login parent"""
        response = self.client.post(self.url, data=json.dumps(self.payload_wrong_pass), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
