# ======================================================
# Imagen de la API de Monitoreo de Signos Vitales
# ======================================================
FROM python:3.12-slim

# No generar .pyc y mostrar logs sin buffer (se ven en tiempo real con docker logs)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 1. Instalamos dependencias primero, en su propia capa.
#    Si solo cambia el código (y no requirements), Docker reutiliza esta capa
#    y el build es mucho más rápido.
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

# 2. Copiamos el resto del proyecto (lo que excluye .dockerignore no entra)
COPY . .

EXPOSE 8000

CMD ["uvicorn", "mainf:app", "--host", "0.0.0.0", "--port", "8000"]
