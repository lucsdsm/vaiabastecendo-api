# VaiAbastecendo - Django / PostGIS

API RESTful construída para alimentar o aplicativo VaiAbastecendo. Conta com cálculos espaciais de distância em tempo real, proteção contra gargalos de query (N+1) e sistema de paginação.

## 🛠 Tecnologias

- **Framework:** Python / Django / Django REST Framework
- **Banco de Dados:** PostgreSQL com extensão PostGIS (dados espaciais)
- **Ambiente:** Docker & Docker Compose
- **Proxy / HTTPS:** Nginx + Certbot + sslh
- **Arquitetura:** MVC adaptado para APIs com Serializers & ViewSets

## 📡 Endpoints

- `GET /api/stations/`: retorna a lista paginada de postos; aceita `lat` e `lng` via query params para ordenar pela distância.
- `GET /api/fuel-types/`: retorna os tipos disponíveis para o formulário do app.
- `POST /api/price-updates/`: registra uma nova modificação de preço, atrelando ao usuário, se autenticado.

## 🚀 Rodando localmente

O ambiente é 100% conteinerizado para garantir paridade entre desenvolvimento e produção.

### 1. Configure as variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto e preencha com as variáveis do seu ambiente:

```env
DB_NAME=
DB_USER=
DB_PASSWORD=

DJANGO_SECRET_KEY=

PLACES_API_KEY=
```

### 2. Suba os containers

```bash
docker compose up --build
```

### 3. Execute as migrações

```bash
docker compose exec web python manage.py migrate
```

### 4. Crie um superusuário

```bash
docker compose exec web python manage.py createsuperuser
```

## ☁️ Deploy na Oracle VM

Este guia documenta o processo usado para configurar uma nova máquina Oracle e restaurar o ambiente de produção com Docker, Django, PostgreSQL/PostGIS, Nginx, Certbot e `sslh`.

### Visão geral da arquitetura

- `db`: PostgreSQL com PostGIS.
- `web`: aplicação Django/Gunicorn na porta interna `8000`.
- `nginx`: proxy reverso, HTTP na `80` e HTTPS interno na `8443`.
- `sslh`: multiplexador que escuta na `443` pública e encaminha:
  - SSH para `127.0.0.1:22`
  - HTTPS/TLS para `127.0.0.1:8443`

Com isso, continuam funcionando ao mesmo tempo:

- SSH em `ssh -p 443 ...`
- Painel Django em `https://vaiabastecendo.lucsdsm.com.br/admin/`

---

## 1. Acesso SSH inicial

Se for necessário liberar uma porta temporária para o primeiro acesso SSH, usar por exemplo a `8443`.

### 1.1. Habilitar SSH em 8443 temporariamente

Editar o arquivo de configuração do SSH:

```bash
sudo nano /etc/ssh/sshd_config
```

Adicionar abaixo de `Port 22`:

```text
Port 8443
```

Liberar a porta no firewall da VM:

```bash
sudo iptables -I INPUT -p tcp --dport 8443 -j ACCEPT
```

Persistir a regra:

```bash
sudo apt update
sudo apt install -y netfilter-persistent
sudo netfilter-persistent save
```

Reiniciar o SSH e validar:

```bash
sudo systemctl restart ssh
sudo systemctl status ssh
```

### 1.2. Conectar por SSH

Via CMD ou PowerShell:

```powershell
ssh -p [porta] -i [caminho-da-chave] [usuario]@[ip]
```

### 1.3. Quando a conexão SSH bugar no VSCode

Acessar o terminal da Oracle e limpar o servidor remoto do VSCode:

```bash
rm -rf ~/.vscode-server
```

---

## 2. Preparação do ambiente

### 2.1. Instalar utilitários básicos

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y tmux git ca-certificates curl gnupg
```

### 2.2. Evitar perda de sessão durante o deploy

```bash
tmux new -s deploy
```

---

## 3. Instalação do Docker

Executar dentro do `tmux`, se estiver usando.

```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
 $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" | \
 sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### 3.1. Validar instalação

```bash
docker --version
docker compose version
```

### 3.2. Usar Docker sem sudo

```bash
sudo usermod -aG docker $USER
newgrp docker
```

---

## 4. Clonar o repositório e preparar estrutura

### 4.1. Clonar o projeto

```bash
cd ~
git clone https://github.com/lucsdsm/vaiabastecendo-api.git
cd vaiabastecendo-api
```

### 4.2. Conferir `.env`

Criar ou ajustar o `.env` com as variáveis corretas do ambiente de produção.

### 4.3. Criar diretórios usados por Nginx e Certbot

```bash
mkdir -p certbot/conf certbot/www nginx
```

---

## 5. Subir `db` e `web` primeiro

Isso ajuda a validar banco, aplicação e migrações antes de colocar o proxy na frente.

```bash
docker compose up -d db web
docker compose ps
docker compose logs -f web
```

### 5.1. Rodar migrações e estáticos

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py collectstatic --noinput
docker compose exec web python manage.py createsuperuser
```

---

## 6. Configurar Django para produção

Conferir no `.env` e/ou `settings.py`:

- `DEBUG=False`
- `ALLOWED_HOSTS=['vaiabastecendo.lucsdsm.com.br', '127.0.0.1', 'localhost']`
- `CSRF_TRUSTED_ORIGINS=['https://vaiabastecendo.lucsdsm.com.br']`
- `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')`

Se houver frontend em outro domínio, ajustar também `CORS_ALLOWED_ORIGINS`.

---

## 7. Configurar Nginx

### 7.1. `docker-compose.yml`

O serviço `nginx` deve expor:

```yaml
nginx:
  image: nginx:alpine
  ports:
    - "80:80"
    - "8443:8443"
  volumes:
    - ./nginx:/etc/nginx/conf.d
    - ./certbot/conf:/etc/letsencrypt
    - ./certbot/www:/var/www/certbot
  depends_on:
    - web
```

### 7.2. `nginx/default.conf`

```nginx
limit_req_zone $binary_remote_addr zone=ratelimit:10m rate=5r/s;

server {
    listen 80;
    server_name vaiabastecendo.lucsdsm.com.br;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 8443 ssl;
    server_name vaiabastecendo.lucsdsm.com.br;

    ssl_certificate /etc/letsencrypt/live/vaiabastecendo.lucsdsm.com.br/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/vaiabastecendo.lucsdsm.com.br/privkey.pem;

    limit_req zone=ratelimit burst=10 nodelay;

    location ~* (/\.env|/\.git|/config\.json|/backup|wp-|xmlrpc\.php|\.php) {
        deny all;
        access_log off;
        log_not_found off;
    }

    location / {
        proxy_pass http://;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

### 7.3. Subir e validar o Nginx

```bash
docker compose up -d nginx
docker compose exec nginx nginx -t
```

Para verificar se o Nginx está ouvindo em `8443` dentro do container:

```bash
docker compose exec nginx ss -ltn | grep 8443
```

---

## 8. Emitir certificado com Certbot

Com o domínio apontando para a VM e a porta 80 liberada:

```bash
docker compose run --rm certbot certonly --webroot \
  --webroot-path /var/www/certbot \
  -d vaiabastecendo.lucsdsm.com.br \
  --email SEU_EMAIL \
  --agree-tos \
  --no-eff-email
```

Depois reiniciar o Nginx:

```bash
docker compose restart nginx
docker compose exec nginx nginx -t
curl -vk https://localhost:8443/admin/
```

Se esse `curl` funcionar, o HTTPS interno está operacional.

---

## 9. Configurar SSH interno novamente na 22

Depois que o acesso inicial pela 8443 não for mais necessário, deixar o SSH apenas na porta 22 local, porque o acesso externo passará a ser multiplexado na 443 via `sslh`.

Editar:

```bash
sudo nano /etc/ssh/sshd_config
```

Deixar apenas:

```text
Port 22
```

Reiniciar e validar:

```bash
sudo sshd -t
sudo systemctl restart ssh
sudo systemctl status ssh
sudo ss -ltnp 'sport = :22'
```

---

## 10. Instalar e configurar `sslh`

### 10.1. Instalar

```bash
sudo apt update
sudo apt install -y sslh
```

### 10.2. Configurar `/etc/default/sslh`

```bash
sudo nano /etc/default/sslh
```

Conteúdo:

```text
RUN=yes

DAEMON=/usr/sbin/sslh

DAEMON_OPTS="--user sslh \
  --listen 0.0.0.0:443 \
  --ssh 127.0.0.1:22 \
  --tls 127.0.0.1:8443 \
  --pidfile /var/run/sslh/sslh.pid"
```

> Observação: nesta versão do `sslh`, usar `--tls` em vez de `--ssl`.

### 10.3. Corrigir diretório do pidfile

```bash
sudo mkdir -p /var/run/sslh
sudo chown sslh:sslh /var/run/sslh
sudo chmod 750 /var/run/sslh
```

### 10.4. Subir o serviço

```bash
sudo systemctl daemon-reload
sudo systemctl restart sslh
sudo systemctl status sslh
```

Validar se a `443` agora pertence ao `sslh`:

```bash
sudo ss -ltnp 'sport = :443'
```

---

## 11. Firewall da VM e regras persistentes

Liberar portas necessárias:

```bash
sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

Se ainda estiver usando a 8443 para acesso temporário, mantê-la liberada até terminar a migração.

---

## 12. Regras na Oracle Cloud

No painel da Oracle, liberar na Security List ou NSG:

- TCP `80`
- TCP `443`
- TCP `8443` apenas se ainda estiver usando essa porta para SSH temporário

---

## 13. Testes finais

### 13.1. SSH pela 443

```powershell
ssh -p [porta] -i [caminho-da-chave] [usuario]@[ip]
```

### 13.2. Acesso ao admin via HTTPS

Abrir no navegador:

```text
https://vaiabastecendo.lucsdsm.com.br/admin/
```

### 13.3. Checklist rápido de diagnóstico

Se algo não funcionar, checar:

```bash
sudo systemctl status sslh
sudo ss -ltnp 'sport = :443'
sudo ss -ltnp 'sport = :22'
docker compose ps
docker compose exec nginx nginx -t
docker compose exec nginx ss -ltn | grep 8443
docker compose logs --tail=100 nginx
docker compose logs --tail=100 web
ls certbot/conf/live/vaiabastecendo.lucsdsm.com.br/
```

---

## 14. Fluxo resumido de reconstrução da VM

1. Acessar a VM por SSH temporário.
2. Instalar `tmux`, `git` e Docker.
3. Clonar o repositório e configurar `.env`.
4. Criar `certbot/conf`, `certbot/www` e `nginx`.
5. Subir `db` e `web`.
6. Rodar `migrate`, `collectstatic` e `createsuperuser`.
7. Configurar Nginx em `80` e `8443`.
8. Emitir certificado com Certbot.
9. Colocar SSH só na `22` local.
10. Instalar e configurar `sslh` na `443`.
11. Liberar `80` e `443` na Oracle e na VM.
12. Testar SSH em `-p 443` e o admin em `https://vaiabastecendo.lucsdsm.com.br/admin/`.