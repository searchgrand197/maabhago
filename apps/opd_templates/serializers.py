from rest_framework import serializers
from .models import OPDTemplate


class OPDTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OPDTemplate
        fields = ["key", "name", "layout"]
