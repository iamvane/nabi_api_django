"""Tests for employment API"""
import json
import operator

from django.conf import settings

from rest_framework import status

from .base_test_class import BaseTest


class EmploymentTest(BaseTest):
    fixtures = ['01_core_users.json', '02_accounts_instructors.json', '08_accounts_employments.json']
    login_data = {
        'email': 'luisinstruct@yopmail.com',
        'password': 'T3st11ng'
    }
    current_data = [{"id": 1, "employer": "Enterprise", "jobTitle": "Backend", "jobLocation": "here",
                     "fromMonth": "august", "fromYear": 2015, "toMonth": None, "toYear": None,
                     "stillWorkHere": True},
                    {"id": 2, "employer": "Company", "jobTitle": "Employer", "jobLocation": "some place",
                     "fromMonth": "march", "fromYear": 2010, "toMonth": "october", "toYear": 2012,
                     "stillWorkHere": False}]

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/employment/'.format(settings.HOSTNAME_PROTOCOL)

    def test_get_data(self):
        """Test getting data"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        list_response = response.json()
        list_response = sorted(list_response, key=operator.itemgetter('id'))
        self.assertListEqual(list_response, self.current_data)

    def test_post_data(self):
        """Test storing data"""
        data = {"employer": "Trading Ltd", "jobTitle": "Assistant", "jobLocation": "5th street",
                "fromMonth": "january", "fromYear": 2007, "toMonth": "june", "toYear": 2010,
                "stillWorkHere": False}
        response = self.client.post(self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        list_response = response.json()
        list_response = sorted(list_response, key=operator.itemgetter('id'))
        dic_data = list_response[-1]
        self.assertDictContained(data, dic_data)

    def test_post_data2(self):
        """Test storing data without stillWorkHere value"""
        data = {"employer": "Trading Ltd", "jobTitle": "Assistant", "jobLocation": "5th street",
                "fromMonth": "january", "fromYear": 2007, "toMonth": "june", "toYear": 2010}
        response = self.client.post(self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        list_response = response.json()
        list_response = sorted(list_response, key=operator.itemgetter('id'))
        dic_data = list_response[-1]
        self.assertDictContained(data, dic_data)

    def test_post_data3(self):
        """Test storing another data"""
        data = {"employer": "Trading Ltd", "jobTitle": "Assistant", "jobLocation": "5th street",
                "fromMonth": "january", "fromYear": 2007, "stillWorkHere": True}
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
        data = {"employer": "Trading Ltd", "jobTitle": "Assistant", "jobLocation": "5th street",
                "fromMonth": "something",
                "fromYear": 2007, "toMonth": "another", "toYear": 2010, "stillWorkHere": False}
        response = self.client.post(self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())

    def test_storing_missing_data(self):
        """Test storing missing data (stillWorkHere)"""
        data = {"employer": "Trading Ltd", "jobTitle": "Assistant", "jobLocation": "5th street",
                "fromMonth": "january", "fromYear": 2007}
        response = self.client.post(self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())


class EmploymentEmptyTest(BaseTest):
    fixtures = ['01_core_users.json', '02_accounts_instructors.json', '08_accounts_employments.json']
    login_data = {
        'email': 'luisinstruct2@yopmail.com',
        'password': 'T3st11ng'
    }
    current_data = []

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/employment/'.format(settings.HOSTNAME_PROTOCOL)

    def test_get_data(self):
        """Test getting data"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        list_response = response.json()
        self.assertListEqual(list_response, self.current_data)


class ItemEmploymentTest(BaseTest):
    fixtures = ['01_core_users.json', '02_accounts_instructors.json', '08_accounts_employments.json']
    login_data = {
        'email': 'luisinstruct@yopmail.com',
        'password': 'T3st11ng'
    }
    current_data = [{"id": 1, "employer": "Enterprise", "jobTitle": "Backend", "jobLocation": "here",
                     "fromMonth": "august", "fromYear": 2015, "toMonth": None, "toYear": None,
                     "stillWorkHere": True},
                    {"id": 2, "employer": "Company", "jobTitle": "Employer", "jobLocation": "some place",
                     "fromMonth": "march", "fromYear": 2010, "toMonth": "october", "toYear": 2012,
                     "stillWorkHere": False}]

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/employment/'.format(settings.HOSTNAME_PROTOCOL)

    def test_put_data(self):
        """Test updating data"""
        new_data = {"jobTitle": "Manager Assistant"}
        list_data = self.current_data[:]
        list_data[-1].update(new_data)
        response = self.client.put(self.url + str(list_data[-1]['id']) + '/', data=json.dumps(new_data),
                                   content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        list_response = response.json()
        list_response = sorted(list_response, key=operator.itemgetter('id'))
        self.assertListEqual(list_response, list_data)

    def test_put_wrong_data(self):
        """Test trying to update data with wrong value"""
        new_data = {"fromMonth": "another"}
        response = self.client.put(self.url + str(self.current_data[-1]['id']) + '/', data=json.dumps(new_data),
                                   content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())

    def test_delete_data(self):
        """Test deleting data (an education entry)"""
        response = self.client.delete(self.url + str(self.current_data[-1]['id']) + '/')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        list_response_new = sorted(response.json(), key=operator.itemgetter('id'))
        self.assertLess(len(list_response_new), len(self.current_data))
        self.assertListEqual(list_response_new, self.current_data[:-1])

    def test_delete_data_wrong_id(self):
        """Test deleting data (an employment entry)"""
        # get current ids
        list_current = [item['id'] for item in self.current_data]
        self.assertNotIn(10, list_current)

        response = self.client.delete(self.url + '10/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
