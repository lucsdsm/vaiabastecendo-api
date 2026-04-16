from api.models import AtualizacaoPreco
from api.serializers import AtualizacaoPrecoSerializer

from rest_framework import viewsets

class AtualizacaoPrecoViewSet(viewsets.ModelViewSet):
    queryset = AtualizacaoPreco.objects.all()
    serializer_class = AtualizacaoPrecoSerializer

