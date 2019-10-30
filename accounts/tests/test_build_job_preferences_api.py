"""Tests for build-job-preferences API"""
import json

from django.conf import settings

from rest_framework import status

from .base_test_class import BaseTest


class BuildJobPreferencesTest(BaseTest):
    fixtures = ['01_core_users.json', '02_accounts_instructors.json']
    login_data = {
        "email": "luisinstruct@yopmail.com",
        "password": "T3st11ng"
    }

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/build-job-preferences/'.format(settings.HOSTNAME_PROTOCOL)

    def test_store_data(self):
        """Test for storing instructor data"""
        whoami_url = '{}/v1/whoami/'.format(settings.HOSTNAME_PROTOCOL)
        # get current data
        response = self.client.get(whoami_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        current_data = response.json()
        self.assertDictEqual(current_data, {"id": 5, "email": "luisinstruct@yopmail.com", "role": "instructor",
                                            "firstName": "Luis", "middleName": None, "lastName": "Instructor",
                                            "birthday": "1975-04-03", "phone": {}, "gender": None,
                                            "location": "", "lat": "", "lng": "",
                                            "referralToken": "WVG3Kw4HaDhEpyag", "bioTitle": "Music instructor",
                                            "bioDescription": "I'm a professional music instructor",
                                            "music": ["piano", "guitar"], "lessonSize": {}, "instruments": [],
                                            "ageGroup": {}, "lessonRate": {}, "placeForLessons": {}, "availability": {},
                                            "qualifications": {}, "studioAddress": None, "travelDistance": None,
                                            "languages": None, "employment": [], "education": []}
                             )

        data = {"instruments": [{"instrument": "piano", "skillLevel": "advanced"}],
                "lessonSize": {"oneStudent": True, "smallGroups": True, "largeGroups": False},
                "ageGroup": {"children": True, "teens": False, "adults": True, "seniors": True},
                "rates": {"mins30": 10, "mins45": 15, "mins60": 20, "mins90": 30},
                "placeForLessons": {"home": True, "studio": False, "online": True},
                "availability": {"mon8to10": True, "mon10to12": False, "mon12to3": False},
                "qualifications": {"certifiedTeacher": True, "musicTherapy": False, "musicProduction": False,
                                   "earTraining": False, "conducting": False, "virtuosoRecognition": False,
                                   "performance": False, "musicTheory": True, "youngChildrenExperience": False,
                                   "repertoireSelection": False},
                "languages": ["french", "spanish"],
                "studioAddress": "Kennedy Avenue",
                "travelDistance": "150 miles"
                }
        response = self.client.post(self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        response = self.client.get(whoami_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        response_data = response.json()
        self.assertListEqual(data['instruments'], response_data['instruments'])
        self.assertDictEqual(data['lessonSize'], response_data['lessonSize'])
        self.assertDictEqual(data['ageGroup'], response_data['ageGroup'])
        self.assertDictEqual(data['placeForLessons'], response_data['placeForLessons'])
        self.assertDictContained(data['availability'], response_data['availability'])
        self.assertDictContained(data['qualifications'], response_data['qualifications'])
        self.assertListEqual(data['languages'], response_data['languages'])
        self.assertDictEqual(data['studioAddress'], response_data['studioAddress'])
        self.assertDictEqual(data['travelDistance'], response_data['travelDistance'])

    def test_store_partial_data(self):
        """Test for storing 'partial' data, not complete"""
        whoami_url = '{}/v1/whoami/'.format(settings.HOSTNAME_PROTOCOL)
        # get current data
        response = self.client.get(whoami_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        current_data = response.json()
        self.assertDictEqual(current_data, {"id": 5, "email": "luisinstruct@yopmail.com", "role": "instructor",
                                            "firstName": "Luis", "middleName": None, "lastName": "Instructor",
                                            "birthday": "1975-04-03", "phone": {}, "gender": None,
                                            "location": "", "lat": "", "lng": "",
                                            "referralToken": "WVG3Kw4HaDhEpyag", "bioTitle": "Music instructor",
                                            "bioDescription": "I'm a professional music instructor",
                                            "music": ["piano", "guitar"], "lessonSize": {}, "instruments": [],
                                            "ageGroup": {}, "lessonRate": {}, "placeForLessons": {}, "availability": {},
                                            "qualifications": {}, "studioAddress": None, "travelDistance": None,
                                            "languages": None, "employment": [], "education": []}
                             )

        data = {"instruments": [{"instrument": "piano", "skillLevel": "advanced"}],
                "lessonSize": {"oneStudent": True},
                "ageGroup": {"children": False, "adults": True},
                "rates": {"mins30": 10, "mins45": 15, "mins60": 20, "mins90": 30},
                "placeForLessons": {"online": True},
                "availability": {"mon8to10": True, "mon10to12": False, "mon12to3": False},
                "qualifications": {"certifiedTeacher": True, "musicTherapy": True, "musicTheory": True},
                "languages": ["french", "spanish"],
                "studioAddress": "Kennedy Avenue",
                "travelDistance": "150 miles"
                }
        response = self.client.post(self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        response = self.client.get(whoami_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        response_data = response.json()
        self.assertListEqual(data['instruments'], response_data['instruments'])
        self.assertDictContained(data['lessonSize'], response_data['lessonSize'])
        self.assertDictContained(data['ageGroup'], response_data['ageGroup'])
        self.assertDictContained(data['placeForLessons'], response_data['placeForLessons'])
        self.assertDictContained(data['availability'], response_data['availability'])
        self.assertDictContained(data['qualifications'], response_data['qualifications'])
        self.assertListEqual(data['languages'], response_data['languages'])
        self.assertDictEqual(data['studioAddress'], response_data['studioAddress'])
        self.assertDictEqual(data['travelDistance'], response_data['travelDistance'])

    def test_store_wrong_data(self):
        """Try to store wrong data"""
        data = {"instruments": [{"instrument": "piano", "skillLevel": "advanced"}],
                "lessonSize": {"something": True},
                "ageGroup": {"group": True, "group2": False},
                "rates": {"mins20": 15, "mins40": 40},
                "placeForLessons": {"myplace": True},
                "availability": {"mon8-10": True, "mon10-12": False, "mon12-3": False},
                "qualifications": {"certicate1": True, "certificate2": True},
                }
        response = self.client.post(self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
