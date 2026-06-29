from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse


class RequireVerifiedEmailMiddleware:
    """
    Не пускает на сайт пользователей с is_active=False (не подтвердили email).
  Разрешены только страницы входа, регистрации и подтверждения.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self._prefixes = (
            "/static/",
            "/media/",
            "/admin/",
            "/verify-email",
            "/register",
            "/login",
            "/logout",
            "/password-reset",
            "/reset/",
        )

    def __call__(self, request):
        user = request.user
        if user.is_authenticated and not user.is_active:
            path = request.path
            if not any(path.startswith(p) for p in self._prefixes):
                logout(request)
                messages.warning(
                    request,
                    "Подтвердите email, чтобы пользоваться сайтом.",
                )
                return redirect(reverse("verify_email"))
        return self.get_response(request)
