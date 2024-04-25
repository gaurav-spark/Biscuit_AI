from django.urls import path
from .views import (
    UserRegistrationView,
    SendPasswordEmailView,
    UserPasswordRestView,
    ChangePasswordView,
    EmailVerificationView,
    ResendVerificationEmailView,
    UserPasswordVerifyResetLink,
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
)


urlpatterns = [
    # path("register/", UserRegistrationView.as_view(), name="register"),
    path(
        "send-password-reset-link/",
        SendPasswordEmailView.as_view(),
        name="password-reset-email.html",
    ),
    path(
        "reset/change-password/<uuid:uid>/",
        UserPasswordRestView.as_view(),
        name="password-reset",
    ),
    path("change-password/", ChangePasswordView.as_view(), name="change_password"),
    path(
        "verify-reset-link/<uuid:id>/",
        UserPasswordVerifyResetLink.as_view(),
        name="verify_reset_link",
    ),
    # path(
    #     "verify-email/<str:uidb64>/",
    #     EmailVerificationView.as_view(),
    #     name="verification-email",
    # ),
    # path(
    #     "resend-verification-email/",
    #     ResendVerificationEmailView.as_view(),
    #     name="resend-verification-email",
    # ),
    path(
        "login/",
        CustomTokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),
    path("refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
]
