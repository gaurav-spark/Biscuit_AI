from rest_framework import serializers
from dashboard.models import CatalogueItem
from accounts.serializers import UserShortDetailSerializer
from dashboard.serializers.category import CategorySerializer


class CatalogueShortDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = CatalogueItem
        fields = ['id', 'name']


class CatalogueListSerializer(serializers.ModelSerializer):
    created_by = UserShortDetailSerializer(many=False)
    category = CategorySerializer(many=False)

    class Meta:
        model = CatalogueItem
        exclude = ['content_type', 'modified_date']


class CatalogueDetailSerializer(serializers.ModelSerializer):
    parent_item = CatalogueShortDetailSerializer(many=False)
    category = CategorySerializer(many=False)
    class Meta:
        model = CatalogueItem
        fields = '__all__'


class CatalogueCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CatalogueItem
        exclude = ['last_modified_by', 'created_by', 'slug']

    def create(self, validated_data):
        created_obj = super().create(validated_data)
        request = self.context.get('request')
        created_obj.created_by = request.user
        created_obj.save()
        return created_obj
