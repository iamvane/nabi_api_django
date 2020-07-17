from django.contrib.auth import get_user_model
from django.contrib import admin
from django.db import transaction
from django.db.models import Q

from accounts.models import Instructor, TiedStudent
from accounts.utils import add_to_email_list_v2
from core.constants import LESSON_REQUEST_CLOSED, PY_APPLIED
from core.models import TaskLog, UserBenefits
from lesson.models import Instrument
from payments.models import Payment

from .models import Application, Lesson, LessonBooking, LessonRequest
from .tasks import (send_application_alert, send_booking_alert, send_booking_invoice, send_info_grade_lesson,
                    send_request_alert_instructors, send_lesson_info_student_parent)

User = get_user_model()


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

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:   # is creation
            task_log = TaskLog.objects.create(task_name='send_application_alert', args={'application_id': obj.id})
            send_application_alert.delay(obj.id, task_log.id)


class LessonBookingAdmin(admin.ModelAdmin):
    fields = ('view_application', 'application', 'request', 'user', 'instructor', 'rate',
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
                obj.request.status = LESSON_REQUEST_CLOSED
                obj.request.save()
                lesson = Lesson.objects.create(booking=obj, scheduled_datetime=obj.request.trial_proposed_datetime,
                                               scheduled_timezone=obj.request.trial_proposed_timezone,
                                               instructor=obj.instructor, rate=obj.rate)
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
                task_log = TaskLog.objects.create(task_name='send_booking_alert', args={'booking_id': obj.id})
                send_booking_alert.delay(obj.id, task_log.id)


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
        lesson = None
        if not change and obj.user.lesson_bookings.count() == 0:
            with transaction.atomic():
                lb = LessonBooking.objects.create(user=obj.user, quantity=1, total_amount=0, request=obj,
                                                  description='Package trial', status=LessonBooking.TRIAL)
                obj.status = LESSON_REQUEST_CLOSED
                obj.save()
                lesson = Lesson.objects.create(booking=lb,
                                               scheduled_datetime=obj.trial_proposed_datetime,
                                               scheduled_timezone=obj.trial_proposed_timezone,
                                               )
            add_to_email_list_v2(request.user, ['trial_to_booking'], ['customer_to_request'])
        if not change or 'instrument' in form.changed_data or 'place_for_lessons' in form.changed_data:
            task_log = TaskLog.objects.create(task_name='send_request_alert_instructors', args={'request_id': obj.id})
            send_request_alert_instructors.delay(obj.id, task_log.id)
        if lesson:
            task_log = TaskLog.objects.create(task_name='send_lesson_info_student_parent', args={'lesson_id': lesson.id})
            send_lesson_info_student_parent.delay(lesson.id, task_log.id)


class LessonAdmin(admin.ModelAdmin):
    fields = ('booking', 'student_details', 'scheduled_datetime', 'scheduled_timezone',
              'instructor', 'rate', 'status')
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


admin.site.register(Application, ApplicationAdmin)
admin.site.register(LessonBooking, LessonBookingAdmin)
admin.site.register(LessonRequest, LessonRequestAdmin)
admin.site.register(Lesson, LessonAdmin)
admin.site.register(Instrument, InstrumentAdmin)
