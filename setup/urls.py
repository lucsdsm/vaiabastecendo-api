from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from api.views import PostoViewSet, TipoCombustivelViewSet, AtualizacaoPrecoViewSet

router = DefaultRouter()
router.register(r'postos', PostoViewSet, basename='posto')
router.register(r'tipos-combustivel', TipoCombustivelViewSet, basename='tipocombustivel')
router.register(r'atualizar-preco', AtualizacaoPrecoViewSet, basename='atualizacaopreco')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
]
