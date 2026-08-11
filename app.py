from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import subprocess
import tempfile
import shutil
import uuid
from pathlib import Path
import time
import json
# Строка import magic ПОЛНОСТЬЮ УДАЛЕНА
from werkzeug.utils import secure_filename

# Инициализация LibreOffice для Render
def init_libreoffice():
    try:
        subprocess.run([
            'libreoffice', '--headless', '--nologo', '--norestore', 
            '--invisible', '--nofirststartwizard', '--accept=socket,host=localhost,port=2002;urp;'
        ], timeout=10, capture_output=True)
    except:
        pass  # Игнорируем ошибки инициализации

# Вызов при старте
init_libreoffice()

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = '/tmp/uploads'
OUTPUT_FOLDER = '/tmp/outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

# Категории форматов
IMAGE_FORMATS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp', 'ico', 'svg', 'heic'}
DOCUMENT_FORMATS = {'pdf', 'doc', 'docx', 'odt', 'rtf', 'txt'}
SPREADSHEET_FORMATS = {'xls', 'xlsx', 'ods', 'csv'}
PRESENTATION_FORMATS = {'ppt', 'pptx', 'odp'}
ARCHIVE_FORMATS = {'zip', 'rar', '7z'}

ALL_FORMATS = IMAGE_FORMATS | DOCUMENT_FORMATS | SPREADSHEET_FORMATS | PRESENTATION_FORMATS | ARCHIVE_FORMATS

# Матрица конвертации
CONVERSION_MATRIX = {
    # Изображения
    # Матрица конвертаций
CONVERSION_MATRIX = {
    # Изображения (включая HEIC)
    'image_to_image': ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'tiff', 'ico', 'heic'],
    'image_to_pdf': ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'tiff', 'ico', 'heic'],
    
    # PDF
    'pdf_to_image': ['png', 'jpg', 'jpeg', 'heic'],  # можно конвертировать PDF в HEIC
    # ... остальное без изменений
}
    'pdf_to_text': ['txt'],
    'pdf_to_svg': ['svg'],
    'pdf_to_pdf': ['pdf'],
    
    # Документы
    'document_to_pdf': ['doc', 'docx', 'odt', 'rtf'],
    'document_to_document': ['doc', 'docx', 'odt', 'rtf'],
    'pdf_to_document': ['doc', 'docx', 'odt', 'rtf'],
    
    # Таблицы
    'spreadsheet_to_pdf': ['xls', 'xlsx', 'ods', 'csv'],
    'spreadsheet_to_csv': ['xls', 'xlsx', 'ods'],
    'csv_to_spreadsheet': ['xls', 'xlsx', 'ods'],
    
    # Презентации
    'presentation_to_pdf': ['ppt', 'pptx', 'odp'],
    'presentation_to_image': ['png', 'jpg', 'jpeg'],
}

def get_conversion_type(input_format, output_format):
    input_format = input_format.lower()
    output_format = output_format.lower()
    
    # Изображения
    if input_format in IMAGE_FORMATS and output_format in IMAGE_FORMATS:
        return 'image_to_image'
    if input_format in IMAGE_FORMATS and output_format == 'pdf':
        return 'image_to_pdf'
    
    # PDF
    if input_format == 'pdf' and output_format in IMAGE_FORMATS:
        return 'pdf_to_image'
    if input_format == 'pdf' and output_format == 'txt':
        return 'pdf_to_text'
    if input_format == 'pdf' and output_format == 'svg':
        return 'pdf_to_svg'
    if input_format == 'pdf' and output_format == 'pdf':
        return 'pdf_to_pdf'
    
    # Документы
    if input_format in DOCUMENT_FORMATS and output_format == 'pdf':
        return 'document_to_pdf'
    if input_format in DOCUMENT_FORMATS and output_format in DOCUMENT_FORMATS:
        return 'document_to_document'
    if input_format == 'pdf' and output_format in DOCUMENT_FORMATS:
        return 'pdf_to_document'
    
    # Таблицы
    if input_format in SPREADSHEET_FORMATS and output_format == 'pdf':
        return 'spreadsheet_to_pdf'
    if input_format in SPREADSHEET_FORMATS and output_format == 'csv':
        return 'spreadsheet_to_csv'
    if input_format == 'csv' and output_format in SPREADSHEET_FORMATS:
        return 'csv_to_spreadsheet'
    
    # Презентации
    if input_format in PRESENTATION_FORMATS and output_format == 'pdf':
        return 'presentation_to_pdf'
    if input_format in PRESENTATION_FORMATS and output_format in IMAGE_FORMATS:
        return 'presentation_to_image'
    
    return None

def convert_image(input_path, output_path, output_format):
    """Конвертация изображений через ImageMagick"""
    cmd = ['convert', input_path, '-quality', '95', output_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"ImageMagick error: {result.stderr}")
    return output_path

def images_to_pdf(input_paths, output_path):
    """Сборка PDF из изображений"""
    cmd = ['convert'] + input_paths + ['-quality', '95', output_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Image to PDF error: {result.stderr}")
    return output_path

def pdf_to_image(input_path, output_dir, output_format):
    """PDF в изображения"""
    output_pattern = os.path.join(output_dir, f'page_%04d.{output_format}')
    cmd = ['pdftoppm', '-r', '300', input_path, output_pattern.replace(f'.{output_format}', '')]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"PDF to image error: {result.stderr}")
    
    # Возвращаем список сгенерированных файлов
    return sorted(Path(output_dir).glob(f'page_*.{output_format}'))

def pdf_to_text(input_path, output_path):
    """Извлечение текста из PDF"""
    cmd = ['pdftotext', input_path, output_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"PDF to text error: {result.stderr}")
    return output_path

def pdf_to_svg(input_path, output_dir):
    """PDF в SVG"""
    cmd = ['pdf2svg', input_path, os.path.join(output_dir, 'page_%d.svg')]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"PDF to SVG error: {result.stderr}")
    return sorted(Path(output_dir).glob('page_*.svg'))

def compress_pdf(input_path, output_path):
    """Сжатие PDF через Ghostscript"""
    cmd = [
        'gs', '-sDEVICE=pdfwrite', '-dCompatibilityLevel=1.4',
        '-dPDFSETTINGS=/ebook', '-dNOPAUSE', '-dQUIET', '-dBATCH',
        f'-sOutputFile={output_path}', input_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"PDF compression error: {result.stderr}")
    return output_path

def convert_document(input_path, output_path, output_format):
    """Конвертация документов через LibreOffice"""
    cmd = [
        'libreoffice', '--headless', '--convert-to', output_format,
        '--outdir', os.path.dirname(output_path), input_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise Exception(f"LibreOffice error: {result.stderr}")
    
    # LibreOffice создаёт файл в том же каталоге с именем как у исходного
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    generated_path = os.path.join(os.path.dirname(output_path), f'{base_name}.{output_format}')
    
    if os.path.exists(generated_path):
        os.rename(generated_path, output_path)
        return output_path
    else:
        raise Exception("Output file not generated")

def convert_spreadsheet(input_path, output_path, output_format):
    """Конвертация таблиц"""
    return convert_document(input_path, output_path, output_format)

def convert_presentation(input_path, output_path, output_format):
    """Конвертация презентаций"""
    if output_format in IMAGE_FORMATS:
        # Сначала в PDF
        pdf_path = output_path.replace(f'.{output_format}', '.pdf')
        convert_document(input_path, pdf_path, 'pdf')
        # Затем PDF в изображения
        output_dir = os.path.dirname(output_path)
        images = pdf_to_image(pdf_path, output_dir, output_format)
        if images:
            # Берём первый слайд
            os.rename(images[0], output_path)
            return output_path
        raise Exception("Failed to convert presentation to image")
    else:
        return convert_document(input_path, output_path, output_format)

@app.route('/api/convert', methods=['POST'])
def convert_file():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        input_format = data.get('inputFormat', '').lower()
        output_format = data.get('outputFormat', '').lower()
        file_content = data.get('fileContent')
        file_name = data.get('fileName', 'file')
        
        if not file_content:
            return jsonify({'error': 'No file content'}), 400
        
        # Проверка форматов
        if input_format not in ALL_FORMATS:
            return jsonify({'error': f'Unsupported input format: {input_format}'}), 400
        if output_format not in ALL_FORMATS:
            return jsonify({'error': f'Unsupported output format: {output_format}'}), 400
        
        # Определяем тип конвертации
        conversion_type = get_conversion_type(input_format, output_format)
        if not conversion_type:
            return jsonify({'error': f'Conversion from {input_format} to {output_format} not supported'}), 400
        
        # Генерируем уникальный ID для сессии
        session_id = str(uuid.uuid4())
        session_dir = os.path.join(UPLOAD_FOLDER, session_id)
        os.makedirs(session_dir, exist_ok=True)
        
        # Сохраняем входной файл
        import base64
        file_data = base64.b64decode(file_content)
        input_path = os.path.join(session_dir, f'input.{input_format}')
        with open(input_path, 'wb') as f:
            f.write(file_data)
        
        output_path = os.path.join(session_dir, f'output.{output_format}')
        
        # Выполняем конвертацию
        if conversion_type == 'image_to_image':
            convert_image(input_path, output_path, output_format)
        elif conversion_type == 'image_to_pdf':
            images_to_pdf([input_path], output_path)
        elif conversion_type == 'pdf_to_image':
            output_dir = os.path.join(session_dir, 'pages')
            os.makedirs(output_dir, exist_ok=True)
            images = pdf_to_image(input_path, output_dir, output_format)
            if images:
                # Возвращаем все страницы в ZIP
                import zipfile
                zip_path = os.path.join(session_dir, 'pages.zip')
                with zipfile.ZipFile(zip_path, 'w') as zipf:
                    for img in images:
                        zipf.write(img, img.name)
                return send_file(zip_path, as_attachment=True, download_name='pages.zip')
            raise Exception("No images generated")
        elif conversion_type == 'pdf_to_text':
            pdf_to_text(input_path, output_path)
        elif conversion_type == 'pdf_to_svg':
            output_dir = os.path.join(session_dir, 'pages')
            os.makedirs(output_dir, exist_ok=True)
            svgs = pdf_to_svg(input_path, output_dir)
            import zipfile
            zip_path = os.path.join(session_dir, 'pages.zip')
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for svg in svgs:
                    zipf.write(svg, svg.name)
            return send_file(zip_path, as_attachment=True, download_name='pages.zip')
        elif conversion_type == 'pdf_to_pdf':
            compress_pdf(input_path, output_path)
        elif conversion_type in ['document_to_pdf', 'document_to_document', 'pdf_to_document']:
            convert_document(input_path, output_path, output_format)
        elif conversion_type in ['spreadsheet_to_pdf', 'spreadsheet_to_csv', 'csv_to_spreadsheet']:
            convert_spreadsheet(input_path, output_path, output_format)
        elif conversion_type in ['presentation_to_pdf', 'presentation_to_image']:
            convert_presentation(input_path, output_path, output_format)
        else:
            return jsonify({'error': f'Unsupported conversion type: {conversion_type}'}), 400
        
        # Проверяем, существует ли выходной файл
        if not os.path.exists(output_path):
            # Ищем файл, который мог создать LibreOffice
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            possible_output = os.path.join(session_dir, f'{base_name}.{output_format}')
            if os.path.exists(possible_output):
                os.rename(possible_output, output_path)
            else:
                raise Exception("Output file not generated")
        
        # Отправляем файл
        return send_file(output_path, as_attachment=True, download_name=f'converted.{output_format}')
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # Очистка временных файлов
        if 'session_id' in locals():
            shutil.rmtree(session_dir, ignore_errors=True)

@app.route('/api/formats', methods=['GET'])
def get_formats():
    """Возвращает список поддерживаемых форматов"""
    return jsonify({
        'formats': list(ALL_FORMATS),
        'categories': {
            'image': list(IMAGE_FORMATS),
            'document': list(DOCUMENT_FORMATS),
            'spreadsheet': list(SPREADSHEET_FORMATS),
            'presentation': list(PRESENTATION_FORMATS),
            'archive': list(ARCHIVE_FORMATS)
        },
        'conversions': CONVERSION_MATRIX
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Проверка работоспособности"""
    return jsonify({'status': 'healthy', 'timestamp': time.time()})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
