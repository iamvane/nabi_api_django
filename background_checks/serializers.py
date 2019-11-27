from django.db.models import ObjectDoesNotExist

from rest_framework import serializers, validators

from accounts.models import Instructor


class BGCheckRequestSerializer(serializers.Serializer):
    instructor_id = serializers.IntegerField(required=False)
    amount = serializers.DecimalField(max_digits=9, decimal_places=4)
    stripe_token = serializers.CharField(max_length=500)

    def validate_instructor_id(self, value):
        try:
            Instructor.objects.get(id=value)
        except ObjectDoesNotExist:
            raise validators.ValidationError('Wrong instructor_id value')
        return value

    def to_internal_value(self, data):
        if 'instructorId' in data.keys():
            data['instructor_id'] = data.pop('instructorId')
        if 'stripeToken' in data.keys():
            data['stripe_token'] = data.pop('stripeToken')
        return super().to_internal_value(data)
