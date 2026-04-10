from .models import Posto, TipoCombustivel, AtualizacaoPreco
from .serializers import PostoSerializer, TipoCombustivelSerializer, AtualizacaoPrecoSerializer

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from rest_framework import viewsets

# Create your views here.
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
        
class TipoCombustivelViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TipoCombustivel.objects.all()
    serializer_class = TipoCombustivelSerializer
    pagination_class = None

class AtualizacaoPrecoViewSet(viewsets.ModelViewSet):
    queryset = AtualizacaoPreco.objects.all()
    serializer_class = AtualizacaoPrecoSerializer