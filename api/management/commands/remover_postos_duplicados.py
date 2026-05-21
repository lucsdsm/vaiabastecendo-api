from django.core.management.base import BaseCommand
from api.models import Posto
from django.contrib.gis.measure import D

class Command(BaseCommand):
    help = 'Remove postos duplicados num raio de 30 metros'

    def handle(self, *args, **options):
        postos = Posto.objects.all().order_by('id')
        total_removidos = 0
        ids_para_ignorar = set() # Guarda IDs de postos que já foram processados/apagados

        for posto in postos:
            if posto.id in ids_para_ignorar:
                continue

            # Busca vizinhos num raio de 30 metros, excluindo ele mesmo
            duplicatas = Posto.objects.filter(
                localizacao__distance_lte=(posto.localizacao, D(m=30))
            ).exclude(id=posto.id)

            if duplicatas.exists():
                self.stdout.write(self.style.WARNING(f"Duplicatas encontradas para '{posto.nome}' (ID {posto.id})"))
                
                for dup in duplicatas:
                    self.stdout.write(f" - Removendo: '{dup.nome}' (ID {dup.id})")
                    ids_para_ignorar.add(dup.id)
                    dup.delete()
                    total_removidos += 1

        self.stdout.write(self.style.SUCCESS(f'\nFaxina concluída! {total_removidos} postos duplicados foram removidos.'))