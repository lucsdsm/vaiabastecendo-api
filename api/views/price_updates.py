from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from api.models import AtualizacaoPreco
from api.serializers import AtualizacaoPrecoSerializer


class PriceUpdateViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Gerencia atualizações de preço associadas ao usuário autenticado.

    Responsabilidades:
    - permitir criação de novas atualizações
    - expor listagem e detalhe quando necessário
    - garantir autoria com base no usuário autenticado
    """

    serializer_class = AtualizacaoPrecoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Retorna as atualizações com relacionamentos carregados para reduzir queries
        em futuras extensões do endpoint.
        """
        return (
            AtualizacaoPreco.objects
            .select_related('posto', 'tipo_combustivel', 'usuario')
            .order_by('-data_hora')
        )

    def perform_create(self, serializer):
        """
        Persiste a atualização vinculando automaticamente o usuário autenticado
        como autor do registro.
        """
        serializer.save(usuario=self.request.user)