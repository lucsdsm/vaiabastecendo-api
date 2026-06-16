from api.models import Posto
from api.serializers import PostoSerializer

from django.contrib.gis.measure import D
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from rest_framework import viewsets

class PostoViewSet(viewsets.ModelViewSet):
    """Expõe postos com suporte opcional de ordenação por proximidade num raio limite."""
    serializer_class = PostoSerializer

    def get_queryset(self):
        queryset = Posto.objects.all()

        lat = self.request.query_params.get('lat')
        lng = self.request.query_params.get('lng')

        if lat and lng:
            user_location = Point(float(lng), float(lat), srid=4326)

            # 1. FILTRO ESPACIAL
            # Força o banco a usar o índice GiST. Descarta instantaneamente qualquer posto que esteja a mais de 10 km de distância do motorista.
            queryset = queryset.filter(localizacao__dwithin=(user_location, D(km=10)))

            # 2. MATEMÁTICA EXATA
            # Só calcula a distância exata para os 10 ou 20 postos que sobraram no filtro acima, em vez de milhares.
            queryset = queryset.annotate(
                distancia_calculada=Distance('localizacao', user_location)
            ).order_by('distancia_calculada')
        else:
            # Se não mandar lat/lng, aí sim ordena por ID
            queryset = queryset.order_by('id')
            
        return queryset