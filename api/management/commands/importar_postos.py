import requests
import time
from django.core.management.base import BaseCommand
from api.models import Posto, TipoCombustivel
import environ

env = environ.Env()

class Command(BaseCommand):
    help = 'Busca postos em uma cidade específica via Google Places'

    def add_arguments(self, parser):
        # Permite passar a cidade como argumento: --cidade "Natal, RN"
        parser.add_argument('--cidade', type=str, help='Cidade e Estado para busca')

    def handle(self, *args, **options):
        cidade = options.get('cidade') or 'Natal, RN'
        api_key = env('PLACES_API_KEY')
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        
        params = {
            'query': f'postos de combustível em {cidade}',
            'key': api_key,
            'language': 'pt-BR'
        }

        self.stdout.write(self.style.SUCCESS(f'🔎 Iniciando busca em: {cidade}...'))

        total_adicionado = 0
        while True:
            response = requests.get(url, params=params).json()
            
            if response.get('status') == 'INVALID_REQUEST':
                self.stdout.write("Token do Google ainda não está pronto. Aguardando mais 2s...")
                time.sleep(2)
                continue 

            if response.get('status') != 'OK' and response.get('status') != 'ZERO_RESULTS':
                self.stdout.write(self.style.ERROR(f"Erro na API: {response.get('status')}"))
                break

            results = response.get('results', [])

            for place in results:
                posto, created = Posto.objects.update_or_create(
                    latitude=place['geometry']['location']['lat'],
                    longitude=place['geometry']['location']['lng'],
                    defaults={
                        'nome': place['name'],
                        'endereco': place.get('formatted_address', '')
                    }
                )
                
                if created:
                    total_adicionado += 1
                    self.stdout.write(f"✅ {posto.nome} cadastrado.")

            next_page_token = response.get('next_page_token')
            if not next_page_token:
                break
            
            self.stdout.write("Aguardando próxima página...")
            time.sleep(2)
            params = {'pagetoken': next_page_token, 'key': api_key}

        self.stdout.write(self.style.SUCCESS(f'🚀 Fim! {total_adicionado} novos postos em {cidade}.'))