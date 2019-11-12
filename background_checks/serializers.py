from django.db.models import ObjectDoesNotExist

from rest_framework import serializers, validators

from accounts.models import Instructor


class InstructorIdSerializer(serializers.Serializer):
    instructor_id = serializers.IntegerField()

    def validate_instructor_id(self, value):
        try:
            Instructor.objects.get(id=value)
        except ObjectDoesNotExist:
            raise validators.ValidationError('Wrong instructor_id value')
        return value
