FROM python:3.11-slim

# Устанавливаем только лёгкие пакеты + libheif для HEIC
RUN apt-get update && apt-get install -y --no-install-recommends \
    imagemagick \
    poppler-utils \
    ghostscript \
    pdf2svg \
    zip \
    unzip \
    libheif-dev \
    libheif-examples \
    && rm -rf /var/lib/apt/lists/*

# Настройка ImageMagick для поддержки HEIC
RUN sed -i 's/<policy domain="path" rights="none" pattern="@\*"/<policy domain="path" rights="read|write" pattern="@\*"/' /etc/ImageMagick-6/policy.xml || true
RUN sed -i 's/<policy domain="coder" rights="none" pattern="PDF"/<policy domain="coder" rights="read|write" pattern="PDF"/' /etc/ImageMagick-6/policy.xml || true
RUN sed -i 's/<policy domain="coder" rights="none" pattern="HEIC"/<policy domain="coder" rights="read|write" pattern="HEIC"/' /etc/ImageMagick-6/policy.xml || true

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
