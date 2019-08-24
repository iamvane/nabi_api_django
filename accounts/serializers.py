from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Parent, Instructor, PhoneNumber
from .utils import *
from core.utils import *
from core.constants import GENDER_CHOICES

User = get_user_model()


class BaseCreateAccountSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    middle_name = serializers.CharField(max_length=100, allow_blank=True, allow_null=True, required=False, )
    display_name = serializers.CharField(max_length=100, allow_blank=True, allow_null=True, required=False, )
    gender = serializers.CharField(max_length=100, allow_blank=True, allow_null=True, required=False, )
    hear_about_us = serializers.CharField(max_length=100, allow_blank=True, allow_null=True, required=False, )
    birthday = serializers.DateField(allow_null=True, required=True, )

    def create(self, validated_data):
        user = update_model(User(), **validated_data)
        user.set_password(validated_data['password'])
        user.save()
        return user

    def update(self, instance, validated_data):
        pass


class ParentCreateAccountSerializer(BaseCreateAccountSerializer):

    def create(self, validated_data):
        user = super().create(validated_data)
        return Parent.objects.create(user=user, **init_kwargs(Parent(), validated_data))


class InstructorCreateAccountSerializer(BaseCreateAccountSerializer):

    def create(self, validated_data):
        user = super().create(validated_data)
        return Instructor.objects.create(user=user, **init_kwargs(Instructor(), validated_data))


class InstructorAccountInfoSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=True, )
    last_name = serializers.CharField(required=True, )
    gender = serializers.ChoiceField(required=True, choices=GENDER_CHOICES)
    phone_number = serializers.CharField(required=True, )
    lat = serializers.CharField(max_length=50, required=True)
    long = serializers.CharField(max_length=50, required=True)

    def update(self, instance, validated_data):
        user = instance.user
        update_model(user, **validated_data)
        user.save()
        if not self.has_number(validated_data['phone_number']):
            PhoneNumber.objects.create(user=user, phone_number=validated_data['phone_number'])
        update_model(instance, **validated_data)
        instance.save()
        return instance

    def has_number(self, number):
        return PhoneNumber.objects.filter(phone_number=number).first() is not None

    def create(self, validated_data):
        raise Exception("Create is not supposed to be called")
