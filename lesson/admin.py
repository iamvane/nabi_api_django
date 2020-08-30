from django.contrib.auth import get_user_model
from django.contrib import admin
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import Instructor, TiedStudent
from accounts.utils import add_to_email_list_v2
from core.constants import LESSON_REQUEST_ACTIVE, LESSON_REQUEST_CLOSED, PY_APPLIED
from core.models import ScheduledEmail, TaskLog, UserBenefits
from lesson.models import Instrument
from payments.models import Payment

from .models import Application, InstructorAcceptanceLessonRequest, Lesson, LessonBooking, LessonRequest
from .tasks import (send_booking_alert, send_booking_invoice, send_info_grade_lesson,
                    send_instructor_grade_lesson, send_lesson_reschedule, send_lesson_info_instructor,
                    send_lesson_info_student_parent, send_request_alert_instructors)

User = get_user_model()


class InstructorAcceptanceLessonRequestAdmin(admin.ModelAdmin):
    list_display = ('instructor', 'request_id', 'accept', )
    search_fields = ('instructor__user__email', 'request__id', )
    list_filter = ('accept', )


class InstrumentAdmin(admin.ModelAdmin):
    fields = ('name', )
    search_fields = ('name', )
    ordering = ['name']


class ApplicationAdmin(admin.ModelAdmin):
    fields = ('view_request', 'request', 'instructor', 'rate', 'message', )
    list_display = ('pk', 'get_instructor_email', 'request_id', 'created_at', )
    readonly_fields = ('view_request', )

    def get_instructor_email(self, obj):
        return obj.instructor.user.email
    get_instructor_email.short_description = 'user email'
    get_instructor_email.admin_order_field = 'instructor__user__email'

    def view_request(self, obj):
        return 'id: {} ({})'.format(obj.request.id, obj.request.user.email)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'request':
            kwargs['queryset'] = LessonRequest.objects.order_by('id')
        elif db_field.name == 'instructor':
            kwargs['queryset'] = Instructor.objects.order_by('user__email')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class LessonBookingAdmin(admin.ModelAdmin):
    fields = ('view_application', 'application', 'request', 'user', 'tied_student', 'instructor', 'rate',
              'quantity', 'total_amount', 'description', 'payment', 'status')
    list_display = ('pk', 'get_user_email', 'application_id', 'quantity', 'total_amount', 'status', )
    list_filter = ('status', )
    readonly_fields = ('view_application', )
    search_fields = ('user__email', )

    def get_user_email(self, obj):
        return '{email} (id: {id})'.format(email=obj.user.email, id=obj.user_id)
    get_user_email.short_description = 'user email'
    get_user_email.admin_order_field = 'user__email'

    def view_application(self, obj):
        return 'id: {} ({})'.format(obj.application.pk, obj.application.instructor.user.email)
    view_application.short_description = 'application info'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'user':
            kwargs['queryset'] = User.objects.filter(Q(student__isnull=False) | Q(parent__isnull=False)
                                                     ).order_by('email')
        elif db_field.name == 'request':
            kwargs['queryset'] = LessonRequest.objects.order_by('id')
        elif db_field.name == 'application':
            kwargs['queryset'] = Application.objects.order_by('id')
        elif db_field.name == 'instructor':
            kwargs['queryset'] = Instructor.objects.order_by('user__email')
        elif db_field.name == 'payment':
            kwargs['queryset'] = Payment.objects.order_by('id')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.refresh_from_db()
        if not change:   # on creation
            if obj.status == LessonBooking.TRIAL:
                if obj.request:
                    obj.request.status = LESSON_REQUEST_CLOSED
                    obj.request.save()
                    lesson = Lesson.objects.create(booking=obj, scheduled_datetime=obj.request.trial_proposed_datetime,
                                                   scheduled_timezone=obj.request.trial_proposed_timezone,
                                                   instructor=obj.instructor, rate=obj.rate)
                else:
                    lesson = Lesson.objects.create(booking=obj, instructor=obj.instructor, rate=obj.rate)
                if not obj.application and not obj.request:
                    lesson_request = obj.create_lesson_request()
                    if lesson_request:
                        obj.request = lesson_request
                        obj.save()
                add_to_email_list_v2(obj.request.user, ['trial_to_booking'], ['customer_to_request'])
                task_log = TaskLog.objects.create(task_name='send_lesson_info_student_parent',
                                                  args={'lesson_id': lesson.id})
                send_lesson_info_student_parent.delay(lesson.id, task_log.id)
            else:
                with transaction.atomic():
                    if obj.payment:
                        obj.payment.status = PY_APPLIED
                        obj.payment.save()
                    if obj.application:
                        obj.application.request.status = LESSON_REQUEST_CLOSED
                        obj.application.request.save()
                # update data for applicable benefits
                UserBenefits.update_applicable_benefits(request.user)
                add_to_email_list_v2(request.user, [], ['trial_to_booking'])
                if obj.payment:
                    task_log = TaskLog.objects.create(task_name='send_booking_invoice', args={'booking_id': obj.id})
                    send_booking_invoice.delay(obj.id, task_log.id)
                if obj.application:
                    task_log = TaskLog.objects.create(task_name='send_booking_alert', args={'booking_id': obj.id})
                    send_booking_alert.delay(obj.id, task_log.id)
        elif 'instructor' in form.changed_data:
            if obj.instructor:
                with transaction.atomic():
                    if 'rate' not in form.changed_data:
                        rate_obj = obj.instructor.instructorlessonrate_set.last()
                        obj.rate = rate_obj.mins30
                        obj.save()
                        obj.refresh_from_db()
                    if obj.status == LessonBooking.TRIAL:
                        lesson = obj.lessons.first()
                        if obj.request and obj.request.status == LESSON_REQUEST_ACTIVE:
                            obj.request.status = LESSON_REQUEST_CLOSED
                            obj.request.save()
                            lesson.instructor = obj.instructor
                            lesson.rate = obj.rate
                            lesson.save()
                        task_log = TaskLog.objects.create(task_name='send_lesson_info_student_parent',
                                                          args={'lesson_id': lesson.id})
                        send_lesson_info_student_parent.delay(lesson.id, task_log.id)
                        task_log = TaskLog.objects.create(task_name='send_lesson_info_instructor',
                                                          args={'lesson_id': lesson.id})
                        send_lesson_info_instructor.delay(lesson.id, task_log.id)
                        ScheduledEmail.objects.create(function_name='send_lesson_reminder',
                                                      schedule=lesson.scheduled_datetime - timezone.timedelta(minutes=30),
                                                      parameters={'lesson_id': lesson.id, 'user_id': obj.instructor.user.id})


def close_lesson_request(model_admin, request, queryset):
    queryset.update(status=LESSON_REQUEST_CLOSED)
close_lesson_request.short_description = 'Close selected lesson requests'


class LessonRequestAdmin(admin.ModelAdmin):
    list_display = ('pk', 'get_user_email',  'title', 'get_instrument', 'status')
    list_filter = ('status', 'skill_level', 'place_for_lessons', 'lessons_duration', )
    list_select_related = ('user', 'instrument', )
    filter_horizontal = ('students', )
    search_fields = ('user__email', 'instrument__name', )
    actions = [close_lesson_request, ]
    object_id = None
    raw_id_fields = ('user', )

    def get_user_email(self, obj):
        return '{email} (user_id: {id})'.format(email=obj.user.email, id=obj.user_id)
    get_user_email.short_description = 'user email'
    get_user_email.admin_order_field = 'user__email'

    def get_instrument(self, obj):
        return obj.instrument.name
    get_instrument.short_description = 'instrument'
    get_instrument.admin_order_field = 'instrument__name'

    def change_view(self, request, object_id, form_url='', extra_context=None):
        self.object_id = object_id
        return super().change_view(request, object_id, form_url, extra_context)

    def add_view(self, request, form_url='', extra_context=None):
        self.object_id = None
        return super().add_view(request, form_url, extra_context)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'user':
            kwargs['queryset'] = User.objects.filter(Q(student__isnull=False) | Q(parent__isnull=False)
                                                     ).order_by('email')
        elif db_field.name == 'instrument':
            kwargs['queryset'] = Instrument.objects.order_by('name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'students':
            if self.object_id:
                requestor = LessonRequest.objects.get(id=self.object_id).user
                if requestor.is_parent():
                    kwargs['queryset'] = TiedStudent.objects.filter(parent=requestor.parent).order_by('name')
                else:
                    kwargs['queryset'] = TiedStudent.objects.none()
            else:
                kwargs['queryset'] = TiedStudent.objects.order_by('name')
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            lesson = None
            is_trial = False
            if obj.user.is_parent() and form.cleaned_data.get('students'):
                if not obj.user.parent.tied_students.filter(id=form.cleaned_data['students'][0].id).exists():
                    raise ValueError("Selected TiedStudent don't belong to this parent")
                if obj.user.lesson_bookings.filter(tied_student=form.cleaned_data['students'][0]).count() == 0:
                    is_trial = True
            elif obj.user.is_student and obj.user.lesson_bookings.count() == 0:
                is_trial = True
            if is_trial:
                with transaction.atomic():
                    lb = LessonBooking.objects.create(user=obj.user, quantity=1, total_amount=0, request=obj,
                                                      description='Package trial', status=LessonBooking.TRIAL)
                    obj.save()
                    lesson = Lesson.objects.create(booking=lb,
                                                   scheduled_datetime=obj.trial_proposed_datetime,
                                                   scheduled_timezone=obj.trial_proposed_timezone,
                                                   )
                add_to_email_list_v2(request.user, ['trial_to_booking'], ['customer_to_request'])
            if lesson:
                task_log = TaskLog.objects.create(task_name='send_lesson_info_student_parent', args={'lesson_id': lesson.id})
                send_lesson_info_student_parent.delay(lesson.id, task_log.id)
            task_log = TaskLog.objects.create(task_name='send_request_alert_instructors', args={'request_id': obj.id})
            send_request_alert_instructors.delay(obj.id, task_log.id)


class LessonAdmin(admin.ModelAdmin):
    fields = ('booking', 'student_details', 'scheduled_datetime', 'scheduled_timezone',
              'instructor', 'rate', 'grade', 'comment', 'status')
    readonly_fields = ('student_details', )
    list_display = ('pk', 'get_booking_id', 'get_user_email', 'get_instructor', 'scheduled_datetime')
    list_filter = ('status', )
    search_fields = ('booking__user__email', 'instructor__user__email')

    def get_user_email(self, obj):
        return '{email} (user_id: {id})'.format(email=obj.booking.user.email, id=obj.booking.user_id)

    def get_booking_id(self, obj):
        return obj.booking.id

    def get_instructor(self, obj):
        if obj.instructor is None:
            return ''
        else:
            return f'{obj.instructor.display_name} ({obj.instructor.user.email})'

    get_user_email.short_description = 'user email'
    get_user_email.admin_order_field = 'booking__user__email'
    get_booking_id.short_description = 'booking id'
    get_booking_id.admin_order_field = 'booking_id'
    get_instructor.short_description = 'instructor'
    get_instructor.admin_order_field = 'instructor__user__email'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'booking':
            kwargs['queryset'] = LessonBooking.objects.order_by('id')
        elif db_field.name == 'instructor':
            kwargs['queryset'] = Instructor.objects.order_by('user__email')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not change and (obj.booking.quantity - obj.booking.lessons.count()) == 0:
            raise Exception('There is not available lessons for selected booking')
        super().save_model(request, obj, form, change)
        if not change:
            task_log = TaskLog.objects.create(task_name='send_lesson_info_student_parent',
                                              args={'lesson_id': obj.id})
            send_lesson_info_student_parent.delay(obj.id, task_log.id)
        else:
            if 'grade' in form.changed_data:
                task_log = TaskLog.objects.create(task_name='send_info_grade_lesson', args={'lesson_id': obj.id})
                send_info_grade_lesson.delay(obj.id, task_log.id)
                task_log = TaskLog.objects.create(task_name='send_instructor_grade_lesson', args={'lesson_id': obj.id})
                send_instructor_grade_lesson.delay(obj.id, task_log.id)    
            if 'scheduled_datetime' in form.changed_data:
                ScheduledEmail.objects.filter(function_name='send_reminder_grade_lesson',
                                              parameters={'lesson_id': obj.id},
                                              executed=False) \
                    .update(schedule=obj.scheduled_datetime + timezone.timedelta(minutes=30))
                if not ScheduledEmail.objects.filter(function_name='send_reminder_grade_lesson',
                                                     parameters={'lesson_id': obj.id},
                                                     executed=False).exists():
                    ScheduledEmail.objects.create(function_name='send_reminder_grade_lesson',
                                                  schedule=obj.scheduled_datetime + timezone.timedelta(minutes=30),
                                                  parameters={'lesson_id': obj.id})
                ScheduledEmail.objects.filter(function_name='send_lesson_reminder',
                                              parameters={'lesson_id': obj.id},
                                              executed=False) \
                    .update(schedule=obj.scheduled_datetime - timezone.timedelta(minutes=30))
                if not ScheduledEmail.objects.filter(function_name='send_lesson_reminder',
                                                     parameters={'lesson_id': obj.id},
                                                     executed=False).exists():
                    ScheduledEmail.objects.create(function_name='send_lesson_reminder',
                                                  schedule=obj.scheduled_datetime - timezone.timedelta(minutes=30),
                                                  parameters={'lesson_id': obj.id,
                                                              'user_id': obj.booking.user.id})
                task_log = TaskLog.objects.create(task_name='send_lesson_reschedule',
                                                  args={'lesson_id': obj.id,
                                                        'previous_datetime': form.initial['scheduled_datetime'].strftime(
                                                            '%Y-%m-%d %I:%M %p')})
                send_lesson_reschedule.delay(obj.id, task_log.id,
                                             form.initial['scheduled_datetime'].astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'))


admin.site.register(Application, ApplicationAdmin)
admin.site.register(LessonBooking, LessonBookingAdmin)
admin.site.register(LessonRequest, LessonRequestAdmin)
admin.site.register(Lesson, LessonAdmin)
admin.site.register(InstructorAcceptanceLessonRequest, InstructorAcceptanceLessonRequestAdmin)
admin.site.register(Instrument, InstrumentAdmin)
