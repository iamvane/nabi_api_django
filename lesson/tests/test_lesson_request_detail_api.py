import json

from django.conf import settings

from rest_framework import status

from accounts.tests.base_test_class import BaseTest

from ..models import LessonRequest


class LessonRequestDeleteTest(BaseTest):
    """Tests for delete lesson requests"""
    fixtures = ['01_core_users.json', '03_accounts_parents.json', '04_accounts_students.json',
                '05_lesson_instruments.json', '15_accounts_tiedstudents', '16_accounts_studentdetails',
                '01_lesson_requests.json']
    login_data = {
        'email': 'luisstudent@yopmail.com',
        'password': 'T3st11ng'
    }

    def setUp(self):
        super().setUp()
        self.url = '{}/v1/lesson-request-item/'.format(settings.HOSTNAME_PROTOCOL)
        self.qty = LessonRequest.objects.count()

    def test_success(self):
        """Successful request"""
        response = self.client.delete(self.url + '1/')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(LessonRequest.objects.count(), self.qty - 1)

    def test_fail(self):
        """Failed request"""
        response = self.client.delete(self.url + '15/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
        self.assertEqual(LessonRequest.objects.count(), self.qty)


class LessonRequestUpdateTest(BaseTest):
    """Tests for update lesson requests"""
    fixtures = ['01_core_users.json', '03_accounts_parents.json', '04_accounts_students.json',
                '05_lesson_instruments.json', '15_accounts_tiedstudents', '16_accounts_studentdetails',
                '01_lesson_requests.json']
    student_login_data = {
        'email': 'luisstudent@yopmail.com',
        'password': 'T3st11ng'
    }
    parent_login_data = {
        'email': 'luisparent@yopmail.com',
        'password': 'T3st11ng'
    }
    current_data = [
        {
            "title": "Piano Instructor needed in Boston MA",
            "message": "Hello, I am looking for a piano instructor",
            "instrument_id": 1,
            "skill_level": "beginner",
            "place_for_lessons": "home",
            "lessons_duration": "45 mins",
            "status": "no seen",
        },
        {
            "title": "Guitar Instructor needed",
            "message": "Hi, I am looking for a guitar instructor for my children",
            "instrument_id": 2,
            "skill_level": "beginner",
            "place_for_lessons": "home",
            "lessons_duration": "60 mins",
            "status": "no seen",
            "students": [1, 2],
        },
    ]

    def setUp(self):
        self.url = '{}/v1/lesson-request-item/'.format(settings.HOSTNAME_PROTOCOL)
        self.qty = LessonRequest.objects.count()

    def test_student_success(self):
        """Successful request, by student user. Make tests for changing fields independently"""
        self.login_data = self.student_login_data
        super().setUp()
        lesson_request = LessonRequest.objects.get(id=1)
        # update title
        self.assertEqual(lesson_request.title, self.current_data[0]['title'])
        response = self.client.put(self.url + '1/', content_type='application/json',
                                   data=json.dumps({'requestTitle': "A piano instructor is needed, in Boston"}))
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(LessonRequest.objects.count(), self.qty)
        lesson_request.refresh_from_db()
        self.assertEqual(lesson_request.title, "A piano instructor is needed, in Boston")
        # update message
        self.assertEqual(lesson_request.message, self.current_data[0]['message'])
        response = self.client.put(self.url + '1/', content_type='application/json',
                                   data=json.dumps({'requestMessage': "Hi, I'm searching for an instructor"}))
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(LessonRequest.objects.count(), self.qty)
        lesson_request.refresh_from_db()
        self.assertEqual(lesson_request.message, "Hi, I'm searching for an instructor")
        # update instrument
        self.assertEqual(lesson_request.instrument_id, self.current_data[0]['instrument_id'])
        response = self.client.put(self.url + '1/', content_type='application/json',
                                   data=json.dumps({'instrument': "flute"}))
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(LessonRequest.objects.count(), self.qty)
        lesson_request.refresh_from_db()
        self.assertEqual(lesson_request.instrument.name, "flute")
        # update skill_level
        self.assertEqual(lesson_request.skill_level, self.current_data[0]['skill_level'])
        response = self.client.put(self.url + '1/', content_type='application/json',
                                   data=json.dumps({'skillLevel': "intermediate"}))
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(LessonRequest.objects.count(), self.qty)
        lesson_request.refresh_from_db()
        self.assertEqual(lesson_request.skill_level, "intermediate")
        # update place_for_lessons
        self.assertEqual(lesson_request.place_for_lessons, self.current_data[0]['place_for_lessons'])
        response = self.client.put(self.url + '1/', content_type='application/json',
                                   data=json.dumps({'placeForLessons': "studio"}))
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(LessonRequest.objects.count(), self.qty)
        lesson_request.refresh_from_db()
        self.assertEqual(lesson_request.place_for_lessons, "studio")
        # update lessons_duration
        self.assertEqual(lesson_request.lessons_duration, self.current_data[0]['lessons_duration'])
        response = self.client.put(self.url + '1/', content_type='application/json',
                                   data=json.dumps({'lessonDuration': "90mins"}))
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(LessonRequest.objects.count(), self.qty)
        lesson_request.refresh_from_db()
        self.assertEqual(lesson_request.lessons_duration, "90mins")

    def test_parent_success(self):
        """Successful request, by parent user. Make tests for changing fields independently"""
        self.login_data = self.parent_login_data
        super().setUp()
        lesson_request = LessonRequest.objects.get(id=2)
        # update title
        self.assertEqual(lesson_request.title, self.current_data[1]['title'])
        response = self.client.put(self.url + '2/', content_type='application/json',
                                   data=json.dumps({'requestTitle': "An instructor is required"}))
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(LessonRequest.objects.count(), self.qty)
        lesson_request.refresh_from_db()
        self.assertEqual(lesson_request.title, "An instructor is required")
        # update message
        self.assertEqual(lesson_request.message, self.current_data[1]['message'])
        response = self.client.put(self.url + '2/', content_type='application/json',
                                   data=json.dumps({'requestMessage': "Hi, I'm searching for an instructor"}))
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(LessonRequest.objects.count(), self.qty)
        lesson_request.refresh_from_db()
        self.assertEqual(lesson_request.message, "Hi, I'm searching for an instructor")
        # update skill_level
        self.assertEqual(lesson_request.skill_level, self.current_data[1]['skill_level'])
        response = self.client.put(self.url + '2/', content_type='application/json',
                                   data=json.dumps({'skillLevel': "intermediate"}))
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(LessonRequest.objects.count(), self.qty)
        lesson_request.refresh_from_db()
        self.assertEqual(lesson_request.skill_level, "intermediate")
        # update students 1
        self.assertEqual(lesson_request.students.count(), 2)
        self.assertListEqual(list(lesson_request.students.values_list('id', flat=True)),
                             self.current_data[1]['students'])
        response = self.client.put(self.url + '2/', content_type='application/json',
                                   data=json.dumps({'students': [{"name": "Santiago", "age": 9},]})
                                   )
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(LessonRequest.objects.count(), self.qty)
        lesson_request.refresh_from_db()
        self.assertListEqual(list(lesson_request.students.values_list('id', flat=True)), [1, ])
        # update students 2
        self.assertEqual(lesson_request.students.count(), 1)
        self.assertListEqual(list(lesson_request.students.values_list('id', flat=True)), [1, ])
        response = self.client.put(self.url + '2/', content_type='application/json',
                                   data=json.dumps({'students': [{"name": "Santiago", "age": 9},
                                                                 {"name": "John", "age": 8}]
                                                    })
                                   )
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(LessonRequest.objects.count(), self.qty)
        lesson_request.refresh_from_db()
        self.assertListEqual(list(lesson_request.students.values_list('id', flat=True)), [1, 4])


class LessonRequestFetchTest(BaseTest):
    """Tests for fetching lesson requests"""
    fixtures = ['01_core_users.json', '03_accounts_parents.json', '04_accounts_students.json',
                '05_lesson_instruments.json', '15_accounts_tiedstudents', '16_accounts_studentdetails',
                '01_lesson_requests.json']
    student_login_data = {
        'email': 'luisstudent@yopmail.com',
        'password': 'T3st11ng'
    }
    parent_login_data = {
        'email': 'luisparent@yopmail.com',
        'password': 'T3st11ng'
    }
    current_data = [
        {
            "id": 1,
            "title": "Piano Instructor needed in Boston MA",
            "message": "Hello, I am looking for a piano instructor",
            "instrument": "piano",
            "skillLevel": "beginner",
            "placeForLessons": "home",
            "lessonDuration": "45 mins",
            "studentDetails": [],
        },
        {
            "id": 2,
            "title": "Guitar Instructor needed",
            "message": "Hi, I am looking for a guitar instructor for my children",
            "instrument": "guitar",
            "skillLevel": "beginner",
            "placeForLessons": "home",
            "lessonDuration": "60 mins",
            "studentDetails": [{"name": "Santiago", "age": 9}, {"name": "Teresa", "age": 7}],
        },
    ]

    def setUp(self):
        self.url = '{}/v1/lesson-request-item/'.format(settings.HOSTNAME_PROTOCOL)
        self.qty = LessonRequest.objects.count()

    def test_student_success(self):
        """Successful request, by student"""
        self.login_data = self.student_login_data
        super().setUp()
        response = self.client.get(self.url + '1/')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(LessonRequest.objects.count(), self.qty)
        self.assertDictEqual(response.json(), self.current_data[0])

    def test_student_fail(self):
        """Failed request, by student, with wrong id"""
        self.login_data = self.student_login_data
        super().setUp()
        response = self.client.get(self.url + '21/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
        self.assertEqual(LessonRequest.objects.count(), self.qty)

    def test_parent_success(self):
        """Successful request, by parent"""
        self.login_data = self.parent_login_data
        super().setUp()
        response = self.client.get(self.url + '2/')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode())
        self.assertEqual(LessonRequest.objects.count(), self.qty)
        self.assertDictEqual(response.json(), self.current_data[1])

    def test_parent_fail(self):
        """Failed request, by parent, with wrong id"""
        self.login_data = self.parent_login_data
        super().setUp()
        response = self.client.get(self.url + '22/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.content.decode())
        self.assertEqual(LessonRequest.objects.count(), self.qty)
