from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.db.models import Prefetch
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from api.pagination import StationPagination
from api.models import FuelType, PriceUpdate, Reaction, Station
from api.serializers import PriceUpdateHistorySerializer, StationSerializer


class StationViewSet(viewsets.ModelViewSet):
    """
    Expõe a listagem de postos com suporte a busca geográfica e histórico de preços.
    """

    serializer_class = StationSerializer
    pagination_class = StationPagination

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

    def _get_radius_km(self):
        radius_km = self.request.query_params.get('radius_km', '3')

        try:
            radius_km = int(radius_km)
        except (TypeError, ValueError):
            raise ValidationError({
                "detail": "O parâmetro 'radius_km' deve ser um número válido."
            })

        if radius_km not in [2, 3, 5]:
            raise ValidationError({
                "detail": "O parâmetro 'radius_km' deve ser 2, 3 ou 5."
            })

        return radius_km

    def get_queryset(self):
        """
        Monta a queryset principal dos postos com prefetch das relações usadas
        na serialização.
        """
        active_updates_queryset = (
            PriceUpdate.objects
            .filter(status='active')
            .select_related('user', 'fuel_type')
            .prefetch_related(
                Prefetch(
                    'reactions',
                    queryset=Reaction.objects.select_related('user')
                )
            )
            .order_by('-created_at')
        )

        queryset = (
            Station.objects
            .all()
            .prefetch_related(
                Prefetch('price_updates', queryset=active_updates_queryset)
            )
        )

        user_location = self._get_user_location()

        if user_location:

            radius_km = self._get_radius_km()

            queryset = (
                queryset
                .annotate(calculated_distance=Distance('location', user_location))
                .filter(calculated_distance__lte=radius_km * 1000)
                .order_by('calculated_distance')
            )

        else:
            queryset = queryset.order_by('id')

        return queryset

    def get_serializer_context(self):
        """
        Injeta no contexto dados reutilizados por todos os itens serializados.
        """
        context = super().get_serializer_context()
        context['fuel_types'] = list(FuelType.objects.all())
        return context

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """
        Retorna as 20 últimas atualizações ativas de preço do posto.
        """
        station = self.get_object()

        history = (
            station.price_updates
            .filter(status='active')
            .select_related('user', 'fuel_type')
            .order_by('-created_at')[:20]
        )

        serializer = PriceUpdateHistorySerializer(history, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)