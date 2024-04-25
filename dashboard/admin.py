from django.contrib import admin

from dashboard.models import CatalogueItem, Category


class CatalogueItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'sku','name')

# Register your models here.
admin.site.register(CatalogueItem, CatalogueItemAdmin)
admin.site.register(Category)