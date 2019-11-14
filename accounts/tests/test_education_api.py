"""Tests for education API"""
import json
import operator

from django.conf import settings

from rest_framework import status

from .base_test_class import BaseTest


class EducationTest(BaseTest):
    fixtures = ['01_core_users.json', '02_accounts_instructors.json', '07_accounts_educations.json']
    login_data = {
        'email': 'luisinstruct@yopmail.com',
        'password': 'T3st11ng'
    }
    current_data = [{"id": 1, "school": "Hopkins", "graduationYear": 2003, "degreeType": "certification",
                     "fieldOfStudy": "Math", "schoolLocation": "Utah"},
                    {"id": 2, "school": "Oregon", "graduationYear": 1997, "degreeType": "certification",
                     "fieldOfStudy": "Law", "schoolLocation": "Kennedy avenue"}]

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/education/'.format(settings.HOSTNAME_PROTOCOL)

    def test_get_data(self):
        """Test getting data"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        list_response = response.json()
        list_response = sorted(list_response, key=operator.itemgetter('id'))
        self.assertListEqual(list_response, self.current_data)

    def test_post_data(self):
        """Test storing data"""
        data = {"school": "Michigan", "graduationYear": 2002, "degreeType": "bachelors",
                "fieldOfStudy": "Chemistry", "schoolLocation": "4th street"}
        response = self.client.post(self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        list_response = response.json()
        list_response = sorted(list_response, key=operator.itemgetter('id'))
        dic_data = list_response[-1]
        self.assertDictContained(data, dic_data)

    def test_storing_wrong_data(self):
        """Test storing wrong data"""
        data = {"school": "Michigan", "graduationYear": 2002,
                "degreeType": "diplopma",
                "fieldOfStudy": "Chemistry", "schoolLocation": "4th street"}
        response = self.client.post(self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())


class EducationEmptyTest(BaseTest):
    fixtures = ['01_core_users.json', '02_accounts_instructors.json', '07_accounts_educations.json']
    login_data = {
        'email': 'luisinstruct2@yopmail.com',
        'password': 'T3st11ng'
    }
    current_data = []

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/education/'.format(settings.HOSTNAME_PROTOCOL)

    def test_get_data(self):
        """Test getting data (no entries)"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        list_response = response.json()
        self.assertListEqual(list_response, self.current_data)


class ItemEducationTest(BaseTest):
    fixtures = ['01_core_users.json', '02_accounts_instructors.json', '07_accounts_educations.json']
    login_data = {
        'email': 'luisinstruct@yopmail.com',
        'password': 'T3st11ng'
    }
    current_data = [{"id": 1, "school": "Hopkins", "graduationYear": 2003, "degreeType": "certification",
                     "fieldOfStudy": "Math", "schoolLocation": "Utah"},
                    {"id": 2, "school": "Oregon", "graduationYear": 1997, "degreeType": "certification",
                     "fieldOfStudy": "Law", "schoolLocation": "Kennedy avenue"}]

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/education/'.format(settings.HOSTNAME_PROTOCOL)

    def test_put_data(self):
        """Test updating data"""
        new_data = {"graduationYear": 2002, "degreeType": "bachelors"}
        list_data = self.current_data[:]
        list_data[-1].update(new_data)
        response = self.client.put(self.url + str(self.current_data[-1]['id']) + '/', data=json.dumps(new_data),
                                   content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        list_response = response.json()
        list_response = sorted(list_response, key=operator.itemgetter('id'))
        dic_data = list_response[-1]
        self.assertDictEqual(list_data[-1], dic_data)

    def test_put_wrong_data(self):
        """Test trying to update data with wrong value"""
        new_data = {"graduationYear": 2002, "degreeType": "diploma"}
        response = self.client.put(self.url + str(self.current_data[-1]['id']) + '/', data=json.dumps(new_data),
                                   content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())

    def test_delete_data(self):
        """Test deleting data (an education entry)"""
        # get current ids
        list_current = [item['id'] for item in self.current_data]
        list_current.sort()
        prev_length = len(list_current)

        response = self.client.delete(self.url + str(list_current[-1]) + '/')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        list_response_new = [item['id'] for item in response.json()]
        list_response_new.sort()
        self.assertLess(len(list_response_new), prev_length)
        self.assertListEqual(list_response_new, list_current[:-1])

    def test_delete_data_wrong_id(self):
        """Test deleting data (an education entry)"""
        # check
        list_current = [item['id'] for item in self.current_data]
        self.assertNotIn(10, list_current)

        response = self.client.delete(self.url + '10/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
