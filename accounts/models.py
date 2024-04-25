from django.contrib.auth.models import (
    BaseUserManager,
    AbstractBaseUser,
)
from django.db import models
import uuid


class MyUserManager(BaseUserManager):
    def create_user(self, email, password=None, password2=None):
        """
        Creates and saves a User with the given email, and password.
        """
        if not email:
            raise ValueError("Users must have an email address")

        user = self.model(
            email=self.normalize_email(email),
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None):
        """
        Creates and saves a superuser with the given email, date of
        birth and password.
        """
        user = self.create_user(
            email,
            password=password,
        )
        user.is_admin = True
        user.is_active = True
        user.save(using=self._db)
        return user


class CustomUser(AbstractBaseUser):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="User ID",
        unique=True,
    )
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=False)

    is_admin = models.BooleanField(default=False)
    example_prompt = models.JSONField(blank=True, null=True)
    USERNAME_FIELD = "email"
    objects = MyUserManager()

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        return True

    def has_module_perms(self, app_label):
        return True

    @property
    def is_staff(self):
        return self.is_admin


class ResetPasswordLink(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="id",
        unique=True,
    )
    user = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name="reset_password_link"
    )
    created_at = models.DateTimeField(auto_now_add=False)
    expired_at = models.DateTimeField(auto_now_add=False)

    class Meta:
        db_table = "reset_password_link"
