from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import HStoreField
from django.db import models

User = get_user_model()


def avatar_directory_path(instance, filename):
    return 'avatars/{0}/{1}'.format(instance.user.email, filename)


class IUserAccount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(blank=True, null=True, upload_to=avatar_directory_path)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Parent(IUserAccount):
    pass


class Instructor(IUserAccount):
    bio = models.TextField(blank=True, null=True)
    social_media_accounts = HStoreField(blank=True, null=True)

    def __str__(self):
        return f'Instructor {self.user}'


class Student(IUserAccount):
    parent = models.ForeignKey(Parent, on_delete=models.SET_NULL, blank=True, null=True, related_name='children')
