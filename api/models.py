from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.contrib.gis.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

class Usuario(AbstractUser):
    pontos = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

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
    cor = models.CharField(max_length=7, default='#000000')

    class Meta:
        verbose_name = "Tipo de Combustível"
        verbose_name_plural = "Tipos de Combustíveis"

    def __str__(self):
        return self.nome

class AtualizacaoPreco(models.Model):
    # on_delete define o comportamento quando um posto é deletado. CASCADE significa que as atualizações relacionadas também serão deletadas.
    posto = models.ForeignKey(Posto, on_delete=models.CASCADE, related_name='atualizacoes')

    # se um usuário for deletado, o campo 'usuario' será definido como NULL, mas a atualização de preço permanecerá.
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='atualizacoes_feitas')
    
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
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reacoes_dadas')
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)

    # usuário só pode reagir uma vez a uma atualização específica
    class Meta:
        verbose_name = "Reação"
        verbose_name_plural = "Reações"

        unique_together = ('atualizacao', 'usuario')

    def __str__(self):
        return f"{self.usuario.username} - {self.tipo} em {self.atualizacao.id}"

# Quando uma Reação é criada ou alterada, atualiza os pontos do usuário que fez a atualização de preço
@receiver(post_save, sender=Reacao)
def processar_pontuacao_reacao(sender, instance, created, **kwargs):
    autor = instance.atualizacao.usuario
    if autor:
        if created:
            autor.pontos += 1 if instance.tipo == 'like' else -1
        else:
            autor.pontos += 2 if instance.tipo == 'like' else -2
        autor.save()

# Quando o usuário clica novamente para remover o like (Delete)
@receiver(post_delete, sender=Reacao)
def reverter_pontuacao_reacao(sender, instance, **kwargs):
    autor = instance.atualizacao.usuario
    
    if not autor:
        return
        
    # Faz o inverso direto no autor. Se apagou um like, perde 1 ponto.
    autor.pontos -= 1 if instance.tipo == 'like' else -1
    autor.save()