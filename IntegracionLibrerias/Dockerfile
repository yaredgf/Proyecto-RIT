FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Instalar las dependencias antes de copiar el código permite
# reutilizar esta capa mientras requirements.txt no cambie.
COPY requirements.txt ./
RUN python -m pip install -r requirements.txt

COPY . .

# Comprobación inicial. Se cambiará cuando exista el spider.
CMD ["python", "-m", "scrapy", "version"]