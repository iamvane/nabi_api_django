from django.contrib.auth import get_user_model
from django.contrib import admin
from django.db.models import Q

from accounts.models import TiedStudent
from core.constants import LESSON_REQUEST_CLOSED
from core.models import TaskLog

from .models import Application, Lesson, LessonBooking, LessonRequest
from .tasks import send_application_alert, send_request_alert_instructors, send_lesson_info_student_parent

User = get_user_model()


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

    def save_model(self, request, obj, form, change):
        application = super().save_model(request, obj, form, change)
        if not change:   # is creation
            task_log = TaskLog.objects.create(task_name='send_application_alert', args={'application_id': application.id})
            send_application_alert.delay(application.id, task_log.id)


class LessonBookingAdmin(admin.ModelAdmin):
    fields = ('view_application', 'application', 'request', 'user', 'instructor', 'rate',
              'quantity', 'total_amount', 'status')
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
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


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
            lb = LessonBooking.objects.create(user=obj.user, quantity=1, total_amount=0, request=obj,
                                              description='Package trial', status=LessonBooking.TRIAL)
            lesson = Lesson.objects.create(booking=lb,
                                           scheduled_datetime=obj.trial_proposed_datetime,
                                           scheduled_timezone=obj.trial_proposed_timezone,
                                           )
        if not change or 'instrument' in form.changed_data or 'place_for_lessons' in form.changed_data:
            task_log = TaskLog.objects.create(task_name='send_request_alert_instructors', args={'request_id': obj.id})
            send_request_alert_instructors.delay(obj.id, task_log.id)
        if lesson:
            task_log = TaskLog.objects.create(task_name='send_request_info_student_parent', args={'lesson_id': lesson.id})
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


admin.site.register(Application, ApplicationAdmin)
admin.site.register(LessonBooking, LessonBookingAdmin)
admin.site.register(LessonRequest, LessonRequestAdmin)
admin.site.register(Lesson, LessonAdmin)
