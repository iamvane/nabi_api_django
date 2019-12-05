"""Tests for references API"""
import operator

from django.conf import settings

from rest_framework import status

from accounts.tests.base_test_class import BaseTest


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
