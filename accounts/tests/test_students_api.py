"""Tests for students API"""
import json
import operator

from django.conf import settings

from rest_framework import status

from .base_test_class import BaseTest


class StudentsTest(BaseTest):
    fixtures = ['01_core_users.json', '03_accounts_parents.json', '05_lesson_instruments',
                '15_accounts_studentdetails.json', '16_accounts_tiedstudents.json']
    login_data = {
        'email': 'luisparent@yopmail.com',
        'password': 'T3st11ng'
    }

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/students/'.format(settings.HOSTNAME_PROTOCOL)

    def test_get_data(self):
        """Test GET request to students API"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        list_response = sorted(response.json(), key=operator.itemgetter('id'))
        self.assertListEqual(list_response, [{"id": 2, "name": "Santiago", "age": 37,
                                              "instrument": "piano", "skillLevel": "beginner",
                                              "lessonPlace": "home", "lessonDuration": "90 mins"},
                                             {"id": 3, "name": "Teresa", "age": 25,
                                              "instrument": "flute", "skillLevel": "beginner",
                                              "lessonPlace": "online", "lessonDuration": "60 mins"},
                                             {"id": 5, "name": "John", "age": 33,
                                              "instrument": "guitar", "skillLevel": "advanced",
                                              "lessonPlace": "home", "lessonDuration": "60 mins"}]
                             )

    def test_post_data(self):
        """Test POST request to students API"""
        # check previous data
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        list_response = sorted(response.json(), key=operator.itemgetter('id'))
        self.assertListEqual(list_response, [{"id": 2, "name": "Santiago", "age": 37,
                                              "instrument": "piano", "skillLevel": "beginner",
                                              "lessonPlace": "home", "lessonDuration": "90 mins"},
                                             {"id": 3, "name": "Teresa", "age": 25,
                                              "instrument": "flute", "skillLevel": "beginner",
                                              "lessonPlace": "online", "lessonDuration": "60 mins"},
                                             {"id": 5, "name": "John", "age": 33,
                                              "instrument": "guitar", "skillLevel": "advanced",
                                              "lessonPlace": "home", "lessonDuration": "60 mins"}]
                             )

        data = {"name": "Joseph", "age": 31, "instrument": "flute",
                "skillLevel": "beginner", "lessonPlace": "home", "lessonDuration": "90 mins"}
        response = self.client.post(self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        response = self.client.get(self.url)
        list_response = sorted(response.json(), key=operator.itemgetter('id'))
        dict_new_data = list_response[-1]
        self.assertDictContained(data, dict_new_data)


class ItemStudentsTest(BaseTest):
    fixtures = ['01_core_users.json', '03_accounts_parents.json', '05_lesson_instruments',
                '15_accounts_studentdetails.json', '16_accounts_tiedstudents.json']
    login_data = {
        'email': 'luisparent@yopmail.com',
        'password': 'T3st11ng'
    }

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/students/'.format(settings.HOSTNAME_PROTOCOL)

    def test_update(self):
        """Test update of a student's data"""
        original_data = {"id": 5, "name": "John", "age": 33, "instrument": "guitar",
                         "skillLevel": "advanced", "lessonPlace": "home", "lessonDuration": "60 mins"}
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        list_response = sorted(response.json(), key=operator.itemgetter('id'))
        dict_data = list_response[-1]
        self.assertEqual(original_data, dict_data)
        new_data = {"age": 35, "lessonPlace": "online"}
        original_data.update(new_data)
        response = self.client.put(self.url + '5/', data=json.dumps(new_data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        response = self.client.get(self.url)
        list_response = sorted(response.json(), key=operator.itemgetter('id'))
        dict_data = list_response[-1]
        self.assertEqual(original_data, dict_data)

    def test_delete(self):
        """Test delete of student's data"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        list_response = [item['id'] for item in response.json()]
        list_response.sort()
        response = self.client.delete(self.url + str(list_response[-1]) + '/')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        response = self.client.get(self.url)
        list_response2 = [item['id'] for item in response.json()]
        list_response2.sort()
        self.assertEqual(list_response[:-1], list_response2)
