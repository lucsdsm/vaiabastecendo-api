from api.models import AtualizacaoPreco
from api.serializers import AtualizacaoPrecoSerializer

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

class AtualizacaoPrecoViewSet(viewsets.ModelViewSet):
    queryset = AtualizacaoPreco.objects.all()
    serializer_class = AtualizacaoPrecoSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)
