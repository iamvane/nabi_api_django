"""Tests for references API"""
from django.conf import settings
from django.contrib.auth import get_user_model

from rest_framework import status

from accounts.tests.base_test_class import BaseTest

User = get_user_model()


class InstructorRegisterReferencesTest(BaseTest):
    fixtures = ['01_core_users.json', ]
    login_data = {
        'email': 'luisinstruct@yopmail.com',
        'password': 'T3st11ng'
    }

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/request-references/'.format(settings.HOSTNAME_PROTOCOL)

    def test_register_references(self):
        """Test registration of references"""
        user = User.objects.get(email=self.login_data['email'])
        self.assertEqual(user.reference_requests.count(), 0)
        response = self.client.post(self.url, data={'emails': ["luistest003@yopmail.com", "luistest005@yopmail.com"]})
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(user.reference_requests.count(), 2)


class InstructorReferencesListTest(BaseTest):
    fixtures = ['01_core_users.json', '01_referencerequests.json']
    login_data = {
        'email': 'luisinstruct@yopmail.com',
        'password': 'T3st11ng'
    }

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/references-list/'.format(settings.HOSTNAME_PROTOCOL)

    def test_get_list(self):
        """Test getting data list"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        list_response = response.json()['emails']
        list_response.sort()
        self.assertListEqual(list_response, ["luistest003@yopmail.com", "luistest005@yopmail.com"])
