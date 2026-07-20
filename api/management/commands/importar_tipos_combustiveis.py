from django.core.management.base import BaseCommand
from api.models import FuelType

class Command(BaseCommand):
    help = 'Importa tipos de combustíveis para o banco de dados'

    def handle(self, *args, **options):
        """Sincroniza catálogo fixo de combustíveis e cores padrão do app."""
        combustiveis = [
            {'name': 'Gasolina Comum', 'color': '#ff8000'},  
            {'name': 'Gasolina Aditivada', 'color': '#0000FF'},
            {'name': 'Gasolina Premium', 'color': '#ffdd00'},
            {'name': 'Etanol Comum', 'color': '#79964d'},
            {'name': 'Etanol Aditivado', 'color': '#008000'},
            {'name': 'Diesel Comum S10', 'color': '#C0C0C0'},
            {'name': 'Diesel Aditivado S10', 'color': '#808080'},
            {'name': 'Diesel Comum S500', 'color': '#FF0000'},
            {'name': 'Diesel Aditivado S500', 'color': '#000000'},   
            {'name': 'GNV', 'color': '#FFFF00'},       
        ]

        for combustivel in combustiveis:
            FuelType.objects.update_or_create(
                name=combustivel['name'],
                defaults={'color': combustivel['color']}
            )

        self.stdout.write(self.style.SUCCESS('Tipos de combustíveis importados com sucesso!'))