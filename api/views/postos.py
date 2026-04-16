from api.models import Posto
from api.serializers import PostoSerializer

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from rest_framework import viewsets

class PostoViewSet(viewsets.ModelViewSet):
    serializer_class = PostoSerializer

    def get_queryset(self):
        queryset = Posto.objects.prefetch_related(
            'atualizacoes__usuario', 
            'atualizacoes__tipo_combustivel').all().order_by('id')

        lat = self.request.query_params.get('lat')
        lng = self.request.query_params.get('lng')

        if lat and lng:
            user_location = Point(float(lng), float(lat), srid=4326)

            # O banco calcula a distância e já ordena
            queryset = queryset.annotate(
                distancia_calculada=Distance('localizacao', user_location)
            ).order_by('distancia_calculada')
            
        return queryset