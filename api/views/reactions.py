from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.models import PriceUpdate, Reaction
from api.serializers import ReactionSerializer


class ReactionViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Gerencia as reações do usuário autenticado sobre atualizações de preço.
    """

    serializer_class = ReactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Restringe a queryset às reações do usuário autenticado.
        """
        return (
            Reaction.objects
            .filter(user=self.request.user)
            .select_related('user', 'price_update')
        )

    def create(self, request, *args, **kwargs):
        """
        Aplica a semântica de toggle para criação, remoção ou troca de reação.
        """
        price_update_id = request.data.get('price_update')
        reaction_type = request.data.get('reaction_type')
        user = request.user

        if not price_update_id or reaction_type not in ('like', 'dislike'):
            return Response(
                {"detail": "Dados inválidos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not PriceUpdate.objects.filter(pk=price_update_id).exists():
            return Response(
                {"detail": "Atualização informada não existe."},
                status=status.HTTP_404_NOT_FOUND,
            )

        existing_reaction = Reaction.objects.filter(
            price_update_id=price_update_id,
            user=user,
        ).first()

        if existing_reaction:
            if existing_reaction.reaction_type == reaction_type:
                existing_reaction.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)

            existing_reaction.reaction_type = reaction_type
            existing_reaction.save(update_fields=['reaction_type'])
            return Response(
                {"detail": "Reação atualizada com sucesso."},
                status=status.HTTP_200_OK,
            )

        Reaction.objects.create(
            price_update_id=price_update_id,
            user=user,
            reaction_type=reaction_type,
        )
        return Response(
            {"detail": "Reação criada com sucesso."},
            status=status.HTTP_201_CREATED,
        )