from django.contrib.gis import admin
from django.contrib.auth.models import AbstractUser
from .models import Usuario, Posto, TipoCombustivel, AtualizacaoPreco, Reacao
from django.db import models
from django.contrib.auth.admin import UserAdmin

@admin.register(Posto)
class PostoAdmin(admin.GISModelAdmin): 
    list_display = ('nome', 'endereco')
    search_fields = ('nome', 'endereco')

    gis_widget_kwargs = {
        'attrs': {
            'default_lon': -35.2094,
            'default_lat': -5.7945,
            'default_zoom': 12,
        }
    }

class CustomUserAdmin(UserAdmin):
    # Adiciona o campo pontos na tela de edição do usuário
    fieldsets = UserAdmin.fieldsets + (
        ('Gamificação', {'fields': ('pontos',)}),
    )
    # Mostra os pontos na lista geral de usuários
    list_display = UserAdmin.list_display + ('pontos',)

admin.site.register(TipoCombustivel)
admin.site.register(Usuario)
admin.site.register(AtualizacaoPreco)
admin.site.register(Reacao)