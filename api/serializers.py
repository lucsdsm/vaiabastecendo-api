from decimal import Decimal

from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import FuelType, PriceUpdate, Reaction, Station


User = get_user_model()


class PriceUpdateHistorySerializer(serializers.ModelSerializer):
    fuel_type = serializers.CharField(source='fuel_type.name', read_only=True)
    color = serializers.CharField(source='fuel_type.color', read_only=True)
    station = serializers.SerializerMethodField()
    author = serializers.SerializerMethodField()
    likes = serializers.SerializerMethodField()

    class Meta:
        model = PriceUpdate
        fields = ['id', 'station', 'fuel_type', 'color', 'price', 'created_at', 'author', 'likes']

    def get_station(self, obj):
        return {
            'id': obj.station_id,
            'name': obj.station.name,
            'brand': obj.station.brand,
            'address': obj.station.address,
        }

    def get_author(self, obj):
        return obj.user.username if obj.user else 'Anônimo'

    def get_likes(self, obj):
        return obj.reactions.filter(reaction_type='like').count()


class UserProfileSerializer(serializers.ModelSerializer):
    photo = serializers.SerializerMethodField()
    likes_given = serializers.SerializerMethodField()
    likes_received = serializers.SerializerMethodField()
    history = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'photo',
            'likes_received',
            'likes_given',
            'history',
        ]

    def get_photo(self, obj):
        social_account = SocialAccount.objects.filter(
            user=obj,
            provider='google',
        ).first()

        if not social_account:
            return None

        return social_account.extra_data.get('picture')

    def get_likes_given(self, obj):
        return Reaction.objects.filter(user=obj, reaction_type='like').count()

    def get_likes_received(self, obj):
        return Reaction.objects.filter(
            price_update__user=obj,
            reaction_type='like',
        ).count()

    def get_history(self, obj):
        updates = (
            PriceUpdate.objects
            .filter(user=obj)
            .select_related('station', 'fuel_type', 'user')
            .prefetch_related('reactions')
            .order_by('-created_at')[:10]
        )
        return PriceUpdateHistorySerializer(updates, many=True, context=self.context).data


class StationSerializer(serializers.ModelSerializer):
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
        return obj.location.y if obj.location else None

    def get_longitude(self, obj):
        return obj.location.x if obj.location else None

    def get_distance_meters(self, obj):
        if hasattr(obj, 'calculated_distance') and obj.calculated_distance:
            return obj.calculated_distance.m
        return None

    def _get_active_updates(self, obj):
        cache_attr = '_cached_active_updates'
        if not hasattr(obj, cache_attr):
            setattr(obj, cache_attr, list(obj.price_updates.all()))
        return getattr(obj, cache_attr)

    def get_last_updated_by(self, obj):
        updates = self._get_active_updates(obj)

        if not updates:
            return {'name': 'Anônimo'}

        latest_update = updates[0]

        if latest_update.user:
            user = latest_update.user
            return {
                'name': user.username,
                'likes_received': Reaction.objects.filter(
                    price_update__user=user,
                    reaction_type='like',
                ).count(),
            }

        return {'name': 'Anônimo', 'likes_received': 0}

    def get_current_prices(self, obj):
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
    class Meta:
        model = FuelType
        fields = ['id', 'name', 'color']


class PriceUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceUpdate
        fields = ['id', 'station', 'fuel_type', 'price', 'user', 'created_at', 'status']
        read_only_fields = ['user', 'created_at', 'status']

    def validate(self, data):
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
                    'price': f'Valor suspeito. O preço atual é de R$ {current_price}'
                })
        else:
            if new_price < Decimal('1.00') or new_price > Decimal('15.00'):
                raise serializers.ValidationError({
                    'price': 'O valor informado está fora da realidade do mercado.'
                })

        return data


class ReactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reaction
        fields = ['id', 'price_update', 'user', 'reaction_type']
        read_only_fields = ['user']