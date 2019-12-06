from rest_framework import serializers

from .models import ReferenceRequest


class RegisterRequestReferenceSerializer(serializers.Serializer):
    emails = serializers.ListField(child=serializers.EmailField())

    def create(self, validated_data):
        for email in validated_data['emails']:
            ReferenceRequest.objects.create(email=email, user=self.context['user'])
        return {}

    def validate(self, data):
        data = super().validate(data)
        new_list = []
        for email in data['emails']:
            if not ReferenceRequest.objects.filter(email=email, user=self.context['user']).exists():
                new_list.append(email)
        if not new_list:
            raise serializers.ValidationError('Not valid emails were provided')
        return {'emails': new_list}
