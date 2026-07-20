from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Posto, TipoCombustivel, AtualizacaoPreco, Reacao
from decimal import Decimal
from django.db.models import OutRef, Subquery, Prefetch

User = get_user_model()

class PostoSerializer(serializers.ModelSerializer):
    """Serializa posto com preços atuais, autor da última atualização e reações."""

    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    distancia_metros = serializers.SerializerMethodField()
    precos_atuais = serializers.SerializerMethodField()
    autor_ultima_atualizacao = serializers.SerializerMethodField()

    class Meta:
        model = Posto
        fields = ['id', 'nome', 'endereco', 'bandeira', 'avaliacao', 'latitude', 'longitude', 'distancia_metros', 'precos_atuais', 
        'autor_ultima_atualizacao']

    def get_latitude(self, obj):
        """Retorna latitude a partir do ponto geográfico do posto."""
        return obj.localizacao.y if obj.localizacao else None

    def get_longitude(self, obj):
        """Retorna longitude a partir do ponto geográfico do posto."""
        return obj.localizacao.x if obj.localizacao else None

    def get_distancia_metros(self, obj):
        """Usa distância já anotada na queryset quando disponível."""
        if hasattr(obj, 'distancia_calculada') and obj.distancia_calculada:
            return obj.distancia_calculada.m
        return None

    def get_autor_ultima_atualizacao(self, obj):
        """Expõe autor da atualização ativa mais recente para o posto, incluindo status de verificado."""
        ultima_atualizacao = obj.atualizacoes.filter(status='ativo').order_by('-data_hora').first()
        
        if ultima_atualizacao and ultima_atualizacao.usuario:
            usuario = ultima_atualizacao.usuario
            return {
                "nome": usuario.username,
                "verificado": usuario.pontos >= 100 
            }
            
        return {
            "nome": "Anônimo",
            "verificado": False
        }

    def get_precos_atuais(self, obj):
        """Retorna um snapshot com o último preço ativo de cada tipo, incluindo suas reações individuais."""
        # Pega o usuário logado a partir do contexto do request (injetado pelo ViewSet)
        request = self.context.get('request')
        usuario_logado = (
            request.user 
            if request and hasattr(request, 'user') and request.user.is_authenticated 
            else None
        )

        # Subquery para pegar o ID da última atualização ativa por tipo
        ultima_por_tipo = AtualizacaoPreco.objects.filter(
            posto=obj,
            tipo_combustivel=OuterRef('tipo_combustivel'),
            status='ativo'
        ).order_by('-data_hora').values('id')[:1]

        # Busca todas as últimas atualizações do posto de uma vez
        ultimas_atualizacoes = (
            AtualizacaoPreco.objects
            .filter(posto=obj, status='ativo', id__in=Subquery(
                AtualizacaoPreco.objects
                .filter(posto=obj, status='ativo')
                .order_by('tipo_combustivel', '-data_hora')
                .distinct('tipo_combustivel')
                .values('id')
            ))
            .select_related('tipo_combustivel')
            .prefetch_related('reacoes')
        )

        lista_precos = []
        for atualizacao in ultimas_atualizacoes:
            total_likes = sum(1 for r in atualizacao.reacoes.all() if r.tipo == 'like')
            usuario_curtiu = (
                any(r.usuario_id == usuario_logado.pk for r in atualizacao.reacoes.all())
                if usuario_logado else False
            )

            lista_precos.append({
                'id': atualizacao.id,
                'tipo': atualizacao.tipo_combustivel.nome,
                'cor': atualizacao.tipo_combustivel.cor,
                'preco': float(atualizacao.preco),
                'data': atualizacao.data_hora,
                'likes': total_likes,
                'is_liked': usuario_curtiu,
            })

        return lista_precos

class TipoCombustivelSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoCombustivel
        fields = ['id', 'nome', 'cor']

class AtualizacaoPrecoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AtualizacaoPreco
        fields = ['id', 'posto', 'tipo_combustivel', 'preco', 'usuario', 'data_hora', 'status']
        read_only_fields = ['usuario', 'data_hora', 'status']

    def validate(self, data):
        """Valida integridade do preço e existência de posto e tipo de combustível."""
        posto = data.get('posto')
        tipo_combustivel = data.get('tipo_combustivel')
        novo_preco = data.get('preco')

        ultimo_preco_obj = AtualizacaoPreco.objects.filter(
            posto=posto,
            tipo_combustivel=tipo_combustivel,
            status='ativo'
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
    """Serializa os dados básicos para a tabela de histórico de preços."""

    tipo_combustivel = serializers.CharField(source='tipo_combustivel.nome', read_only=True)
    autor = serializers.CharField(source='usuario.username', default='Anônimo', read_only=True)

    class Meta:
        model = AtualizacaoPreco
        fields = ['id', 'tipo_combustivel', 'preco', 'data_hora', 'autor']

    def get_autor(self, obj):
        if obj.usuario:
            return obj.usuario.username
        return "Anônimo"

class ReacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reacao
        fields = ['id', 'atualizacao', 'usuario', 'tipo']
        read_only_fields = ['usuario'] 