from rest_framework import serializers


class ProcessQuery(serializers.Serializer):
    query = serializers.CharField()
    history = serializers.JSONField(required=False)
    workflow = serializers.CharField()
    recent_response = serializers.CharField(required=False)


class SpeechToTextSerializer(serializers.Serializer):
    audio_file = serializers.FileField()
    recent_response = serializers.CharField(required=False)

