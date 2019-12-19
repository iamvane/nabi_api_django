import json

from django.conf import settings

from rest_framework import status

from accounts.tests.base_test_class import BaseTest

from ..models import Application


class ApplicationCreateTest(BaseTest):
    """Tests for create an application at a lesson request"""
    fixtures = ['01_core_users.json', '02_accounts_instructors.json', '03_accounts_parents.json',
                '04_accounts_students.json', '05_lesson_instruments.json', '15_accounts_tiedstudents',
                '16_accounts_studentdetails', '01_lesson_requests.json']
    login_data = {
        'email': 'luisinstruct@yopmail.com',
        'password': 'T3st11ng'
    }

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/applications/'.format(settings.HOSTNAME_PROTOCOL)
        self.qty = Application.objects.count()

    def test_success(self):
        """Successful creation of application"""
        response = self.client.post(self.url,
                                    data=json.dumps({"requestId": 1, "rate": "40.00",
                                                     "message": "Hello, I can provide the teaching lessons"}),
                                    content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(Application.objects.count(), self.qty + 1)

    def test_fail(self):
        """Failed creation of application, by missing rate value"""
        response = self.client.post(self.url,
                                    data=json.dumps({'requestId': 1,
                                                     'message': "Hello, I can provide the teaching lessons"}),
                                    content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
        self.assertEqual(Application.objects.count(), self.qty)
