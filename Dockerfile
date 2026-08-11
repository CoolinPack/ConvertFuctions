FROM python:3.11-slim

# Устанавливаем системные пакеты по частям, чтобы снизить нагрузку на память
RUN apt-get update && apt-get install -y --no-install-recommends \
    imagemagick \
    poppler-utils \
    ghostscript \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем LibreOffice отдельно (самый тяжёлый)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-core \
    libreoffice-writer \
    libreoffice-calc \
    libreoffice-impress \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем остальное
RUN apt-get update && apt-get install -y --no-install-recommends \
    pdf2svg \
    zip \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Настройка ImageMagick политики
RUN sed -i 's/<policy domain="path" rights="none" pattern="@\*"/<policy domain="path" rights="read|write" pattern="@\*"/' /etc/ImageMagick-6/policy.xml || true
RUN sed -i 's/<policy domain="coder" rights="none" pattern="PDF"/<policy domain="coder" rights="read|write" pattern="PDF"/' /etc/ImageMagick-6/policy.xml || true

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
