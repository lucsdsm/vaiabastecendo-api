from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views.postos import PostoViewSet
from .views.combustiveis import TipoCombustivelViewSet
from .views.atualizacoes import AtualizacaoPrecoViewSet
from .views.auth import GoogleLogin, UserProfileView

router = DefaultRouter()
router.register(r'postos', PostoViewSet, basename='posto')
router.register(r'tipos-combustivel', TipoCombustivelViewSet, basename='tipocombustivel')
router.register(r'atualizar-preco', AtualizacaoPrecoViewSet, basename='atualizacaopreco')

urlpatterns = [
    path('', include(router.urls)),
    
    path('auth/google/', GoogleLogin.as_view(), name='google_login'),
    path('auth/me/', UserProfileView.as_view(), name='user_profile'),
]