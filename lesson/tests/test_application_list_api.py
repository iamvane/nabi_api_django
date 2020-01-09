from django.conf import settings

from rest_framework import status

from accounts.tests.base_test_class import BaseTest

from ..models import Application


class ListApplicationLessonRequestTest(BaseTest):
    """Tests for get a list of lesson request's applications"""
    fixtures = ['01_core_users.json', '02_accounts_instructors.json', '03_accounts_parents.json',
                '04_accounts_students.json', '05_lesson_instruments.json', '06_accounts_availabilities.json',
                '08_accounts_employments.json', '15_accounts_tiedstudents', '16_accounts_studentdetails',
                '01_lesson_requests.json', '02_applications.json']
    login_data = {
        'email': 'luisstudent@yopmail.com',
        'password': 'T3st11ng'
    }

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/application-list/'.format(settings.HOSTNAME_PROTOCOL)
        self.qty = Application.objects.count()

    def test_success(self):
        """Get data of lesson request's applications successfully"""
        response = self.client.get(self.url + '1/',)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        resp_data = response.json()
        self.assertDictContained(
            {'id': 1, 'requestTitle': 'Piano Instructor needed in Boston MA',
             'dateCreated': '2019-12-17 13:51:49'}, resp_data
        )
        self.assertEqual(len(resp_data['applications']), 2)
        for application in resp_data['applications']:
            if application['instructorId'] == 1:
                self.assertDictEqual(application, {
                    'instructorId': 1, 'applicationMessage': "Hello I'm available for teaching lessons",
                    'applicationRate': '35.0000', 'age': 44, 'avatar': '', 'backgroundCheckStatus': 'NOT_VERIFIED',
                    'displayName': 'Luis I.', 'reviews': 0, 'yearsOfExperience': 6,
                    'availability': {'mon8to10': True, 'mon10to12': False, 'mon12to3': True, 'mon3to6': False,
                                     'mon6to9': False, 'tue8to10': False, 'tue10to12': False, 'tue12to3': False,
                                     'tue3to6': False, 'tue6to9': False, 'wed8to10': False, 'wed10to12': False,
                                     'wed12to3': False, 'wed3to6': False, 'wed6to9': False, 'thu8to10': False,
                                     'thu10to12': False, 'thu12to3': False, 'thu3to6': False, 'thu6to9': False,
                                     'fri8to10': False, 'fri10to12': False, 'fri12to3': False, 'fri3to6': False,
                                     'fri6to9': False, 'sat8to10': False, 'sat10to12': False, 'sat12to3': False,
                                     'sat3to6': False, 'sat6to9': False, 'sun8to10': False, 'sun10to12': False,
                                     'sun12to3': False, 'sun3to6': False, 'sun6to9': False}
                })
            else:
                self.assertDictEqual(application, {
                    'instructorId': 2, 'applicationMessage': "Hello I'm available",
                    'applicationRate': '45.0000', 'age': 44, 'avatar': '', 'backgroundCheckStatus': 'NOT_VERIFIED',
                    'displayName': 'Luis I.', 'reviews': 0, 'yearsOfExperience': 3,
                    'availability': {'mon8to10': False, 'mon10to12': False, 'mon12to3': False, 'mon3to6': False,
                                     'mon6to9': False, 'tue8to10': False, 'tue10to12': False, 'tue12to3': False,
                                     'tue3to6': False, 'tue6to9': False, 'wed8to10': False, 'wed10to12': False,
                                     'wed12to3': False, 'wed3to6': False, 'wed6to9': False, 'thu8to10': False,
                                     'thu10to12': False, 'thu12to3': False, 'thu3to6': False, 'thu6to9': True,
                                     'fri8to10': False, 'fri10to12': False, 'fri12to3': False, 'fri3to6': False,
                                     'fri6to9': False, 'sat8to10': False, 'sat10to12': False, 'sat12to3': False,
                                     'sat3to6': False, 'sat6to9': False, 'sun8to10': False, 'sun10to12': False,
                                     'sun12to3': False, 'sun3to6': False, 'sun6to9': False}
                })

    def test_not_applications(self):
        """Get data of lesson request which have not applications"""
        response = self.client.get(self.url + '3/',)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        resp_data = response.json()
        self.assertDictContained(
            {'id': 1, 'requestTitle': 'Flute Instructor needed',
             'dateCreated': '2019-12-18 16:12:35'}, resp_data
        )
        self.assertEqual(len(resp_data['applications']), 0)

    def test_request_not_exists(self):
        """Make a call providing wrong id (lesson request not exists)"""
        response = self.client.get(self.url + '8/',)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
