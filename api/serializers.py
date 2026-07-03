from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Posto, TipoCombustivel, AtualizacaoPreco, Reacao
from decimal import Decimal

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
        usuario_logado = request.user if request and hasattr(request, 'user') and request.user.is_authenticated else None

        tipos = TipoCombustivel.objects.all()
        lista_precos = []
        
        for tipo in tipos:
            ultima_atualizacao = obj.atualizacoes.filter(tipo_combustivel=tipo, status='ativo').order_by('-data_hora').first()
            
            if ultima_atualizacao:
                # Calcula as reações exclusivamente para essa atualização
                total_likes = Reacao.objects.filter(atualizacao=ultima_atualizacao, tipo='like').count()
                
                # Verifica se o usuário logado curtiu essa atualização
                usuario_curtiu = False
                if usuario_logado:
                    usuario_curtiu = Reacao.objects.filter(atualizacao=ultima_atualizacao, usuario=usuario_logado, tipo='like').exists()

                lista_precos.append({
                    'id': ultima_atualizacao.id,
                    'tipo': tipo.nome,
                    'cor': tipo.cor,
                    'preco': float(ultima_atualizacao.preco),
                    'data': ultima_atualizacao.data_hora,
                    'likes': total_likes,     
                    'is_liked': usuario_curtiu
                })
                
        return lista_precos

    def get_likes(self, obj):
        """Conta reações positivas vinculadas às atualizações do posto."""
        return Reacao.objects.filter(atualizacao__posto=obj, tipo='like').count()
    
    def get_is_liked(self, obj):
        """Indica se o usuário autenticado curtiu alguma atualização do posto."""
        request = self.context.get('request')

        if request and hasattr(request, 'user') and request.user.is_authenticated:
            return Reacao.objects.filter(atualizacao__posto=obj, usuario=request.user, tipo='like').exists()
        
        return False

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

            # 1. Busca se já existe um preço ativo para esse combustível neste posto.
            ultimo_preco_obj = AtualizacaoPreco.objects.filter(
                posto=posto,
                tipo_combustivel=tipo_combustivel,
                status='ativo'
            ).order_by('-data_hora').first()

            # 2. Se existir, define uma tolerância de 30% para evitar atualizações triviais.
            if ultimo_preco_obj:
                preco_atual = ultimo_preco_obj.preco
                limite_superior = preco_atual * 1.3
                limite_inferior = preco_atual * 0.7
                
                if novo_preco > limite_superior or novo_preco < limite_inferior:
                    raise serializers.ValidationError({
                        "preco": f"Valor suspeito. O preço atual é de R$ {preco_atual}"
                    })

            # 3. Se for o primeiro preço do posto, faz uma trava de validação para evitar preços absurdos.
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