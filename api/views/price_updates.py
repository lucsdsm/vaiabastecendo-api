from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from api.models import PriceUpdate
from api.serializers import PriceUpdateSerializer


class PriceUpdateViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Gerencia atualizações de preço associadas ao usuário autenticado.
    """

    serializer_class = PriceUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Retorna as atualizações com relacionamentos carregados para reduzir queries
        durante serialização e futuras extensões do endpoint.
        """
        return (
            PriceUpdate.objects
            .select_related('station', 'fuel_type', 'user')
            .order_by('-created_at')
        )

    def perform_create(self, serializer):
        """
        Persiste a atualização vinculando automaticamente o usuário autenticado
        como autor do registro.
        """
        serializer.save(user=self.request.user)