import base64
import requests

from django.conf import settings
from django.db.models import ObjectDoesNotExist

from core.constants import BG_STATUS_NOT_VERIFIED, BG_STATUS_PENDING, BG_STATUS_VERIFIED, BG_STATUS_WARNING
from core.models import ProviderRequest
from core.utils import send_admin_email

from .models import BackgroundCheckRequest, BackgroundCheckStep

PROVIDER_NAME = 'accurate'
CANDIDATE_REGISTER_STEP = 'candidate_register'
CANDIDATE_UPDATE_STEP = 'candidate_update'
ORDER_PLACE_STEP = 'order_place'
PRODUCT_SAFE_RESULTS = ['PENDING', 'COMPLETE', 'NO RECORD FOUND', 'VERIFIED', 'NOT APPLICABLE']


class AccurateApiClient:

    def __init__(self, path_resource):
        self.target_url = 'https://api.accuratebackground.com/v3/{}'.format(path_resource)

    def generate_auth_header(self):
        credentials_string = '{}:{}'.format(settings.ACCURATE_CLIENT_ID, settings.ACCURATE_CLIENT_SECRET)
        credentials_base64 = base64.b64encode(credentials_string.encode())
        return {'Authorization': 'Basic {}'.format(credentials_base64.decode())}

    def send_request(self, api_name, method='GET', headers=None, params=None, data=None):
        """A registry in ProviderRequest is created, in order to have a record about communication to Accurate API"""
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
        bg_request_id allows to update info about this process in DB
        If response of Accurate API is successful, a registry in BackgroundCheckStep is created.
        Returned result:
           {'provider_id': jj, 'error_code': 0, 'bg_step_id': nn} on success
           {'provider_id': jj, 'error_code': kk, 'msg': 'details'}"""
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
                result = {'provider_id': resp['pr_id'], 'error_code': 0, 'bg_step_id': bg_step.id}
            else:
                result = {'provider_id': resp['pr_id'], 'error_code': 500, 'msg': 'Bad format response'}
        else:
            result = {'provider_id': resp['pr_id'], 'error_code': resp['code'], 'msg': resp['content']}
        return result

    def update_candidate(self, bg_request_id, instructor, old_data):
        """Request to update candidate API provider.
        bg_request_id allows to update info about this process in DB
        If response of Accurate API is successful, a registry in BackgroundCheckStep is created.
        Returned result:
           {'provider_id': jj, 'error_code': 0, 'bg_step_id': nn}   on success
           {'provider_id': jj, 'error_code': kk, 'msg': 'details'}   on failure"""
        data = {}
        if old_data['firstName'] != instructor.user.first_name:
            data['firstName'] = instructor.user.first_name
        if old_data['lastName'] != instructor.user.first_name:
            data['lastName'] = instructor.user.last_name
        if old_data['email'] != instructor.user.first_name:
            data['email'] = instructor.user.email
        if not data:
            result = {'provider_id': 0, 'error_code': 500, 'msg': 'No data for update'}
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
                    result = {'provider_id': resp['pr_id'], 'error_code': 0, 'bg_step_id': bg_step.id}
                else:
                    result = {'provider_id': resp['pr_id'], 'error_code': 500, 'msg': 'Bad format response'}
            else:
                result = {'provider_id': resp['pr_id'], 'error_code': resp['code'], 'msg': resp['content']}
        return result

    def place_order(self, bg_request_id, user, candidate_id, previous_step=None):
        """Request to place order API provider
        If response of Accurate API is successful, a registry in BackgroundCheckStep is created
        Side effects:
          - Background Check Request is marked as requested.
          - Instructor's bg_status is set to PENDING.
        Returned result:
           {'provider_id': jj, 'error_code': 0, 'bg_step_id': nn}   on success
           {'provider_id': jj, 'error_code': kk, 'msg': 'details'}   on failure"""
        location = user.instructor.get_location(result_type='tuple')
        if not location:
            return {'provider_id': 0, 'error_code': 500, 'msg': 'User location is missing'}
        data = {'candidateId': candidate_id,
                'jobLocation': {'country': location[0], 'region': location[1], 'city': location[2]},
                'packageType': settings.ACCURATE_PLAN_PARAMETER, 'workflow': 'INTERACTIVE'}
        if settings.ACCURATE_PLAN_ADDITIONALS:
            data['additionalProductTypes'] = []
            for additional in settings.ACCURATE_PLAN_ADDITIONALS:
                data['additionalProductTypes'].append({"productType": additional})
        resp = self.send_request('order', method='POST', headers={'Content-Type': 'application/json'}, data=data)
        # after request to provider, create entries in DB
        if resp['code'] == 200:
            if resp['format'] == 'json':
                BackgroundCheckRequest.objects.filter(id=bg_request_id).update(
                    status=BackgroundCheckRequest.REQUESTED, observation='Request made to provider successfully')
                bg_request = BackgroundCheckRequest.objects.get(id=bg_request_id)
                bg_request.instructor.bg_status = BG_STATUS_PENDING
                bg_request.instructor.save()
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
                result = {'provider_id': resp['pr_id'], 'error_code': 0, 'bg_step_id': bg_step.id}
            else:
                result = {'provider_id': resp['pr_id'], 'error_code': 500, 'msg': 'Bad format response'}
        else:
            result = {'provider_id': resp['pr_id'], 'error_code': resp['code'], 'msg': resp['content']}
        return result

    def check_order(self, user):
        """Check status of last order for user"""
        try:
            bg_request = BackgroundCheckRequest.objects.filter(user=user).last()
            bg_step = BackgroundCheckStep.objects.filter(request=bg_request).last()
        except ObjectDoesNotExist:
            return {'provider_id': 0, 'error_code': 500, 'msg': 'There is no order to this user'}
        if bg_request.status != BackgroundCheckRequest.REQUESTED:
            return {'provider_id': 0, 'error_code': 500, 'msg': 'No pending order'}
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
                data_result = {'id': resp['content']['id'],
                               'status': resp['content']['status'], 'result': resp['content']['result'],
                               'provider_id': resp['pr_id'], 'previousStatus': prev_status,
                               'packageType': resp['content']['packageType'], 'workflow': resp['content']['workflow'],
                               'additionalProductTypes': resp['content']['additionalProductTypes'],
                               'products': resp['content']['products'],
                               'candidate': {'id': resp['content']['candidateId'],
                                             'firstName': resp['content']['candidate']['firstName'],
                                             'lastName': resp['content']['candidate']['lastName'],
                                             'middleName': resp['content']['candidate']['middleName'],
                                             'suffix': resp['content']['candidate']['suffix'],
                                             'email': resp['content']['candidate']['email'],
                                             },
                               'percentageComplete': resp['content']['percentageComplete'],
                               'createdAt': bg_request.created_at.strftime('%Y-%m-%d %H:%M:%S')
                               }
                if bg_request.provider_results.get('status') != data_result['status'] \
                    or (bg_request.provider_results.get('status') == 'COMPLETE'
                        and bg_request.provider_results.get('result') == 'NEEDS REVIEW'
                        and data_result['result'] != 'NEEDS REVIEW'):
                    if data_result['status'] == 'OTHER INFO NEEDED':
                        send_admin_email('[INFO] Background check needs information',
                                         "The background check with id {bg_id} (instructor {ins_name}, id {ins_id}) "
                                         "had changed its status from {prev_status} to {curr_status}."
                                         .format(bg_id=bg_request.id,
                                                 ins_name=bg_request.instructor.display_name,
                                                 ins_id=bg_request.instructor.id,
                                                 prev_status=bg_request.provider_results.get('status'),
                                                 curr_status=data_result['status'])
                                         )
                    elif data_result['status'] == 'CANCELLED':
                        bg_request.status = BackgroundCheckRequest.CANCELLED
                        bg_request.instructor.bg_status = BG_STATUS_NOT_VERIFIED
                        bg_request.instructor.save()
                        send_admin_email('[ALERT] Background check was cancelled',
                                         "The background check with id {bg_id} (instructor {ins_name}, id {ins_id}) "
                                         "was cancelled, and status in Instructor remains as PENDING."
                                         .format(bg_id=bg_request.id,
                                                 ins_name=bg_request.instructor.display_name,
                                                 ins_id=bg_request.instructor.id)
                                         )
                    elif data_result['status'] == 'DISPUTED':
                        send_admin_email('[INFO] Background check was disputed by instructor',
                                         "The background check with id {bg_id} (instructor {ins_name}, id {ins_id}) "
                                         "was disputed, previous status was {prev_status}."
                                         .format(bg_id=bg_request.id,
                                                 ins_name=bg_request.instructor.display_name,
                                                 ins_id=bg_request.instructor.id,
                                                 prev_status=bg_request.provider_results.get('status'))
                                         )
                    elif data_result['status'] == 'COMPLETE':
                        if data_result['result'] == 'FAIL':
                            bg_request.status = BackgroundCheckRequest.COMPLETE
                            bg_request.observation = 'Provider background check result was FAIL'
                            bg_request.instructor.bg_status = BG_STATUS_WARNING
                            bg_request.instructor.save()
                        elif data_result['result'] == 'PASS':
                            bg_request.status = BackgroundCheckRequest.COMPLETE
                            bg_request.observation = 'Provider background check result was PASS'
                            bg_request.instructor.bg_status = BG_STATUS_VERIFIED
                            bg_request.instructor.save()
                        elif data_result['result'] == 'NOT APPLICABLE':
                            bg_request.status = BackgroundCheckRequest.COMPLETE
                            found_list = [
                                'Product: {}, flag: {}, result: {}.'.format(product['productType'], product['flag'],
                                                                            product['result'])
                                for product in resp['content']['products']
                                if product['flag'] or (product['result'] not in PRODUCT_SAFE_RESULTS)
                            ]
                            if found_list:
                                bg_request.observation = 'Provider result products were interpreted as FAIL'
                                bg_request.instructor.bg_status = BG_STATUS_WARNING
                                bg_request.instructor.save()
                                send_admin_email('[ADVICE] Background check was interpreted as FAIL',
                                                 "In the background check (id: " + str(bg_request.id)
                                                 + ") the following was found:\n\n"
                                                 + '\n'.join(found_list))
                            else:
                                bg_request.observation = 'Provider result products were interpreted as PASS'
                                bg_request.instructor.bg_status = BG_STATUS_VERIFIED
                                bg_request.instructor.save()
                        elif data_result['result'] == 'NEEDS REVIEW':
                            send_admin_email('[ALERT] Background check needs to be reviewed',
                                             "The background check with id {bg_id} (instructor {ins_name}, id {ins_id}) "
                                             "should be reviewed, previous status was {prev_status}."
                                             .format(bg_id=bg_request.id,
                                                     ins_name=bg_request.instructor.display_name,
                                                     ins_id=bg_request.instructor.id,
                                                     prev_status=bg_request.provider_results.get('status'))
                                             )
                    bg_request.provider_results = {'status': data_result['status'], 'result': data_result['result']}
                    bg_request.save()
                    result = {'provider_id': resp['pr_id'], 'error_code': 0, 'msg': data_result}
                else:
                    result = {'provider_id': resp['pr_id'], 'error_code': 0, 'msg': data_result}
            else:
                result = {'provider_id': resp['pr_id'], 'error_code': 500, 'msg': 'Bad format response'}
        else:
            result = {'provider_id': resp['pr_id'], 'error_code': resp['code'], 'msg': resp['content']}
        return result
