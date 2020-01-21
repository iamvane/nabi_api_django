from django.conf import settings

from rest_framework import status

from accounts.tests.base_test_class import BaseTest


class LessonRequestsListTest(BaseTest):
    """Tests for get a list of lesson requests"""
    fixtures = ['01_core_users.json', '02_accounts_instructors.json', '03_accounts_parents.json',
                '04_accounts_students.json', '05_lesson_instruments.json', '15_accounts_tiedstudents',
                '16_accounts_studentdetails', '01_lesson_requests.json']
    login_data = {
        'email': 'luisinstruct@yopmail.com',
        'password': 'T3st11ng'
    }

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/lesson-request-list/'.format(settings.HOSTNAME_PROTOCOL)

    def test_success(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(len(response.json().get('results')), 3)

    def test_success_filter_by_age(self):
        # filter by age
        response = self.client.get(self.url + '?age=children')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        resp_data = response.json()
        self.assertEqual(len(resp_data.get('results')), 2)
        for item in resp_data.get('results'):
            comply = False
            for student in item.get('studentDetails'):
                if student.get('age') <= 12:
                    comply = True
            self.assertTrue(comply)

    def test_success_filter_by_instrument(self):
        # filter by instrument
        response = self.client.get(self.url + '?instrument=piano')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        resp_data = response.json()
        self.assertEqual(len(resp_data.get('results')), 1)
        for item in resp_data.get('results'):
            self.assertIn(item.get('instrument'), 'piano')

    def test_success_filter_by_distance(self):
        # filter by distance
        response = self.client.get(self.url + '?distance=120')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        resp_data = response.json()
        self.assertEqual(len(resp_data.get('results')), 2)
        for item in resp_data.get('results'):
            self.assertIn(item.get('id'), [4, 5])

    def test_success_placeforlessons(self):
        # filter by placeForlessons
        response = self.client.get(self.url + '?placeForLessons=home')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        result_data = response.json().get('results')
        self.assertEqual(len(result_data), 1)
        # verify that all requests have placeForLessons = home
        for item in result_data:
            self.assertEqual(item['placeForLessons'], 'home')

    def test_success_placeforlessons_various_values(self):
        # filter by placeForlessons
        response = self.client.get(self.url + '?placeForLessons=home,online')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        result_data = response.json().get('results')
        self.assertEqual(len(response.json().get('results')), 3)
        # verify that all requests have placeForLessons = home or placeForLessons = online
        for item in result_data:
            self.assertIn(item['placeForLessons'], ['home', 'online'])
