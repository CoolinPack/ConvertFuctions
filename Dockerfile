FROM python:3.11-slim

# Установка системных зависимостей
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
    && rm -rf /var/lib/apt/lists/*

# Настройка ImageMagick политики (разрешаем все операции)
RUN sed -i 's/<policy domain="path" rights="none" pattern="@\*"/<policy domain="path" rights="read|write" pattern="@\*"/' /etc/ImageMagick-6/policy.xml || true
RUN sed -i 's/<policy domain="coder" rights="none" pattern="PDF"/<policy domain="coder" rights="read|write" pattern="PDF"/' /etc/ImageMagick-6/policy.xml || true

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 5000

CMD ["python", "app.py"]
