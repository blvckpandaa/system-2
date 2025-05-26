from django import forms
from dal import autocomplete
from .models import Announcement, Comment, User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm


class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")


class LoginForm(AuthenticationForm):
    error_messages = {
        'invalid_login': 'Пожалуйста, введите правильное имя пользователя и пароль. '
                         'Учтите, что оба поля могут быть чувствительны к регистру.',
        'inactive': 'Этот аккаунт неактивен.',
    }


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
            'fkko_code',
            'price',
            'plan',
            'status',
        ]
        widgets = {
            # При создании/редактировании всегда ставим статус pending
            'status': forms.HiddenInput(attrs={'value': 'pending'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Подключаем AJAX-автодополнение для fkko_code
        self.fields['fkko_code'].required = False
        self.fields['fkko_code'].widget = autocomplete.ListSelect2(
            url='fkko-autocomplete',
            attrs={
                'data-placeholder': 'Начните вводить код ФККО…',
                'class': 'form-select',  # можно поменять на form-control, если нужно
            }
        )

        # Делаем остальные поля не обязательными, где нужно
        self.fields['city'].required = False
        self.fields['condition'].required = False


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['announcement', 'text', 'rating']
