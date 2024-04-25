from django.db import models
from django.utils.text import slugify


# Create your models here.


class BaseModel(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        "accounts.CustomUser",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="created_by",
    )
    last_modified_by = models.ForeignKey(
        "accounts.CustomUser",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="modified_by",
    )

    class Meta:
        abstract = True


class CatalogueItem(BaseModel):
    parent_item = models.ForeignKey(
        "self", on_delete=models.SET_NULL, blank=True, null=True
    )
    category = models.ForeignKey('dashboard.Category', on_delete=models.CASCADE, blank=True, null=True)
    slug = models.SlugField(max_length=255, blank=True, null=True)
    sku = models.CharField(max_length=200)
    name = models.CharField(max_length=250)
    content_type = models.CharField(max_length=250, blank=True, null=True)
    data = models.TextField()
    data_id = models.CharField(max_length=250, blank=True, null=True)
    source = models.CharField(max_length=250, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Category(models.Model):
    user = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class UserChat(models.Model):
    user = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE, blank=True, null=True)
    recent_response = models.TextField(blank=True, null=True)
    chat_history = models.JSONField(blank=True, null=True)
