import re
from pygeocoder import Geocoder, GeocoderError

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib import admin
from django.contrib.gis.db.models import PointField
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.db.models import Q
from django.db.models.functions import Cast

from accounts.models import (Availability, Education, Employment, Instructor, InstructorAdditionalQualifications,
                             InstructorAgeGroup, InstructorInstruments, InstructorLessonRate, InstructorLessonSize,
                             InstructorPlaceForLessons, Parent, Student, StudentDetails, TiedStudent)
from accounts.utils import get_geopoint_from_location

User = get_user_model()


class EducationInline(admin.TabularInline):
    model = Education
    extra = 1


class EmploymentInline(admin.TabularInline):
    model = Employment
    extra = 1


class AdditionalQualificationsAdmin(admin.TabularInline):
    model = InstructorAdditionalQualifications
    extra = 1


class AgeGroupAdmin(admin.TabularInline):
    model = InstructorAgeGroup
    extra = 1


class InstrumentsAdmin(admin.TabularInline):
    model = InstructorInstruments
    extra = 1


class LessonRateAdmin(admin.TabularInline):
    model = InstructorLessonRate
    extra = 1


class LessonSizeAdmin(admin.TabularInline):
    model = InstructorLessonSize
    extra = 1


class AvailabilityAdmin(admin.StackedInline):
    model = Availability
    fieldsets = (
        (None, {'fields': (('mon8to10', 'mon10to12', 'mon12to3', 'mon3to6', 'mon6to9'),)}),
        (None, {'fields': (('tue8to10', 'tue10to12', 'tue12to3', 'tue3to6', 'tue6to9'),)}),
        (None, {'fields': (('wed8to10', 'wed10to12', 'wed12to3', 'wed3to6', 'wed6to9'),)}),
        (None, {'fields': (('thu8to10', 'thu10to12', 'thu12to3', 'thu3to6', 'thu6to9'),)}),
        (None, {'fields': (('fri8to10', 'fri10to12', 'fri12to3', 'fri3to6', 'fri6to9'),)}),
        (None, {'fields': (('sat8to10', 'sat10to12', 'sat12to3', 'sat3to6', 'sat6to9'),)}),
        (None, {'fields': (('sun8to10', 'sun10to12', 'sun12to3', 'sun3to6', 'sun6to9'),)}),
    )


class InstructorPlaceForLessonsAdmin(admin.TabularInline):
    model = InstructorPlaceForLessons
    extra = 1


class InstructorAdmin(admin.ModelAdmin):
    fields = ('user', 'display_name', 'age', 'avatar', 'bio_title', 'bio_description', 'bg_status', 'location',
              'music', 'interviewed', 'languages', 'studio_address', 'travel_distance', 'years_of_experience', 'video',
              'zoom_link')
    list_display = ('pk', 'user', 'display_name', 'distance', )
    list_filter = ('interviewed', 'complete', )
    list_select_related = ('user', )
    search_fields = ('user__email', 'display_name', 'instruments__name')
    location_search_values = {}
    places_search_values = {}
    readonly_fields = ('user', 'display_name', 'age', 'distance', )
    inlines = [EducationInline, EmploymentInline, AdditionalQualificationsAdmin, InstrumentsAdmin,
               InstructorPlaceForLessonsAdmin, LessonRateAdmin, AgeGroupAdmin, LessonSizeAdmin, AvailabilityAdmin, ]

    def has_add_permission(self, request):
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(distance=Cast(None, PointField()))

    def changelist_view(self, request, extra_context=None):
        self.location_search_values = {}
        self.places_search_values = {}
        request.GET._mutable = True
        keys = dict.fromkeys(request.GET, 1)
        if keys.get('address'):
            if len(request.GET.get('address')) > 0 and request.GET.get('address')[0]:
                self.location_search_values['address'] = request.GET.pop('address')[0]
            else:
                request.GET.pop('address')
            if keys.get('distance'):
                if len(request.GET.get('distance')) > 0 and request.GET.get('distance')[0] is not None:
                    self.location_search_values['distance'] = request.GET.pop('distance')[0]
                else:
                    request.GET.pop('distance')
            if self.location_search_values.get('address') is not None and self.location_search_values.get('distance') is None:
                self.location_search_values['distance'] = 50
        if keys.get('home'):
            self.places_search_values['home'] = True
            request.GET.pop('home')
        if keys.get('online'):
            self.places_search_values['online'] = True
            request.GET.pop('online')
        if keys.get('studio'):
            self.places_search_values['studio'] = True
            request.GET.pop('studio')
        request.GET._mutable = False
        return super().changelist_view(request, extra_context={'location_values': self.location_search_values,
                                                               'places_values': self.places_search_values})

    def get_search_results(self, request, queryset, search_term):
        if self.location_search_values:
            geocoder = Geocoder(api_key=settings.GOOGLE_MAPS_API_KEY)
            try:
                results = geocoder.geocode(self.location_search_values['address'])
            except GeocoderError as e:
                self.location_search_values = {}
                raise Exception(e.status, e.response)
            point = Point(results[0].coordinates[1], results[0].coordinates[0], srid=4326)
            qs = queryset.filter(coordinates__isnull=False).annotate(
                distance=Distance('coordinates', point)
            ).filter(distance__lte=D(mi=self.location_search_values['distance']))
        else:
            qs = queryset
        if self.places_search_values:
            condics = None
            if self.places_search_values.get('home'):
                if condics is None:
                    condics = Q(instructorplaceforlessons__home=True)
                else:
                    condics = condics | Q(instructorplaceforlessons__home=True)
            if self.places_search_values.get('online'):
                if condics is None:
                    condics = Q(instructorplaceforlessons__online=True)
                else:
                    condics = condics | Q(instructorplaceforlessons__online=True)
            if self.places_search_values.get('studio'):
                if condics is None:
                    condics = Q(instructorplaceforlessons__studio=True)
                else:
                    condics = condics | Q(instructorplaceforlessons__studio=True)
            if condics:
                qs = qs.filter(condics)
        return super().get_search_results(request, qs, search_term)

    def distance(self, instance):
        if instance.distance is not None:
            return instance.distance.mi
        else:
            return None

    def save_model(self, request, obj, form, change):
        if 'location' in form.changed_data:
            geocoder = Geocoder(api_key=settings.GOOGLE_MAPS_API_KEY)
            try:
                results = geocoder.geocode(obj.location)
            except GeocoderError as e:
                raise Exception(e.status, e.response)
            obj.coordinates = Point(results[0].coordinates[1], results[0].coordinates[0], srid=4326)
        if 'zoom_link' in form.changed_data:
            if re.match(r'^https://.+\.zoom\.us/j/[\d]+.*', obj.zoom_link) is None:
                raise Exception('Wrong Zoom meeting link')
        super().save_model(request, obj, form, change)


class TiedStudentAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'parent')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'parent':
            kwargs['queryset'] = Parent.objects.order_by('user__email')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class HasCoordinatesFilter(admin.SimpleListFilter):
    title = 'Has Coordinates'
    parameter_name = 'coordinates'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(coordinates__isnull=False)
        if self.value() == 'no':
            return queryset.filter(coordinates__isnull=True)


class StudentAdmin(admin.ModelAdmin):
    fields = ('user', 'display_name', 'age', 'avatar', 'birthday', 'gender', 'location',)
    list_display = ('pk', 'user', 'display_name',)
    list_filter = ('gender', HasCoordinatesFilter,)
    search_fields = ('user__email', 'display_name',)
    readonly_fields = ('user', 'display_name', 'age',)

    def has_add_permission(self, request):
        return False

    def save_model(self, request, obj, form, change):
        if 'location' in form.changed_data:
            obj.coordinates = get_geopoint_from_location(obj.location)
        super().save_model(request, obj, form, change)


class TiedStudentInline(admin.TabularInline):
    model = TiedStudent
    extra = 1


class StudentDetailsAdmin(admin.ModelAdmin):
    list_display = ('get_user_email', 'get_tied_student_name')
    list_filter = ('instrument', )
    fields = ('user', 'tied_student', 'instrument', 'skill_level', 'lesson_place', 'lesson_duration', )

    def get_user_email(self, instance):
        return instance.user.email
    get_user_email.short_description = 'user email'
    get_user_email.admin_order_field = 'user__email'

    def get_tied_student_name(self, instance):
        if instance.tied_student:
            return instance.tied_student.name
        else:
            return ' - '
    get_tied_student_name.short_description = 'tied student name'
    get_tied_student_name.admin_order_field = 'tied_student__name'


class ParentAdmin(admin.ModelAdmin):
    fields = ('user', 'display_name', 'age', 'avatar', 'birthday', 'gender', 'location',)
    list_display = ('pk', 'user', 'display_name',)
    list_filter = ('gender', HasCoordinatesFilter,)
    search_fields = ('user__email', 'display_name',)
    readonly_fields = ('user', 'display_name', 'age',)
    inlines = (TiedStudentInline,)

    def has_add_permission(self, request):
        return False

    def save_model(self, request, obj, form, change):
        if 'location' in form.changed_data:
            obj.coordinates = get_geopoint_from_location(obj.location)
        super().save_model(request, obj, form, change)


admin.site.register(Instructor, InstructorAdmin)
admin.site.register(Parent, ParentAdmin)
admin.site.register(Student, StudentAdmin)
admin.site.register(TiedStudent, TiedStudentAdmin)
admin.site.register(StudentDetails, StudentDetailsAdmin)
