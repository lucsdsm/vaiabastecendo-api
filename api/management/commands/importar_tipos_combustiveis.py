from django.core.management.base import BaseCommand
from api.models import FuelType

class Command(BaseCommand):
    help = 'Importa tipos de combustíveis para o banco de dados'

    def handle(self, *args, **options):
        """Sincroniza catálogo fixo de combustíveis e cores padrão do app."""
        combustiveis = [
            {'name': 'Gasolina Comum', 'color': '#ff8000', 'order': 1},  
            {'name': 'Gasolina Aditivada', 'color': '#0000FF', 'order': 2},
            {'name': 'Gasolina Premium', 'color': '#ffdd00', 'order': 5},
            {'name': 'Etanol Comum', 'color': '#79964d', 'order': 3},
            {'name': 'Etanol Aditivado', 'color': '#008000', 'order': 6},
            {'name': 'Diesel Comum S10', 'color': '#C0C0C0', 'order': 7},
            {'name': 'Diesel Aditivado S10', 'color': '#808080', 'order': 8},
            {'name': 'Diesel Comum S500', 'color': '#FF0000', 'order': 9},
            {'name': 'Diesel Aditivado S500', 'color': '#000000', 'order': 10},
            {'name': 'GNV', 'color': '#FFFF00', 'order': 4},       
        ]

        for combustivel in combustiveis:
            FuelType.objects.update_or_create(
                name=combustivel['name'],
                defaults={'color': combustivel['color'], 'order': combustivel['order']}
            )

        self.stdout.write(self.style.SUCCESS('Tipos de combustíveis importados com sucesso!'))