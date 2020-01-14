from django.contrib import admin

from .models import Application, LessonBooking, LessonRequest


class ApplicationAdmin(admin.ModelAdmin):
    fields = ('view_request', 'instructor', 'rate', 'message', 'seen', )
    list_display = ('pk', 'get_instructor_email', 'request_id', 'created_at', )
    readonly_fields = ('view_request', )
    ordering = ('pk', )

    def get_instructor_email(self, obj):
        return obj.instructor.user.email

    def view_request(self, obj):
        return 'id: {} ({})'.format(obj.request.id, obj.request.user.email)


class LessonBookingAdmin(admin.ModelAdmin):
    fields = ('user', 'quantity', 'total_amount', 'view_application', 'status')
    list_display = ('pk', 'get_user_email', 'application_id', 'quantity', 'total_amount', 'status', )
    list_filter = ('status', )
    readonly_fields = ('view_application', )
    ordering = ('pk', )

    def get_user_email(self, obj):
        return '{email} (id: {id})'.format(email=obj.user.email, id=obj.user_id)
    get_user_email.short_description = 'user email'
    get_user_email.admin_order_field = 'user__email'

    def view_application(self, obj):
        return 'id: {} ({})'.format(obj.application.pk, obj.application.instructor.user.email)
    view_application.short_description = 'application'


class LessonRequestAdmin(admin.ModelAdmin):
    list_display = ('pk', 'get_user_email',  'title', 'get_instrument', 'status')
    list_filter = ('status', 'skill_level', 'place_for_lessons', 'lessons_duration', )
    list_select_related = ('user', 'instrument', )
    filter_horizontal = ('students', )
    search_fields = ('user__email', 'instrument__name', )
    ordering = ('pk',)

    def get_user_email(self, obj):
        return '{email} (id: {id})'.format(email=obj.user.email, id=obj.user_id)
    get_user_email.short_description = 'user email'
    get_user_email.admin_order_field = 'user__email'

    def get_instrument(self, obj):
        return obj.instrument.name
    get_instrument.short_description = 'instrument'
    get_instrument.admin_order_field = 'instrument__name'


admin.site.register(Application, ApplicationAdmin)
admin.site.register(LessonBooking, LessonBookingAdmin)
admin.site.register(LessonRequest, LessonRequestAdmin)
