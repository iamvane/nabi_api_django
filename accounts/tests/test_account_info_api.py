"""Tests for account-info API"""
import json

from django.conf import settings

from rest_framework import status

from accounts.models import User

from .base_test_class import BaseTest


class AccountInfoInstructorTest(BaseTest):
    """Tests using instructor data"""
    fixtures = ['01_core_users.json', '02_accounts_instructors.json']
    login_data = {
        'email': 'luisinstruct@yopmail.com',
        'password': 'T3st11ng'
    }

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/account-info/'.format(settings.HOSTNAME_PROTOCOL)

    def test_update_data(self):
        """Update data account"""
        # previous check
        user = User.objects.get(email=self.login_data['email'])
        self.assertIsNone(user.instructor.middle_name)
        self.assertIsNone(user.instructor.gender)
        self.assertEqual(user.instructor.location, '')

        data = {'middleName': 'M', 'gender': 'male', 'location': 'Oregon'}
        response = self.client.put(self.url, data=json.dumps(data), content_type='application/json')
        user.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(user.instructor.middle_name, data['middleName'])
        self.assertEqual(user.instructor.gender, data['gender'])
        self.assertEqual(user.instructor.location, data['location'])

    def test_update_wrong_gender(self):
        """Try to update with wrong gender value"""
        user = User.objects.get(email=self.login_data['email'])
        prev_gender = user.instructor.gender
        response = self.client.put(self.url, data=json.dumps({'gender': '0'}), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
        user.refresh_from_db()
        self.assertEqual(prev_gender, user.instructor.gender)


class AccountInfoParentTest(BaseTest):
    """Tests using parent data"""
    fixtures = ['01_core_users.json', '03_accounts_parents.json']
    login_data = {
        'email': 'luisparent@yopmail.com',
        'password': 'T3st11ng'
    }

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/account-info/'.format(settings.HOSTNAME_PROTOCOL)

    def test_update_data(self):
        """Update data account"""
        # previous check
        user = User.objects.get(email=self.login_data['email'])
        self.assertIsNone(user.parent.middle_name)
        self.assertIsNone(user.parent.gender)
        self.assertEqual(user.parent.location, '')

        data = {'middleName': 'M', 'gender': 'male', 'location': 'Oregon'}
        response = self.client.put(self.url, data=json.dumps(data), content_type='application/json')
        user.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(user.parent.middle_name, data['middleName'])
        self.assertEqual(user.parent.gender, data['gender'])
        self.assertEqual(user.parent.location, data['location'])

    def test_update_wrong_gender(self):
        """Try to update with wrong gender value"""
        user = User.objects.get(email=self.login_data['email'])
        prev_gender = user.parent.gender
        response = self.client.put(self.url, data=json.dumps({'gender': '0'}), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
        user.refresh_from_db()
        self.assertEqual(prev_gender, user.parent.gender)


class AccountInfoStudentTest(BaseTest):
    """Tests using student data"""
    fixtures = ['01_core_users.json', '04_accounts_students.json']
    login_data = {
        'email': 'luisstudent2@yopmail.com',
        'password': 'T3st11ng'
    }

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/account-info/'.format(settings.HOSTNAME_PROTOCOL)

    def test_update_data(self):
        """Update data account"""
        # previous check
        user = User.objects.get(email=self.login_data['email'])
        self.assertIsNone(user.student.middle_name)
        self.assertIsNone(user.student.gender)
        self.assertEqual(user.student.location, '')

        data = {'middleName': 'M', 'gender': 'male', 'location': 'Oregon'}
        response = self.client.put(self.url, data=json.dumps(data), content_type='application/json')
        user.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(user.student.middle_name, data['middleName'])
        self.assertEqual(user.student.gender, data['gender'])
        self.assertEqual(user.student.location, data['location'])

    def test_update_wrong_gender(self):
        """Try to update with wrong gender"""
        user = User.objects.get(email=self.login_data['email'])
        prev_gender = user.student.gender
        response = self.client.put(self.url, data=json.dumps({'gender': '0'}), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
        user.refresh_from_db()
        self.assertEqual(prev_gender, user.student.gender)
