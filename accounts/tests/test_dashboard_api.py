from django.conf import settings

from rest_framework import status

from .base_test_class import BaseTest


class DashboardStudentTest(BaseTest):
    """Test dashboard endpoint for a student"""
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
        self.assertDictEqual(response.json(), {'bookings': [{'age': 29, 'instrument': 'piano', 'skillLevel': 'beginner',
                                                           'instructor': 'Luis I.', 'lessonsRemaining': 2}],
                                               'requests': [{'id': 3, 'instrument': 'flute', 'placeForLessons': 'online',
                                                             'lessonDuration': '30 mins', 'skillLevel': 'beginner',
                                                             'requestTitle': 'Flute Instructor needed',
                                                             'requestMessage': 'Hello, I am looking for a flute instructor',
                                                             'studentDetails': {'name': 'Luis', 'age': 29},
                                                             'applications': 0, 'createdAt': '2019-12-18 11:12:35'}
                                                            ]
                                               }
                             )

    def test_dashboard_empty(self):
        self.login_data = {'email': 'luisstudent2@yopmail.com', 'password': 'T3st11ng'}
        super().setUp()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictEqual(response.json(), {'bookings': [], 'requests': []})


class DashboardParentTest(BaseTest):
    """Test dashboard endpoint for a parent"""
    fixtures = ['01_core_users.json', '02_accounts_instructors.json', '03_accounts_parents.json',
                '04_accounts_students.json', '05_lesson_instruments.json',
                '08_accounts_employments.json',
                '15_accounts_tiedstudents.json', '16_accounts_studentdetails.json', '01_lesson_requests.json',
                '01_payments.json', '02_applications.json', '03_instruments.json', '04_lesson_bookings.json']
    login_data = {
        'email': 'luisparent@yopmail.com',
        'password': 'T3st11ng'
    }

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/dashboard/'.format(settings.HOSTNAME_PROTOCOL)

    def test_dashboard(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictEqual(response.json(), {'bookings': [{'instrument': 'guitar', 'skillLevel': 'beginner',
                                                           'instructor': 'Luis I.', 'lessonsRemaining': 2,
                                                           'students': [{'name': 'Santiago', 'age': 9},
                                                                        {'name': 'Teresa', 'age': 7}]
                                                           }],
                                               'requests': [{'id': 5, 'instrument': 'guitar', 'placeForLessons': 'home',
                                                             'lessonDuration': '30 mins', 'skillLevel': 'beginner',
                                                             'requestTitle': 'Searching for a Guitar Instructor',
                                                             'requestMessage': "I'm looking for a guitar instructor for my children",
                                                             'studentDetails': [{'age': 9, 'name': 'Santiago'},
                                                                                {'age': 7, 'name': 'Teresa'}],
                                                             'applications': 0, 'createdAt': '2019-12-22 08:24:16'}
                                                            ]
                                               }
                             )

    def test_dashboard_empty(self):
        self.login_data = {'email': 'luisparent3@yopmail.com', 'password': 'T3st11ng'}
        super().setUp()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictEqual(response.json(), {'bookings': [], 'requests': []})


class DashboardInstructorTest(BaseTest):
    """Test dashboard endpoint for an instructor"""
    fixtures = ['01_core_users.json', '02_accounts_instructors.json', '03_accounts_parents.json',
                '04_accounts_students.json', '05_lesson_instruments.json',
                '08_accounts_employments.json',
                '15_accounts_tiedstudents.json', '16_accounts_studentdetails.json', '01_lesson_requests.json',
                '01_payments.json', '02_applications.json', '03_instruments.json', '04_lesson_bookings.json']
    login_data = {
        'email': 'luisinstruct@yopmail.com',
        'password': 'T3st11ng'
    }

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/dashboard/'.format(settings.HOSTNAME_PROTOCOL)

    def test_dashboard(self):
        expected_data = {'backgroundCheckStatus': 'NOT_VERIFIED', 'complete': True, 'missingFields': ['qualification', ],
                         'lessons': [{'bookingId': 1, 'instrument': 'piano', 'lessonsBooked': 2, 'lessonsRemaining': 2,
                                      'skillLevel': 'beginner',  'studentName': 'Luis S.', 'age': 29},
                                     {'bookingId': 2, 'instrument': 'guitar', 'lessonsBooked': 2, 'lessonsRemaining': 2,
                                      'skillLevel': 'beginner', 'parent': 'Luis P.',
                                      'students': [{'name': 'Santiago', 'age': 9}, {'name': 'Teresa', 'age': 7}]}
                                     ],
                         'requests': [{'id': 3, 'displayName': 'Luis S.', 'role': 'student', 'avatar': '',
                                       'distance': '1143.40', 'requestTitle': 'Flute Instructor needed',
                                       'instrument': 'flute', 'placeForLessons': 'online', 'skillLevel': 'beginner',
                                       'lessonDuration': '30 mins', 'location': 'Boon, MI',
                                       'studentDetails': {'age': 29},
                                       'applicationsReceived': 0},
                                      {'id': 4, 'displayName': 'Luis P.', 'role': 'parent', 'avatar': '',
                                       'distance': '36.96', 'requestTitle': 'Piano Instructor needed',
                                       'instrument': 'piano', 'placeForLessons': 'online', 'skillLevel': 'beginner',
                                       'lessonDuration': '30 mins', 'location': 'Montgomery, TX',
                                       'studentDetails': [{'name': 'Paul', 'age': 10}],
                                       'applicationsReceived': 0},
                                      {'id': 5, 'displayName': 'Luis P.', 'role': 'parent', 'avatar': '',
                                       'distance': '110.79', 'requestTitle': 'Searching for a Guitar Instructor',
                                       'instrument': 'guitar', 'placeForLessons': 'home', 'skillLevel': 'beginner',
                                       'lessonDuration': '30 mins', 'location': 'Cameron, LA',
                                       'studentDetails': [{'name': 'Santiago', 'age': 9}, {'name': 'Teresa', 'age': 7}],
                                       'applicationsReceived': 0}
                                      ]
                         }
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        resp_data = response.json()
        num_items = len(resp_data['requests'])
        for i in range(num_items):
            self.assertIsNotNone(resp_data['requests'][i].pop('elapsedTime'))
        self.assertDictEqual(expected_data, resp_data)

    def test_dashboard_without_lessons(self):
        expected_data = {'backgroundCheckStatus': 'NOT_VERIFIED', 'complete': False,
                         'missingFields': ['location', 'avatar', 'references', 'isPhoneVerified',
                                           'bioTitle', 'bioDescription', 'instruments', 'lessonSize', 'ageGroup',
                                           'rates', 'availability', 'employment', 'education', 'qualification',
                                           'music', ],
                         'lessons': [],
                         'requests': []
                         }
        self.login_data = {'email': 'luisinstruct4@yopmail.com', 'password': 'T3st11ng'}
        super().setUp()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictEqual(expected_data, response.json())
