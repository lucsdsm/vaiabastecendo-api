import re
import time
import requests
import environ

from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D

from api.models import Station


env = environ.Env()


def identificar_bandeira(nome_posto):
    """
    Analisa o nome do posto e retorna a bandeira ou rede regional correspondente.
    """
    nome = str(nome_posto).lower()

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


def place_score(place):
    """
    Score do resultado vindo da Places API.
    Prioriza volume de avaliações e depois nota.
    """
    user_ratings_total = place.get('user_ratings_total') or 0
    rating = place.get('rating') or 0
    return (user_ratings_total, rating)


def station_score(station):
    """
    Score do posto salvo no banco.
    """
    user_ratings_total = getattr(station, 'user_ratings_total', None) or 0
    rating = station.rating or 0
    return (user_ratings_total, rating)


def should_replace_station(existing_station, incoming_place):
    """
    Decide se o posto novo deve substituir o existente.
    """
    return place_score(incoming_place) > station_score(existing_station)


class Command(BaseCommand):
    help = 'Busca postos varrendo regiões específicas via Google Places'

    def handle(self, *args, **options):
        api_key = env('PLACES_API_KEY')
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"

        regioes = [
            'Emaús, Parnamirim, RN',
        ]

        total_geral_adicionado = 0
        total_geral_atualizado = 0
        total_geral_ignorados = 0
        total_geral_duplicados_removidos = 0

        for regiao in regioes:
            self.stdout.write(self.style.WARNING(f'\n--- Iniciando busca em: {regiao} ---'))

            params = {
                'query': f'postos de combustível em {regiao}',
                'key': api_key,
                'language': 'pt-BR',
            }

            tentativas_invalidas = 0

            while True:
                response = requests.get(url, params=params, timeout=30).json()
                status = response.get('status')

                if status == 'INVALID_REQUEST':
                    tentativas_invalidas += 1
                    if tentativas_invalidas > 5:
                        self.stdout.write(
                            self.style.ERROR('Falha crítica no token. Pulando para a próxima região.')
                        )
                        break

                    self.stdout.write('Token ainda imaturo. Aguardando mais 2 segundos...')
                    time.sleep(2)
                    continue

                tentativas_invalidas = 0

                if status not in ['OK', 'ZERO_RESULTS']:
                    self.stdout.write(self.style.ERROR(f"Erro na API: {status}"))
                    break

                results = response.get('results', [])

                for place in results:
                    geometry = place.get('geometry', {}).get('location', {})
                    lat = geometry.get('lat')
                    lng = geometry.get('lng')

                    if lat is None or lng is None:
                        self.stdout.write(
                            self.style.WARNING(f" - Resultado ignorado sem coordenadas válidas: {place.get('name', 'Sem nome')}")
                        )
                        total_geral_ignorados += 1
                        continue

                    ponto_espacial = Point(float(lng), float(lat), srid=4326)
                    place_id = place.get('place_id')

                    defaults = {
                        'place_id': place_id or '',
                        'name': place.get('name', 'Posto sem nome'),
                        'address': place.get('formatted_address', ''),
                        'brand': identificar_bandeira(place.get('name', '')),
                        'rating': place.get('rating'),
                        'user_ratings_total': place.get('user_ratings_total'),
                        'location': ponto_espacial,
                    }

                    # 1) Prioridade máxima: se já existe pelo mesmo place_id, atualiza esse registro.
                    if place_id:
                        posto_por_place_id = Station.objects.filter(place_id=place_id).first()
                        if posto_por_place_id:
                            for field, value in defaults.items():
                                setattr(posto_por_place_id, field, value)
                            posto_por_place_id.save()

                            total_geral_atualizado += 1
                            self.stdout.write(f" ~ Atualizado por place_id: {posto_por_place_id.name}")
                            continue

                    # 2) Se não encontrou por place_id, procura duplicados por proximidade.
                    postos_proximos = list(
                        Station.objects.filter(
                            location__distance_lte=(ponto_espacial, D(m=30))
                        )
                    )

                    if not postos_proximos:
                        posto = Station.objects.create(**defaults)
                        total_geral_adicionado += 1
                        self.stdout.write(f" + {posto.name} cadastrado.")
                        continue

                    # 3) Se houver mais de um posto próximo, mantém o melhor já salvo.
                    melhor_existente = max(postos_proximos, key=station_score)

                    # 4) Decide se o novo resultado é melhor que o melhor existente.
                    if should_replace_station(melhor_existente, place):
                        for field, value in defaults.items():
                            setattr(melhor_existente, field, value)
                        melhor_existente.save()

                        total_geral_atualizado += 1
                        self.stdout.write(
                            f" ~ Posto próximo substituído por melhor avaliação: {melhor_existente.name}"
                        )
                    else:
                        total_geral_ignorados += 1
                        self.stdout.write(
                            f" - Ignorado '{place.get('name', 'Sem nome')}' pois já existe posto melhor avaliado nas proximidades."
                        )

                    # 5) Limpeza: remove duplicados antigos no mesmo agrupamento, mantendo só o melhor_existente.
                    duplicados_para_remover = [
                        posto for posto in postos_proximos if posto.id != melhor_existente.id
                    ]

                    for duplicado in duplicados_para_remover:
                        duplicado.delete()
                        total_geral_duplicados_removidos += 1
                        self.stdout.write(f" x Duplicado removido: {duplicado.name}")

                next_page_token = response.get('next_page_token')
                if not next_page_token:
                    break

                self.stdout.write('Preparando próxima página...')
                time.sleep(2)
                params = {
                    'pagetoken': next_page_token,
                    'key': api_key,
                }

        self.stdout.write(
            self.style.SUCCESS(
                '\nFim da varredura! '
                f'{total_geral_adicionado} novos postos cadastrados, '
                f'{total_geral_atualizado} atualizados, '
                f'{total_geral_ignorados} ignorados e '
                f'{total_geral_duplicados_removidos} duplicados removidos.'
            )
        )