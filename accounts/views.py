from drf_spectacular.utils import extend_schema
from rest_framework import generics
from django.template.loader import render_to_string
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from rest_framework import status
from .serializers import *
from rest_framework import permissions
from accounts.utils import (
    send_email,
    generate_verification_link,
    send_verification_email,
)
from accounts.constants import RESET_PASSWORD_EMAIL_SUBJECT

from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import render
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)


@extend_schema(tags=["User-Account-Registration API's"], auth=[])
class UserRegistrationView(generics.CreateAPIView):
    """
    User Registration API.
    """

    parser_classes = (MultiPartParser, FormParser, JSONParser)

    serializer_class = UserSerializer
    permission_classes = [AllowAny]
    template = "emails/html/verification-email.html"

    def post(self, request):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user_register_obj = serializer.save()

        # encode user uid
        uid = urlsafe_base64_encode(force_bytes(user_register_obj.id))

        # Generate Verification Link to send in mail
        verification_link = generate_verification_link(request, uid)
        print(verification_link)
        # Send the verification email
        send_verification_email(
            request,
            user_register_obj.email,
            verification_link,
            user_register_obj.first_name,
            self.template,
        )

        return Response(
            "User Registered Successfully",
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Verification Api"], responses=None)
class EmailVerificationView(generics.GenericAPIView):
    """
    Email Verification API.
    """

    permission_classes = [AllowAny]
    permission_classes = [AllowAny]
    serializer_class = None

    def get(self, request, uidb64):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = CustomUser.objects.get(id=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
        if user and user.is_active:
            return Response(
                {"detail": "Email already verified. Please login."},
                status=status.HTTP_200_OK,
            )
        if user:
            user.is_active = True
            user.save()
            return Response(
                {"detail": "Email verified successfully."}, status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"detail": "Verification failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )


@extend_schema(tags=["Resend Verification Api"])
class ResendVerificationEmailView(generics.CreateAPIView):
    """
    Resend Verification Email API View.
    """

    permission_classes = [AllowAny]

    serializer_class = ResendVerificationEmailSerializer  # Use the new serializer
    template = "emails/html/verification-email.html"

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data.get("email")

            # Find the user by email
            user = get_object_or_404(User, email__iexact=email)

            if not user.is_active:
                uid = urlsafe_base64_encode(force_bytes(user.id))
                verification_link = generate_verification_link(request, uid)

                # Send the verification email
                send_verification_email(
                    request,
                    user.email,
                    verification_link,
                    user.first_name,
                    self.template,
                )

                return Response(
                    {"detail": "Verification email has been resent."},
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"detail": "Email is already verified."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["User-Account-Registration API's"])
class SendPasswordEmailView(generics.CreateAPIView):
    """
    Sending email to user for resetting the password.
    """

    serializer_class = ResetPasswordLinkSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        reset_password_obj = serializer.save()
        context = {
            "link": f"{settings.FRONT_END_CHANGE_PASSWORD_URL}{reset_password_obj.id}",
            "reset_password_obj": reset_password_obj,
            "request": request,
            "name": reset_password_obj.user.first_name,
        }
        body_text_content = render_to_string("emails/text/password-reset-email.txt")
        subject = RESET_PASSWORD_EMAIL_SUBJECT
        html_content = render_to_string(
            "emails/html/password-reset-email.html", context
        )
        send_email(
            subject, body_text_content, [reset_password_obj.user.email], html_content
        )
        return Response(
            "Password Reset link sent successfully. Please check your email",
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["User-Account-Registration API's"])
class ChangePasswordView(generics.CreateAPIView):
    """
    This function help user to change the password
    after login.
    Validating user old password.

    """

    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Password updated successfully"}, status=status.HTTP_200_OK
        )


@extend_schema(tags=["User-Account-Registration API's"], auth=[])
class UserPasswordRestView(generics.CreateAPIView):
    """
    User reset password function when reset request
    received by email.
    """

    serializer_class = UserPasswordResetSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = UserPasswordResetSerializer(data=request.data, context=kwargs)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Password Reset Successfully"}, status=status.HTTP_200_OK
        )


@extend_schema(tags=["User-Account-Registration API's"], responses=None)
class UserPasswordVerifyResetLink(generics.RetrieveAPIView):
    """
    User reset password function when reset request
    received by email.
    """

    queryset = ResetPasswordLink.objects.all()
    lookup_field = "id"
    authentication_classes = []

    def retrieve(self, request, *args, **kwargs):
        uuid = self.kwargs.get("id")
        reset_password_link_obj = ResetPasswordLink.objects.filter(
            id=uuid, expired_at__gte=timezone.now()
        ).first()
        if not reset_password_link_obj:
            return Response(
                {"message": "Link has been expired or is invalid"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            return Response({"message": "Link is valid"}, status=status.HTTP_200_OK)


# @extend_schema(tags=["User-Account-Registeration Api's"])
# class UserProfileUpdateView(generics.UpdateAPIView):
#     """
#     User Profile update
#     """
#
#     parser_classes = (MultiPartParser, FormParser)
#
#     serializer_class = UserProfileUpdateSerializer
#     permission_classes = (permissions.IsAuthenticated,)
#     http_method_names = ["patch"]
#
#     @extend_schema(
#         summary="User Profile Update Api",
#         description="User can update all the fields except the email. "
#         "Parent Name, Phone Number, Country Code, Address "
#         "and Email are required fields.",
#     )
#     def patch(self, request, *args, **kwargs):
#         uuid = request.user.id
#         instance = CustomUser.objects.get(id=uuid)
#         serializer = self.serializer_class(
#             instance, data=request.data, context={"request": request}, partial=True
#         )
#         serializer.is_valid(raise_exception=True)
#         new_password = serializer.validated_data.get("new_password")
#         if new_password:
#             instance.set_password(new_password)
#             instance.save()
#
#         serializer.save()
#         return Response(
#             {"message": "Profile updated successfully"},
#             status=status.HTTP_200_OK,
#         )
#
#
# @extend_schema(tags=["User-Account-Registeration Api's"])
# class UserDetails(generics.RetrieveAPIView):
#     """
#     User details
#     """
#
#     serializer_class = UserDetailsSerializer
#     permission_classes = (permissions.IsAuthenticated,)
#     http_method_names = ["get"]
#
#     def get(self, request, *args, **kwargs):
#         uuid = request.user.id
#         instance = CustomUser.objects.get(id=uuid)
#         serializers = self.serializer_class(instance, context={"request": request})
#         return Response(serializers.data, status=status.HTTP_200_OK)


def page_not_found_view(request, exception):
    return render(request, "404.html", status=404)


def Bad_Gateway(request, exception):
    return render(request, "502.html", status=404)


@extend_schema(tags=["Authentication Api's"])
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            token_data = serializer.validated_data

            return Response(token_data, status=status.HTTP_200_OK)
        return Response(
            {"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED
        )


@extend_schema(tags=["Authentication Api's"])
class CustomTokenRefreshView(TokenRefreshView):
    pass


# @extend_schema(tags=["User-Account-Registeration Api's"])
# class UserDeleteView(generics.DestroyAPIView):
#     queryset = CustomUser.objects.all()
#     serializer_class = UserSerializer
#
#     def delete(self, request, *args, **kwargs):
#         try:
#             user = CustomUser.objects.get(id=kwargs["uuid"])
#         except CustomUser.DoesNotExist:
#             return Response({"message": "User not found."})
#
#         user.is_active = False
#         user.save()
#
#         return Response({"message": "Account deleted successfully."})
