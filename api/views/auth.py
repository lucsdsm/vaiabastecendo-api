from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from dj_rest_auth.registration.views import SocialLoginView

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.providers.oauth2.client import OAuth2Client


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

        return Response({
            "primeiro_nome": user.first_name,
            "ultimo_nome": user.last_name,
            "email": user.email,
            "foto": foto_url
        })