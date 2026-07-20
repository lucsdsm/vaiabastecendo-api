from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.models import AtualizacaoPreco, Reacao
from api.serializers import ReacaoSerializer


class ReactionViewSet(viewsets.ModelViewSet):
    """
    Gerencia as reações do usuário autenticado sobre atualizações de preço.

    Regras de negócio:
    - o usuário pode ter no máximo uma reação por atualização
    - enviar a mesma reação remove a reação existente
    - enviar uma reação diferente troca o tipo da reação existente
    """

    serializer_class = ReacaoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Restringe a queryset às reações do usuário autenticado.

        Isso evita exposição desnecessária das reações de outros usuários em
        operações diretas do viewset.
        """
        return Reacao.objects.filter(usuario=self.request.user).select_related(
            'usuario',
            'atualizacao',
        )

    def create(self, request, *args, **kwargs):
        """
        Aplica a semântica de toggle para criação, remoção ou troca de reação.
        """
        atualizacao_id = request.data.get('atualizacao')
        reaction_type = request.data.get('tipo')
        user = request.user

        if not atualizacao_id or reaction_type not in ('like', 'dislike'):
            return Response(
                {"erro": "Dados inválidos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not AtualizacaoPreco.objects.filter(pk=atualizacao_id).exists():
            return Response(
                {"erro": "Atualização informada não existe."},
                status=status.HTTP_404_NOT_FOUND,
            )

        existing_reaction = Reacao.objects.filter(
            atualizacao_id=atualizacao_id,
            usuario=user,
        ).first()

        if existing_reaction:
            if existing_reaction.tipo == reaction_type:
                existing_reaction.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)

            existing_reaction.tipo = reaction_type
            existing_reaction.save(update_fields=['tipo'])
            return Response({"status": "alterado"}, status=status.HTTP_200_OK)

        Reacao.objects.create(
            atualizacao_id=atualizacao_id,
            usuario=user,
            tipo=reaction_type,
        )
        return Response({"status": "criado"}, status=status.HTTP_201_CREATED)