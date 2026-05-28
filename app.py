import os
import time
import requests
from typing import Dict, List, Any
from flask import Flask, render_template, jsonify
from dotenv import load_dotenv

# Инициализация конфигурации
load_dotenv()

app = Flask(__name__)

# Константы API Яндекса
YANDEX_PUBLIC_URL = os.getenv('YANDEX_PUBLIC_URL', 'https://disk.yandex.ru/d/GIXFpB9WYoReyA')
YANDEX_API_ENDPOINT = 'https://cloud-api.yandex.net/v1/disk/public/resources'

# Глобальный In-Memory кэш
cache: Dict[str, Any] = {
    'data': [],
    'timestamp': 0.0
}
CACHE_TTL_SECONDS = 300  # Время жизни кэша


def fetch_yandex_disk_files() -> List[Dict[str, str]]:
    """
    Запрашивает список файлов из публичной папки Яндекс.Диска.
    Возвращает отформатированный список словарей с превью и ссылками на оригиналы.
    """
    current_time = time.time()

    # Возвращаем данные из кэша, если он еще валиден
    if cache['data'] and (current_time - cache['timestamp'] < CACHE_TTL_SECONDS):
        return cache['data']

    params = {
        'public_key': YANDEX_PUBLIC_URL,
        'limit': 60,  # Ограничиваем выгрузку последними 60 файлами
        'media_type': 'image,video',
        'sort': 'random'  # Новые файлы появляются первыми -created
    }

    try:
        response = requests.get(YANDEX_API_ENDPOINT, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        items = []
        for item in data.get('_embedded', {}).get('items', []):
            # Извлекаем превью (для оптимизации) и оригинал
            preview_url = item.get('preview', item.get('file'))
            original_url = item.get('file')
            media_type = item.get('media_type')

            if preview_url:
                items.append({
                    'preview': preview_url,
                    'original': original_url,
                    'type': media_type,
                    'name': item.get('name', 'Media')
                })

        # Атомарное обновление кэша
        cache['data'] = items
        cache['timestamp'] = current_time
        return items

    except requests.RequestException as e:
        print(f"Ошибка интеграции с Yandex API: {e}")
        # Graceful degradation: отдаем старый кэш в случае падения Яндекса
        return cache['data']


@app.route('/')
def index():
    """Рендеринг главной страницы."""
    return render_template('index.html')


@app.route('/api/gallery')
def gallery_api():
    """API endpoint для фронтенда."""
    data = fetch_yandex_disk_files()
    return jsonify({'success': True, 'items': data})


if __name__ == '__main__':
    # Production запуск должен осуществляться через Gunicorn
    app.run(debug=False, host='0.0.0.0', port=5000)