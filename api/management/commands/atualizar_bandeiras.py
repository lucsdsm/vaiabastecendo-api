from django.core.management.base import BaseCommand
from api.models import Posto
from api.management.commands.importar_postos import identificar_bandeira

"""
"""

class Command(BaseCommand):
    help = 'Reavalia o nome de todos os postos e atualiza a bandeira no banco'

    def handle(self, *args, **options):
        postos = Posto.objects.all()
        total_atualizados = 0

        self.stdout.write("Iniciando reclassificação de bandeiras...")

        for posto in postos:
            nova_bandeira = identificar_bandeira(posto.nome)
            
            # Só faz o update no banco de dados se a bandeira realmente mudou
            if posto.bandeira != nova_bandeira:
                self.stdout.write(f"Atualizando: {posto.nome} ({posto.bandeira} -> {nova_bandeira})")
                posto.bandeira = nova_bandeira
                posto.save(update_fields=['bandeira'])
                total_atualizados += 1

        self.stdout.write(self.style.SUCCESS(f'\nConcluído! {total_atualizados} postos tiveram sua bandeira alterada.'))