"""
Importa postos de combustível para o backend usando Places API (New).

Suporta dois tipos de região:
1. Bairro + cidade + UF
   Ex.: {'bairro': 'Alecrim', 'cidade': 'Natal', 'uf': 'RN'}
2. Cidade inteira + UF
   Ex.: {'cidade': 'São José de Mipibu', 'uf': 'RN'}

Comportamento:
- Por padrão, cria apenas postos novos e ignora os já existentes.
- Com --sync, atualiza registros existentes.
- Com --dry-run, executa tudo em transação e desfaz ao final.

Exemplos:
    python manage.py importar_postos
    python manage.py importar_postos --dry-run
    python manage.py importar_postos --sync
    python manage.py importar_postos --sync --dry-run
"""

import re
import time
import requests
import environ

from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.db import transaction

from api.models import Station

env = environ.Env()

regioes = [
    # EXEMPLO COM BAIRRO + CIDADE
    {'bairro': 'Nova Parnamirim', 'cidade': 'Parnamirim', 'uf': 'RN', 'aliases': ['nova parnamirim']},

    # EXEMPLO COM CIDADE INTEIRA
    # {'cidade': 'São José de Mipibu', 'uf': 'RN', 'aliases': ['são josé de mipibu']},
]

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
    nome = str(nome).lower()
    for bandeira, padrao in BANDEIRAS.items():
        if re.search(padrao, nome):
            return bandeira
    return 'Bandeira Branca'


def place_score(place):
    return (place.get('user_ratings_total') or 0, place.get('rating') or 0)


def station_score(station):
    return (getattr(station, 'user_ratings_total', None) or 0, station.rating or 0)


class Command(BaseCommand):
    help = 'Importa postos via Places Text Search (New), com suporte a bairros e cidades inteiras.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Simula sem persistir alterações.')
        parser.add_argument('--sync', action='store_true', help='Atualiza registros existentes em vez de apenas ignorá-los.')

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
                'nextPageToken',
            ]),
        }

    def has_bairro(self, regiao):
        return bool(regiao.get('bairro'))

    def region_label(self, regiao):
        if self.has_bairro(regiao):
            return f"{regiao['bairro']}, {regiao['cidade']}, {regiao['uf']}"
        return f"{regiao['cidade']}, {regiao['uf']}"

    def fetch(self, url, headers, payload):
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        return response.status_code, response.json()

    def geocode_region(self, url, headers, regiao):
        payload = {
            'textQuery': self.region_label(regiao),
            'languageCode': 'pt-BR',
            'regionCode': 'br',
            'pageSize': 1,
        }
        status, data = self.fetch(url, headers, payload)
        if status != 200:
            self.stdout.write(self.style.ERROR(
                f"Não foi possível geocodificar {self.region_label(regiao)}: HTTP {status} - {data}"
            ))
            return None

        places = data.get('places', [])
        if not places:
            self.stdout.write(self.style.WARNING(
                f"Nenhum ponto encontrado para {self.region_label(regiao)}. Seguindo sem viés geográfico."
            ))
            return None

        location = (places[0].get('location') or {})
        lat = location.get('latitude')
        lng = location.get('longitude')
        if lat is None or lng is None:
            return None

        self.stdout.write(self.style.SUCCESS(
            f"Centro aproximado de {self.region_label(regiao)}: lat={lat}, lng={lng}"
        ))
        return {'latitude': lat, 'longitude': lng}

    def payload(self, regiao, center=None, page_token=None):
        data = {
            'textQuery': f"postos de combustível em {self.region_label(regiao)}",
            'languageCode': 'pt-BR',
            'regionCode': 'br',
            'pageSize': 20,
            'includedType': 'gas_station',
            'strictTypeFiltering': True,
        }
        if center:
            data['locationBias'] = {
                'circle': {
                    'center': center,
                    'radius': 4000.0 if self.has_bairro(regiao) else 7000.0,
                }
            }
        if page_token:
            data['pageToken'] = page_token
        return data

    def fetch_next_page(self, url, headers, regiao, center, token):
        for tentativa in range(1, 11):
            time.sleep(5 if tentativa == 1 else 3)
            status, data = self.fetch(url, headers, self.payload(regiao, center=center, page_token=token))
            if status == 200:
                return data
            self.stdout.write(f'Tentativa {tentativa}/10 para próxima página falhou (HTTP {status}).')
        return None

    def normalize_text(self, value):
        return re.sub(r'\s+', ' ', (value or '').strip().lower())

    def normalize_place(self, raw):
        display_name = raw.get('displayName') or {}
        location = raw.get('location') or {}
        return {
            'place_id': raw.get('id'),
            'name': display_name.get('text', 'Posto sem nome'),
            'address': raw.get('formattedAddress', ''),
            'lat': location.get('latitude'),
            'lng': location.get('longitude'),
            'rating': raw.get('rating'),
            'user_ratings_total': raw.get('userRatingCount'),
            'types': raw.get('types', []),
        }

    def address_matches_region(self, address, regiao):
        address = self.normalize_text(address)
        cidade = self.normalize_text(regiao['cidade'])
        uf = self.normalize_text(regiao['uf'])
        aliases = [self.normalize_text(a) for a in regiao.get('aliases', [])]

        if cidade not in address or uf not in address:
            return False

        if not self.has_bairro(regiao):
            return True

        if not aliases:
            aliases = [self.normalize_text(regiao['bairro'])]

        return any(alias in address for alias in aliases)

    def is_valid_place(self, place, regiao):
        if place['lat'] is None or place['lng'] is None:
            return False
        if 'gas_station' not in place.get('types', []):
            return False
        if not self.address_matches_region(place['address'], regiao):
            return False
        return True

    def build_defaults(self, place):
        return {
            'place_id': place['place_id'] or '',
            'name': place['name'],
            'address': place['address'],
            'brand': identificar_bandeira(place['name']),
            'rating': place['rating'],
            'user_ratings_total': place['user_ratings_total'],
            'location': Point(float(place['lng']), float(place['lat']), srid=4326),
        }

    def apply_updates(self, station, defaults):
        for field, value in defaults.items():
            setattr(station, field, value)
        station.save()

    def remove_duplicates(self, duplicates):
        for station in duplicates:
            station.delete()
        return len(duplicates)

    def process_place(self, place, sync=False):
        defaults = self.build_defaults(place)
        place_id = place['place_id']

        if place_id:
            existing = Station.objects.filter(place_id=place_id).first()
            if existing:
                if sync:
                    self.apply_updates(existing, defaults)
                    return 'updated', existing.name, 0
                return 'ignored', existing.name, 0

        nearby = list(Station.objects.filter(location__distance_lte=(defaults['location'], D(m=30))))
        if not nearby:
            station = Station.objects.create(**defaults)
            return 'created', station.name, 0

        best = max(nearby, key=station_score)
        duplicates = [s for s in nearby if s.id != best.id]

        if sync and place_score(place) > station_score(best):
            self.apply_updates(best, defaults)
            removed = self.remove_duplicates(duplicates)
            return 'updated', best.name, removed

        removed = self.remove_duplicates(duplicates)
        return 'ignored', place['name'], removed

    def run_import(self, dry_run=False, sync=False):
        api_key = env('PLACES_API_KEY')
        url = 'https://places.googleapis.com/v1/places:searchText'
        headers = self.headers(api_key)

        totals = {'created': 0, 'updated': 0, 'ignored': 0, 'duplicates_removed': 0, 'filtered_out': 0}

        for regiao in regioes:
            nome_regiao = self.region_label(regiao)
            self.stdout.write(self.style.WARNING(f'\n--- Iniciando busca em: {nome_regiao} ---'))
            if dry_run:
                self.stdout.write(self.style.WARNING('MODO SIMULAÇÃO ATIVO: alterações serão desfeitas ao final.'))
            if sync:
                self.stdout.write(self.style.WARNING('MODO SYNC ATIVO: registros existentes poderão ser atualizados.'))

            center = self.geocode_region(url, headers, regiao)
            counters = {'created': 0, 'updated': 0, 'ignored': 0, 'duplicates_removed': 0, 'filtered_out': 0}

            status, response = self.fetch(url, headers, self.payload(regiao, center=center))
            if status != 200:
                self.stdout.write(self.style.ERROR(f'Erro na API para {nome_regiao}: HTTP {status} - {response}'))
                continue

            page = 1
            while True:
                places = response.get('places', [])
                self.stdout.write(f'Resultados na página {page} ({nome_regiao}): {len(places)}')

                for raw_place in places:
                    place = self.normalize_place(raw_place)

                    if not self.is_valid_place(place, regiao):
                        counters['filtered_out'] += 1
                        totals['filtered_out'] += 1
                        self.stdout.write(f" - Filtrado fora da região: {place['name']} | {place['address']}")
                        continue

                    action, name, removed = self.process_place(place, sync=sync)
                    counters[action] += 1
                    totals[action] += 1
                    counters['duplicates_removed'] += removed
                    totals['duplicates_removed'] += removed

                    if action == 'created':
                        self.stdout.write(f' + Cadastrado {place['name']} | {place['address']}.')
                    elif action == 'updated':
                        self.stdout.write(f' ~ Atualizado: {place['name']} | {place['address']}')
                    else:
                        self.stdout.write(f" - Ignorado {place['name']} | {place['address']} pois já existe posto correspondente.")

                token = response.get('nextPageToken')
                if not token:
                    break

                self.stdout.write('Preparando próxima página...')
                response = self.fetch_next_page(url, headers, regiao, center, token)
                if not response:
                    self.stdout.write(self.style.ERROR('Falha ao carregar próxima página. Pulando região.'))
                    break
                page += 1

            self.stdout.write(self.style.SUCCESS(
                f"Resumo da região '{nome_regiao}': "
                f"{counters['created']} novos, {counters['updated']} atualizados, "
                f"{counters['ignored']} ignorados, {counters['duplicates_removed']} duplicados removidos, "
                f"{counters['filtered_out']} filtrados fora da região."
            ))

        self.stdout.write(self.style.SUCCESS(
            '\nFim da varredura! '
            f"{totals['created']} novos, {totals['updated']} atualizados, {totals['ignored']} ignorados, "
            f"{totals['duplicates_removed']} duplicados removidos e {totals['filtered_out']} filtrados fora da região."
        ))

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        sync = options['sync']

        with transaction.atomic():
            self.run_import(dry_run=dry_run, sync=sync)
            if dry_run:
                self.stdout.write(self.style.WARNING('DRY-RUN concluído. Desfazendo alterações...'))
                transaction.set_rollback(True)