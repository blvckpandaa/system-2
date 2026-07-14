from urllib.parse import urljoin

from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from dal import autocomplete

from .models import Announcement, Comment, User


class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_active = False
        if commit:
            user.save()
        return user


class EmailVerificationForm(forms.Form):
    code = forms.CharField(
        label="Код из письма",
        min_length=6,
        max_length=6,
        widget=forms.TextInput(
            attrs={
                "class": "form-control text-center fs-4 letter-spacing",
                "placeholder": "000000",
                "inputmode": "numeric",
                "autocomplete": "one-time-code",
                "maxlength": "6",
            }
        ),
    )

    def clean_code(self):
        code = (self.cleaned_data.get("code") or "").strip()
        if not code.isdigit() or len(code) != 6:
            raise ValidationError("Введите 6 цифр из письма.")
        return code


class ResendVerificationForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "example@gmail.com"}),
    )


class BrandedPasswordResetForm(PasswordResetForm):
    """PasswordResetForm.save() вызывает send_mail у формы, не у PasswordResetView."""

    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        proto = getattr(settings, "SITE_PROTOCOL", "https")
        domain = getattr(settings, "SITE_DOMAIN", "eccoprom.windexs.ru")
        reset_base = f"{proto}://{domain}".rstrip("/")

        path = reverse(
            "password_reset_confirm",
            kwargs={"uidb64": context["uid"], "token": context["token"]},
        )
        reset_url = urljoin(reset_base + "/", path.lstrip("/"))

        subject = render_to_string(subject_template_name, context).strip()
        mail_ctx = {
            **context,
            "reset_url": reset_url,
            "site_domain": domain,
        }
        text_body = render_to_string(email_template_name, mail_ctx)
        html_name = html_email_template_name or "emails/password_reset.html"
        html_body = render_to_string(
            html_name,
            {**mail_ctx, "year": timezone.now().year},
        )

        from django.core.mail import EmailMultiAlternatives

        msg = EmailMultiAlternatives(subject, text_body, from_email, [to_email])
        msg.attach_alternative(html_body, "text/html")
        msg.send()


class LoginForm(AuthenticationForm):
    error_messages = {
        'invalid_login': 'Пожалуйста, введите правильное имя пользователя и пароль. '
                         'Учтите, что оба поля могут быть чувствительны к регистру.',
        'inactive': 'Подтвердите email — на почту был отправлен 6-значный код. '
                    'Если письма нет, запросите код повторно на странице подтверждения.',
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
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Подключаем AJAX-автодополнение для fkko_code
        self.fields['fkko_code'].required = False
        self.fields['fkko_code'].widget = autocomplete.ListSelect2(
            url='fkko-autocomplete',
            attrs={
                'data-placeholder': 'Начните вводить код ФККО…',
                'class': 'form-select',
            }
        )

        self.fields['city'].required = False
        self.fields['condition'].required = False


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['announcement', 'text', 'rating']
