import os
import time
import requests
from typing import Dict, List, Any
from flask import Flask, render_template, jsonify, request, Response, redirect
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

load_dotenv()

app = Flask(__name__)

# ───────────────────────────────────────────────
# Конфигурация
# ───────────────────────────────────────────────
YANDEX_PUBLIC_URL        = os.getenv('YANDEX_PUBLIC_URL',        'https://disk.yandex.ru/d/PDkGv3aF63URNg')
YANDEX_PUBLIC_URL_COUPLE = os.getenv('YANDEX_PUBLIC_URL_COUPLE', 'https://disk.yandex.ru/d/aPgFUXz2TFaYFA')
YANDEX_API_BASE          = 'https://cloud-api.yandex.net/v1/disk'
YANDEX_OAUTH_TOKEN       = os.getenv('YANDEX_OAUTH_TOKEN', '')
UPLOAD_FOLDER_PATH       = os.getenv('YANDEX_UPLOAD_FOLDER', '/Свадьба Ильи и Даши/Фото от гостей')

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'mp4', 'mov', 'avi', 'heic'}
MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # 200 МБ
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# ───────────────────────────────────────────────
# Кэш метаданных (НЕ кэшируем сами URL превью)
# Кэшируем только: имя файла, тип, размеры
# Свежие ссылки запрашиваем при каждом обращении
# ───────────────────────────────────────────────
_meta_cache: Dict[str, Any] = {}
CACHE_TTL = 120  # метаданные обновляем каждые 2 минуты


def _get_cache(url: str) -> Dict[str, Any]:
    if url not in _meta_cache:
        _meta_cache[url] = {'data': [], 'timestamp': 0.0}
    return _meta_cache[url]


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ───────────────────────────────────────────────
# Получение списка файлов (только метаданные)
# ───────────────────────────────────────────────
def fetch_file_list(public_url: str) -> List[Dict]:
    cache = _get_cache(public_url)
    now = time.time()
    if cache['data'] and (now - cache['timestamp'] < CACHE_TTL):
        return cache['data']

    headers = {}
    if YANDEX_OAUTH_TOKEN:
        headers['Authorization'] = f'OAuth {YANDEX_OAUTH_TOKEN}'

    params = {
        'public_key':  public_url,
        'limit':       60,
        'media_type':  'image,video',
        'sort':        '-created',
        'preview_size': 'M',
        'preview_crop': 'false',
    }

    try:
        resp = requests.get(f'{YANDEX_API_BASE}/public/resources', params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        items = []
        raw_items = data.get('_embedded', {}).get('items', [])

        for item in raw_items:
            if item.get('type') != 'file':
                continue

            media_type = item.get('media_type', '')
            if media_type not in ('image', 'video'):
                continue

            file_path = item.get('path', '')
            sizes     = item.get('sizes', [])
            orig_size = next((s for s in sizes if s.get('name') == 'ORIGINAL'), None)
            w = item.get('width')  or (orig_size.get('width')  if orig_size else None)
            h = item.get('height') or (orig_size.get('height') if orig_size else None)

            items.append({
                'name':       item.get('name', 'Media'),
                'type':       media_type,
                'width':      w,
                'height':     h,
                # thumb_api для сетки карусели (маленький размер M)
                'thumb_api':  f'/api/thumb?pub={requests.utils.quote(public_url)}&path={requests.utils.quote(file_path)}&size=M',
                # large_api для качественного отображения фото в лайтбоксе без скачивания тяжелого оригинала
                'large_api':  f'/api/thumb?pub={requests.utils.quote(public_url)}&path={requests.utils.quote(file_path)}&size=2048x2048',
                # orig_api используется для стриминга видео и скачивания оригиналов
                'orig_api':   f'/api/orig?pub={requests.utils.quote(public_url)}&path={requests.utils.quote(file_path)}',
            })

        cache['data']      = items
        cache['timestamp'] = now
        return items
    except requests.RequestException as e:
        print(f'[YaDisk] Ошибка запроса {public_url}: {e}')
        return cache['data']


# ───────────────────────────────────────────────
# Получение свежей ссылки на превью (вызывается при каждом запросе)
# ───────────────────────────────────────────────
def get_fresh_preview(public_url: str, file_path: str, size: str = 'M') -> str | None:
    """
    Запрашивает у Яндекс API свежую ссылку на превью конкретного файла с заданным размером.
    Поддерживаемые размеры: 'S', 'M', 'L', 'XL', 'XXL', 'XXXL' или точные грани, например '2048x2048'
    """
    headers = {}
    if YANDEX_OAUTH_TOKEN:
        headers['Authorization'] = f'OAuth {YANDEX_OAUTH_TOKEN}'

    params = {
        'public_key':   public_url,
        'path':         file_path,
        'preview_size': size,
    }

    try:
        resp = requests.get(
            f'{YANDEX_API_BASE}/public/resources',
            params=params,
            headers=headers,
            timeout=8
        )
        if resp.status_code == 200:
            data = resp.json()
            preview = data.get('preview')
            if preview:
                return preview
            return data.get('file')
    except requests.RequestException as e:
        print(f'[YaDisk] Ошибка получения превью {file_path}: {e}')
    return None


def get_fresh_download(public_url: str, file_path: str) -> str | None:
    """Запрашивает свежую прямую ссылку на файл."""
    headers = {}
    if YANDEX_OAUTH_TOKEN:
        headers['Authorization'] = f'OAuth {YANDEX_OAUTH_TOKEN}'

    try:
        resp = requests.get(
            f'{YANDEX_API_BASE}/public/resources/download',
            params={'public_key': public_url, 'path': file_path},
            headers=headers,
            timeout=8
        )
        if resp.status_code == 200:
            return resp.json().get('href')
    except requests.RequestException as e:
        print(f'[YaDisk] Ошибка получения download {file_path}: {e}')
    return None


# ───────────────────────────────────────────────
# Загрузка файлов на Яндекс Диск
# ───────────────────────────────────────────────
def upload_to_yandex_disk(file_bytes: bytes, filename: str) -> dict:
    if not YANDEX_OAUTH_TOKEN:
        return {'success': False, 'error': 'YANDEX_OAUTH_TOKEN не задан в .env'}

    headers     = {'Authorization': f'OAuth {YANDEX_OAUTH_TOKEN}'}
    remote_path = f'{UPLOAD_FOLDER_PATH}/{filename}'

    # Создаём папки если нет
    current = ''
    for folder in UPLOAD_FOLDER_PATH.split('/'):
        if not folder:
            continue
        current += f'/{folder}'
        requests.put(f'{YANDEX_API_BASE}/resources', headers=headers,
                     params={'path': current}, timeout=10)

    try:
        link_resp = requests.get(
            f'{YANDEX_API_BASE}/resources/upload',
            headers=headers,
            params={'path': remote_path, 'overwrite': 'false'},
            timeout=10,
        )
        if link_resp.status_code == 409:
            name, ext = os.path.splitext(filename)
            filename  = f'{name}_{int(time.time())}{ext}'
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
        return {'success': False, 'error': f'Ошибка получения ссылки: {e}'}

    try:
        put_resp = requests.put(upload_url, data=file_bytes, timeout=120)
        put_resp.raise_for_status()
        return {'success': True}
    except requests.RequestException as e:
        return {'success': False, 'error': f'Ошибка загрузки: {e}'}


# ═══════════════════════════════════════════════
# РОУТЫ
# ═══════════════════════════════════════════════

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/gallery')
def gallery_api():
    """Метаданные фото гостей. Живые ссылки — через /api/thumb."""
    data = fetch_file_list(YANDEX_PUBLIC_URL)
    return jsonify({'success': True, 'items': data})


@app.route('/api/gallery/couple')
def gallery_couple_api():
    """Метаданные фото пары. Живые ссылки — через /api/thumb."""
    data = fetch_file_list(YANDEX_PUBLIC_URL_COUPLE)
    return jsonify({'success': True, 'items': data})


@app.route('/api/thumb')
def thumb_proxy():
    pub_url   = request.args.get('pub', '')
    file_path = request.args.get('path', '')
    size      = request.args.get('size', 'M') # Принимаем динамический размер контента

    if not pub_url or not file_path:
        return 'Missing params', 400

    preview_url = get_fresh_preview(pub_url, file_path, size)
    if not preview_url:
        return 'Preview not available', 404

    headers = {}
    if YANDEX_OAUTH_TOKEN:
        headers['Authorization'] = f'OAuth {YANDEX_OAUTH_TOKEN}'

    try:
        r = requests.get(preview_url, headers=headers, timeout=15, stream=True)
        r.raise_for_status()
        content_type = r.headers.get('Content-Type', 'image/jpeg')
        return Response(
            r.content,
            status=200,
            headers={
                'Content-Type':  content_type,
                'Cache-Control': 'public, max-age=300',
            }
        )
    except requests.RequestException as e:
        print(f'[Thumb] Ошибка проксирования: {e}')
        return 'Thumbnail unavailable', 502


@app.route('/api/orig')
def orig_proxy():
    """
    Стабильный inline-прокси для видео и тяжелых медиафайлов.
    Корректно обрабатывает Range-запросы браузера без принудительного чанкирования,
    исключая появление серого экрана в плеере лайтбокса.
    """
    pub_url = request.args.get('pub', '')
    file_path = request.args.get('path', '')

    if not pub_url or not file_path:
        return 'Missing params', 400

    download_url = get_fresh_download(pub_url, file_path)
    if not download_url:
        return 'File not available', 404

    # Перенаправляем заголовок Range от браузера к серверам Яндекса
    headers = {}
    range_header = request.headers.get('Range', None)
    if range_header:
        headers['Range'] = range_header

    if YANDEX_OAUTH_TOKEN:
        headers['Authorization'] = f'OAuth {YANDEX_OAUTH_TOKEN}'

    try:
        # ВАЖНО: Не используем stream=True совместно с Response(iter_content),
        # чтобы избежать автоматической генерации Transfer-Encoding: chunked.
        yandex_resp = requests.get(download_url, headers=headers, timeout=15)

        # Переопределяем MIME-тип, если Яндекс отдал сырой бинарный octet-stream
        ext = file_path.split('.')[-1].lower()
        content_type = yandex_resp.headers.get('Content-Type', '')

        if 'octet-stream' in content_type or not content_type:
            if ext == 'mp4':
                content_type = 'video/mp4'
            elif ext in ['mov', 'qt']:
                content_type = 'video/quicktime'
            elif ext == 'avi':
                content_type = 'video/x-msvideo'
            elif ext in ['jpg', 'jpeg']:
                content_type = 'image/jpeg'
            elif ext == 'png':
                content_type = 'image/png'
            else:
                content_type = 'video/mp4'  # Дефолтный фолбек для видео плеера

        # Формируем строгие заголовки ответа согласно спецификации HTTP 206 / 200
        resp_headers = {
            'Content-Type': content_type,
            'Content-Disposition': 'inline',
            'Accept-Ranges': 'bytes'
        }

        # Пробрасываем оригинальные параметры позиционирования байт
        if 'Content-Range' in yandex_resp.headers:
            resp_headers['Content-Range'] = yandex_resp.headers['Content-Range']
        if 'Content-Length' in yandex_resp.headers:
            resp_headers['Content-Length'] = yandex_resp.headers['Content-Length']

        # Возвращаем фиксированный бинарный контент с сохранением оригинального статус-кода (200 или 206)
        return Response(
            yandex_resp.content,
            status=yandex_resp.status_code,
            headers=resp_headers
        )

    except requests.RequestException as e:
        print(f'[Orig Proxy] Ошибка трансляции медиапотока: {e}')
        return 'Error streaming file', 502


@app.route('/api/debug')
def debug_api():
    """Диагностика — открой в браузере чтобы проверить конфиг. Удали после отладки."""
    result = {
        'config': {
            'YANDEX_PUBLIC_URL':        YANDEX_PUBLIC_URL,
            'YANDEX_PUBLIC_URL_COUPLE': YANDEX_PUBLIC_URL_COUPLE,
            'OAUTH_TOKEN_SET':          bool(YANDEX_OAUTH_TOKEN),
        },
        'galleries': {}
    }
    for name, url in [('guests', YANDEX_PUBLIC_URL), ('couple', YANDEX_PUBLIC_URL_COUPLE)]:
        headers = {}
        if YANDEX_OAUTH_TOKEN:
            headers['Authorization'] = f'OAuth {YANDEX_OAUTH_TOKEN}'
        try:
            resp      = requests.get(f'{YANDEX_API_BASE}/public/resources',
                                     params={'public_key': url, 'limit': 3,
                                             'media_type': 'image,video',
                                             'preview_size': 'XXL','preview_crop': 'false'},
                                     headers=headers, timeout=10)
            raw       = resp.json()
            raw_items = raw.get('_embedded', {}).get('items', [])
            result['galleries'][name] = {
                'http_status':       resp.status_code,
                'total_in_folder':   raw.get('_embedded', {}).get('total', 0),
                'fetched':           len(raw_items),
                'first_item_fields': list(raw_items[0].keys()) if raw_items else [],
                'has_preview_field': bool(raw_items[0].get('preview')) if raw_items else False,
                'has_file_field':    bool(raw_items[0].get('file'))    if raw_items else False,
                'has_path_field':    bool(raw_items[0].get('path'))    if raw_items else False,
            }
        except Exception as e:
            result['galleries'][name] = {'error': str(e)}
    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)