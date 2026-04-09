# Usa uma imagem oficial e leve do Python
FROM python:3.12-slim

# Impede o Python de gravar arquivos .pyc no disco
ENV PYTHONDONTWRITEBYTECODE=1
# Impede o Python de fazer buffer no stdout/stderr (melhora os logs no Docker)
ENV PYTHONUNBUFFERED=1

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Instala as dependências do sistema necessárias para compilar pacotes como o psycopg2
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    binutils \
    libproj-dev \
    gdal-bin \
    libgdal-dev \
    python3-gdal \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala as dependências do Python
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copia o resto do código do projeto
COPY . /app/