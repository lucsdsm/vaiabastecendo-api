from rest_framework import serializers
from .models import Posto

class PostoSerializer(serializers.ModelSerializer):
    # Campos adicionais para latitude, longitude e distância em metros
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    distancia_metros = serializers.SerializerMethodField()

    class Meta:
        model = Posto
        fields = ['id', 'nome', 'endereco', 'latitude', 'longitude', 'distancia_metros']

    # Extrai o eixo Y do campo 'localizacao' para a latitude
    def get_latitude(self, obj):
        return obj.localizacao.y if obj.localizacao else None

    # Extrai o eixo X do campo 'localizacao' para a longitude
    def get_longitude(self, obj):
        return obj.localizacao.x if obj.localizacao else None

    # Calcula a distância em metros entre o posto e um ponto de referência (ex: usuário)
    def get_distancia_metros(self, obj):
        if hasattr(obj, 'distancia_calculada') and obj.distancia_calculada:
            return obj.distancia_calculada.m  # Retorna os metros
        return None