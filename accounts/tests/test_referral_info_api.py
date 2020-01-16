"""Tests for referral-info API"""
from django.conf import settings

from rest_framework import status

from .base_test_class import BaseTest


class ReferralInfoTest(BaseTest):
    fixtures = ['01_core_users.json', '02_accounts_instructors.json', '03_accounts_parents.json',
                '04_accounts_students.json']

    def setUp(self):
        self.url = '{}/v1/referral-info/'.format(settings.HOSTNAME_PROTOCOL)

    def test_success_instructor(self):
        """Success request for instructor"""
        response = self.client.get(self.url + 'WVG3Kw4HaDhEpyag/')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertDictEqual({'displayName': 'Luis I.', 'avatar': ''}, response.json())

    def test_success_parent(self):
        """Success request for parent"""
        response = self.client.get(self.url + 'EljB8wAa40oDPUIt/')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertDictEqual({'displayName': 'Luis P.', 'avatar': ''}, response.json())

    def test_success_student(self):
        """Success request for student"""
        response = self.client.get(self.url + 'THoANSG6cV60dya1/')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertDictEqual({'displayName': 'Luis S.', 'avatar': ''}, response.json())

    def test_not_existent_token(self):
        """Request with non-existent token """
        response = self.client.get(self.url + 'ABC123def456ghi7/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
