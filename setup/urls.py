from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from api.views.postos import PostoViewSet
from api.views.combustiveis import TipoCombustivelViewSet
from api.views.atualizacoes import AtualizacaoPrecoViewSet
from api.views.auth import GoogleLogin
from api.views.auth import UserProfileView

router = DefaultRouter()
router.register(r'postos', PostoViewSet, basename='posto')
router.register(r'tipos-combustivel', TipoCombustivelViewSet, basename='tipocombustivel')
router.register(r'atualizar-preco', AtualizacaoPrecoViewSet, basename='atualizacaopreco')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/auth/google/', GoogleLogin.as_view(), name='google_login'),
    path('api/auth/me/', UserProfileView.as_view(), name='user_profile'),
]
