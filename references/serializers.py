from rest_framework import serializers

from .models import ReferenceRequest


class RegisterRequestReferenceSerializer(serializers.Serializer):
    emails = serializers.ListField(child=serializers.EmailField())

    def create(self, validated_data):
        for email in validated_data['emails']:
            ReferenceRequest.objects.create(email=email, user=self.context['user'])
        return {}
