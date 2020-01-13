from pygeocoder import Geocoder, GeocoderError

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.gis.db.models import PointField
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.db.models.functions import Cast

from accounts.models import (Education, Employment, Instructor, InstructorAdditionalQualifications,
                             InstructorAgeGroup, InstructorInstruments, InstructorLessonRate, InstructorLessonSize)

User = get_user_model()


class EducationInline(admin.TabularInline):
    model = Education
    extra = 1


class EmploymentInline(admin.TabularInline):
    model = Employment
    extra = 1


class AdicionalQualificationsAdmin(admin.TabularInline):
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


class InstructorAdmin(admin.ModelAdmin):
    fields = ('user', 'display_name', 'age', 'avatar', 'bio_title', 'bio_description', 'distance',
              'music', 'interviewed', 'languages', 'studio_address', 'travel_distance', 'experience_years', )
    list_display = ('pk', 'user', 'display_name', 'distance', )
    list_filter = ('interviewed', 'completed', )
    list_select_related = ('user', )
    search_fields = ('user__email', 'display_name', )
    location_search_values = {}
    readonly_fields = ('user', 'display_name', 'age', 'experience_years', 'distance', )
    ordering = ('pk', )
    inlines = [EducationInline, EmploymentInline, AdicionalQualificationsAdmin, AgeGroupAdmin,
               InstrumentsAdmin, LessonRateAdmin, LessonSizeAdmin]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(distance=Cast(None, PointField()))

    def changelist_view(self, request, extra_context=None):
        self.location_search_values = {}
        request.GET._mutable = True
        keys = dict.fromkeys(request.GET, 1)
        if keys.get('address'):
            if len(request.GET.get('address')) > 0 and request.GET.get('address')[0]:
                self.location_search_values['address'] = request.GET.pop('address')[0]
            else:
                request.GET.pop('address')
            if keys.get('distance'):
                if len(request.GET.get('distance')) > 0 and request.GET.get('distance')[0]:
                    self.location_search_values['distance'] = request.GET.pop('distance')[0]
                else:
                    request.GET.pop('distance')
            if self.location_search_values.get('address') is not None and self.location_search_values.get('distance') is None:
                self.location_search_values['distance'] = 50
        request.GET._mutable = False
        return super().changelist_view(request, extra_context={'location_values': self.location_search_values})

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
        return super().get_search_results(request, qs, search_term)

    def distance(self, instance):
        if instance.distance:
            return instance.distance.mi
        else:
            return None


admin.site.register(User, UserAdmin)
admin.site.register(Instructor, InstructorAdmin)
