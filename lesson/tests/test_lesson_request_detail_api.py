import json

from django.conf import settings

from rest_framework import status

from accounts.tests.base_test_class import BaseTest

from ..models import LessonRequest


class LessonRequestDeleteTest(BaseTest):
    """Tests for delete lesson requests"""
    fixtures = ['01_core_users.json', '03_accounts_parents.json', '04_accounts_students.json',
                '05_lesson_instruments.json', '15_accounts_tiedstudents', '16_accounts_studentdetails',
                '01_lesson_requests.json']
    login_data = {
        'email': 'luisstudent@yopmail.com',
        'password': 'T3st11ng'
    }

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/lesson-request-item/'.format(settings.HOSTNAME_PROTOCOL)
        self.qty = LessonRequest.objects.count()

    def test_success(self):
        """Delete lesson request successfully"""
        response = self.client.delete(self.url + '1/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(LessonRequest.objects.count(), self.qty - 1)

    def test_fail(self):
        """Fail in deletion of lesson request, because id don't exists"""
        response = self.client.delete(self.url + '15/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(LessonRequest.objects.count(), self.qty)
