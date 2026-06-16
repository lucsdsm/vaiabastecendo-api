import requests
import time
from django.core.management.base import BaseCommand
from api.models import Posto
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
import environ
import re

env = environ.Env()

def identificar_bandeira(nome_posto):
    """
    Analisa o nome do posto e retorna a bandeira ou rede regional correspondente.
    """
    nome = str(nome_posto.lower())

    # Dicionário de mapeamento: 'Nome da Bandeira': r'Regra de Captura'
    regras = {
        'Petrobras': r'\b(petrobras|br)\b',
        'Shell': r'\bshell\b',
        'Ipiranga': r'\b(ipiranga|ampm)\b',
        'Ale': r'\bale\b',
        'Texaco': r'\btexaco\b',
        'Pinheiro Borges': r'\bpinheiro borges\b',
        'Cirne': r'\bcirne\b',
        'Lemon': r'\blemon\b',
        'Estrela': r'\bestrela\b',
        'Posto Macaco': r'\bmacaco\b',
        'Setta': r'\bsetta\b',
    }

    for bandeira, padrao in regras.items():
        if re.search(padrao, nome):
            return bandeira
            
    return 'Bandeira Branca'

class Command(BaseCommand):
    help = 'Busca postos varrendo regiões específicas via Google Places'

    def handle(self, *args, **options):
        api_key = env('PLACES_API_KEY')
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        
        # Estratégia de grade: Varremos por bairros para burlar o limite de 60 resultados do Google
        regioes = [
            # 'Centro, Natal, RN',
            # 'Alecrim, Natal, RN',
            # 'Lagoa Nova, Natal, RN',
            # 'Ponta Negra, Natal, RN',
            # 'Capim Macio, Natal, RN',
            # 'Tirol, Natal, RN',
            # 'Igapó, Natal, RN',
            # 'Nova Parnamirim, Parnamirim, RN',
            # 'Centro, Parnamirim, RN'
            # 'Nova Esperança, Parnamirim, RN',
            'São José do Mipibu, RN',
        ]

        total_geral_adicionado = 0

        for regiao in regioes:
            self.stdout.write(self.style.WARNING(f'\n--- Iniciando busca em: {regiao} ---'))
            
            params = {
                'query': f'postos de combustível em {regiao}',
                'key': api_key,
                'language': 'pt-BR'
            }

            tentativas_invalidas = 0

            while True:
                response = requests.get(url, params=params).json()
                status = response.get('status')
                
                if status == 'INVALID_REQUEST':
                    tentativas_invalidas += 1
                    if tentativas_invalidas > 3:
                        self.stdout.write(self.style.ERROR("Falha crítica no token. Pulando para a próxima região."))
                        break
                    
                    self.stdout.write("Token ainda imaturo. Aguardando mais 5 segundos...")
                    time.sleep(5)
                    continue
                
                tentativas_invalidas = 0

                if status not in ['OK', 'ZERO_RESULTS']:
                    self.stdout.write(self.style.ERROR(f"Erro na API: {status}"))
                    break

                results = response.get('results', [])
                adicionados_nesta_pagina = 0

                for place in results:
                    lat = place['geometry']['location']['lat']
                    lng = place['geometry']['location']['lng']
                    ponto_espacial = Point(float(lng), float(lat), srid=4326)

                    # Verificar se já existe um posto a menos de 30 metros para evitar duplicatas
                    posto_existente = Posto.objects.filter(
                        localizacao__distance_lte=(ponto_espacial, D(m=30))
                    ).first()

                    if posto_existente:
                        # Se já existe um posto colado nesse, apenas ignora o novo
                        continue

                    posto, created = Posto.objects.update_or_create(
                        localizacao=ponto_espacial,
                        defaults={
                            'place_id': place.get('place_id', ''),
                            'nome': place['name'],
                            'endereco': place.get('formatted_address', ''),
                            'bandeira': identificar_bandeira(place['name'])
                        }
                    )
                    
                    if created:
                        adicionados_nesta_pagina += 1
                        total_geral_adicionado += 1
                        self.stdout.write(f" + {posto.nome} cadastrado.")

                next_page_token = response.get('next_page_token')
                if not next_page_token:
                    break # Acabaram as páginas desta região
                
                self.stdout.write("Preparando próxima página...")
                # O SEGREDO: 5 segundos é o tempo mínimo seguro para não queimar o token
                time.sleep(5) 
                params = {'pagetoken': next_page_token, 'key': api_key}

        self.stdout.write(self.style.SUCCESS(f'\nFim da varredura! {total_geral_adicionado} novos postos cadastrados no total.'))