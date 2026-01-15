"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from blog.views_auth import BrandedPasswordResetView
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('blog.urls')),
] 

urlpatterns += [
    path("password-reset/", BrandedPasswordResetView.as_view(
        template_name="auth/password_reset_form.html",
        subject_template_name="emails/password_reset_subject.txt",
        email_template_name="emails/password_reset_email.txt",
        html_email_template_name="emails/password_reset.html",
    ), name="password_reset"),

    path("password-reset/done/", auth_views.PasswordResetDoneView.as_view(
        template_name="auth/password_reset_done.html"
    ), name="password_reset_done"),

    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="auth/password_reset_confirm.html",
        success_url="/reset/done/"
    ), name="password_reset_confirm"),

    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(
        template_name="auth/password_reset_complete.html"
    ), name="password_reset_complete"),
]
if settings.DEBUG:  
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
