import os
import json
import threading
import time
import requests
from queue import Queue
from django.conf import settings

# Substitua pela sua URL
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
                    {"name": "IP", "value": log['ip'], "inline": True},
                    {"name": "Usuário", "value": log['user'], "inline": True},
                    {"name": "User-Agent", "value": log.get('user_agent', 'N/A'), "inline": False},
                ]
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
        response = self.get_response(request)

        # Captura o IP verdadeiro
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')

        # Captura o nome de usuário (se estiver logado pelo sistema de auth do Django)
        user = request.user.username if hasattr(request, 'user') and request.user.is_authenticated else "Anônimo"

        # Coloca as informações na fila de forma quase instantânea
        log_data = {
            'method': request.method,
            'path': request.get_full_path(),
            'status': response.status_code,
            'ip': ip,
            'user': user
        }
        log_queue.put(log_data)

        return response