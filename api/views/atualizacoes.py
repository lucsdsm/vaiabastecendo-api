from api.models import AtualizacaoPreco
from api.serializers import AtualizacaoPrecoSerializer

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

class AtualizacaoPrecoViewSet(viewsets.ModelViewSet):
    """Gerencia atualizações de preço associando o usuário autenticado."""

    queryset = AtualizacaoPreco.objects.all()
    serializer_class = AtualizacaoPrecoSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        """Garante autoria da atualização com base no token da requisição."""
        serializer.save(usuario=self.request.user)
