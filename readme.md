# VaiAbastecendo - Django / PostGIS

API RESTful construída para alimentar o aplicativo VaiAbastecendo. Conta com cálculos espaciais de distância em tempo real, proteção contra gargalos de query (N+1) e sistema de paginação.

## 🛠 Tecnologias

* **Framework:** Python / Django / Django REST Framework
* **Banco de Dados:** PostgreSQL com extensão PostGIS (Dados Espaciais)
* **Ambiente:** Docker & Docker Compose
* **Arquitetura:** Model-View-Controller (MVC) adaptado para APIs (Serializers & ViewSets)

## 📡 Endpoints

* `GET /api/stations/`: Retorna a lista paginada de postos. Aceita `lat` e `lng` via query params para ordenar pela distância.
* `GET /api/fuel-types/`: Retorna os tipos disponíveis para o formulário do app.
* `POST /api/price-updates/`: Registra uma nova modificação de preço, atrelando ao usuário (se autenticado).

## 🚀 Localmente

O ambiente é 100% conteinerizado para garantir paridade entre desenvolvimento e produção.

1. **Configure as variáveis de ambiente:**

    Crie um arquivo .env na raíz do projeto e adicione as variáveis de ambiente com as informações do seu projeto:

    ```
    DB_NAME=
    DB_USER=
    DB_PASSWORD=

    DJANGO_SECRET_KEY=

    PLACES_API_KEY=
    ```

2. **Suba os containers (Banco e Servidor):**
   ```bash
   docker compose up --build
   ```

3. **Execute as Migrações (em outro terminal):**
    ```
    docker compose exec web python manage.py migrate
    ```

4. **Crie um usuário administrador:**
    ```
    docker compose exec web python manage.py createsuperuser
    ```

##