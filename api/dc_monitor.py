import os
import json
import threading
import time
import requests
from queue import Queue
from django.conf import settings
from django.utils import timezone

DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')

# Fila global em memória
log_queue = Queue()
_worker_started = False

def discord_worker():
    """
    Trabalhador em segundo plano que esvazia a fila e envia para o Discord.
    """
    while True:
        # Aguarda 5 segundos entre cada envio para evitar spam
        time.sleep(5)
        
        if log_queue.empty():
            continue

        batch = []
        # O Discord aceita no máximo 10 Embeds (cartões) por mensagem
        while not log_queue.empty() and len(batch) < 10:
            batch.append(log_queue.get())

        if not batch:
            continue

        embeds = []
        for log in batch:
            # Cores dinâmicas: Verde (200), Laranja (400), Vermelho (500)
            if log['status'] >= 500:
                color = 16711680 # Vermelho
            elif log['status'] >= 400:
                color = 16753920 # Laranja
            else:
                color = 65280    # Verde

            embeds.append({
                "title": f"[{log['method']}] {log['path']}",
                "color": color,
                "fields": [
                    {"name": "Status", "value": str(log['status']), "inline": True},
                    {"name": "Tempo", "value": f"{log['duration_ms']} ms", "inline": True},
                    {"name": "Usuário", "value": log['user'], "inline": True},
                    {"name": "IP", "value": log['ip'], "inline": True},
                    {"name": "Rota", "value": log['route_name'], "inline": True},
                    {"name": "Query", "value": log['query_string'] or "-", "inline": False},
                    {"name": "UA", "value": (log['user_agent'][:100] or "-"), "inline": False},
                ],
                "footer": {
                    "text": log['timestamp']
                }
            })

        payload = {"embeds": embeds}

        if not DISCORD_WEBHOOK_URL:
            print("AVISO: DISCORD_WEBHOOK_URL não definida no .env. Logs ignorados.")
            continue
        
        try:
            requests.post(
                DISCORD_WEBHOOK_URL, 
                data=json.dumps(payload), 
                headers={"Content-Type": "application/json"},
                timeout=5
            )
        except Exception as e:
            # Falhas aqui não derrubam o backend
            print(f"Erro no worker do Discord: {e}")

class DiscordMonitorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Garante que a thread operária seja iniciada apenas uma vez quando o Django subir
        global _worker_started
        if not _worker_started:
            # daemon=True faz com que a thread morra automaticamente se o servidor Django desligar
            worker_thread = threading.Thread(target=discord_worker, daemon=True)
            worker_thread.start()
            _worker_started = True

    def __call__(self, request):
        start = time.monotonic() # Marca o tempo de início para medir a duração da requisição
        response = self.get_response(request) # Processa a requisição e obtém a resposta
        duration_ms = round((time.monotonic() - start) * 1000, 2) # Calcula a duração da requisição

        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR') # Captura o IP real do cliente, mesmo atrás de proxies
        ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR') # Captura o IP do cliente diretamente do request

        user = request.user.username if hasattr(request, 'user') and request.user.is_authenticated else "Anônimo" # Captura o nome do usuário autenticado, ou "Anônimo" se não estiver autenticado

        user_id = request.user.id if hasattr(request, 'user') and request.user.is_authenticated else None
        user_agent = request.META.get('HTTP_USER_AGENT', '-')
        referer = request.META.get('HTTP_REFERER', '-')
        content_type = request.META.get('CONTENT_TYPE', '-')
        route_name = getattr(getattr(request, 'resolver_match', None), 'view_name', '-') or '-'
        path = request.path
        query_string = request.META.get('QUERY_STRING', '')
        status_code = response.status_code
        response_size = response.get('Content-Length', '-') or '-'
        method = request.method
        timestamp = timezone.now().isoformat()

        # Coloca as informações na fila de forma quase instantânea
        log_data = {
            'timestamp': timestamp,
            'method': method,
            'path': path,
            'query_string': query_string,
            'status': status_code,
            'duration_ms': duration_ms,
            'ip': ip,
            'user': user,
            'user_id': str(user_id) if user_id is not None else '-',
            'user_agent': user_agent,
            'referer': referer,
            'content_type': content_type,
            'response_size': str(response_size),
            'route_name': route_name,
        }
        log_queue.put(log_data)

        return response