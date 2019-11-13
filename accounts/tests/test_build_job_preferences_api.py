"""Tests for build-job-preferences API"""
import json

from django.conf import settings

from rest_framework import status

from .base_test_class import BaseTest


class BuildJobPreferencesTest(BaseTest):
    fixtures = ['01_core_users.json', '02_accounts_instructors.json', '05_lesson_instruments',
                '06_accounts_availabilities', '07_accounts_educations', '08_accounts_employments',
                '09_accounts_instructoradditionalqualifications', '10_accounts_instructoragegroups',
                '11_accounts_instructorinstruments', '12_accounts_instructorlessonrates',
                '13_accounts_instructorlessonsizes', '14_accounts_instructorplaceforlessons']
    login_data = {
        "email": "luisinstruct@yopmail.com",
        "password": "T3st11ng"
    }

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/build-job-preferences/'.format(settings.HOSTNAME_PROTOCOL)

    def test_store_data(self):
        """Test for storing instructor data"""
        # get current data
        instructors_url = '{}/v1/instructors/1/'.format(settings.HOSTNAME_PROTOCOL)
        response = self.client.get(instructors_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        current_data = response.json()

        data = {"instruments": [{"instrument": "piano", "skillLevel": "advanced"}],
                "lessonSize": {"oneStudent": True, "smallGroups": True, "largeGroups": False},
                "ageGroup": {"children": True, "teens": False, "adults": True, "seniors": True},
                "rates": {"mins30": '10.20', "mins45": '15.30', "mins60": '20.00', "mins90": '30.60'},
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
        response = self.client.get(instructors_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        response_data = response.json()
        new_data = current_data.copy()
        instruments = data.pop('instruments')
        new_data.update(data)
        new_data.update([{'name': item['instrument'], 'skillLevel': item['skillLevel']} for item in instruments])
        self.assertDictListUnsorted(new_data['instruments'], response_data['instruments'], 'name')
        self.assertDictEqual(new_data['lessonSize'], response_data['lessonSize'])
        self.assertDictEqual(new_data['ageGroup'], response_data['ageGroup'])
        self.assertDictEqual(new_data['placeForLessons'], response_data['placeForLessons'])
        self.assertDictEqual(new_data['rates'], response_data['rates'])
        self.assertDictContained(new_data['availability'], response_data['availability'])
        self.assertDictContained(new_data['qualifications'], response_data['qualifications'])
        self.assertListEqual(new_data['languages'], response_data['languages'])
        self.assertEqual(new_data['studioAddress'], response_data['studioAddress'])
        self.assertEqual(new_data['travelDistance'], response_data['travelDistance'])

    def test_store_partial_data(self):
        """Test for storing 'partial' data, not complete"""
        # get current data
        instructors_url = '{}/v1/instructors/1/'.format(settings.HOSTNAME_PROTOCOL)
        response = self.client.get(instructors_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        current_data = response.json()

        data = {"instruments": [{"instrument": "piano", "skillLevel": "advanced"}],
                "lessonSize": {"oneStudent": True},
                "ageGroup": {"children": False, "adults": True},
                "rates": {"mins30": '10.30', "mins45": '15.45', "mins60": '20.60', "mins90": '30.00'},
                "placeForLessons": {"online": True},
                "availability": {"mon8to10": True, "mon10to12": False, "mon12to3": False},
                "qualifications": {"certifiedTeacher": True, "musicTherapy": True, "musicTheory": True},
                "languages": ["french", "spanish"],
                "studioAddress": "Kennedy Avenue",
                "travelDistance": "150 miles"
                }
        response = self.client.post(self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        response = self.client.get(instructors_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        response_data = response.json()
        new_data = current_data.copy()
        instruments = data.pop('instruments')
        new_data.update(data)
        new_data.update([{'name': item['instrument'], 'skillLevel': item['skillLevel']} for item in instruments])
        self.assertDictListUnsorted(new_data['instruments'], response_data['instruments'], 'name')
        self.assertDictContained(new_data['lessonSize'], response_data['lessonSize'])
        self.assertDictContained(new_data['ageGroup'], response_data['ageGroup'])
        self.assertDictContained(new_data['placeForLessons'], response_data['placeForLessons'])
        self.assertDictEqual(new_data['rates'], response_data['rates'])
        self.assertDictContained(new_data['availability'], response_data['availability'])
        self.assertDictContained(new_data['qualifications'], response_data['qualifications'])
        self.assertListEqual(new_data['languages'], response_data['languages'])
        self.assertEqual(new_data['studioAddress'], response_data['studioAddress'])
        self.assertEqual(new_data['travelDistance'], response_data['travelDistance'])

    def test_store_wrong_data(self):
        """Try to store wrong data"""
        data = {"instruments": [{"instrument": "piano", "skillLevel": "advanced"}],
                "lessonSize": {"something": True},
                "ageGroup": {"group": True, "group2": False},
                "rates": {"mins20": '15', "mins40": '40'},
                "placeForLessons": {"myplace": True},
                "availability": {"mon8-10": True, "mon10-12": False, "mon12-3": False},
                "qualifications": {"certicate1": True, "certificate2": True},
                }
        response = self.client.post(self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
