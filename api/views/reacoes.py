from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ..models import Reacao, AtualizacaoPreco
from ..serializers import ReacaoSerializer

class ReacaoViewSet(viewsets.ModelViewSet):
    queryset = Reacao.objects.all()
    serializer_class = ReacaoSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        id_atualizacao = request.data.get('atualizacao')
        tipo_reacao = request.data.get('tipo')
        usuario = request.user

        if not id_atualizacao or tipo_reacao not in ['like', 'dislike']:
            return Response({"erro": "Dados inválidos"}, status=status.HTTP_400_BAD_REQUEST)

        reacao_existente = Reacao.objects.filter(atualizacao_id=id_atualizacao, usuario=usuario).first()

        if reacao_existente:
            if reacao_existente.tipo == tipo_reacao:
                reacao_existente.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                reacao_existente.tipo = tipo_reacao
                reacao_existente.save()
                return Response({"status": "alterado"}, status=status.HTTP_200_OK)
        
        Reacao.objects.create(atualizacao_id=id_atualizacao, usuario=usuario, tipo=tipo_reacao)
        return Response({"status": "criado"}, status=status.HTTP_201_CREATED)