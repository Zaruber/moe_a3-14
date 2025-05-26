import requests
import json
import csv
import os
import pandas as pd
import uuid
from datetime import datetime, timedelta
import threading
import schedule
import time

# Словарь активных задач отслеживания
tracking_jobs = {}

def search_wildberries(query, page=1):
    """
    Выполняет поисковый запрос к API Wildberries
    
    Args:
        query (str): Поисковый запрос
        page (int): Номер страницы (по умолчанию 1)
        
    Returns:
        dict: Результаты поиска в формате JSON
    """
    url = f"https://search.wb.ru/exactmatch/ru/common/v13/search"
    params = {
        "ab_old_spell": "oct",
        "appType": "64",
        "curr": "rub",
        "dest": "-1257786",
        "hide_dtype": "13",
        "lang": "ru",
        "locale": "ru",
        "page": page,
        "query": query,
        "resultset": "catalog",
        "sort": "popular"
    }
    
    headers = {
        "Accept": "*/*",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Origin": "https://www.wildberries.ru",
        "Pragma": "no-cache",
        "Referer": "https://www.wildberries.ru/catalog/0/search.aspx",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise Exception(f"Ошибка при запросе к API поиска: {str(e)}")

def find_product_by_sku(data, target_sku):
    """
    Ищет товар с заданным SKU в данных
    
    Args:
        data (dict): Данные поисковой выдачи
        target_sku (str): Искомый артикул товара
        
    Returns:
        tuple: Кортеж (товар, позиция) или (None, 0) если товар не найден
    """
    if not data or 'data' not in data or 'products' not in data['data']:
        return None, 0
    
    products = data['data']['products']
    
    for index, product in enumerate(products):
        sku = str(product.get('id', ''))
        if sku == str(target_sku):
            return product, index + 1
    
    return None, 0

def search_product_position(query, target_sku, max_pages=10):
    """
    Ищет позицию товара с заданным SKU в поисковой выдаче
    
    Args:
        query (str): Поисковый запрос
        target_sku (str): Артикул товара
        max_pages (int): Максимальное количество страниц для поиска
        
    Returns:
        dict: Результат поиска с информацией о позиции товара
    """
    # Валидация входных данных
    try:
        target_sku = str(int(target_sku))  # Проверка, что это число
    except ValueError:
        raise ValueError("Артикул должен быть числом")
    
    if not query or not query.strip():
        raise ValueError("Поисковый запрос не может быть пустым")
    
    result = {
        "query": query,
        "sku": target_sku,
        "found": False,
        "timestamp": datetime.now().isoformat()
    }
    
    for page in range(1, max_pages + 1):
        search_data = search_wildberries(query, page)
        
        if not search_data:
            continue
            
        product, position_on_page = find_product_by_sku(search_data, target_sku)
        
        if product:
            # Сохраняем найденный товар и его позицию
            global_position = (page-1)*100 + position_on_page
            
            # Базовая информация о позиции
            result["found"] = True
            result["page"] = page
            result["position_on_page"] = position_on_page
            result["global_position"] = global_position
            
            # Анализ рекламной информации
            has_ads = 'log' in product and product['log']
            result["is_advertised"] = has_ads
            
            if has_ads:
                ad_log = product['log']
                
                # Тип рекламы
                if ad_log.get('tp') == 'c':
                    result["ad_type"] = "Аукцион"
                elif ad_log.get('tp') == 'b':
                    result["ad_type"] = "АРК"
                else:
                    result["ad_type"] = "Неизвестный"
                
                # Органическая и рекламная позиции
                result["organic_position"] = ad_log.get('position', '')
                result["promo_position"] = ad_log.get('promoPosition', '')
                
                # CPM и стоимость буста
                if 'cpm' in ad_log:
                    result["cpm"] = ad_log['cpm']
                    
                    # Расчет стоимости буста если есть обе позиции
                    if result["organic_position"] and result["promo_position"]:
                        position_diff = abs(int(result["organic_position"]) - int(result["promo_position"]))
                        if position_diff > 0:
                            result["boost_cost"] = float(ad_log['cpm']) / position_diff
            
            # Информация о цене
            if 'salePriceU' in product:
                result["price"] = product['salePriceU'] / 100
            elif 'sizes' in product and len(product['sizes']) > 0:
                first_size = product['sizes'][0]
                if 'price' in first_size:
                    if 'total' in first_size['price']:
                        result["price"] = first_size['price']['total'] / 100
                    elif 'basic' in first_size['price']:
                        result["price"] = first_size['price']['basic'] / 100
            
            # Основная информация о товаре
            result["brand"] = product.get('brand', '')
            result["name"] = product.get('name', '')
            
            # Сохраняем данные о позиции в CSV
            save_position_to_csv(
                sku=target_sku,
                query=query,
                organic_position=result.get("organic_position"),
                promo_position=result.get("promo_position"),
                price=result.get("price"),
                cpm=result.get("cpm"),
                ad_type=result.get("ad_type", "Органика"),
                page=page,
                position_on_page=position_on_page,
                boost_cost=result.get("boost_cost")
            )
            
            return result
    
    # Товар не найден
    return result

def save_position_to_csv(sku, query, organic_position, promo_position, price, cpm, ad_type, page, position_on_page, boost_cost):
    """
    Сохраняет данные о позиции товара в CSV файл
    
    Args:
        sku (str): Артикул товара
        query (str): Поисковый запрос
        organic_position (str): Органическая позиция
        promo_position (str): Рекламная позиция
        price (float): Цена товара
        cpm (str): CPM
        ad_type (str): Тип рекламы
        page (int): Страница
        position_on_page (int): Позиция на странице
        boost_cost (float): Стоимость буста
        
    Returns:
        bool: True в случае успеха, False в случае ошибки
    """
    # Проверяем существование директории
    os.makedirs("data", exist_ok=True)
    
    timestamp = datetime.now()
    filename = f"data/positions_{sku}.csv"
    file_exists = os.path.isfile(filename)
    
    try:
        with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['timestamp', 'sku', 'query', 'organic_position', 'promo_position', 
                          'price', 'cpm', 'ad_type', 'page', 'position_on_page', 'boost_cost']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
            
            writer.writerow({
                'timestamp': timestamp,
                'sku': sku,
                'query': query,
                'organic_position': organic_position,
                'promo_position': promo_position,
                'price': price,
                'cpm': cpm,
                'ad_type': ad_type,
                'page': page,
                'position_on_page': position_on_page,
                'boost_cost': boost_cost
            })
            return True
    except Exception as e:
        raise Exception(f"Ошибка при сохранении данных в CSV: {str(e)}")

def get_position_history_data(sku, query=None, days=30):
    """
    Получает историю позиций товара из CSV файлов
    
    Args:
        sku (str): Артикул товара
        query (str, optional): Поисковый запрос
        days (int): Количество дней для выборки (по умолчанию 30)
        
    Returns:
        dict: Данные истории позиций
    """
    filename = f"data/positions_{sku}.csv"
    if not os.path.isfile(filename):
        return {"error": "История позиций не найдена"}
    
    try:
        # Загружаем данные из CSV
        df = pd.read_csv(filename, parse_dates=['timestamp'])
        
        # Фильтруем по дате
        date_limit = datetime.now() - timedelta(days=days)
        df = df[df['timestamp'] > date_limit]
        
        # Фильтруем по запросу, если указан
        if query:
            df = df[df['query'] == query]
        
        if df.empty:
            return {"error": "Нет данных за указанный период"}
        
        # Преобразуем DataFrame в список словарей для ответа API
        records = []
        
        for _, row in df.iterrows():
            record = {
                'timestamp': row['timestamp'].isoformat(),
                'sku': row['sku'],
                'query': row['query'],
                'organic_position': row['organic_position'],
                'promo_position': row['promo_position'],
                'price': row['price'],
                'cpm': row['cpm'],
                'ad_type': row['ad_type'],
                'page': row['page'],
                'position_on_page': row['position_on_page'],
                'boost_cost': row['boost_cost']
            }
            records.append(record)
        
        # Формируем статистику
        stats = {
            'min_organic_position': df['organic_position'].min() if 'organic_position' in df.columns and not df['organic_position'].isna().all() else None,
            'max_organic_position': df['organic_position'].max() if 'organic_position' in df.columns and not df['organic_position'].isna().all() else None,
            'min_price': df['price'].min() if 'price' in df.columns and not df['price'].isna().all() else None,
            'max_price': df['price'].max() if 'price' in df.columns and not df['price'].isna().all() else None,
            'avg_cpm': df['cpm'].mean() if 'cpm' in df.columns and not df['cpm'].isna().all() else None,
            'records_count': len(df)
        }
        
        return {
            'sku': sku,
            'query': query,
            'days': days,
            'stats': stats,
            'records': records
        }
    except Exception as e:
        raise Exception(f"Ошибка при получении истории позиций: {str(e)}")

def setup_tracking_job(query, sku, interval=60, interval_type="minutes", max_pages=10):
    """
    Настраивает регулярное отслеживание позиций товара
    
    Args:
        query (str): Поисковый запрос
        sku (str): Артикул товара
        interval (int): Интервал отслеживания
        interval_type (str): Тип интервала ("minutes" или "hours")
        max_pages (int): Максимальное количество страниц для поиска
        
    Returns:
        str: Идентификатор задачи отслеживания
    """
    # Создаем уникальный идентификатор для задачи
    tracking_id = str(uuid.uuid4())
    
    # Функция для выполнения отслеживания
    def tracking_job():
        try:
            search_product_position(query, sku, max_pages)
        except Exception as e:
            print(f"Ошибка при отслеживании позиции {sku}: {str(e)}")
    
    # Настраиваем расписание
    if interval_type == "minutes":
        if interval < 1:
            interval = 1  # Минимальный интервал - 1 минута
        job = schedule.every(interval).minutes.do(tracking_job)
    else:
        job = schedule.every(interval).hours.do(tracking_job)
    
    # Запускаем первое отслеживание сразу
    tracking_job()
    
    # Сохраняем информацию о задаче
    tracking_jobs[tracking_id] = {
        'job': job,
        'query': query,
        'sku': sku,
        'interval': interval,
        'interval_type': interval_type,
        'max_pages': max_pages,
        'start_time': datetime.now().isoformat(),
        'active': True
    }
    
    # Запускаем отдельный поток для выполнения задач по расписанию, если это первая задача
    if len(tracking_jobs) == 1:
        thread = threading.Thread(target=run_scheduler, daemon=True)
        thread.start()
    
    return tracking_id

def run_scheduler():
    """
    Запускает бесконечный цикл планировщика для выполнения отложенных задач
    """
    while True:
        schedule.run_pending()
        time.sleep(10)  # Проверяем расписание каждые 10 секунд

def get_active_tracking_jobs():
    """
    Возвращает список активных задач отслеживания
    
    Returns:
        list: Список активных задач
    """
    result = []
    
    for tracking_id, job_info in tracking_jobs.items():
        if job_info['active']:
            result.append({
                'tracking_id': tracking_id,
                'query': job_info['query'],
                'sku': job_info['sku'],
                'interval': job_info['interval'],
                'interval_type': job_info['interval_type'],
                'start_time': job_info['start_time']
            })
    
    return result

def stop_tracking_job(tracking_id):
    """
    Останавливает задачу отслеживания по ID
    
    Args:
        tracking_id (str): Идентификатор задачи
        
    Returns:
        bool: True если задача остановлена, False если задача не найдена
    """
    if tracking_id in tracking_jobs and tracking_jobs[tracking_id]['active']:
        schedule.cancel_job(tracking_jobs[tracking_id]['job'])
        tracking_jobs[tracking_id]['active'] = False
        return True
    
    return False 