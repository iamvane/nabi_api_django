"""Tests for build-profile API"""
import json

from django.conf import settings

from rest_framework import status

from accounts.models import User

from .base_test_class import BaseTest


class BuildProfileInstructorTest(BaseTest):
    fixtures = ['01_core_users.json', '02_accounts_instructors.json']
    login_data = {
        'email': 'luisinstruct2@yopmail.com',
        'password': 'T3st11ng'
    }

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/build-profile/'.format(settings.HOSTNAME_PROTOCOL)

    def test_update_data(self):
        """Test for updating instructor profile data"""
        user = User.objects.get(email=self.login_data['email'])
        self.assertIsNone(user.instructor.bio_title)
        self.assertIsNone(user.instructor.bio_description)
        self.assertIsNone(user.instructor.music)
        data = {"bioTitle": "An amateur musician",
                "bioDescription": "I'm an amateur musician instructor",
                "music": ["flute", "pan flute"]
                }
        response = self.client.put(self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, msg=response.content.decode())
        user.refresh_from_db()
        self.assertEqual(user.instructor.bio_title, data['bioTitle'])
        self.assertEqual(user.instructor.bio_description, data['bioDescription'])
        self.assertEqual(user.instructor.music, data['music'])

    def test_update_title_only(self):
        """Test to set instructor bio_title only"""
        user = User.objects.get(email=self.login_data['email'])
        self.assertIsNone(user.instructor.bio_title)
        self.assertIsNone(user.instructor.bio_description)
        self.assertIsNone(user.instructor.music)
        data = {"bioTitle": "A musician"}
        response = self.client.put(self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, msg=response.content.decode())
        user.refresh_from_db()
        self.assertEqual(user.instructor.bio_title, data['bioTitle'])
        self.assertIsNone(user.instructor.bio_description)
        self.assertIsNone(user.instructor.music)
