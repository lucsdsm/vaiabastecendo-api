import csv

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.gis import admin
from django.http import HttpResponse

from .models import FuelType, PriceUpdate, Reaction, Station, User

admin.site.site_header = "Vai Abastecendo"
admin.site.site_title = "Vai Abastecendo"
admin.site.index_title = "Painel administrativo"

@admin.action(description='Exportar postos selecionados para CSV')
def export_selected_stations_to_csv(modeladmin, request, queryset):
    """
    Exporta os postos selecionados no admin para um arquivo CSV.
    """
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="stations.csv"'

    writer = csv.writer(response)
    writer.writerow(['id', 'name', 'city', 'neighborhood', 'address', 'brand', 'rating', 'created_at', 'updated_at'])

    for station in queryset:
        writer.writerow([station.id, station.name, station.city, station.neighborhood, station.address, station.brand, station.rating, station.created_at, station.updated_at])

    return response


@admin.register(Station)
class StationAdmin(admin.GISModelAdmin):
    list_display = ('place_id', 'name', 'city', 'neighborhood', 'address', 'brand', 'rating', 'created_at', 'updated_at')
    search_fields = ('place_id', 'name', 'city', 'neighborhood', 'address', 'brand', 'created_at', 'updated_at')
    actions = [export_selected_stations_to_csv]

    gis_widget_kwargs = {
        'attrs': {
            'default_lon': -35.2094,
            'default_lat': -5.7945,
            'default_zoom': 12,
        }
    }


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Customiza a administração do usuário adicionando o campo de pontuação.
    """

    readonly_fields = ('username', 'email', 'likes_received')

admin.site.register(FuelType)
admin.site.register(PriceUpdate)
admin.site.register(Reaction)