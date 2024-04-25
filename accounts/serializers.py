import re

from django.conf import settings
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from django.contrib.auth import get_user_model

from django.utils import timezone
from accounts.models import *
from django.contrib.auth.hashers import check_password

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        max_length=15, write_only=True, style={"input_type": "password"}
    )
    password2 = serializers.CharField(
        max_length=15, write_only=True, style={"input_type": "password"}
    )

    email = serializers.EmailField(max_length=100, write_only=True)

    class Meta:
        model = CustomUser
        fields = (
            "first_name",
            "last_name",
            "email",
            "password",
            "password2",
        )
        extra_kwargs = {
            "first_name": {
                "error_messages": {
                    "required": "First name is required.",
                    "blank": "First name is required.",
                }
            },
            "email": {
                "error_messages": {
                    "required": "Email is required.",
                    "unique": "The user with this email already exists.",
                }
            },
            "password": {"error_messages": {"required": "Password is required."}},
            "password2": {
                "required": "Passwords do not match. Make sure password and confirm password are same."
            },
        }

    def validate(self, attrs):
        password = attrs.get("password")
        password2 = attrs.get("password2")
        # parent_name = attrs.get("parent_name")
        reg = "^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!#%*?&]{6,20}$"
        pattern = re.compile(reg)

        if password != password2:
            raise serializers.ValidationError("Password doesn't match")
        elif not re.search(pattern, password):
            raise serializers.ValidationError(
                "Password is invalid. Password should be more than 8 characters and must"
                " contain one Uppercase, Lowercase and Alphanumeric value"
            )

        return attrs

    def validate_email(self, value):
        # Check if the email is already registered in a case-insensitive manner
        existing_user = CustomUser.objects.filter(email__iexact=value)
        if existing_user.exists():
            raise serializers.ValidationError("User with this email already exists.")

        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        email_pattern = re.compile(email_regex)
        if not re.match(email_pattern, value):
            raise serializers.ValidationError("Please enter a valid email address.")

        return value

    def create(self, validated_data):
        password = validated_data["password"]
        validated_data.pop("password2")
        user = CustomUser(is_active=True, **validated_data)
        user.set_password(password)
        user.save()
        return user


class ResetPasswordLinkSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(max_length=255)

    class Meta:
        model = ResetPasswordLink
        fields = [
            "email",
        ]

    def validate_email(self, email):
        if email:
            check_user = CustomUser.objects.filter(email__iexact=email).exists()
            if not check_user:
                raise serializers.ValidationError(
                    "No user exists with provided email id."
                )
        else:
            raise serializers.ValidationError("Please provide email id")
        return email

    def create(self, validated_data):
        user_obj = CustomUser.objects.get(email=validated_data.get("email"))
        current_datetime = timezone.now()
        reset_passw_link_obj = ResetPasswordLink.objects.filter(user=user_obj).first()
        if reset_passw_link_obj:
            reset_passw_link_obj.delete()

        reset_password_link = ResetPasswordLink()
        reset_password_link.user = user_obj
        reset_password_link.created_at = current_datetime
        reset_password_link.expired_at = (
            current_datetime + settings.RESET_PASSWORD_EXPIRY
        )
        reset_password_link.save()
        return reset_password_link


class UserPasswordResetSerializer(serializers.Serializer):
    password = serializers.CharField(
        max_length=15, style={"input_type": "password"}, write_only=True
    )
    password2 = serializers.CharField(
        max_length=15, style={"input_type": "password"}, write_only=True
    )

    class Meta:
        fields = ["password", "password2"]

    def validate(self, attrs):
        uuid = self.context.get("uid")
        reset_password_link_obj = ResetPasswordLink.objects.filter(
            id=uuid, expired_at__gte=timezone.now()
        ).first()
        if not reset_password_link_obj:
            raise serializers.ValidationError(
                {"message": "Link has been expired or is invalid."}
            )
        return attrs

    def validate_password(self, value):
        reg = "^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!#%*?&]{6,20}$"
        pattern = re.compile(reg)

        if not re.search(pattern, value):
            raise serializers.ValidationError(
                "Password is invalid. Password should contain atleast 8 characters and must"
                " contain one Uppercase, Lowercase and Alphanumeric value"
            )

        return value

    def validate_password2(self, value):
        data = self.get_initial()
        if value != data.get("password"):
            raise serializers.ValidationError(
                "Confirm Password is not same as New Password."
            )
        return value

    def create(self, data):
        new_password = data.get("password")
        uuid = self.context.get("uid")
        reset_password_link_obj = ResetPasswordLink.objects.get(
            id=uuid, expired_at__gte=timezone.now()
        )
        user = CustomUser.objects.get(email__iexact=reset_password_link_obj.user.email)
        if user:
            user.set_password(new_password)
            user.save()
            reset_password_link_obj.delete()
        return data


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    confirm_new_password = serializers.CharField(required=True)

    class Meta:
        fields = ["old_password", "new_password", "confirm_new_password"]

    def validate(self, attrs):
        old_password = attrs.get("old_password")
        new_password = attrs.get("new_password")
        confirm_password = attrs.get("confirm_new_password")
        email = self.context["request"].user
        user = CustomUser.objects.get(email=email)
        if user:
            if user.check_password(old_password):
                if old_password == new_password:
                    raise serializers.ValidationError(
                        "Password already has been used by you previous time please enter new "
                        "password."
                    )
            else:
                raise serializers.ValidationError(
                    "old password you entered is incorrect."
                )
        else:
            raise serializers.ValidationError("invalid credentials.")
        if new_password != confirm_password:
            raise serializers.ValidationError(
                "New password do not match with confirm password."
            )
        elif not len(new_password) >= 8:
            raise serializers.ValidationError("Password length should be more than 8")
        elif not re.findall("[A-Z]", new_password):
            raise serializers.ValidationError(
                "The password must contain at least 1 uppercase letter, A-Z."
            )
        elif not re.findall("[a-z]", new_password):
            raise serializers.ValidationError(
                "The password must contain at least 1 lowercase letter, a-z."
            )
        return attrs

    def create(self, data):
        new_password = data.get("new_password")
        email = self.context["request"].user
        user = CustomUser.objects.get(email__iexact=email)

        if user:
            user.set_password(new_password)
            user.save()
        return data


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True)
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    def validated_email(self, value):
        # Your custom email validation logic goes here
        if not re.match(self.email_pattern, value):
            raise serializers.ValidationError(
                {"email": "Invalid email format. Please enter a valid email address."}
            )

        try:
            get_user_model().objects.get(email__iexact=value, is_admin=False)
        except get_user_model().DoesNotExist:
            raise serializers.ValidationError(
                {
                    "email": "User not found. Please check your email address and try again."
                }
            )
        # if not user.is_active:
        #     raise serializers.ValidationError({"isActive": False})

        return value

    def validated_password(self, value):
        data = self.get_initial()
        email = data.get("email")

        user = get_user_model().objects.get(email__iexact=email, is_admin=False)
        # if not user.check_password(value):
        #     raise serializers.ValidationError(
        #         {
        #             "password": "Password that you have entered is incorrect. Please try again."
        #         }
        #     )

        return value

    def validate(self, attrs):
        data = {}
        email = attrs.get("email")
        password = attrs.get("password")
        # Call the custom email and password validation methods
        self.validated_email(email)
        self.validated_password(password)

        user = get_user_model().objects.get(email__iexact=email, is_admin=False)

        refresh = self.get_token(user)
        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)

        return data


class ResendVerificationEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()


class UserShortDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["first_name", "last_name"]
