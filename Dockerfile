FROM python:3.11-slim

# Добавьте libmagic в список устанавливаемых пакетов
RUN apt-get update && apt-get install -y \
    imagemagick \
    poppler-utils \
    ghostscript \
    libreoffice \
    libreoffice-writer \
    libreoffice-calc \
    libreoffice-impress \
    pdf2svg \
    zip \
    unzip \
    libmagic-dev \    # ← Добавьте эту строку
    && rm -rf /var/lib/apt/lists/*

# Остальное без изменений...
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
EXPOSE 5000
CMD ["python", "app.py"]
