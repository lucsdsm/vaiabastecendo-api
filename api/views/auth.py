from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from dj_rest_auth.registration.views import SocialLoginView

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.providers.oauth2.client import OAuth2Client

from api.models import Reacao

class GoogleLogin(SocialLoginView):
    """Endpoint de login social com Google para o app cliente."""

    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client
    callback_url = 'https://auth.expo.io'


class UserProfileView(APIView):
    """Retorna dados básicos do usuário autenticado e foto social quando existir."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Resolve foto do provedor Google e devolve payload de perfil."""
        user = request.user
        foto_url = None
        
        # O app exibe avatar remoto; sem conta social, a foto permanece nula.
        social_account = SocialAccount.objects.filter(user=user, provider='google').first()
        if social_account:
            foto_url = social_account.extra_data.get('picture')

        # Conta quantos likes as atualizacoes deste usuario receberam
        likes_recebidos = Reacao.objects.filter(atualizacao__usuario=user, tipo='like').count()

        # Conta quantos likes este usuario distribuiu no app
        likes_deferidos = Reacao.objects.filter(usuario=user, tipo='like').count()

        return Response({
            "id": user.id,
            "username": user.username,
            "primeiro_nome": user.first_name,
            "ultimo_nome": user.last_name,
            "email": user.email,
            "foto": foto_url,
            "likes_recebidos": likes_recebidos,
            "likes_deferidos": likes_deferidos,
            "verificado": user.verificado
        })