from django import forms
from .models import Announcement, Comment, User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm


class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")


class LoginForm(AuthenticationForm):
    pass


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = [
            'title',
            'category',
            'description',
            'condition',
            'location',
            'city',
            'phone',
            'price',
            'plan',
            'status'
        ]
        widgets = {
            'status': forms.HiddenInput(attrs={'value': 'draft'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'city' in self.fields:
            self.fields['city'].required = False
        if 'condition' in self.fields:
            self.fields['condition'].required = False


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['announcement', 'text', 'rating']
