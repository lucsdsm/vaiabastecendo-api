from django.db import models
from django.contrib.auth.models import User
from django.contrib.gis.db import models

# Create your models here.

class Posto(models.Model):
    nome = models.CharField(max_length=255)
    localizacao = models.PointField(srid=4326, geography=True)  # Usando PointField para armazenar latitude e longitude
    endereco = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Posto"
        verbose_name_plural = "Postos"

    def __str__(self):
        return self.nome

class TipoCombustivel(models.Model):
    nome = models.CharField(max_length=50)

    class Meta:
        verbose_name = "Tipo de Combustível"
        verbose_name_plural = "Tipos de Combustíveis"

    def __str__(self):
        return self.nome

class AtualizacaoPreco(models.Model):
    # on_delete define o comportamento quando um posto é deletado. CASCADE significa que as atualizações relacionadas também serão deletadas.
    posto = models.ForeignKey(Posto, on_delete=models.CASCADE, related_name='atualizacoes')

    # se um usuário for deletado, o campo 'usuario' será definido como NULL, mas a atualização de preço permanecerá.
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='atualizacoes_feitas')
    
    tipo_combustivel = models.ForeignKey(TipoCombustivel, on_delete=models.CASCADE)
    preco = models.DecimalField(max_digits=5, decimal_places=2)
    
    # preenche automaticamente com a data/hora do servidor no momento da criação
    data_hora = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='ativo')

    class Meta:
        verbose_name = "Atualização de Preço"
        verbose_name_plural = "Atualizações de Preços"

    def __str__(self):
        return f"{self.posto.nome} - {self.tipo_combustivel.nome} - R$ {self.preco}"

class Reacao(models.Model):
    TIPO_CHOICES = (
        ('like', 'Like'),
        ('dislike', 'Dislike'),
    )
    atualizacao = models.ForeignKey(AtualizacaoPreco, on_delete=models.CASCADE, related_name='reacoes')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reacoes_dadas')
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)

    # usuário só pode reagir uma vez a uma atualização específica
    class Meta:
        verbose_name = "Reação"
        verbose_name_plural = "Reações"

        unique_together = ('atualizacao', 'usuario')

    def __str__(self):
        return f"{self.usuario.username} - {self.tipo} em {self.atualizacao.id}"