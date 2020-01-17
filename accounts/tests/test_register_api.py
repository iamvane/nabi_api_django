"""Tests for account creation with different roles: instructor, parent, student"""
import json

from django.conf import settings

from rest_framework import status
from rest_framework.test import APITestCase

from core.models import User, UserBenefits

from ..models import Instructor, Parent, Student


class CreateInstructorTest(APITestCase):

    def setUp(self):
        self.url = '{}/v1/register/'.format(settings.HOSTNAME_PROTOCOL)
        self.qty = Instructor.objects.count()
        self.qty_users = User.objects.count()
        self.payload = {
            "email": "instructor1@yopmail.com",
            "password": "123456",
            "role": "instructor",
            "birthday": "1990-11-19",
        }
        self.payload_all = {
            "email": "instructor2@yopmail.com",
            "password": "123456",
            "role": "instructor",
            "birthday": "1990-09-17",
            "gender": "female",
            "firstName": "Sara",
            "lastName": "Connor",
            "reference": "facebook",
            "termsAccepted": True,
        }
        self.payload_repeated = {
            "email": "instructor3@yopmail.com",
            "password": "123456",
            "role": "instructor",
            "birthday": "1990-12-07",
        }
        self.payload_missing_birthday = {
            "email": "instructor4@yopmail.com",
            "password": "123456",
            "role": "instructor",
            "gender": "female",
        }
        self.payload_missing_role = {
            "email": "instructor5@yopmail.com",
            "password": "123456",
            "birthday": "1990-09-17",
            "gender": "female",
        }

    def test_create_instructor(self):
        """Test instructor creation with minimal data (email, password, role, birthday)"""
        response = self.client.post(self.url, data=json.dumps(self.payload), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(Instructor.objects.count(), self.qty + 1)
        self.assertTrue(User.objects.filter(email=self.payload['email']).exists())
        self.assertTrue(User.objects.filter(username=self.payload['email']).exists())
        user_id = User.objects.get(username=self.payload['email']).id
        self.assertTrue(Instructor.objects.filter(user_id=user_id).exists())

    def test_create_instructor_complete_data(self):
        """Test instructor creation with complete data (email, password, role, birthday, gender)"""
        response = self.client.post(self.url, data=json.dumps(self.payload_all), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(Instructor.objects.count(), self.qty + 1)
        self.assertTrue(User.objects.filter(email=self.payload_all['email']).exists())
        self.assertTrue(User.objects.filter(username=self.payload_all['email']).exists())
        user_id = User.objects.get(username=self.payload_all['email']).id
        self.assertTrue(Instructor.objects.filter(user_id=user_id).exists())

    def test_create_instructor_twice(self):
        """Test instructor creation twice (same data)"""
        response = self.client.post(self.url, data=json.dumps(self.payload_repeated), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(Instructor.objects.count(), self.qty + 1)
        self.assertEqual(User.objects.count(), self.qty_users + 1)
        response = self.client.post(self.url, data=json.dumps(self.payload_repeated), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
        self.assertEqual(Instructor.objects.count(), self.qty + 1)
        self.assertEqual(User.objects.count(), self.qty_users + 1)

    def test_create_instructor_missing_birthday(self):
        """Test instructor creation with missing birthday info"""
        response = self.client.post(self.url, data=json.dumps(self.payload_missing_birthday),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
        self.assertEqual(Instructor.objects.count(), self.qty)

    def test_create_instructor_missing_role(self):
        """Test instructor creation with missing role info"""
        response = self.client.post(self.url, data=json.dumps(self.payload_missing_role),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
        self.assertEqual(Instructor.objects.count(), self.qty)


class CreateParentTest(APITestCase):

    def setUp(self):
        self.url = '{}/v1/register/'.format(settings.HOSTNAME_PROTOCOL)
        self.qty = Parent.objects.count()
        self.qty_users = User.objects.count()
        self.payload = {
            "email": "parent1@yopmail.com",
            "password": "123456",
            "role": "parent",
            "birthday": "1990-11-19",
        }
        self.payload_all = {
            "email": "parent2@yopmail.com",
            "password": "123456",
            "role": "parent",
            "birthday": "1990-09-17",
            "gender": "male",
            "firstName": "John",
            "lastName": "Connor",
            "reference": "foro",
            "termsAccepted": True,
        }
        self.payload_repeated = {
            "email": "parent3@yopmail.com",
            "password": "123456",
            "role": "parent",
            "birthday": "1990-08-16",
            "gender": "male",
        }
        self.payload_missing_birthday = {
            "email": "parent4@yopmail.com",
            "password": "123456",
            "role": "parent",
            "gender": "female",
        }
        self.payload_missing_role = {
            "email": "parent5@yopmail.com",
            "password": "123456",
            "birthday": "1990-09-17",
            "gender": "male",
        }

    def test_create_parent(self):
        """Test parent creation with minimal data (email, password, role, birthday)"""
        response = self.client.post(self.url, data=json.dumps(self.payload), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(Parent.objects.count(), self.qty + 1)
        self.assertTrue(User.objects.filter(email=self.payload['email']).exists())
        self.assertTrue(User.objects.filter(username=self.payload['email']).exists())
        user_id = User.objects.get(username=self.payload['email']).id
        self.assertTrue(Parent.objects.filter(user_id=user_id).exists())

    def test_create_parent_complete_data(self):
        """Test parent creation with complete data (email, password, role, birthday, gender)"""
        response = self.client.post(self.url, data=json.dumps(self.payload_all), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(Parent.objects.count(), self.qty + 1)
        self.assertTrue(User.objects.filter(email=self.payload_all['email']).exists())
        self.assertTrue(User.objects.filter(username=self.payload_all['email']).exists())
        user_id = User.objects.get(username=self.payload_all['email']).id
        self.assertTrue(Parent.objects.filter(user_id=user_id).exists())

    def test_create_parent_twice(self):
        """Test parent creation twice (same data)"""
        response = self.client.post(self.url, data=json.dumps(self.payload_repeated), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(Parent.objects.count(), self.qty + 1)
        self.assertEqual(User.objects.count(), self.qty_users + 1)
        response = self.client.post(self.url, data=json.dumps(self.payload_repeated), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
        self.assertEqual(Parent.objects.count(), self.qty + 1)
        self.assertEqual(User.objects.count(), self.qty_users + 1)

    def test_create_parent_missing_birthday(self):
        """Test parent creation with missing birthday info"""
        response = self.client.post(self.url, data=json.dumps(self.payload_missing_birthday),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
        self.assertEqual(Parent.objects.count(), self.qty)

    def test_create_parent_missing_role(self):
        """Test parent creation with missing role info"""
        response = self.client.post(self.url, data=json.dumps(self.payload_missing_role),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
        self.assertEqual(Parent.objects.count(), self.qty)


class CreateStudentTest(APITestCase):

    def setUp(self):
        self.url = '{}/v1/register/'.format(settings.HOSTNAME_PROTOCOL)
        self.qty = Student.objects.count()
        self.qty_users = User.objects.count()
        self.payload = {
            "email": "student1@yopmail.com",
            "password": "123456",
            "role": "student",
            "birthday": "1990-11-19",
        }
        self.payload_all = {
            "email": "student2@yopmail.com",
            "password": "123456",
            "role": "student",
            "birthday": "1990-09-17",
            "gender": "male",
            "firstName": "Tom",
            "lastName": "Connor",
            "reference": "friend",
            "termsAccepted": False,
        }
        self.payload_repeated = {
            "email": "student3@yopmail.com",
            "password": "123456",
            "role": "student",
            "birthday": "1990-08-16",
            "gender": "male",
        }
        self.payload_missing_birthday = {
            "email": "student4@yopmail.com",
            "password": "123456",
            "role": "student",
            "gender": "female",
        }
        self.payload_missing_role = {
            "email": "student5@yopmail.com",
            "password": "123456",
            "birthday": "1990-09-17",
            "gender": "male",
        }

    def test_create_student(self):
        """Test student creation with minimal data (email, password, role, birthday)"""
        response = self.client.post(self.url, data=json.dumps(self.payload), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(Student.objects.count(), self.qty + 1)
        self.assertTrue(User.objects.filter(email=self.payload['email']).exists())
        self.assertTrue(User.objects.filter(username=self.payload['email']).exists())
        user_id = User.objects.get(username=self.payload['email']).id
        self.assertTrue(Student.objects.filter(user_id=user_id).exists())

    def test_create_student_complete_data(self):
        """Test student creation with complete data (email, password, role, birthday, gender)"""
        response = self.client.post(self.url, data=json.dumps(self.payload_all), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(Student.objects.count(), self.qty + 1)
        self.assertTrue(User.objects.filter(email=self.payload_all['email']).exists())
        self.assertTrue(User.objects.filter(username=self.payload_all['email']).exists())
        user_id = User.objects.get(username=self.payload_all['email']).id
        self.assertTrue(Student.objects.filter(user_id=user_id).exists())

    def test_create_student_twice(self):
        """Test student creation twice (same data)"""
        response = self.client.post(self.url, data=json.dumps(self.payload_repeated), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(Student.objects.count(), self.qty + 1)
        self.assertEqual(User.objects.count(), self.qty_users + 1)
        response = self.client.post(self.url, data=json.dumps(self.payload_repeated), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
        self.assertEqual(Student.objects.count(), self.qty + 1)
        self.assertEqual(User.objects.count(), self.qty_users + 1)

    def test_create_student_missing_birthday(self):
        """Test student creation with missing birthday info"""
        response = self.client.post(self.url, data=json.dumps(self.payload_missing_birthday),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
        self.assertEqual(Student.objects.count(), self.qty)

    def test_create_student_missing_role(self):
        """Test student creation with missing role info"""
        response = self.client.post(self.url, data=json.dumps(self.payload_missing_role),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
        self.assertEqual(Student.objects.count(), self.qty)


class CreateUserWithReferringCodeTest(APITestCase):
    """Test creation of benefits due to registration of user with referringCode"""

    def setUp(self):
        self.url = '{}/v1/register/'.format(settings.HOSTNAME_PROTOCOL)
        instructor_data = {
            "email": "instructor1@yopmail.com",
            "password": "123456",
            "role": "instructor",
            "birthday": "1990-11-19",
        }
        response = self.client.post(self.url, data=json.dumps(instructor_data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.payload_referred_instructor = {
            "email": "instructor2@yopmail.com",
            "password": "123456",
            "role": "instructor",
            "birthday": "1990-10-18",
        }
        parent_data = {
            "email": "parent1@yopmail.com",
            "password": "123456",
            "role": "parent",
            "birthday": "1990-11-19",
        }
        response = self.client.post(self.url, data=json.dumps(parent_data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.payload_referred_parent = {
            "email": "parent2@yopmail.com",
            "password": "123456",
            "role": "parent",
            "birthday": "1990-10-18",
        }
        self.payload_another_referred_parent = {
            "email": "parent3@yopmail.com",
            "password": "123456",
            "role": "parent",
            "birthday": "1990-09-16",
        }
        student_data = {
            "email": "student1@yopmail.com",
            "password": "123456",
            "role": "student",
            "birthday": "1990-11-19",
        }
        response = self.client.post(self.url, data=json.dumps(student_data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.payload_referred_student = {
            "email": "student2@yopmail.com",
            "password": "123456",
            "role": "student",
            "birthday": "1990-10-18",
        }

    def test_create_instructor_referred(self):
        """Test instructor creation with referring code"""
        referring_user = User.objects.get(email='instructor1@yopmail.com')
        self.payload_referred_instructor['referringCode'] = referring_user.referral_token
        response = self.client.post('{}/v1/register/'.format(settings.HOSTNAME_PROTOCOL),
                                    data=json.dumps(self.payload_referred_instructor),
                                    content_type='application/json',)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertTrue(UserBenefits.objects.filter(
            user=User.objects.get(email=self.payload_referred_instructor['email']),
            user_origin=referring_user,
        ).exists())

    def test_create_parent_referred(self):
        """Test parent creation with referring code"""
        referring_user = User.objects.get(email='parent1@yopmail.com')
        self.payload_referred_parent['referringCode'] = referring_user.referral_token
        response = self.client.post('{}/v1/register/'.format(settings.HOSTNAME_PROTOCOL),
                                    data=json.dumps(self.payload_referred_parent),
                                    content_type='application/json',)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertTrue(UserBenefits.objects.filter(
            user=User.objects.get(email=self.payload_referred_parent['email']),
            user_origin=referring_user,
        ).exists())

    def test_create_another_parent_referred(self):
        """Test parent creation with referring code, from instructor"""
        referring_user = User.objects.get(email='instructor1@yopmail.com')
        self.payload_another_referred_parent['referringCode'] = referring_user.referral_token
        response = self.client.post('{}/v1/register/'.format(settings.HOSTNAME_PROTOCOL),
                                    data=json.dumps(self.payload_another_referred_parent),
                                    content_type='application/json',)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertTrue(UserBenefits.objects.filter(
            user=User.objects.get(email=self.payload_another_referred_parent['email']),
            user_origin=referring_user,
        ).exists())

    def test_create_student_referred(self):
        """Test student creation with referring code"""
        referring_user = User.objects.get(email='student1@yopmail.com')
        self.payload_referred_student['referringCode'] = referring_user.referral_token
        response = self.client.post('{}/v1/register/'.format(settings.HOSTNAME_PROTOCOL),
                                    data=json.dumps(self.payload_referred_student),
                                    content_type='application/json',)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertTrue(UserBenefits.objects.filter(
            user=User.objects.get(email=self.payload_referred_student['email']),
            user_origin=referring_user,
        ).exists())
