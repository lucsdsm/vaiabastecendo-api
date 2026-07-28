"""
Importa postos faltantes com base em uma planilha da ANP e enriquece com Google Places.

Fluxo:
1. Lê uma planilha .xlsx com Latitude/Longitude (arquivo ajustável por argumento).
2. Para cada linha válida, verifica se já existe posto correspondente no banco,
   usando proximidade geográfica e place_id quando disponível.
3. Se o posto não existir, consulta a Places API e cria um novo Station
   com os dados enriquecidos.
4. Se já existir, ignora.

Exemplos:
python manage.py importar_postos_faltantes_anp --planilha natal.xlsx
python manage.py importar_postos_faltantes_anp --planilha natal.xlsx --raio 30
python manage.py importar_postos_faltantes_anp --planilha natal.xlsx --dry-run
python manage.py importar_postos_faltantes_anp --planilha natal.xlsx --sheet 0
"""

import math
import re
from pathlib import Path

import environ
import pandas as pd
import requests
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from api.models import Station

env = environ.Env()

BANDEIRAS = {
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
    'Domingos': r'\bdomingos\b',
}


def identificar_bandeira(nome):
    nome = str(nome or '').lower()
    for bandeira, padrao in BANDEIRAS.items():
        if re.search(padrao, nome):
            return bandeira
    return 'Bandeira Branca'


class Command(BaseCommand):
    help = 'Cria postos faltantes a partir de uma planilha ANP, enriquecendo com Google Places.'

    def add_arguments(self, parser):
        parser.add_argument('--planilha', required=True, help='Nome/caminho da planilha .xlsx da ANP.')
        parser.add_argument('--raio', type=float, default=30.0, help='Raio em metros para considerar posto já existente. Padrão: 30.')
        parser.add_argument('--sheet', default=0, help='Nome ou índice da aba da planilha. Padrão: primeira aba.')
        parser.add_argument('--dry-run', action='store_true', help='Simula sem persistir alterações.')

    def headers(self, api_key):
        return {
            'Content-Type': 'application/json',
            'X-Goog-Api-Key': api_key,
            'X-Goog-FieldMask': ','.join([
                'places.id',
                'places.displayName',
                'places.formattedAddress',
                'places.location',
                'places.rating',
                'places.userRatingCount',
                'places.types',
            ]),
        }

    def resolve_sheet_value(self, raw):
        if isinstance(raw, str) and raw.isdigit():
            return int(raw)
        return raw

    def load_spreadsheet(self, path, sheet):
        df = pd.read_excel(path, sheet_name=self.resolve_sheet_value(sheet))
        df.columns = [str(c).strip() for c in df.columns]

        required = ['Latitude', 'Longitude']
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise CommandError(f'Planilha sem colunas obrigatórias: {missing}')

        return df

    def to_float(self, value):
        if pd.isna(value):
            return None
        if isinstance(value, str):
            value = value.strip().replace(',', '.')
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def is_valid_coordinate(self, lat, lng):
        return lat is not None and lng is not None and -90 <= lat <= 90 and -180 <= lng <= 180

    def haversine_m(self, lat1, lng1, lat2, lng2):
        r = 6371000
        p1 = math.radians(lat1)
        p2 = math.radians(lat2)
        dp = math.radians(lat2 - lat1)
        dl = math.radians(lng2 - lng1)
        a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        return 2 * r * math.asin(math.sqrt(a))

    def build_text_query(self, row):
        parts = []
        for col in ['Razão Social', 'Endereço', 'BAIRRO', 'MUNICÍPIO', 'UF']:
            value = row.get(col)
            if pd.notna(value) and str(value).strip():
                parts.append(str(value).strip())
        return ', '.join(parts) if parts else None

    def search_place(self, url, headers, row, lat, lng):
        text_query = self.build_text_query(row)
        if not text_query:
            return None

        payload = {
            'textQuery': text_query,
            'languageCode': 'pt-BR',
            'regionCode': 'br',
            'pageSize': 5,
            'includedType': 'gas_station',
            'strictTypeFiltering': True,
            'locationBias': {
                'circle': {
                    'center': {'latitude': lat, 'longitude': lng},
                    'radius': 120.0,
                }
            },
        }

        response = requests.post(url, headers=headers, json=payload, timeout=30)
        data = response.json()
        if response.status_code != 200:
            raise CommandError(f'Erro na Places API: HTTP {response.status_code} - {data}')

        places = data.get('places', [])
        if not places:
            return None

        return self.pick_best_place(places, lat, lng)

    def pick_best_place(self, places, lat, lng):
        best = None
        best_key = None
        for raw in places:
            location = raw.get('location') or {}
            plat = location.get('latitude')
            plng = location.get('longitude')
            if plat is None or plng is None:
                continue

            distance = self.haversine_m(lat, lng, plat, plng)
            score = (
                distance,
                -(raw.get('userRatingCount') or 0),
                -float(raw.get('rating') or 0),
            )
            if best is None or score < best_key:
                best = raw
                best_key = score
        return best

    def find_existing_by_location(self, lat, lng, radius_m):
        point = Point(float(lng), float(lat), srid=4326)
        nearby = list(Station.objects.filter(location__distance_lte=(point, D(m=radius_m))))
        if not nearby:
            return None
        nearby.sort(key=lambda s: s.location.distance(point) if s.location else float('inf'))
        return nearby[0]

    def find_existing_by_place_id(self, place_id):
        if not place_id:
            return None
        return Station.objects.filter(place_id=place_id).first()

    def build_defaults(self, row, place, fallback_lat, fallback_lng):
        display_name = (place.get('displayName') or {}).get('text') or str(row.get('Razão Social') or 'Posto sem nome').strip()
        formatted_address = place.get('formattedAddress') or str(row.get('Endereço') or '').strip()
        location = place.get('location') or {}
        lat = location.get('latitude', fallback_lat)
        lng = location.get('longitude', fallback_lng)

        defaults = {
            'place_id': place.get('id') or '',
            'name': display_name,
            'address': formatted_address,
            'brand': identificar_bandeira(display_name),
            'rating': place.get('rating'),
            'user_ratings_total': place.get('userRatingCount'),
            'location': Point(float(lng), float(lat), srid=4326),
        }

        cnpj = row.get('CNPJ')
        if 'cnpj' in [f.name for f in Station._meta.fields] and pd.notna(cnpj):
            defaults['cnpj'] = re.sub(r'\D', '', str(cnpj))

        company_name = row.get('Razão Social')
        if 'company_name' in [f.name for f in Station._meta.fields] and pd.notna(company_name):
            defaults['company_name'] = str(company_name).strip()

        return defaults

    def create_station(self, defaults):
        return Station.objects.create(**defaults)

    def handle_row(self, row, url, headers, radius_m):
        lat = self.to_float(row.get('Latitude'))
        lng = self.to_float(row.get('Longitude'))
        if not self.is_valid_coordinate(lat, lng):
            return 'invalid_coordinate', None, 'Coordenadas inválidas'

        existing = self.find_existing_by_location(lat, lng, radius_m)
        if existing:
            return 'already_exists', existing, 'Já existe posto próximo no banco'

        place = self.search_place(url, headers, row, lat, lng)
        if not place:
            return 'places_not_found', None, 'Places API não encontrou posto correspondente'

        existing_by_place_id = self.find_existing_by_place_id(place.get('id'))
        if existing_by_place_id:
            return 'already_exists', existing_by_place_id, 'Já existe posto com o mesmo place_id'

        defaults = self.build_defaults(row, place, lat, lng)
        station = self.create_station(defaults)
        return 'created', station, 'Posto criado com base na planilha + Places API'

    def run_import(self, planilha, radius_m, dry_run=False, sheet=0):
        api_key = env('PLACES_API_KEY')
        url = 'https://places.googleapis.com/v1/places:searchText'
        headers = self.headers(api_key)

        path = Path(planilha)
        if not path.exists():
            raise CommandError(f'Planilha não encontrada: {planilha}')

        df = self.load_spreadsheet(path, sheet)
        totals = {
            'created': 0,
            'already_exists': 0,
            'places_not_found': 0,
            'invalid_coordinate': 0,
        }

        for _, row in df.iterrows():
            status, station, message = self.handle_row(row, url, headers, radius_m)
            totals[status] += 1

            nome = None
            if station is not None:
                nome = station.name
            elif pd.notna(row.get('Razão Social')):
                nome = str(row.get('Razão Social')).strip()
            else:
                nome = 'Posto sem identificação'

            if status == 'created':
                self.stdout.write(self.style.SUCCESS(f'+ {nome}: {message}'))
            elif status == 'already_exists':
                self.stdout.write(self.style.WARNING(f'- {nome}: {message}'))
            else:
                self.stdout.write(self.style.ERROR(f'! {nome}: {message}'))

        self.stdout.write(self.style.SUCCESS(
            'Resumo final: '
            f"{totals['created']} criados, "
            f"{totals['already_exists']} já existentes, "
            f"{totals['places_not_found']} sem correspondente na Places API, "
            f"{totals['invalid_coordinate']} com coordenadas inválidas."
        ))

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        planilha = options['planilha']
        radius_m = options['raio']
        sheet = options['sheet']

        with transaction.atomic():
            self.run_import(planilha=planilha, radius_m=radius_m, dry_run=dry_run, sheet=sheet)
            if dry_run:
                self.stdout.write(self.style.WARNING('DRY-RUN concluído. Desfazendo alterações...'))
                transaction.set_rollback(True)