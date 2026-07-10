# ============================================================
# Engenharia de Dados — Saneamento Brasil
# ============================================================
# Imagem Docker para rodar o pipeline e o dashboard.
#
# Como usar:
#   docker build -t saneamento-pipeline .
#   docker run -p 8501:8501 saneamento-pipeline
#
# Ou com docker-compose:
#   docker-compose up
# ============================================================

FROM python:3.11-slim

# Metadados
LABEL maintainer="TiagoMFernandes"
LABEL description="Pipeline de engenharia de dados de saneamento básico brasileiro"

# Variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Diretório de trabalho dentro do container
WORKDIR /app

# Instala dependências do sistema necessárias para openpyxl/pyarrow
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala dependências Python primeiro (melhor uso do cache Docker)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copia o restante do projeto
COPY . .

# Cria pastas de dados (vazias — dados não são versionados)
RUN mkdir -p data/raw/sinisa data/bronze/sinisa data/silver/sinisa data/gold

# Porta do Streamlit
EXPOSE 8501

# Comando padrão: inicia o dashboard
# Para rodar o pipeline, use: docker-compose run pipeline
CMD ["streamlit", "run", "dashboard/app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
