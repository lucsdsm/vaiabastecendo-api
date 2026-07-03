from django.core.management.base import BaseCommand
from api.models import TipoCombustivel

class Command(BaseCommand):
    help = 'Importa tipos de combustíveis para o banco de dados'

    def handle(self, *args, **options):
        """Sincroniza catálogo fixo de combustíveis e cores padrão do app."""
        combustiveis = [
            {'nome': 'Gasolina Comum', 'cor': '#ff8000'},  
            {'nome': 'Gasolina Aditivada', 'cor': '#0000FF'},
            {'nome': 'Gasolina Premium', 'cor': '#ffdd00'},
            {'nome': 'Etanol Comum', 'cor': '#00FF00'},
            {'nome': 'Etanol Aditivado', 'cor': '#008000'},
            {'nome': 'Diesel Comum S10', 'cor': '#C0C0C0'},
            {'nome': 'Diesel Aditivado S10', 'cor': '#808080'},
            {'nome': 'Diesel Comum S500', 'cor': '#FF0000'},
            {'nome': 'Diesel Aditivado S500', 'cor': '#000000'},   
            {'nome': 'GNV', 'cor': '#FFFF00'},       
        ]

        for combustivel in combustiveis:
            TipoCombustivel.objects.update_or_create(
                nome=combustivel['nome'],
                defaults={'cor': combustivel['cor']}
            )

        self.stdout.write(self.style.SUCCESS('Tipos de combustíveis importados com sucesso!'))