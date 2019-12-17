import json

from django.conf import settings

from rest_framework import status

from accounts.tests.base_test_class import BaseTest

from ..models import LessonRequest


class LessonRequestCreateTest(BaseTest):
    """Tests for create lesson requests"""
    fixtures = ['01_core_users.json', '03_accounts_parents.json', '04_accounts_students.json',
                '05_lesson_instruments.json', '15_accounts_tiedstudents', '16_accounts_studentdetails', ]
    student_login_data = {
        'email': 'luisstudent@yopmail.com',
        'password': 'T3st11ng'
    }
    parent_login_data = {
        'email': 'luisparent@yopmail.com',
        'password': 'T3st11ng'
    }
    student_data = {
        'requestTitle': "Guitar Instructor needed in Boston MA",
        'instrument': "guitar",
        'placeForLessons': "home",
        'skillLevel': "beginner",
        'lessonDuration': "45mins",
        'requestMessage': "Hello I am looking for a guitar instructor"
    }
    parent_data = {
        'students': [
            {
                'name': 'Santiago',
                'age': 9,
            },
            {
                'name': 'Teresa',
                'age': 7,
            }
        ],
        'requestTitle': "Piano Instructor needed in Boston MA",
        'instrument': "piano",
        'placeForLessons': "home",
        'skillLevel': "beginner",
        'lessonDuration': "60mins",
        'requestMessage': "My twins want to take piano lessons together"
    }

    def setUp(self):
        self.url = '{}/v1/lesson-request/'.format(settings.HOSTNAME_PROTOCOL)
        self.qty = LessonRequest.objects.count()

    def test_student_success(self):
        """Create a lesson request successfully, by an student"""
        self.login_data = self.student_login_data
        super().setUp()
        response = self.client.post(self.url, data=json.dumps(self.student_data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(LessonRequest.objects.count(), self.qty + 1)

    def test_parent_success(self):
        """Create a lesson request successfully, by a parent"""
        self.login_data = self.parent_login_data
        super().setUp()
        response = self.client.post(self.url, data=json.dumps(self.parent_data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(LessonRequest.objects.count(), self.qty + 1)

    def test_missing_data(self):
        """Fail with creation of lesson request, because data is missing"""
        self.login_data = self.student_login_data
        super().setUp()
        # test without requestTitle
        data = self.student_data.copy()
        data.pop('requestTitle')
        response = self.client.post(self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
        # test without instrument
        data = self.student_data.copy()
        data.pop('instrument')
        response = self.client.post(self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
        # test without placeForLessons
        data = self.student_data.copy()
        data.pop('placeForLessons')
        response = self.client.post(self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
        # test without skillLevel
        data = self.student_data.copy()
        data.pop('skillLevel')
        response = self.client.post(self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
        # test without lessonDuration
        data = self.student_data.copy()
        data.pop('lessonDuration')
        response = self.client.post(self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
        # test without requestMessage
        data = self.student_data.copy()
        data.pop('requestMessage')
        response = self.client.post(self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
        self.assertEqual(LessonRequest.objects.count(), self.qty)

    def test_not_logged_user(self):
        """Fail with creation a lesson request, because there isn't a logged user"""
        response = self.client.post(self.url, data=json.dumps(self.student_data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED, msg=response.content.decode())
        self.assertEqual(LessonRequest.objects.count(), self.qty)
