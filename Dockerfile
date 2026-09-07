FROM python:3.12-slim

# Evitar que Python escriba archivos .pyc y forzar salida sin buffer para logs inmediatos
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependencias del sistema mínimas requeridas si fuera necesario
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY src/ ./src/
COPY pyproject.toml README.md ./

# Crear carpeta para persistencia de datos (SQLite / uploads)
RUN mkdir -p /app/data

# Puerto expuesto para cuando se agregue el dashboard web en la fase final
EXPOSE 8000

CMD ["python", "-m", "src.main"]
