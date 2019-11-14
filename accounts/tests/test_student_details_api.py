"""Tests for student-details API"""
import json

from django.conf import settings

from rest_framework import status

from .base_test_class import BaseTest


class StudentDetailsTest(BaseTest):
    fixtures = ['01_core_users.json', '03_accounts_parents.json', '04_accounts_students.json',
                '05_lesson_instruments.json', '15_accounts_studentdetails.json', '16_accounts_tiedstudents.json']
    login_data = {
        'email': 'luisstudent@yopmail.com',
        'password': 'T3st11ng'
    }

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/student-details/'.format(settings.HOSTNAME_PROTOCOL)

    def test_get_data(self):
        """Test request to get student details"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertDictEqual(response.json(), {"id": 1, "instrument": "flute", "lessonDuration": "90 mins",
                                               "lessonPlace": "home", "skillLevel": "beginner"}
                             )

    def test_update_lesson_place(self):
        """Test request to update lesson_place in student details"""
        # check previous data
        data = {"id": 1, "instrument": "flute", "lessonDuration": "90 mins",
                "lessonPlace": "home", "skillLevel": "beginner"}
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertDictEqual(response.json(), data)

        data.update({"lessonPlace": "online"})
        response = self.client.put(self.url, data=json.dumps({"lessonPlace": "online"}), content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertDictEqual(response.json(), data)

    def test_update_instrument(self):
        """Test request to update instrument in student details"""
        # check previous data
        data = {"id": 1, "instrument": "flute", "lessonDuration": "90 mins",
                "lessonPlace": "home", "skillLevel": "beginner"}
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertDictEqual(response.json(), data)

        data.update({"instrument": "oboe"})
        response = self.client.put(self.url, data=json.dumps({"instrument": "oboe"}),
                                   content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertDictEqual(response.json(), data)

    def test_update_skill_level_wrong(self):
        """Test request to update skill level in student details, using a wrong value"""
        # check previous data
        data = {"id": 1, "instrument": "flute", "lessonDuration": "90 mins",
                "lessonPlace": "home", "skillLevel": "beginner"}
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertDictEqual(response.json(), data)

        response = self.client.put(self.url, data=json.dumps({"skillLevel": "very master"}),
                                   content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())


class GetStudentDetailsTest(BaseTest):
    fixtures = ['01_core_users.json', '03_accounts_parents.json', '04_accounts_students.json',
                '05_lesson_instruments.json', '15_accounts_studentdetails.json', '16_accounts_tiedstudents.json']
    login_data = {
        'email': 'luisstudent2@yopmail.com',
        'password': 'T3st11ng'
    }

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/student-details/'.format(settings.HOSTNAME_PROTOCOL)

    def test_get_data(self):
        """Test request to get student details (empty data)"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertDictEqual(response.json(), {})
