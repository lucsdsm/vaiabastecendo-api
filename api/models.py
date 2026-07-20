from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.gis.db import models
from django.db.models import Case, F, IntegerField, UniqueConstraint, Value, When
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver


class Usuario(AbstractUser):
    """
    Modelo de usuário customizado da aplicação.

    Armazena a pontuação acumulada do usuário com base nas reações recebidas
    nas atualizações de preço publicadas por ele.
    """

    pontos = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

    @property
    def verificado(self):
        """
        Indica se o usuário já atingiu a pontuação mínima para verificação.
        """
        return self.pontos >= 100


class Posto(models.Model):
    """
    Representa um posto de combustível disponível na plataforma.
    """

    place_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    nome = models.CharField(max_length=255)
    localizacao = models.PointField(srid=4326, geography=True)
    endereco = models.CharField(max_length=255)
    bandeira = models.CharField(max_length=50, default='Bandeira Branca')
    avaliacao = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name = "Posto"
        verbose_name_plural = "Postos"

    def __str__(self):
        return self.nome


class TipoCombustivel(models.Model):
    """
    Define os tipos de combustível e seus metadados visuais.
    """

    nome = models.CharField(max_length=50)
    cor = models.CharField(max_length=7, default='#000000')
    order = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Tipo de Combustível"
        verbose_name_plural = "Tipos de Combustíveis"
        ordering = ['order', 'nome']

    def __str__(self):
        return self.nome


class AtualizacaoPreco(models.Model):
    """
    Representa uma atualização de preço enviada por um usuário para um posto
    e um tipo de combustível específicos.
    """

    posto = models.ForeignKey(Posto, on_delete=models.CASCADE, related_name='atualizacoes')
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='atualizacoes_feitas'
    )
    tipo_combustivel = models.ForeignKey(TipoCombustivel, on_delete=models.CASCADE)
    preco = models.DecimalField(max_digits=5, decimal_places=2)
    data_hora = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='ativo')

    class Meta:
        verbose_name = "Atualização de Preço"
        verbose_name_plural = "Atualizações de Preços"

    def __str__(self):
        return f"{self.posto.nome} - {self.tipo_combustivel.nome} - R$ {self.preco}"


class Reacao(models.Model):
    """
    Representa a reação de um usuário a uma atualização de preço.
    """

    TIPO_CHOICES = (
        ('like', 'Like'),
        ('dislike', 'Dislike'),
    )

    atualizacao = models.ForeignKey(
        AtualizacaoPreco,
        on_delete=models.CASCADE,
        related_name='reacoes'
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reacoes_dadas'
    )
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)

    class Meta:
        verbose_name = "Reação"
        verbose_name_plural = "Reações"
        constraints = [
            UniqueConstraint(
                fields=['atualizacao', 'usuario'],
                name='unique_reacao_por_usuario_em_atualizacao'
            )
        ]

    def __str__(self):
        return f"{self.usuario.username} - {self.tipo} em {self.atualizacao.id}"


def _atualizar_pontos_usuario(usuario_id, delta):
    """
    Atualiza a pontuação do usuário de forma atômica, impedindo valores negativos.
    """
    Usuario.objects.filter(pk=usuario_id).update(
        pontos=Case(
            When(pontos__lte=-delta, then=Value(0)),
            default=F('pontos') + delta,
            output_field=IntegerField(),
        )
    )


@receiver(post_save, sender=Reacao)
def processar_pontuacao_reacao(sender, instance, created, **kwargs):
    """
    Atualiza a pontuação do autor da atualização quando uma reação é criada
    ou quando uma reação existente muda de tipo.
    """
    autor = instance.atualizacao.usuario
    if not autor:
        return

    if created:
        delta = 1 if instance.tipo == 'like' else -1
    else:
        delta = 2 if instance.tipo == 'like' else -2

    _atualizar_pontos_usuario(autor.pk, delta)


@receiver(post_delete, sender=Reacao)
def reverter_pontuacao_reacao(sender, instance, **kwargs):
    """
    Reverte a pontuação do autor quando uma reação é removida.
    """
    autor = instance.atualizacao.usuario
    if not autor:
        return

    delta = -1 if instance.tipo == 'like' else 1
    _atualizar_pontos_usuario(autor.pk, delta)