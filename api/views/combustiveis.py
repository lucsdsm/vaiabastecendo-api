from api.models import TipoCombustivel
from api.serializers import TipoCombustivelSerializer

from rest_framework import viewsets

class TipoCombustivelViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TipoCombustivel.objects.all()
    serializer_class = TipoCombustivelSerializer
    pagination_class = None