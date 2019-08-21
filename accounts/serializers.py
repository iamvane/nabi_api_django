from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Parent
from .utils import *

User = get_user_model()


class BaseCreateAccountSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    middle_name = serializers.CharField(max_length=100, allow_blank=True, allow_null=True, required=False, )
    display_name = serializers.CharField(max_length=100, allow_blank=True, allow_null=True, required=False, )
    gender = serializers.CharField(max_length=100, allow_blank=True, allow_null=True, required=False, )
    hear_about_us = serializers.CharField(max_length=100, allow_blank=True, allow_null=True, required=False, )
    birthday = serializers.DateField(allow_null=True, required=False,)

    def create(self, validated_data):
        user = User()
        user.email = validated_data['email']
        user.set_password(validated_data['password'])
        user.save()
        return user

    def update(self, instance, validated_data):
        pass


class ParentCreateAccountSerializer(BaseCreateAccountSerializer):

    def create(self, validated_data):
        user = super().create(validated_data)
        return Parent.objects.create(user=user, **init_kwargs(Parent(), validated_data))
