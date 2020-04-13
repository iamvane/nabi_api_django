from django import forms
from django.contrib.auth import get_user_model

from .constants import ROLE_INSTRUCTOR, ROLE_PARENT, ROLE_STUDENT

User = get_user_model()


class CreateUserForm(forms.ModelForm):
    ROLES = (
        (ROLE_INSTRUCTOR, 'Instructor'),
        (ROLE_PARENT, 'Parent'),
        (ROLE_STUDENT, 'Student'),
    )
    birthday = forms.DateField(label='Birthday (YYYY-MM-DD)')
    referringCode = forms.CharField(max_length=20, required=False, label='Referring Code')
    role = forms.ChoiceField(choices=ROLES)

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'birthday', 'referringCode', 'role',)
