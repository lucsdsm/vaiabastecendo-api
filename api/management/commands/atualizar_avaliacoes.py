import requests
import environ
import time
from django.core.management.base import BaseCommand
from api.models import Posto

env = environ.Env()

class Command(BaseCommand):
    help = 'Busca a avaliação atualizada de todos os postos baseada no place_id'

    def handle(self, *args, **options):
        api_key = env('PLACES_API_KEY')
        url = "https://maps.googleapis.com/maps/api/place/details/json"
        
        # Ignora postos que por algum motivo não tenham o place_id salvo
        postos = Posto.objects.exclude(place_id__isnull=True).exclude(place_id__exact='')
        total_atualizados = 0

        self.stdout.write("Buscando avaliações no Google Places...")

        for posto in postos:
            params = {
                'place_id': posto.place_id,
                'fields': 'rating,user_ratings_total', # Pede ao Google apenas os campos que quero para economizar banda/custo
                'key': api_key,
                'language': 'pt-BR'
            }

            response = requests.get(url, params=params).json()
            status = response.get('status')

            if status == 'OK':
                result = response.get('result', {})
                novo_rating = result.get('rating')

                if posto.avaliacao != novo_rating:
                    self.stdout.write(f"Atualizando {posto.nome}: {novo_rating} estrelas")
                    posto.avaliacao = novo_rating
                    posto.save(update_fields=['avaliacao'])
                    total_atualizados += 1
            else:
                self.stdout.write(self.style.WARNING(f"Ignorando {posto.nome}: API retornou status {status}"))
            
            # Pausa para não estourar o limite de requisições por segundo da API
            time.sleep(0.5)

        self.stdout.write(self.style.SUCCESS(f'\nConcluído! {total_atualizados} postos tiveram suas avaliações atualizadas.'))