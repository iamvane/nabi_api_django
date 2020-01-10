from django.conf import settings

from rest_framework import status

from .base_test_class import BaseTest


class DashboardStudentTest(BaseTest):
    fixtures = ['01_core_users.json', '02_accounts_instructors.json', '03_accounts_parents.json',
                '04_accounts_students.json', '05_lesson_instruments.json',
                '08_accounts_employments.json',
                '15_accounts_tiedstudents.json', '16_accounts_studentdetails.json', '01_lesson_requests.json',
                '01_payments.json', '02_applications.json', '03_instruments.json', '04_lesson_bookings.json']
    login_data = {
        'email': 'luisstudent@yopmail.com',
        'password': 'T3st11ng'
    }

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/dashboard/'.format(settings.HOSTNAME_PROTOCOL)

    def test_dashboard(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictEqual(response.json(), {'booking': {'age': 29, 'instrument': 'piano', 'skillLevel': 'beginner',
                                                           'instructor': 'Luis I.', 'lessonsRemaining': 2},
                                               'requests': [{'id': 3, 'instrument': 'flute', 'placeForLessons': 'online',
                                                             'requestTitle': 'Flute Instructor needed',
                                                             'requestMessage': 'Hello, I am looking for a flute instructor',
                                                             'studentDetails': {'age': 29},
                                                             'applications': 0, 'createdAt': '2019-12-18 11:12:35'}
                                                            ]
                                               }
                             )

    def test_dashboard_empty(self):
        self.login_data = {'email': 'luisstudent2@yopmail.com', 'password': 'T3st11ng'}
        super().setUp()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictEqual(response.json(), {'booking': {}, 'requests': []})
