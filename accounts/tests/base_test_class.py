import operator

from django.conf import settings

from rest_framework import status
from rest_framework.test import APITestCase


class BaseTest(APITestCase):
    login_data = {
        'email': 'address@provider.com',
        'password': 'mypass'
    }

    def get_token(self, email, password):
        """Return user's token from provided email and password"""
        url = '{}/v1/api-token/'.format(settings.HOSTNAME_PROTOCOL)
        response = self.client.post(url, {'email': email, 'password': password})
        if response.status_code == status.HTTP_200_OK:
            return response.json()['access']
        else:
            return ''

    def setUp(self):
        """Set token authorization in client"""
        token = self.get_token(**self.login_data)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(token))

    def assertDictContained(self, sub_dic, super_dic):
        """Check whether sub_dic is contained in super_dic"""
        all_keys = dict.fromkeys(super_dic, 1)
        not_contained = False
        for key, value in sub_dic.items():
            if all_keys.get(key):
                if super_dic[key] != value:
                    not_contained = True
                    break
            else:
                not_contained = True
                break
        return not not_contained

    def assertDictListUnsorted(self, list1, list2, field_name):
        """Check whether list1 and list2 are equals, which are sorted before, by provided field_name"""
        list1_sorted = sorted(list1, key=operator.itemgetter(field_name))
        list2_sorted = sorted(list2, key=operator.itemgetter(field_name))
        if list1_sorted == list2_sorted:
            return True
        else:
            return False
