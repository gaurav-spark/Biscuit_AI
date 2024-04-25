from django.urls import path, include
from .views import CatalogueViewset, ProcessEmbeddings, ProcessQuestion, CategoryViewset, ProcessVoice
from rest_framework import routers

router = routers.DefaultRouter()

router.register(r"catalogue",CatalogueViewset, basename='catalogue')
router.register(r"category",CategoryViewset, basename='categories')

urlpatterns = [
    path('process-embeddings', ProcessEmbeddings.as_view(), name="process-embeddings"),
    path('process-question', ProcessQuestion.as_view(), name="process-question"),
    path('speech-to-text', ProcessVoice.as_view(), name="speech-to-text"),
    path('', include(router.urls)),
]
