from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.db.models import Prefetch
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from api.models import AtualizacaoPreco, Posto, Reacao, TipoCombustivel
from api.serializers import HistoricoAtualizacaoSerializer, PostoSerializer


class PostoViewSet(viewsets.ModelViewSet):
    """
    Expõe a listagem de postos com suporte a busca geográfica e histórico de preços.
    """

    serializer_class = PostoSerializer

    def _get_user_location(self):
        """
        Lê latitude e longitude da query string e retorna um Point válido.

        Retorna None quando a busca não for geográfica.
        Lança ValidationError quando os parâmetros forem inválidos.
        """
        lat = self.request.query_params.get('lat')
        lng = self.request.query_params.get('lng')

        if not lat or not lng:
            return None

        try:
            return Point(float(lng), float(lat), srid=4326)
        except (TypeError, ValueError):
            raise ValidationError({
                "detail": "Os parâmetros 'lat' e 'lng' devem ser números válidos."
            })

    def get_queryset(self):
        """
        Monta a queryset principal dos postos com prefetch das relações usadas
        na serialização.
        """
        atualizacoes_ativas_qs = (
            AtualizacaoPreco.objects
            .filter(status='ativo')
            .select_related('usuario', 'tipo_combustivel')
            .prefetch_related(
                Prefetch(
                    'reacoes',
                    queryset=Reacao.objects.select_related('usuario')
                )
            )
            .order_by('-data_hora')
        )

        queryset = (
            Posto.objects
            .all()
            .prefetch_related(
                Prefetch('atualizacoes', queryset=atualizacoes_ativas_qs)
            )
        )

        user_location = self._get_user_location()

        if user_location:
            queryset = (
                queryset
                .filter(localizacao__dwithin=(user_location, D(km=10)))
                .annotate(distancia_calculada=Distance('localizacao', user_location))
                .order_by('distancia_calculada')
            )
        else:
            queryset = queryset.order_by('id')

        return queryset

    def get_serializer_context(self):
        """
        Injeta no contexto dados reutilizados por todos os itens serializados.
        """
        context = super().get_serializer_context()
        context['tipos_combustivel'] = list(TipoCombustivel.objects.all())
        return context

    @action(detail=True, methods=['get'])
    def historico(self, request, pk=None):
        """
        Retorna as 20 últimas atualizações ativas de preço do posto.
        """
        posto = self.get_object()

        historico = (
            posto.atualizacoes
            .filter(status='ativo')
            .select_related('usuario', 'tipo_combustivel')
            .order_by('-data_hora')[:20]
        )

        serializer = HistoricoAtualizacaoSerializer(historico, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)