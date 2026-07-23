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
    Curtidas/descurtidas do próprio autor não são computadas no backend.
    """
    price_update_id = request.data.get('price_update')
    reaction_type = request.data.get('reaction_type')
    user = request.user

    if not price_update_id or reaction_type not in ('like', 'dislike'):
        return Response(
            {"detail": "Dados inválidos."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    price_update = (
        PriceUpdate.objects
        .filter(pk=price_update_id)
        .select_related('user')
        .first()
    )

    if not price_update:
        return Response(
            {"detail": "Atualização informada não existe."},
            status=status.HTTP_404_NOT_FOUND,
        )

    is_own_update = price_update.user_id == user.id

    existing_reaction = Reaction.objects.filter(
        price_update_id=price_update_id,
        user=user,
    ).first()

    if is_own_update:
        if existing_reaction:
            if existing_reaction.reaction_type == reaction_type:
                existing_reaction.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)

            existing_reaction.reaction_type = reaction_type
            existing_reaction.save(update_fields=['reaction_type'])
            return Response(
                {"detail": "Reação atualizada com sucesso.", "counted": False},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"detail": "Reação registrada localmente, mas não contabilizada.", "counted": False},
            status=status.HTTP_200_OK,
        )

    if existing_reaction:
        if existing_reaction.reaction_type == reaction_type:
            existing_reaction.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        existing_reaction.reaction_type = reaction_type
        existing_reaction.save(update_fields=['reaction_type'])
        return Response(
            {"detail": "Reação atualizada com sucesso.", "counted": True},
            status=status.HTTP_200_OK,
        )

    Reaction.objects.create(
        price_update=price_update,
        user=user,
        reaction_type=reaction_type,
    )
    return Response(
        {"detail": "Reação criada com sucesso.", "counted": True},
        status=status.HTTP_201_CREATED,
    )