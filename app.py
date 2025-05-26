from flask import Flask, jsonify, request, render_template
import logging
from logging.handlers import RotatingFileHandler
import os

# Импорт сервисов
from services.product_service import get_product_details
from services.position_service import (
    search_product_position, 
    setup_tracking_job,
    get_position_history_data,
    get_active_tracking_jobs,
    stop_tracking_job
)

# Создание и настройка приложения
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # Для корректного отображения кириллицы
app.config['JSON_SORT_KEYS'] = False  # Сохраняем порядок ключей в JSON

# Настройка логирования
if not os.path.exists('logs'):
    os.makedirs('logs')

file_handler = RotatingFileHandler('logs/wildberries_api.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('Wildberries API запущен')

# Инициализация директорий для хранения данных
os.makedirs("reports", exist_ok=True)
os.makedirs("data", exist_ok=True)

# API маршруты

@app.route('/')
def index():
    """Главная страница API с документацией"""
    return render_template('index.html')

# API для получения информации о товаре
@app.route('/api/product/<article_id>', methods=['GET'])
def get_product(article_id):
    """Получение детальной информации о товаре по артикулу"""
    try:
        product_info = get_product_details(article_id)
        return jsonify(product_info)
    except Exception as e:
        app.logger.error(f"Ошибка при получении информации о товаре {article_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

# API для поиска позиции товара
@app.route('/api/position', methods=['GET'])
def get_position():
    """Поиск позиции товара в выдаче по запросу"""
    sku = request.args.get('sku')
    query = request.args.get('query')
    max_pages = int(request.args.get('max_pages', 10))
    
    if not sku or not query:
        return jsonify({"error": "Необходимо указать параметры sku и query"}), 400
    
    try:
        result = search_product_position(query, sku, max_pages)
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Ошибка при поиске позиции товара {sku} по запросу '{query}': {str(e)}")
        return jsonify({"error": str(e)}), 500

# API для настройки отслеживания позиции
@app.route('/api/tracking', methods=['POST'])
def setup_tracking():
    """Настройка отслеживания позиции товара с заданным интервалом"""
    data = request.json
    
    if not data:
        return jsonify({"error": "Необходимо предоставить данные в формате JSON"}), 400
    
    sku = data.get('sku')
    query = data.get('query')
    interval = int(data.get('interval', 60))
    interval_type = data.get('interval_type', 'minutes')
    max_pages = int(data.get('max_pages', 10))
    
    if not sku or not query:
        return jsonify({"error": "Необходимо указать параметры sku и query"}), 400
    
    if interval_type not in ['minutes', 'hours']:
        return jsonify({"error": "interval_type должен быть 'minutes' или 'hours'"}), 400
    
    try:
        tracking_id = setup_tracking_job(query, sku, interval, interval_type, max_pages)
        return jsonify({
            "success": True,
            "tracking_id": tracking_id,
            "message": f"Отслеживание настроено с интервалом {interval} {interval_type}"
        })
    except Exception as e:
        app.logger.error(f"Ошибка при настройке отслеживания для {sku}: {str(e)}")
        return jsonify({"error": str(e)}), 500

# API для получения истории позиций
@app.route('/api/history', methods=['GET'])
def get_history():
    """Получение истории позиций товара"""
    sku = request.args.get('sku')
    query = request.args.get('query')
    days = int(request.args.get('days', 30))
    
    if not sku:
        return jsonify({"error": "Необходимо указать параметр sku"}), 400
    
    try:
        history_data = get_position_history_data(sku, query, days)
        return jsonify(history_data)
    except Exception as e:
        app.logger.error(f"Ошибка при получении истории для {sku}: {str(e)}")
        return jsonify({"error": str(e)}), 500

# API для получения списка активных отслеживаний
@app.route('/api/tracking', methods=['GET'])
def get_tracking_jobs():
    """Получение списка активных задач отслеживания"""
    try:
        jobs = get_active_tracking_jobs()
        return jsonify({
            "total_jobs": len(jobs),
            "jobs": jobs
        })
    except Exception as e:
        app.logger.error(f"Ошибка при получении списка отслеживаний: {str(e)}")
        return jsonify({"error": str(e)}), 500

# API для остановки отслеживания
@app.route('/api/tracking/<tracking_id>', methods=['DELETE'])
def stop_tracking(tracking_id):
    """Остановка задачи отслеживания по ID"""
    try:
        result = stop_tracking_job(tracking_id)
        if result:
            return jsonify({
                "success": True,
                "message": f"Отслеживание {tracking_id} остановлено"
            })
        else:
            return jsonify({
                "success": False,
                "message": f"Отслеживание {tracking_id} не найдено или уже остановлено"
            }), 404
    except Exception as e:
        app.logger.error(f"Ошибка при остановке отслеживания {tracking_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 