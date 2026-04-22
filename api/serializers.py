from rest_framework import serializers
from .models import Posto, TipoCombustivel, AtualizacaoPreco, Reacao

class PostoSerializer(serializers.ModelSerializer):
    # Campos adicionais para latitude, longitude e distância em metros
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    distancia_metros = serializers.SerializerMethodField()
    precos_atuais = serializers.SerializerMethodField()
    autor_ultima_atualizacao = serializers.SerializerMethodField()
    likes = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Posto
        fields = ['id', 'nome', 'endereco', 'latitude', 'longitude', 'distancia_metros', 'precos_atuais', 
        'autor_ultima_atualizacao', 'likes', 'is_liked']

    # Extrai o eixo Y do campo 'localizacao' para a latitude
    def get_latitude(self, obj):
        return obj.localizacao.y if obj.localizacao else None

    # Extrai o eixo X do campo 'localizacao' para a longitude
    def get_longitude(self, obj):
        return obj.localizacao.x if obj.localizacao else None

    # Calcula a distância em metros entre o posto e um ponto de referência (ex: usuário)
    def get_distancia_metros(self, obj):
        if hasattr(obj, 'distancia_calculada') and obj.distancia_calculada:
            return obj.distancia_calculada.m  # Retorna os metros
        return None

    # Retorna o nome do autor da última atualização de preço para o posto
    def get_autor_ultima_atualizacao(self, obj):
        ultima_atualizacao = obj.atualizacoes.filter(status='ativo').order_by('-data_hora').first()
        if ultima_atualizacao and ultima_atualizacao.usuario:
            return ultima_atualizacao.usuario.username
        return "Anônimo"

    # Retorna os preços mais recentes de cada tipo de combustível para o posto
    def get_precos_atuais(self, obj):
        tipos = TipoCombustivel.objects.all()
        lista_precos = []
        for tipo in tipos:
            ultima_atualizacao = obj.atualizacoes.filter(tipo_combustivel=tipo, status='ativo').order_by('-data_hora').first()
            if ultima_atualizacao:
                lista_precos.append({
                    'id': ultima_atualizacao.id,
                    'tipo': tipo.nome,
                    'cor': tipo.cor,
                    'preco': float(ultima_atualizacao.preco),
                    'data': ultima_atualizacao.data_hora,
                })
        return lista_precos

    def get_likes(self, obj):
        return Reacao.objects.filter(atualizacao__posto=obj, tipo='like').count()
    
    def get_is_liked(self, obj):
        # 1. Tenta pegar o request de forma segura
        request = self.context.get('request')
        
        # 2. Verifica se o request existe, se tem um usuário atrelado, e se ele está logado
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            # 3. Importante: Garanta que o modelo Reacao foi importado lá no topo do arquivo!
            from .models import Reacao 
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

class ReacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reacao
        fields = ['id', 'atualizacao', 'usuario', 'tipo']
        read_only_fields = ['usuario'] 