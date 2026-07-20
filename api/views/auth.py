from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Reaction


class GoogleLogin(SocialLoginView):
    """
    Endpoint de autenticação social com Google para o cliente mobile.
    """

    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client
    callback_url = 'https://auth.expo.io'


class UserProfileView(APIView):
    """
    Retorna os dados públicos e estatísticos do usuário autenticado.
    """

    permission_classes = [IsAuthenticated]

    def _get_google_photo_url(self, user):
        """
        Recupera a URL da foto do usuário a partir da conta social do Google,
        quando disponível.
        """
        social_account = SocialAccount.objects.filter(
            user=user,
            provider='google',
        ).first()

        if not social_account:
            return None

        return social_account.extra_data.get('picture')

    def get(self, request):
        """
        Retorna o payload de perfil do usuário autenticado com contrato em inglês.
        """
        user = request.user
        photo_url = self._get_google_photo_url(user)

        likes_given = Reaction.objects.filter(user=user, reaction_type='like').count()

        return Response({
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "photo": photo_url,
            "likes_received": user.points,
            "likes_given": likes_given,
            "points": user.points,
            "verified": user.verified,
        })