import os
import time
import requests
from typing import Dict, List, Any
from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

# Инициализация конфигурации
load_dotenv()

app = Flask(__name__)

# ───────────────────────────────────────────────
# Конфигурация
# ───────────────────────────────────────────────
YANDEX_PUBLIC_URL = os.getenv('YANDEX_PUBLIC_URL', 'https://disk.yandex.ru/d/GIXFpB9WYoReyA')
YANDEX_API_BASE = 'https://cloud-api.yandex.net/v1/disk'

YANDEX_OAUTH_TOKEN = os.getenv('YANDEX_OAUTH_TOKEN', '') # токен для загрузки файлов
UPLOAD_FOLDER_PATH = os.getenv('YANDEX_UPLOAD_FOLDER', '/Свадьба Даши и Ильи 2026/Фото от гостей')

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'mp4', 'mov', 'avi', 'heic'}
MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # 200 МБ

app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# In-memory кэш для галереи
# ───────────────────────────────────────────────
cache: Dict[str, Any] = {'data': [], 'timestamp': 0.0}
CACHE_TTL = 300  # секунд


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def fetch_yandex_disk_files() -> List[Dict[str, str]]:
    """Возвращает список файлов из публичной папки (с кэшированием)."""
    now = time.time()
    if cache['data'] and (now - cache['timestamp'] < CACHE_TTL):
        return cache['data']

    params = {
        'public_key': YANDEX_PUBLIC_URL,
        'limit': 60,
        'media_type': 'image,video',
        'sort': '-created',  # новые первыми
    }

    try:
        resp = requests.get(f'{YANDEX_API_BASE}/public/resources', params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        items = []
        for item in data.get('_embedded', {}).get('items', []):
            preview_url = item.get('preview', item.get('file'))
            original_url = item.get('file')
            media_type = item.get('media_type')

            if preview_url:
                items.append({
                    'preview': preview_url,
                    'original': original_url,
                    'type': media_type,
                    'name': item.get('name', 'Media'),
                })

        cache['data'] = items
        cache['timestamp'] = now
        return items

    except requests.RequestException as e:
        print(f'[Яндекс API] Ошибка: {e}')
        return cache['data']  # graceful degradation


def upload_to_yandex_disk(file_bytes: bytes, filename: str) -> dict:
    """
    Загружает файл в папку Яндекс Диска через OAuth.
    Требует YANDEX_OAUTH_TOKEN в .env.
    Возвращает {'success': True} или {'success': False, 'error': '...'}.
    """
    if not YANDEX_OAUTH_TOKEN:
        return {'success': False, 'error': 'YANDEX_OAUTH_TOKEN не задан в .env'}

    headers = {'Authorization': f'OAuth {YANDEX_OAUTH_TOKEN}'}
    remote_path = f'{UPLOAD_FOLDER_PATH}/{filename}'

    # 1. Убедимся, что папка существует
    folders = UPLOAD_FOLDER_PATH.split('/')
    current = ''
    for folder in folders:
        if not folder:
            continue
        current += f'/{folder}'
        requests.put(
            f'{YANDEX_API_BASE}/resources',
            headers=headers,
            params={'path': current},
            timeout=10,
        )

    # 2. Запросить ссылку для загрузки
    try:
        link_resp = requests.get(
            f'{YANDEX_API_BASE}/resources/upload',
            headers=headers,
            params={'path': remote_path, 'overwrite': 'false'},
            timeout=10,
        )
        if link_resp.status_code == 409:
            # Файл уже существует — добавим timestamp к имени
            name, ext = os.path.splitext(filename)
            filename = f'{name}_{int(time.time())}{ext}'
            remote_path = f'{UPLOAD_FOLDER_PATH}/{filename}'
            link_resp = requests.get(
                f'{YANDEX_API_BASE}/resources/upload',
                headers=headers,
                params={'path': remote_path, 'overwrite': 'false'},
                timeout=10,
            )
        link_resp.raise_for_status()
        upload_url = link_resp.json()['href']

    except requests.RequestException as e:
        return {'success': False, 'error': f'Не удалось получить ссылку загрузки: {e}'}

    # 3. Загрузить файл
    try:
        put_resp = requests.put(upload_url, data=file_bytes, timeout=120)
        put_resp.raise_for_status()
        return {'success': True}
    except requests.RequestException as e:
        return {'success': False, 'error': f'Ошибка загрузки файла: {e}'}


# ───────────────────────────────────────────────
# Роуты
# ───────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/gallery')
def gallery_api():
    """Список фото/видео из публичной папки."""
    data = fetch_yandex_disk_files()
    return jsonify({'success': True, 'items': data})


@app.route('/api/upload', methods=['POST'])
def upload_api():
    """
    Принимает файл от гостя и загружает его на Яндекс Диск.
    Гостю не нужен аккаунт — загрузка идёт через серверный OAuth-токен.
    """
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Файл не найден в запросе'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'success': False, 'error': 'Имя файла пустое'}), 400

    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'Недопустимый тип файла'}), 400

    filename = secure_filename(file.filename)
    file_bytes = file.read()

    result = upload_to_yandex_disk(file_bytes, filename)

    if result['success']:
        # Инвалидируем кэш, чтобы новый файл появился в галерее
        cache['timestamp'] = 0
        return jsonify({'success': True, 'message': 'Файл успешно загружен!'})
    else:
        return jsonify(result), 500


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)