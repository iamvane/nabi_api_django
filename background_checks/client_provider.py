import base64
import requests

from django.conf import settings
from django.db.models import ObjectDoesNotExist

from core.models import ProviderRequest
from core.utils import send_admin_email

from .models import BackgroundCheckRequest, BackgroundCheckStep

PROVIDER_NAME = 'accurate'
CANDIDATE_REGISTER_STEP = 'candidate_register'
CANDIDATE_UPDATE_STEP = 'candidate_update'
ORDER_PLACE_STEP = 'order_place'


class AccurateApiClient:

    def __init__(self, path_resource):
        self.target_url = 'https://api.accuratebackground.com/v3/{}'.format(path_resource)

    def generate_auth_header(self):
        credentials_string = '{}:{}'.format(settings.ACCURATE_CLIENT_ID, settings.ACCURATE_CLIENT_SECRET)
        credentials_base64 = base64.b64encode(credentials_string.encode())
        return {'Authorization': 'Basic {}'.format(credentials_base64.decode())}

    def send_request(self, api_name, method='GET', headers=None, params=None, data=None):
        if params is None:
            params = {}
        if data is None:
            data = {}
        if headers is None:
            headers = {}
        provider = ProviderRequest(provider=PROVIDER_NAME, api_name=api_name, url_request=self.target_url,
                                   method=method, headers=headers, parameters=params, data=data)
        provider.save()
        headers.update(self.generate_auth_header())
        if method == "GET":
            response = requests.get(self.target_url, headers=headers)
        elif method == 'POST':
            response = requests.post(self.target_url, headers=headers, json=data)
        else:
            raise Exception('Method not allowed')
        provider.response_status = response.status_code
        resp_format = 'string'
        try:
            resp_content = response.json()
            resp_format = 'json'
            provider.response_content = resp_content
        except ValueError:
            resp_content = response.content.decode()
            provider.response_content_text = resp_content
        provider.save()
        if response.status_code >= 200 and response.status_code < 300:
            return {'pr_id': provider.id, 'code': 200, 'format': resp_format, 'content': resp_content}
        else:
            return {'pr_id': provider.id, 'code': response.status_code, 'format': resp_format, 'content': resp_content}

    def create_candidate(self, bg_request_id, instructor):
        """Request to create candidate API provider.
        bg_request_id allows to update info about this process in DB"""
        data = {'firstName': instructor.user.first_name, 'lastName': instructor.user.last_name,
                'email': instructor.user.email, 'middleName': '', 'suffix': ''}
        resp = self.send_request('candidate', method='POST', headers={'Content-Type': 'application/json'}, data=data)
        if resp['code'] == 200:
            if resp['format'] == 'json':
                # after request to provider, update entries in DB
                BackgroundCheckRequest.objects.filter(id=bg_request_id).update(
                    user=instructor.user, status=BackgroundCheckRequest.PRELIMINARY)
                bg_step = BackgroundCheckStep(request_id=bg_request_id, step=CANDIDATE_REGISTER_STEP,
                                              provider_request_id=resp['pr_id'])
                bg_step.resource_id = resp['content']['id']
                bg_step.data = {'id': resp['content']['id'], 'firstName': resp['content']['firstName'],
                                'lastName': resp['content']['lastName'], 'middleName': resp['content']['middleName'],
                                'suffix': resp['content']['suffix'], 'email': resp['content']['email']}
                bg_step.save()
                result = {'error_code': 0, 'bg_step_id': bg_step.id}
            else:
                result = {'error_code': 500, 'msg': 'Bad format response'}
        else:
            result = {'error_code': resp['code'], 'msg': resp['content']}
        return result

    def update_candidate(self, bg_request_id, instructor, old_data):
        """Request to update candidate API provider.
        bg_request_id allows to update info about this process in DB"""
        data = {}
        if old_data['firstName'] != instructor.user.first_name:
            data['firstName'] = instructor.user.first_name
        if old_data['lastName'] != instructor.user.first_name:
            data['lastName'] = instructor.user.last_name
        if old_data['email'] != instructor.user.first_name:
            data['email'] = instructor.user.email
        if not data:
            result = {'error_code': 500, 'msg': 'No data for update'}
        else:
            resp = self.send_request('candidate', method='PUT', data=data,
                                     headers={'Content-Type': 'application/x-www-form-urlencoded'})
            if resp['code'] == 200:
                if resp['format'] == 'json':
                    # after request to provider, create entries in DB
                    BackgroundCheckRequest.objects.filter(id=bg_request_id).update(
                        user=instructor.user, status=BackgroundCheckRequest.PRELIMINARY)
                    bg_step = BackgroundCheckStep(request_id=bg_request_id, step=CANDIDATE_UPDATE_STEP,
                                                  provider_request_id=resp['pr_id'])
                    bg_step.resource_id = resp['content']['id']
                    bg_step.data = {'id': resp['content']['id'], 'firstName': resp['content']['firstName'],
                                    'lastName': resp['content']['lastName'], 'middleName': resp['content']['middleName'],
                                    'suffix': resp['content']['suffix'], 'email': resp['content']['email']}
                    bg_step.save()
                    result = {'error_code': 0, 'bg_step_id': bg_step.id}
                else:
                    result = {'error_code': 500, 'msg': 'Bad format response'}
            else:
                result = {'error_code': resp['code'], 'msg': resp['content']}
        return result

    def place_order(self, bg_request_id, user, candidate_id, previous_step=None):
        """Request to place order API provider"""
        location = user.instructor.get_location(result_type='tuple')
        if not location:
            return {'error_code': 500, 'msg': 'User location is missing'}
        data = {'candidateId': candidate_id,
                'jobLocation': {'country': location[0], 'region': location[1], 'city': location[2]},
                'packageType': settings.ACCURATE_PLAN_PARAMETER, 'workflow': 'INTERACTIVE'}
        resp = self.send_request('order', method='POST', headers={'Content-Type': 'application/json'}, data=data)
        # after request to provider, create entries in DB
        if resp['code'] == 200:
            if resp['format'] == 'json':
                BackgroundCheckRequest.objects.filter(id=bg_request_id).update(
                    status=BackgroundCheckRequest.REQUESTED, observation='Request made to provider successfully')
                bg_step = BackgroundCheckStep(request_id=bg_request_id, step=ORDER_PLACE_STEP,
                                              provider_request_id=resp['pr_id'], previous_step=previous_step)
                bg_step.resource_id = resp['content']['id']
                bg_step.data = {'id': resp['content']['id'],
                                'candidateId': resp['content']['candidateId'],
                                'candidate': {
                                    'firstName': resp['content']['candidate']['firstName'],
                                    'lastName': resp['content']['candidate']['lastName'],
                                    'middleName': resp['content']['candidate']['middleName'],
                                    'suffix': resp['content']['candidate']['suffix'],
                                    'email': resp['content']['candidate']['email']
                                },
                                'jobLocation': {
                                    'country': resp['content']['jobLocation']['country'],
                                    'region': resp['content']['jobLocation']['region'],
                                    'region2': resp['content']['jobLocation']['region2'],
                                    'city': resp['content']['jobLocation']['city']
                                },
                                'packageType': resp['content']['packageType'],
                                'workflow': resp['content']['workflow'],
                                'status': resp['content']['status'],
                                'result': resp['content']['result'],
                                }
                bg_step.save()
                result = {'error_code': 0, 'bg_step_id': bg_step.id}
            else:
                result = {'error_code': 500, 'msg': 'Bad format response'}
        else:
            result = {'error_code': resp['code'], 'msg': resp['content']}
        return result

    def check_order(self, user):
        """Check status of last order for user"""
        try:
            bg_request = BackgroundCheckRequest.objects.filter(user=user).last()
            bg_step = BackgroundCheckStep.objects.filter(request=bg_request).last()
        except ObjectDoesNotExist:
            return {'error_code': 500, 'msg': 'There is no order to this user'}
        if bg_request.status != BackgroundCheckRequest.REQUESTED:
            return {'error_code': 500, 'msg': 'No pending order'}
        self.target_url += '/' + bg_step.resource_id
        resp = self.send_request('order', method='GET')
        if resp['code'] == 200:
            if resp['format'] == 'json':
                # get prev status
                qs_pr = ProviderRequest.objects.filter(url_request=self.target_url, method='GET').order_by('-id')
                if qs_pr.count() > 1:
                    prev_status = qs_pr[1].data.get('status')
                else:
                    prev_status = None
                data_result = {'id': resp['content']['id'], 'status': resp['content']['result'],
                               'provider_id': resp['pr_id'], 'previousStatus': prev_status,
                               'packageType': resp['content']['packageType'], 'workflow': resp['content']['workflow'],
                               'candidate': {'id': resp['content']['candidateId'],
                                             'firstName': resp['content']['candidate']['firstName'],
                                             'lastName': resp['content']['candidate']['lastName'],
                                             'middleName': resp['content']['candidate']['middleName'],
                                             'suffix': resp['content']['candidate']['suffix'],
                                             'email': resp['content']['candidate']['email'],
                                             }
                               }
                if data_result['status'] == 'COMPLETE':
                    bg_request.status = BackgroundCheckRequest.COMPLETE
                    bg_request.observation = 'Provider marks background check as completed'
                    bg_request.save()
                    send_admin_email('[INFO] Background check is completed',
                                     "The background check with id {} (instructor {}, id {}) was marked as complete."
                                     .format(bg_request.id, bg_request.instructor.display_name, bg_request.instructor.id)
                                     )
                elif bg_request.status == BackgroundCheckRequest.REQUESTED and data_result['status'] != prev_status:
                    if data_result['status'] == 'PENDING' and prev_status is not None:
                        send_admin_email('[INFO] Background check change its status',
                                         "The background check with id {bg_id} (instructor {ins_name}, id {ins_id}) "
                                         "had changed its status from {prev_status} to {curr_status}."
                                         .format(bg_id=bg_request.id, ins_name=bg_request.instructor.display_name,
                                                 ins_id=bg_request.instructor.id, prev_status=prev_status,
                                                 curr_status=data_result['status'])
                                         )
                result = {'error_code': 0, 'msg': data_result}
            else:
                result = {'error_code': 500, 'msg': 'Bad format response'}
        else:
            result = {'error_code': resp['code'], 'msg': resp['content']}
        return result
