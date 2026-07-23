from django.core.management.base import BaseCommand
from api.models import Station
from api.management.commands.importar_postos import identificar_bandeira


class Command(BaseCommand):
    help = 'Reavalia o nome de todos os postos e atualiza a bandeira no banco'

    def handle(self, *args, **options):
        postos = Station.objects.all()
        total_atualizados = 0

        self.stdout.write("Iniciando reclassificação de bandeiras...")

        for station in postos:
            new_brand = identificar_bandeira(station.name)
            
            # Só faz o update no banco de dados se a bandeira realmente mudou
            if station.brand != new_brand:
                self.stdout.write(f"Atualizando: {station.name} ({station.brand} -> {new_brand})")
                station.brand = new_brand
                station.save(update_fields=['brand'])
                total_atualizados += 1

        self.stdout.write(self.style.SUCCESS(f'\nConcluído! {total_atualizados} postos tiveram sua bandeira alterada.'))