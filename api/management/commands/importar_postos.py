import requests
import time
from django.core.management.base import BaseCommand
from api.models import Posto
from django.contrib.gis.geos import Point
import environ

env = environ.Env()


class Command(BaseCommand):
    help = 'Busca postos em uma cidade específica via Google Places'

    def add_arguments(self, parser):
        parser.add_argument('--cidade', type=str, help='Cidade e Estado para busca')

    def handle(self, *args, **options):
        """Importa postos via Google Places respeitando paginação por token."""
        cidade = options.get('cidade') or 'Natal, RN'
        api_key = env('PLACES_API_KEY')
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        
        params = {
            'query': f'postos de combustível em {cidade}',
            'key': api_key,
            'language': 'pt-BR'
        }

        self.stdout.write(self.style.SUCCESS(f'Iniciando busca em: {cidade}...'))

        total_adicionado = 0
        while True:
            response = requests.get(url, params=params).json()
            
            if response.get('status') == 'INVALID_REQUEST':
                # O token de próxima página demora alguns segundos para ficar válido.
                self.stdout.write("Aguardando token do Google...")
                time.sleep(2)
                continue

            if response.get('status') not in ['OK', 'ZERO_RESULTS']:
                self.stdout.write(self.style.ERROR(f"Erro: {response.get('status')}"))
                break

            results = response.get('results', [])

            for place in results:
                lat = place['geometry']['location']['lat']
                lng = place['geometry']['location']['lng']
                
                # Em geometrias WGS84 o eixo X é longitude e o Y é latitude.
                ponto_espacial = Point(float(lng), float(lat), srid=4326)

                posto, created = Posto.objects.update_or_create(
                    localizacao=ponto_espacial,
                    defaults={
                        'nome': place['name'],
                        'endereco': place.get('formatted_address', '')
                    }
                )
                
                if created:
                    total_adicionado += 1
                    self.stdout.write(f"{posto.nome} cadastrado.")

            next_page_token = response.get('next_page_token')
            if not next_page_token:
                break
            
            self.stdout.write("Buscando próxima página...")
            time.sleep(2)
            params = {'pagetoken': next_page_token, 'key': api_key}

        self.stdout.write(self.style.SUCCESS(f'Fim. {total_adicionado} novos postos.'))