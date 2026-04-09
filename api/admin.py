from django.contrib.gis import admin
from .models import Posto, TipoCombustivel, AtualizacaoPreco, Reacao

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

admin.site.register(TipoCombustivel)
admin.site.register(AtualizacaoPreco)
admin.site.register(Reacao)