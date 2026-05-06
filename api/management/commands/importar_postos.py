import requests
import time
from django.core.management.base import BaseCommand
from api.models import Posto
from django.contrib.gis.geos import Point
import environ
import re

env = environ.Env()

def identificar_bandeira(nome_posto):
    """
    Analisa o nome do posto e retorna a bandeira correspondente.
    Converte tudo para minúsculo para facilitar a busca.
    """
    nome = str(nome_posto.lower())

    if re.search(r'\b(petrobras|br)\b', nome):
        return 'Petrobras'
    
    if re.search(r'\bshell\b', nome):
        return 'Shell'
        
    if re.search(r'\bipiranga\b', nome):
        return 'Ipiranga'
    
    if re.search(r'\bale\b', nome):
        return 'Ale'

    if re.search(r'\btexaco\b', nome):
        return 'Texaco'
    
    return 'Bandeira Branca'  # Se não identificar, assume que é independente

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
        tentativas_invalidas = 0

        while True:
            response = requests.get(url, params=params).json()
            status = response.get('status')
            
            if status == 'INVALID_REQUEST':
                tentativas_invalidas += 1
                if tentativas_invalidas > 3:
                    self.stdout.write(self.style.ERROR("Falha: Token inválido 3 vezes seguidas. Abortando paginação para evitar loop infinito."))
                    break # Sai do loop
                    
                self.stdout.write("Aguardando ativação do token do Google...")
                time.sleep(3) # Dorme um tempo extra
                continue
            
            # Se a resposta deu certo, resetamos a trava de segurança
            tentativas_invalidas = 0

            if response.get('status') not in ['OK', 'ZERO_RESULTS']:
                self.stdout.write(self.style.ERROR(f"Erro: {response.get('status')}"))
                break

            results = response.get('results', [])

            for place in results:
                nome_do_posto = place['name']
                lat = place['geometry']['location']['lat']
                lng = place['geometry']['location']['lng']
                
                # Em geometrias WGS84 o eixo X é longitude e o Y é latitude.
                ponto_espacial = Point(float(lng), float(lat), srid=4326)

                bandeira_detectada = identificar_bandeira(nome_do_posto)

                posto, created = Posto.objects.update_or_create(
                    localizacao=ponto_espacial,
                    defaults={
                        'place_id': place['place_id'],
                        'nome': place['name'],
                        'endereco': place.get('formatted_address', ''),
                        'bandeira': bandeira_detectada
                    }
                )
                
                if created:
                    total_adicionado += 1
                    self.stdout.write(f"{posto.nome} cadastrado.")

            next_page_token = response.get('next_page_token')
            if not next_page_token:
                break
            
            self.stdout.write("Preparando próxima página (delay exigido pelo Google)...")
            time.sleep(2)
            params = {'pagetoken': next_page_token, 'key': api_key}

        self.stdout.write(self.style.SUCCESS(f'Fim. {total_adicionado} novos postos.'))