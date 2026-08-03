from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.gis.db import models
from django.db.models import Case, F, IntegerField, UniqueConstraint, Value, When
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver


class User(AbstractUser):
    """
    Modelo de usuário customizado da aplicação.

    Armazena a pontuação acumulada do usuário com base nas reações recebidas
    nas atualizações de preço publicadas por ele.
    """

    likes_received_test = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

    @property
    def likes_received(self):
        return Reaction.objects.filter(
            price_update__user=self,
            reaction_type='like',
        ).count()


class Station(models.Model):
    """
    Representa um posto de combustível disponível na plataforma.
    """

    place_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    name = models.CharField(max_length=255)
    location = models.PointField(srid=4326, geography=True)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=120, null=True, blank=True)
    neighborhood = models.CharField(max_length=120, null=True, blank=True)
    brand = models.CharField(max_length=50, default='Bandeira Branca')
    rating = models.FloatField(null=True, blank=True)
    user_ratings_total = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Posto"
        verbose_name_plural = "Postos"

    def __str__(self):
        return self.name


class FuelType(models.Model):
    """
    Define os tipos de combustível e seus metadados visuais.
    """

    name = models.CharField(max_length=50)
    color = models.CharField(max_length=7, default='#000000')
    order = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Tipo de Combustível"
        verbose_name_plural = "Tipos de Combustíveis"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class PriceUpdate(models.Model):
    """
    Representa uma atualização de preço enviada por um usuário para um posto
    e um tipo de combustível específicos.
    """

    station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name='price_updates')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='price_updates_created'
    )
    fuel_type = models.ForeignKey(FuelType, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=5, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='active')

    class Meta:
        verbose_name = "Atualização de Preço"
        verbose_name_plural = "Atualizações de Preços"

    def __str__(self):
        return f"{self.station.name} - {self.fuel_type.name} - R$ {self.price}"


class Reaction(models.Model):
    """
    Representa a reação de um usuário a uma atualização de preço.
    """

    REACTION_TYPE_CHOICES = (
        ('like', 'Like'),
        ('dislike', 'Dislike'),
    )

    price_update = models.ForeignKey(
        PriceUpdate,
        on_delete=models.CASCADE,
        related_name='reactions'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reactions_given'
    )
    reaction_type = models.CharField(max_length=10, choices=REACTION_TYPE_CHOICES)

    class Meta:
        verbose_name = "Reação"
        verbose_name_plural = "Reações"
        constraints = [
            UniqueConstraint(
                fields=['price_update', 'user'],
                name='unique_reaction_per_user_per_price_update'
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.reaction_type} em {self.price_update.id}"
