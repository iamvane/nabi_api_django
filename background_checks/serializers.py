from django.db.models import ObjectDoesNotExist

from rest_framework import serializers, validators

from accounts.models import Instructor

from .models import BackgroundCheckRequest


class BGCheckRequestSerializer(serializers.Serializer):
    """Serializer to create a background check request"""
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
        new_data = {}
        if 'instructorId' in data.keys():
            new_data['instructor_id'] = data.get('instructorId')
        if 'stripeToken' in data.keys():
            new_data['stripe_token'] = data.get('stripeToken')
        if 'amount' in data.keys():
            new_data['amount'] = data.get('amount')
        return super().to_internal_value(new_data)


class InstructorIdSerializer(serializers.Serializer):
    """Serializer to validate received instructorId value"""
    instructor_id = serializers.IntegerField()

    def to_internal_value(self, data):
        new_data = {}
        if 'instructorId' in data.keys():
            new_data['instructor_id'] = data.get('instructorId')
        return super().to_internal_value(new_data)

    def validate_instructor_id(self, value):
        try:
            Instructor.objects.get(id=value)
        except ObjectDoesNotExist:
            raise validators.ValidationError('Wrong instructor_id value')
        return value


class BGCheckRequestModelSerializer(serializers.ModelSerializer):
    """Serializer to retrieve data of a background check"""
    requestorEmail = serializers.EmailField(source='user.email')
    instructorName = serializers.CharField(max_length=200, source='instructor.display_name')
    result = serializers.CharField(max_length=200, source='provider_results')
    createdAt = serializers.DateTimeField(source='created_at', format='%Y-%m-%d %H:%M:%S')

    class Meta:
        model = BackgroundCheckRequest
        fields = ('requestorEmail', 'instructorName', 'observation', 'status', 'result', 'createdAt')

    def get_result(self, instance):
        return instance.provider_results.get('result')
