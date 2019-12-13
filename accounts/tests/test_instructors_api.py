"""Tests for instructors API"""
import operator

from django.conf import settings

from rest_framework import status

from .base_test_class import BaseTest


class InstructorsTest(BaseTest):
    fixtures = ['01_core_users.json', '02_accounts_instructors.json', '05_lesson_instruments.json',
                '06_accounts_availabilities.json', '07_accounts_educations.json', '08_accounts_employments.json',
                '09_accounts_instructoradditionalqualifications.json', '10_accounts_instructoragegroups.json',
                '11_accounts_instructorinstruments.json', '12_accounts_instructorlessonrates.json',
                '14_accounts_instructorplaceforlessons.json', '18_phonenumbers.json']
    login_data = {
        'email': 'luisinstruct@yopmail.com',
        'password': 'T3st11ng'
    }
    current_data = [{"id": 1, "displayName": "Luis I.", "age": 44, "avatar": None, "interviewed": False, "gender": None,
                     "bioTitle": "Music instructor", "bioDescription": "I'm a professional music instructor",
                     "location": "Houston, TX", "reviews": 0, "lessonsTaught": 0, "instruments": ['guitar', 'piano'],
                     "rates": {'mins30': '10.00', 'mins45': '15.00', 'mins60': '20.00', 'mins90': '30.00'},
                     "qualifications": {"certifiedTeacher": True, "musicTherapy": False, "musicProduction": False,
                                        "earTraining": True, "conducting": False, "virtuosoRecognition": False,
                                        "performance": False, "musicTheory": True, "youngChildrenExperience": False,
                                        "repertoireSelection": False},
                     "placeForLessons": {"home": True, "studio": False, "online": True},
                     "availability": {"mon8to10": True, "mon10to12": False, "mon12to3": True, "mon3to6": False,
                                      "mon6to9": False, "tue8to10": False, "tue10to12": False, "tue12to3": False,
                                      "tue3to6": False, "tue6to9": False, "wed8to10": False, "wed10to12": False,
                                      "wed12to3": False, "wed3to6": False, "wed6to9": False, "thu8to10": False,
                                      "thu10to12": False, "thu12to3": False, "thu3to6": False, "thu6to9": False,
                                      "fri8to10": False, "fri10to12": False, "fri12to3": False, "fri3to6": False,
                                      "fri6to9": False, "sat8to10": False, "sat10to12": False, "sat12to3": False,
                                      "sat3to6": False, "sat6to9": False, "sun8to10": False, "sun10to12": False,
                                      "sun12to3": False, "sun3to6": False, "sun6to9": False},
                     "student_ages": {"children": True, "teens": False, "adults": True, "seniors": True},
                     "languages": None, "lastLogin": "2019-10-30 17:13:11", "memberSince": "2019"}]

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
    current_data = {"id": 1, 'userId': 5, 'displayName': 'Luis I.', 'age': 44, 'interviewed': False,
                    'avatar': None, 'memberSince': '2019', 'yearsOfExperience': 0, 'reviews': 0,
                    "bioTitle": "Music instructor", 'languages': None,
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
