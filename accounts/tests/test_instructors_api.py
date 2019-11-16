"""Tests for instructors API"""
import operator

from django.conf import settings

from rest_framework import status

from .base_test_class import BaseTest


class InstructorsTest(BaseTest):
    fixtures = ['01_core_users.json', '02_accounts_instructors.json', '05_lesson_instruments.json']
    login_data = {
        'email': 'luisinstruct@yopmail.com',
        'password': 'T3st11ng'
    }
    current_data = [{"id": 1, "displayName": "Luis I.", "age": 44, "avatar": None,
                     "bioTitle": "Music instructor", "bioDescription": "I'm a professional music instructor",
                     "location": None, "reviews": 0, "lessonsTaught": 0, "instruments": [],
                     "rates": {'mins30': '', 'mins45': '', 'mins60': '', 'mins90': ''},
                     "lastLogin": "2019-10-30 17:13:11", "memberSince": "2019"},
                    {"id": 2, "displayName": "Luis I.", "age": 44, "avatar": None,
                     "bioTitle": None, "bioDescription": None,
                     "location": None, "reviews": 0, "lessonsTaught": 0, "instruments": [],
                     "rates": {'mins30': '', 'mins45': '', 'mins60': '', 'mins90': ''},
                     "lastLogin": None, "memberSince": "2019"},
                    {"id": 3, "displayName": "Luis I.", "age": 44, "avatar": None,
                     "bioTitle": None, "bioDescription": None,
                     "location": None, "reviews": 0, "lessonsTaught": 0, "instruments": [],
                     "rates": {'mins30': '', 'mins45': '', 'mins60': '', 'mins90': ''},
                     "lastLogin": None, "memberSince":"2019"},
                    {"id": 4, "displayName": "Luis I.", "age": 53, "avatar": None,
                     "bioTitle": None, "bioDescription": None,
                     "location": None, "reviews": 0, "lessonsTaught": 0, "instruments": [],
                     "rates": {'mins30': '', 'mins45': '', 'mins60': '', 'mins90': ''},
                     "lastLogin": "2019-10-30 18:26:38", "memberSince": "2019"}]

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/instructors/'.format(settings.HOSTNAME_PROTOCOL)

    def test_get_data(self):
        """Test getting data"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        list_response = response.json()['results']
        list_response = sorted(list_response, key=operator.itemgetter('id'))
        self.assertListEqual(list_response, self.current_data)


class ItemInstructorsTest(BaseTest):
    fixtures = ['01_core_users.json', '02_accounts_instructors.json', '05_lesson_instruments.json']
    login_data = {
        'email': 'luisinstruct@yopmail.com',
        'password': 'T3st11ng'
    }
    current_data = {"id": 1, 'userId': 5, "bioTitle": "Music instructor", 'languages': None,
                    "bioDescription": "I'm a professional music instructor", 'instruments': [],
                    'education': [], 'employment': [], 'availability': [],
                    'ageGroup': [], 'lessonSize': [], 'lessonsTaught': 0,
                    'music': ['piano', 'guitar'], 'placeForLessons': [],
                    'qualifications': None,
                    'rates': {'mins30': '', 'mins45': '', 'mins60': '', 'mins90': ''},
                    'studioAddress': None, 'travelDistance': None}

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/instructors/'.format(settings.HOSTNAME_PROTOCOL)

    def test_get_single_data(self):
        """Test getting data of a single entry"""
        response = self.client.get(self.url + str(self.current_data['id']) + '/')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        dict_data = response.json()
        self.assertDictEqual(dict_data, self.current_data)

    def test_get_wrong_id(self):
        """Test getting data of a non-existent entry"""
        response = self.client.get(self.url + '33/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, msg=response.content.decode())
