import json
from datetime import timedelta

from django.conf import settings
from django.utils.timezone import now

from rest_framework import status

from accounts.tests.base_test_class import BaseTest

from ..models import GradedLesson


class GradeLessonTest(BaseTest):
    """Tests for grade a lesson belong to a booking"""
    fixtures = ['01_core_users.json', '02_accounts_instructors.json', '03_accounts_parents.json',
                '04_accounts_students.json', '05_lesson_instruments.json', '15_accounts_tiedstudents',
                '16_accounts_studentdetails', '01_lesson_requests.json', '02_applications.json',
                '03_instruments', '04_lesson_bookings.json', '01_payments.json']
    login_data = {
        'email': 'luisinstruct@yopmail.com',
        'password': 'T3st11ng'
    }

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/lesson-grade/'.format(settings.HOSTNAME_PROTOCOL)
        self.qty = GradedLesson.objects.count()

    def test_success(self):
        """Grade a lesson successfully"""
        response = self.client.post(self.url + '1/',
                                    data=json.dumps({'date': '2020-01-03', 'grade': 2,
                                                     'comment': 'Something', 'studentName': 'John'}),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertDictEqual(response.json(), {"message": "success"})
        self.assertEqual(GradedLesson.objects.count(), self.qty + 1)

    def test_error_booking_not_exist(self):
        """Error providing booking_id from not existent booking"""
        response = self.client.post(self.url + '5/',
                                    data=json.dumps({'date': '2020-01-03', 'grade': 2,
                                                     'comment': 'Something', 'studentName': 'John'}),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
        self.assertDictEqual(response.json(), {"message": "There is no Lesson Booking with provided id"})

    def test_error_date(self):
        """Wrong value for date parameter"""
        today = now().date() + timedelta(days=5)
        response = self.client.post(self.url + '1/',
                                    data=json.dumps({'date': today.strftime('%Y-%m-%d'), 'grade': 2,
                                                     'comment': 'Something', 'studentName': 'John'}),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
        self.assertIsNotNone(response.json().get('date'))

    def test_error_missing_grade(self):
        """Error missing grade value parameter"""
        response = self.client.post(self.url + '1/',
                                    data=json.dumps({'date': '2020-01-03', 'comment': 'Something',
                                                     'studentName': 'John'}),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
        self.assertIsNotNone(response.json().get('grade'))
