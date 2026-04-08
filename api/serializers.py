from rest_framework import serializers
from .models import Posto

class PostoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Posto
        fields = '__all__'