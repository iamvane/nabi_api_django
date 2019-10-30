"""Tests for whoami API"""
import json

from django.conf import settings

from rest_framework import status

from .base_test_class import BaseTest


class WhoAmiInstructorTest(BaseTest):
    fixtures = ['01_core_users.json', '02_accounts_instructors.json']
    login_data = {
        'email': 'luisinstruct@yopmail.com',
        'password': 'T3st11ng'
    }

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/whoami/'.format(settings.HOSTNAME_PROTOCOL)

    def test_get_data(self):
        """Test whoami data returned for instructor"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(response.json(),
                         {"id": 5, "email": "luisinstruct@yopmail.com", "role": "instructor",
                          "firstName": "Luis", "middleName": None, "lastName": "Instructor",
                          "birthday": "1975-04-03", "phone": {}, "gender": None, "location": "", "lat": "", "lng": "",
                          "referralToken": "WVG3Kw4HaDhEpyag", "bioTitle": "Music instructor",
                          "bioDescription": "I'm a professional music instructor",
                          "music": ["piano", "guitar"], "lessonSize": {}, "instruments": [], "ageGroup": {},
                          "lessonRate": {}, "placeForLessons": {}, "availability": {},
                          "qualifications": {}, "studioAddress": None, "travelDistance": None,
                          "languages": None, "employment": [], "education": []}
                         )


class WhoAmiInstructorTest2(BaseTest):
    fixtures = ['01_core_users.json', '02_accounts_instructors.json']
    login_data = {
        'email': 'luisinstruct2@yopmail.com',
        'password': 'T3st11ng'
    }

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/whoami/'.format(settings.HOSTNAME_PROTOCOL)

    def test_get_data(self):
        """Test whoami data returned for instructor2"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertDictEqual(response.json(), {"id": 7, "email": "luisinstruct2@yopmail.com", "role": "instructor",
                                               "firstName": "Luis", "middleName": None, "lastName": "Instructor two",
                                               "birthday": "1975-04-03", "phone": {}, "gender": None, "location": "",
                                               "lat": "", "lng": "", "referralToken": "VMxGjIPkVJ4CXGCM",
                                               "bioTitle": None, "bioDescription": None, "music": None,
                                               "lessonSize": {}, "instruments": [], "ageGroup": {}, "lessonRate": {},
                                               "placeForLessons": {}, "availability": {}, "qualifications": {},
                                               "studioAddress": None, "travelDistance": None, "languages": None,
                                               "employment": [], "education": []}
                             )


class WhoAmiParentTest(BaseTest):
    fixtures = ['01_core_users.json', '03_accounts_parents.json']

    def setUp(self):
        self.login_data = {
            'email': 'luisparent@yopmail.com',
            'password': 'T3st11ng'
        }
        self.token = self.get_token(**self.login_data)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(self.token))
        self.url = '{}/v1/whoami/'.format(settings.HOSTNAME_PROTOCOL)

    def test_get_data(self):
        """Test whoami data returned for parent"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(json.loads(response.content.decode()),
                         {"id": 3, "email": "luisparent@yopmail.com", "role": "parent",
                          "firstName": "Luis", "middleName": None, "lastName": "Parent",
                          "birthday": "1979-01-23", "phone": {}, "gender": None, "location": "", "lat": "", "lng": "",
                          "referralToken": "EljB8wAa40oDPUIt", "students": []}
                         )


class WhoAmiStudentTest(BaseTest):
    fixtures = ['01_core_users.json', '04_accounts_students.json']

    def setUp(self):
        self.login_data = {
            'email': 'luisstudent@yopmail.com',
            'password': 'T3st11ng'
        }
        self.token = self.get_token(**self.login_data)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(self.token))
        self.url = '{}/v1/whoami/'.format(settings.HOSTNAME_PROTOCOL)

    def test_get_data(self):
        """Test whoami data returned for student"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(json.loads(response.content.decode()),
                         {"id": 1, "email": "luisstudent@yopmail.com", "role": "student",
                          "firstName": "Luis", "middleName": "A.", "lastName": "Student",
                          "birthday": "1990-03-13", "phone": {}, "gender": "male",
                          "location": "Michigan, United States", "lat": "", "lng": "",
                          "referralToken": "THoANSG6cV60dya1"}
                         )


class WhoAmiStudentTest2(BaseTest):
    fixtures = ['01_core_users.json', '04_accounts_students.json']

    def setUp(self):
        self.login_data = {
            'email': 'luisstudent2@yopmail.com',
            'password': 'T3st11ng'
        }
        self.token = self.get_token(**self.login_data)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(self.token))
        self.url = '{}/v1/whoami/'.format(settings.HOSTNAME_PROTOCOL)

    def test_get_data(self):
        """Test whoami data returned for student"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(json.loads(response.content.decode()),
                         {"id": 2, "email": "luisstudent2@yopmail.com", "role": "student", "firstName": "Luis",
                          "middleName": None, "lastName": "Student two", "birthday": "1988-07-26", "phone": {},
                          "gender": None, "location": "", "lat": "", "lng": "", "referralToken": "R72-BlRs7HAAenV0"}

                         )
