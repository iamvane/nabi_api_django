from rest_framework import status, views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import AccessForInstructor
from core.utils import build_error_dict, DayChoices

from .models import InstructorParticularAvailability, InstructorRegularAvailability
from .serializers import InstructorAvailabilitySerializer


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
