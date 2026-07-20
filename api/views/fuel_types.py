from rest_framework import viewsets

from api.models import FuelType
from api.serializers import FuelTypeSerializer


class FuelTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Expõe apenas operações de leitura para os tipos de combustível.

    Esse recurso fornece ao frontend os metadados necessários para renderização,
    como nome, cor e ordenação padrão definida no modelo.
    """

    queryset = FuelType.objects.all()
    serializer_class = FuelTypeSerializer
    pagination_class = None