from django.contrib import admin
from .models import Posto, TipoCombustivel, AtualizacaoPreco, Reacao

# Register your models here.

@admin.register(Posto)
class PostoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'latitude', 'longitude', 'endereco')
    search_fields = ('nome', 'endereco')

admin.site.register(TipoCombustivel)
admin.site.register(AtualizacaoPreco)
admin.site.register(Reacao)