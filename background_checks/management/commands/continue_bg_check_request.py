import json

from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

from accounts.models import Instructor
from background_checks.models import BackgroundCheckRequest, BackgroundCheckStep
from background_checks.client_provider import AccurateApiClient, CANDIDATE_REGISTER_STEP, CANDIDATE_UPDATE_STEP
from core.constants import PY_PROCESSED

User = get_user_model()


class Command(BaseCommand):
    """Complete the process of request a background check for an instructor"""
    help = 'Complete the process of request a background check for an instructor. ' \
           'One of following parameters must be provided: email, user_id, instructor_id'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str)
        parser.add_argument('--instructor_id', type=int)
        parser.add_argument('--user_id', type=int)

    def handle(self, *args, **options):
        self.stdout.write('Starting ...')
        self.stdout.flush()
        if options.get('email') or options.get('user_id'):
            try:
                if options.get('email'):
                    field = 'email'
                    user = User.objects.get(email=options.get('email'))
                else:
                    field = 'id'
                    user = User.objects.get(id=options.get('user_id'))
            except User.DoesNotExist:
                self.stdout.write('There is not user with provided ' + field)
                self.stdout.flush()
                exit()
            if not hasattr(user, 'instructor'):
                self.stdout.write('User with provided {} is not an instructor'.format(field))
                self.stdout.flush()
                exit()
            instructor = user.instructor
        elif options.get('instructor_id'):
            try:
                instructor = Instructor.objects.get(id=options.get('instructor_id'))
                user = instructor.user
            except Instructor.DoesNotExist:
                self.stdout.write('There is not instructor with provided id')
                self.stdout.flush()
                exit()
        else:
            self.stdout.write('email, user_id or instructor_id value must be provided')
            self.stdout.flush()
            exit()
        pending_bg_check = instructor.bg_check_requests.filter(status=BackgroundCheckRequest.PRELIMINARY).last()
        if not pending_bg_check:
            self.stdout.write('There is not BackgroundCheck with PRELIMINARY status')
            self.stdout.flush()
            exit()

        bg_check_step = BackgroundCheckStep.objects.filter(request_id=pending_bg_check.id).last()
        if bg_check_step:
            if bg_check_step.step == CANDIDATE_REGISTER_STEP or bg_check_step.step == CANDIDATE_UPDATE_STEP:
                # call to create order
                provider_client = AccurateApiClient('order')
                resp_dict = provider_client.place_order(pending_bg_check.id, user,
                                                        bg_check_step.resource_id, bg_check_step)
                error = resp_dict.pop('error_code')
                if error:
                    self.stdout.write('Error in place order. bg_request_id: {} , bg_request_last_step_id: {}\n'
                                      'response_error_code={} , response_error_info='.format(pending_bg_check.id,
                                                                                             bg_check_step.id,
                                                                                             error,
                                                                                             json.dumps(resp_dict))
                                      )
                    self.stdout.flush()
                else:
                    # get related payment
                    pending_bg_check.payment.status = PY_PROCESSED
                    pending_bg_check.payment.save()
                    self.stdout.write('Order place successfully to Accurate provider')
                    self.stdout.flush()
            else:
                self.stdout.write('Unexpected last step in BG request: {}'.format(bg_check_step.step))
                self.stdout.write('Any action will be taken')
                self.stdout.flush()
        else:
            provider_client = AccurateApiClient('candidate')
            resp_dict = provider_client.create_candidate(pending_bg_check.id, instructor)
            error = resp_dict.pop('error_code')
            if error:
                self.stdout.write('Error creating candidate. bg_request_id: {}\n'
                                  'response_error_code={} , response_error_info='.format(pending_bg_check.id,
                                                                                         error,
                                                                                         json.dumps(resp_dict))
                                  )
                self.stdout.flush()
            else:
                bg_step = BackgroundCheckStep.objects.get(id=resp_dict['bg_step_id'])
                provider_client = AccurateApiClient('order')
                resp_dict = provider_client.place_order(pending_bg_check.id, user, bg_step.resource_id, bg_step)
                error = resp_dict.pop('error_code')
                if error:
                    self.stdout.write('Error in place order. bg_request_id: {} , bg_request_last_step_id: {}\n'
                                      'response_error_code={} , response_error_info='.format(pending_bg_check.id,
                                                                                             bg_check_step.id,
                                                                                             error,
                                                                                             json.dumps(resp_dict))
                                      )
                    self.stdout.flush()
                else:
                    # get related payment
                    pending_bg_check.payment.status = PY_PROCESSED
                    pending_bg_check.payment.save()
                    self.stdout.write('Order place successfully to Accurate provider')
                    self.stdout.flush()
