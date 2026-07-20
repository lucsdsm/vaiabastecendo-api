from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import FuelType, PriceUpdate, Reaction, Station


User = get_user_model()


class StationSerializer(serializers.ModelSerializer):
    """
    Serializa os dados de um posto com seus preços atuais e metadados de localização.
    """

    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    distance_meters = serializers.SerializerMethodField()
    current_prices = serializers.SerializerMethodField()
    last_updated_by = serializers.SerializerMethodField()

    class Meta:
        model = Station
        fields = [
            'id',
            'name',
            'address',
            'brand',
            'rating',
            'latitude',
            'longitude',
            'distance_meters',
            'current_prices',
            'last_updated_by',
        ]

    def get_latitude(self, obj):
        """
        Retorna a latitude extraída do ponto geográfico do posto.
        """
        return obj.location.y if obj.location else None

    def get_longitude(self, obj):
        """
        Retorna a longitude extraída do ponto geográfico do posto.
        """
        return obj.location.x if obj.location else None

    def get_distance_meters(self, obj):
        """
        Retorna a distância em metros anotada na queryset da view.
        """
        if hasattr(obj, 'calculated_distance') and obj.calculated_distance:
            return obj.calculated_distance.m
        return None

    def _get_active_updates(self, obj):
        """
        Retorna as atualizações ativas já prefetchadas, reutilizando cache local
        no objeto quando disponível.
        """
        cache_attr = '_cached_active_updates'

        if not hasattr(obj, cache_attr):
            setattr(obj, cache_attr, list(obj.price_updates.all()))

        return getattr(obj, cache_attr)

    def get_last_updated_by(self, obj):
        """
        Retorna o autor da atualização mais recente do posto.
        """
        updates = self._get_active_updates(obj)

        if not updates:
            return {
                "name": "Anônimo",
                "verified": False,
            }

        latest_update = updates[0]

        if latest_update.user:
            user = latest_update.user
            return {
                "name": user.username,
                "verified": user.verified,
            }

        return {
            "name": "Anônimo",
            "verified": False,
        }

    def get_current_prices(self, obj):
        """
        Monta o snapshot do preço mais recente de cada tipo de combustível.
        """
        request = self.context.get('request')
        authenticated_user = (
            request.user
            if request and hasattr(request, 'user') and request.user.is_authenticated
            else None
        )

        fuel_types = self.context.get('fuel_types')
        if fuel_types is None:
            fuel_types = list(FuelType.objects.all())

        updates = self._get_active_updates(obj)

        latest_update_by_fuel_type = {}
        for update in updates:
            fuel_type_id = update.fuel_type_id
            if fuel_type_id not in latest_update_by_fuel_type:
                latest_update_by_fuel_type[fuel_type_id] = update

        current_prices = []

        for fuel_type in fuel_types:
            update = latest_update_by_fuel_type.get(fuel_type.id)
            if not update:
                continue

            reactions = list(update.reactions.all())
            total_likes = sum(1 for reaction in reactions if reaction.reaction_type == 'like')

            user_liked = False
            if authenticated_user:
                user_liked = any(
                    reaction.reaction_type == 'like' and reaction.user_id == authenticated_user.id
                    for reaction in reactions
                )

            current_prices.append({
                'id': update.id,
                'fuel_type': fuel_type.name,
                'color': fuel_type.color,
                'price': float(update.price),
                'created_at': update.created_at,
                'likes': total_likes,
                'is_liked': user_liked,
            })

        return current_prices


class FuelTypeSerializer(serializers.ModelSerializer):
    """
    Serializa os metadados do tipo de combustível.
    """

    class Meta:
        model = FuelType
        fields = ['id', 'name', 'color']


class PriceUpdateSerializer(serializers.ModelSerializer):
    """
    Serializa uma atualização de preço e aplica validações de consistência.
    """

    class Meta:
        model = PriceUpdate
        fields = ['id', 'station', 'fuel_type', 'price', 'user', 'created_at', 'status']
        read_only_fields = ['user', 'created_at', 'status']

    def validate(self, data):
        """
        Valida a faixa aceitável do preço com base no último valor ativo.
        """
        station = data.get('station')
        fuel_type = data.get('fuel_type')
        new_price = data.get('price')

        latest_price_obj = PriceUpdate.objects.filter(
            station=station,
            fuel_type=fuel_type,
            status='active',
        ).order_by('-created_at').first()

        if latest_price_obj:
            current_price = latest_price_obj.price
            upper_limit = current_price * Decimal('1.3')
            lower_limit = current_price * Decimal('0.7')

            if new_price > upper_limit or new_price < lower_limit:
                raise serializers.ValidationError({
                    "price": f"Valor suspeito. O preço atual é de R$ {current_price}"
                })
        else:
            if new_price < Decimal('1.00') or new_price > Decimal('15.00'):
                raise serializers.ValidationError({
                    "price": "O valor informado está fora da realidade do mercado."
                })

        return data


class PriceUpdateHistorySerializer(serializers.ModelSerializer):
    """
    Serializa os dados necessários para listagem de histórico de preços.
    """

    fuel_type = serializers.CharField(source='fuel_type.name', read_only=True)
    author = serializers.SerializerMethodField()

    class Meta:
        model = PriceUpdate
        fields = ['id', 'fuel_type', 'price', 'created_at', 'author']

    def get_author(self, obj):
        """
        Retorna o nome do autor da atualização ou um fallback anônimo.
        """
        return obj.user.username if obj.user else "Anônimo"


class ReactionSerializer(serializers.ModelSerializer):
    """
    Serializa as reações vinculadas a uma atualização de preço.
    """

    class Meta:
        model = Reaction
        fields = ['id', 'price_update', 'user', 'reaction_type']
        read_only_fields = ['user']