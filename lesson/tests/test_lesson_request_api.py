import json

from django.conf import settings

from rest_framework import status

from accounts.tests.base_test_class import BaseTest

from ..models import Instrument, LessonRequest


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
        'lessonDuration': "45 mins",
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
        'requestTitle': "Ukulele Instructor needed in Boston MA",
        'instrument': "ukulele",
        'placeForLessons': "home",
        'skillLevel': "beginner",
        'lessonDuration': "60 mins",
        'requestMessage': "My twins want to take ukulele lessons together"
    }

    def setUp(self):
        self.url = '{}/v1/lesson-request/'.format(settings.HOSTNAME_PROTOCOL)
        self.qty = LessonRequest.objects.count()

    def test_student_success(self):
        """Successful request, by student"""
        self.login_data = self.student_login_data
        super().setUp()
        response = self.client.post(self.url, data=json.dumps(self.student_data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(LessonRequest.objects.count(), self.qty + 1)

    def test_parent_success(self):
        """Successful request, by parent"""
        self.login_data = self.parent_login_data
        super().setUp()
        self.assertEqual(Instrument.objects.count(), 3)
        response = self.client.post(self.url, data=json.dumps(self.parent_data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(LessonRequest.objects.count(), self.qty + 1)
        self.assertEqual(Instrument.objects.count(), 4)   # check that new instrument was added

    def test_missing_data(self):
        """Failed request, by student, because some data is missing. Tests missing fields independently"""
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
        """Failed request, because user is not logged"""
        response = self.client.post(self.url, data=json.dumps(self.student_data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED, msg=response.content.decode())
        self.assertEqual(LessonRequest.objects.count(), self.qty)


class LessonRequestListTest(BaseTest):
    """Tests for get a list of lesson requests"""
    fixtures = ['01_core_users.json', '03_accounts_parents.json', '04_accounts_students.json',
                '05_lesson_instruments.json', '15_accounts_tiedstudents', '16_accounts_studentdetails',
                "01_lesson_requests.json"]
    student_login_data = {
        'email': 'luisstudent@yopmail.com',
        'password': 'T3st11ng'
    }
    another_student_login_data = {
        'email': 'luisstudent3@yopmail.com',
        'password': 'T3st11ng'
    }
    parent_login_data = {
        'email': 'luisparent@yopmail.com',
        'password': 'T3st11ng'
    }
    another_parent_login_data = {
        'email': 'luisparent2@yopmail.com',
        'password': 'T3st11ng'
    }

    def setUp(self):
        self.url = '{}/v1/lesson-request/'.format(settings.HOSTNAME_PROTOCOL)
        self.qty = LessonRequest.objects.count()

    def test_student_full_data(self):
        """Get a list of data, with length > 0, by student"""
        self.login_data = self.student_login_data
        super().setUp()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(LessonRequest.objects.count(), self.qty)
        self.assertEqual(len(response.json()), 2)

    def test_student_empty_data(self):
        """Get an empty list, by student"""
        self.login_data = self.another_student_login_data
        super().setUp()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(LessonRequest.objects.count(), self.qty)
        self.assertEqual(response.json(), [])

    def test_parent_full_data(self):
        """Get a list of data, with length > 0, by parent"""
        self.login_data = self.parent_login_data
        super().setUp()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(LessonRequest.objects.count(), self.qty)
        self.assertEqual(len(response.json()), 1)

    def test_parent_empty_data(self):
        """Get an empty list, by parent"""
        self.login_data = self.another_parent_login_data
        super().setUp()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(LessonRequest.objects.count(), self.qty)
        self.assertEqual(response.json(), [])
