from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import AtualizacaoPreco, Posto, Reacao, TipoCombustivel


User = get_user_model()


class PostoSerializer(serializers.ModelSerializer):
    """
    Serializa os dados de um posto com seus preços atuais e metadados de localização.
    """

    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    distancia_metros = serializers.SerializerMethodField()
    precos_atuais = serializers.SerializerMethodField()
    autor_ultima_atualizacao = serializers.SerializerMethodField()

    class Meta:
        model = Posto
        fields = [
            'id',
            'nome',
            'endereco',
            'bandeira',
            'avaliacao',
            'latitude',
            'longitude',
            'distancia_metros',
            'precos_atuais',
            'autor_ultima_atualizacao',
        ]

    def get_latitude(self, obj):
        return obj.localizacao.y if obj.localizacao else None

    def get_longitude(self, obj):
        return obj.localizacao.x if obj.localizacao else None

    def get_distancia_metros(self, obj):
        if hasattr(obj, 'distancia_calculada') and obj.distancia_calculada:
            return obj.distancia_calculada.m
        return None

    def _get_atualizacoes_ativas(self, obj):
        """
        Retorna as atualizações ativas já prefetchadas, reutilizando cache local
        no objeto quando disponível.
        """
        cache_attr = '_cached_atualizacoes_ativas'

        if not hasattr(obj, cache_attr):
            setattr(obj, cache_attr, list(obj.atualizacoes.all()))

        return getattr(obj, cache_attr)

    def get_autor_ultima_atualizacao(self, obj):
        """
        Retorna o autor da atualização mais recente do posto.
        """
        atualizacoes = self._get_atualizacoes_ativas(obj)

        if not atualizacoes:
            return {
                "nome": "Anônimo",
                "verificado": False,
            }

        ultima_atualizacao = atualizacoes[0]

        if ultima_atualizacao.usuario:
            usuario = ultima_atualizacao.usuario
            return {
                "nome": usuario.username,
                "verificado": usuario.pontos >= 100,
            }

        return {
            "nome": "Anônimo",
            "verificado": False,
        }

    def get_precos_atuais(self, obj):
        """
        Monta o snapshot do preço mais recente de cada tipo de combustível.
        """
        request = self.context.get('request')
        usuario_logado = (
            request.user
            if request and hasattr(request, 'user') and request.user.is_authenticated
            else None
        )

        tipos_combustivel = self.context.get('tipos_combustivel')
        if tipos_combustivel is None:
            tipos_combustivel = list(TipoCombustivel.objects.all())

        atualizacoes = self._get_atualizacoes_ativas(obj)

        ultima_atualizacao_por_tipo = {}
        for atualizacao in atualizacoes:
            tipo_id = atualizacao.tipo_combustivel_id
            if tipo_id not in ultima_atualizacao_por_tipo:
                ultima_atualizacao_por_tipo[tipo_id] = atualizacao

        lista_precos = []

        for tipo in tipos_combustivel:
            atualizacao = ultima_atualizacao_por_tipo.get(tipo.id)
            if not atualizacao:
                continue

            reacoes = list(atualizacao.reacoes.all())
            total_likes = sum(1 for reacao in reacoes if reacao.tipo == 'like')

            usuario_curtiu = False
            if usuario_logado:
                usuario_curtiu = any(
                    reacao.tipo == 'like' and reacao.usuario_id == usuario_logado.id
                    for reacao in reacoes
                )

            lista_precos.append({
                'id': atualizacao.id,
                'tipo': tipo.nome,
                'cor': tipo.cor,
                'preco': float(atualizacao.preco),
                'data': atualizacao.data_hora,
                'likes': total_likes,
                'is_liked': usuario_curtiu,
            })

        return lista_precos


class TipoCombustivelSerializer(serializers.ModelSerializer):
    """
    Serializa os metadados do tipo de combustível.
    """

    class Meta:
        model = TipoCombustivel
        fields = ['id', 'nome', 'cor']


class AtualizacaoPrecoSerializer(serializers.ModelSerializer):
    """
    Serializa uma atualização de preço e aplica validações de consistência.
    """

    class Meta:
        model = AtualizacaoPreco
        fields = ['id', 'posto', 'tipo_combustivel', 'preco', 'usuario', 'data_hora', 'status']
        read_only_fields = ['usuario', 'data_hora', 'status']

    def validate(self, data):
        """
        Valida a faixa aceitável do preço com base no último valor ativo.
        """
        posto = data.get('posto')
        tipo_combustivel = data.get('tipo_combustivel')
        novo_preco = data.get('preco')

        ultimo_preco_obj = AtualizacaoPreco.objects.filter(
            posto=posto,
            tipo_combustivel=tipo_combustivel,
            status='ativo',
        ).order_by('-data_hora').first()

        if ultimo_preco_obj:
            preco_atual = ultimo_preco_obj.preco
            limite_superior = preco_atual * Decimal('1.3')
            limite_inferior = preco_atual * Decimal('0.7')

            if novo_preco > limite_superior or novo_preco < limite_inferior:
                raise serializers.ValidationError({
                    "preco": f"Valor suspeito. O preço atual é de R$ {preco_atual}"
                })
        else:
            if novo_preco < Decimal('1.00') or novo_preco > Decimal('15.00'):
                raise serializers.ValidationError({
                    "preco": "O valor informado está fora da realidade do mercado."
                })

        return data


class HistoricoAtualizacaoSerializer(serializers.ModelSerializer):
    """
    Serializa os dados necessários para listagem de histórico de preços.
    """

    tipo_combustivel = serializers.CharField(source='tipo_combustivel.nome', read_only=True)
    autor = serializers.SerializerMethodField()

    class Meta:
        model = AtualizacaoPreco
        fields = ['id', 'tipo_combustivel', 'preco', 'data_hora', 'autor']

    def get_autor(self, obj):
        return obj.usuario.username if obj.usuario else "Anônimo"


class ReacaoSerializer(serializers.ModelSerializer):
    """
    Serializa as reações vinculadas a uma atualização de preço.
    """

    class Meta:
        model = Reacao
        fields = ['id', 'atualizacao', 'usuario', 'tipo']
        read_only_fields = ['usuario']