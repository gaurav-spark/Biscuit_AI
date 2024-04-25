import os

import requests
from django.conf import settings
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from accounts.models import CustomUser
from dashboard.models import CatalogueItem, Category, UserChat
from dashboard.serializers import CatalogueListSerializer, CatalogueDetailSerializer, CatalogueCreateUpdateSerializer
from dashboard.process_query import QueryProcessor
from dashboard.serializers.category import CategorySerializer
from dashboard.serializers.process_query import ProcessQuery, SpeechToTextSerializer

from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from django.templatetags.static import static
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores.pinecone import Pinecone
from openai import OpenAI
import whisper
import librosa
import numpy as np
from pydub import AudioSegment


# Create your views here.
@extend_schema(tags=["Catalogue APIs"])
class CatalogueViewset(ModelViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    model_class = CatalogueItem
    list_serializer_class = CatalogueListSerializer
    detail_serializer_class = CatalogueDetailSerializer
    serializer_class = CatalogueCreateUpdateSerializer

    def get_serializer_class(self):
        if self.action == "list":
            return self.list_serializer_class
        elif self.action == "retrieve":
            return self.detail_serializer_class
        else:
            return self.serializer_class

    def get_queryset(self):
        item_queryset = self.model_class.objects.filter(created_by=self.request.user)
        return item_queryset


@extend_schema(tags=["Langchain APIs"])
class ProcessEmbeddings(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        embeddings = OpenAIEmbeddings()
        items = CatalogueItem.objects.filter(created_by=request.user)
        for item in items:
            filename = item.slug if hasattr(item, 'slug') else None
            if filename:
                raw_data = item.data
                documents = [Document(page_content=raw_data, metadata={"source": filename})]
                text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
                docs = text_splitter.split_documents(documents)
                Pinecone.from_documents(docs, embeddings, index_name='testing', namespace=item.category.slug)
        return Response({'message': 'Success'}, status=status.HTTP_200_OK)


@extend_schema(tags=["Langchain APIs"])
class ProcessVoice(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = SpeechToTextSerializer

    def post(self, request, *args, **kwargs):
        user = request.user
        audio_file = request.data.get("audio_file")
        recent_response = request.data.get("recent_response")
        audio_files_dir = os.path.join(settings.BASE_DIR, "static", "audio_files")
        speech_files_dir = os.path.join(settings.BASE_DIR, "static", "speech_files")
        os.makedirs(audio_files_dir, exist_ok=True)
        os.makedirs(speech_files_dir, exist_ok=True)

        print("audio_file.name:: ", audio_file.name)

        # Save the uploaded audio file
        file_path = os.path.join(audio_files_dir, audio_file.name)
        with open(file_path, 'wb') as audio_dest:
            for chunk in audio_file.chunks():
                audio_dest.write(chunk)

        try:
            client = OpenAI()
            audio_file = open(file_path, "rb")
            voice_model_result = client.audio.translations.create(
                model="whisper-1",
                file=audio_file
            )
            # result = ""
            url = "http://localhost:9000/api/v1/dashboard/process-question"
            api_call = requests.post(url, headers={}, data={'query': voice_model_result.text, 'workflow': 'wine',
                                                            'history': [], 'recent_response': recent_response})
            api_response = api_call.json()
            user = UserChat.objects.filter(user=user).first()
            chat_history = [] if not user else user.chat_history
            if not user:
                user = UserChat.objects.create(user=user, recent_response=api_response['response'])


            os.remove(file_path)

            speech_file_path = os.path.join(speech_files_dir, "speech.mp3")
            response = client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=api_response['response']
            )
            speech_file_url = request.build_absolute_uri(settings.STATIC_URL + "speech_files/speech.mp3")
            response.stream_to_file(speech_file_path)

            result = {"speech": voice_model_result.text,
                      "model_response": api_response['response'],
                      "speech_file": speech_file_url
                      }
            user.chat_history = chat_history.append({"Human:": voice_model_result.text,
                                                     "AI:": api_response['response']})
            user.recent_response = api_response['response']
            user.save()
        except Exception as e:
            return Response(f'Error: {e.args}')
        return Response(result, status=status.HTTP_200_OK)


@extend_schema(tags=["Langchain APIs"])
class ProcessQuestion(APIView):
    # permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ProcessQuery

    def post(self, request, *args, **kwargs):
        user = CustomUser.objects.filter(email="asheem@sparkbrains.in").first()
        serializer_obj = self.serializer_class(data=request.data)
        serializer_obj.is_valid(raise_exception=True)
        query = serializer_obj.validated_data.get('query')
        workflow = serializer_obj.validated_data.get('workflow')
        history = serializer_obj.validated_data.get('history', [])
        recent_response = serializer_obj.validated_data.get('recent_response', '')
        query_processor_object = QueryProcessor(user=user)
        if workflow == "Other":
            classification = query_processor_object.select_workflow(query)
            if "healthcare" in classification.lower():
                namespace = "cvs-health"
            elif 'drinks' in classification.lower():
                namespace = 'wine'
            else:
                namespace = None
        else:
            namespace = workflow
        response = query_processor_object.process_query(response=recent_response, query=query, namespace=namespace,
                                                        chat_history=history)
        print(response, '++++++++++++++++++++++++++++++++++++++++++++')
        response['classified'] = "Other" if namespace is None else namespace.capitalize()
        return Response(response, status=status.HTTP_200_OK)


@extend_schema(tags=["Categories APIs"])
class CategoryViewset(ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)


class ChatBotTest(TemplateView):
    template_name = "chatbot/index.html"
