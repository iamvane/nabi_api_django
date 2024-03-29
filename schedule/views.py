from django.db.models import Q
from django.utils import timezone

from rest_framework import status, views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import AccessForInstructor
from core.utils import build_error_dict, DayChoices

from .models import InstructorParticularAvailability, InstructorRegularAvailability, get_instructor_schedule
from .serializers import InstructorAvailabilitySerializer
from .utils import compose_schedule_data


class Availability(views.APIView):
    permission_classes = (IsAuthenticated, AccessForInstructor)

    def post(self, request):
        ser = InstructorAvailabilitySerializer(data=request.data)
        if ser.is_valid():
            if ser.validated_data.get('dates'):
                for item in ser.validated_data['dates']:
                    if InstructorParticularAvailability.objects.filter(instructor=request.user.instructor,
                                                                       date=item).exists():
                        InstructorParticularAvailability.objects.filter(instructor=request.user.instructor,
                                                                        date=item)\
                            .update(schedule=ser.validated_data['intervals'])
                    else:
                        InstructorParticularAvailability.objects.create(instructor=request.user.instructor,
                                                                        date=item,
                                                                        schedule=ser.validated_data['intervals'])
            else:
                for item in ser.validated_data['weekDays']:
                    if InstructorRegularAvailability.objects.filter(instructor=request.user.instructor,
                                                                    week_day=getattr(DayChoices, item)).exists():
                        InstructorRegularAvailability.objects.filter(instructor=request.user.instructor,
                                                                     week_day=getattr(DayChoices, item))\
                            .update(schedule=ser.validated_data['intervals'])
                    else:
                        InstructorRegularAvailability.objects.create(instructor=request.user.instructor,
                                                                     week_day=getattr(DayChoices, item),
                                                                     schedule=ser.validated_data['intervals'])
            return Response({'message': 'Availability registered successfully'})
        else:
            result = build_error_dict(ser.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)


class Schedule(views.APIView):
    permission_classes = (IsAuthenticated, AccessForInstructor)

    def get(self, request):
        days_to_add = 0
        if request.query_params.get('step'):
            try:
                days_to_add = 14 * int(request.query_params.get('step'))
            except ValueError:
                pass
        today = timezone.datetime.now()
        this_date = today - timezone.timedelta(days=(today.weekday() + 1)) \
            + timezone.timedelta(days=days_to_add)
        end_date = this_date + timezone.timedelta(days=13)
        data = []
        while this_date <= end_date:
            next_date = this_date + timezone.timedelta(days=1)
            pre_data = {'date': this_date.strftime('%Y-%m-%d'), 'available': [], 'lessons': []}
            schedule = get_instructor_schedule(request.user.instructor, this_date.date())
            lessons_qs = request.user.instructor.lessons\
                .filter(Q(scheduled_datetime__date=this_date.date()) | Q(scheduled_datetime__date=next_date.date()))\
                .values('id', 'scheduled_datetime').order_by('scheduled_datetime')
            time_zone = request.user.instructor.timezone or request.user.instructor.get_timezone_from_location_zipcode()
            sch_data = compose_schedule_data(schedule, lessons_qs, time_zone, this_date.strftime('%Y-%m-%d'))
            pre_data.update(sch_data)
            data.append(pre_data)
            this_date = this_date + timezone.timedelta(days=1)
        return Response(data)
