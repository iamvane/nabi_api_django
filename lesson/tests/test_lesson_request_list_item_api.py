from django.conf import settings

from rest_framework import status

from accounts.tests.base_test_class import BaseTest


class LessonRequestsListTest(BaseTest):
    """Tests for get an item of lesson requests, called by an instructor"""
    fixtures = ['01_core_users.json', '02_accounts_instructors.json', '03_accounts_parents.json',
                '04_accounts_students.json', '05_lesson_instruments.json', '15_accounts_tiedstudents',
                '16_accounts_studentdetails', '01_lesson_requests.json', '02_applications.json']
    login_data = {
        'email': 'luisinstruct@yopmail.com',
        'password': 'T3st11ng'
    }

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/lesson-request-item/'.format(settings.HOSTNAME_PROTOCOL)

    def test_success(self):
        response = self.client.get(self.url + '1/')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        resp_data = response.json()
        self.assertDictEqual(resp_data, {'id': 1, 'avatar': '', 'displayName': 'Luis S.',
                                         'instrument': 'piano', 'lessonDuration': '45 mins', 'location': 'Boon, MI',
                                         'requestMessage': 'Hello, I am looking for a piano instructor',
                                         'placeForLessons': 'home',
                                         'skillLevel': 'beginner',
                                         'studentDetails': [{'name': 'Luis', 'age': 29}],
                                         'requestTitle': 'Piano Instructor needed in Boston MA',
                                         'applied': True,
                                         'application': {'rate': 35.0,
                                                         'message': "Hello I'm available for teaching lessons",
                                                         'dateApplied': '2019-12-19 21:07:30'}
                                         })

    def test_success_user_is_not_applicant(self):
        self.login_data = {'email': 'luisinstruct2@yopmail.com', 'password': 'T3st11ng'}
        super().setUp()
        response = self.client.get(self.url + '2/')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        resp_data = response.json()
        self.assertDictEqual(resp_data, {'id': 2, 'avatar': '', 'displayName': 'Luis P.', 'instrument': 'guitar',
                                         'lessonDuration': '60 mins', 'location': 'Cameron, LA',
                                         'placeForLessons': 'home',
                                         'skillLevel': 'beginner',
                                         'studentDetails': [{'name': 'Santiago', 'age': 9},
                                                            {'name': 'Teresa', 'age': 7}],
                                         'requestMessage': 'Hi, I am looking for a guitar instructor for my children',
                                         'requestTitle': 'Guitar Instructor needed',
                                         'applied': False,
                                         'application': {}
                                         })

    def test_request_not_exist(self):
        response = self.client.get(self.url + '5/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
