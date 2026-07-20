from rest_framework import viewsets

from api.models import TipoCombustivel
from api.serializers import TipoCombustivelSerializer


class FuelTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Expõe apenas operações de leitura para os tipos de combustível.

    Esse recurso fornece ao frontend os metadados necessários para renderização,
    como nome, cor e ordenação padrão definida no modelo.
    """

    queryset = TipoCombustivel.objects.all()
    serializer_class = TipoCombustivelSerializer
    pagination_class = None