import csv
from django.http import HttpResponse

from django.contrib.gis import admin
from django.contrib.auth.models import AbstractUser
from .models import Usuario, Posto, TipoCombustivel, AtualizacaoPreco, Reacao
from django.db import models
from django.contrib.auth.admin import UserAdmin

@admin.action(description='Exportar postos selecionados para CSV')
def exportar_para_csv(modeladmin, request, queryset):
    # Cria a resposta HTTP com o tipo de arquivo correto
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="postos_selecionados.csv"'
    
    writer = csv.writer(response)
    # Escreve o cabeçalho
    writer.writerow(['id', 'nome', 'bandeira', 'endereco', 'avaliacao'])
    
    # Escreve os dados dos postos que você marquei na tela
    for posto in queryset:
        writer.writerow([posto.id, posto.nome, posto.bandeira, posto.endereco])
        
    return response

@admin.register(Posto)
class PostoAdmin(admin.GISModelAdmin): 
    list_display = ('place_id', 'nome', 'endereco', 'bandeira', 'avaliacao')
    search_fields = ('place_id', 'nome', 'endereco', 'bandeira')
    actions = [exportar_para_csv]

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