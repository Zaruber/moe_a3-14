import requests
import json
from datetime import datetime

def get_product_details(article_id):
    """
    Получение детальной информации о товаре по артикулу
    
    Args:
        article_id (str): Артикул товара на Wildberries
        
    Returns:
        dict: Словарь с детальной информацией о товаре
    """
    # Валидация входных данных
    try:
        article_id = str(int(article_id))  # Проверка, что это число
    except ValueError:
        raise ValueError("Артикул должен быть числом")
    
    # URL для запроса информации о товаре
    url = f"https://card.wb.ru/cards/detail?appType=0&curr=rub&dest=-1257786&spp=30&nm={article_id}"
    
    try:
        # Выполняем запрос к API
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Парсим ответ в JSON
        data = response.json()
        
        # Проверяем, что продукт найден
        if not data.get('data') or not data['data'].get('products') or len(data['data']['products']) == 0:
            return {"error": "Товар не найден"}
        
        # Получаем данные о первом продукте (всегда должен быть один, т.к. запрос по конкретному артикулу)
        product = data['data']['products'][0]
        
        # Формируем и возвращаем обогащенный объект товара
        return format_product_data(product)
    
    except requests.exceptions.RequestException as e:
        raise Exception(f"Ошибка при запросе к API: {str(e)}")
    except json.JSONDecodeError:
        raise Exception("Ошибка при парсинге ответа")
    except Exception as e:
        raise Exception(f"Непредвиденная ошибка: {str(e)}")

def generate_image_url(article_id):
    """
    Генерация URL изображения товара на основе артикула
    
    Args:
        article_id (str): Артикул товара
        
    Returns:
        str: URL изображения товара
    """
    article_id = int(article_id)
    vol = article_id // 100000
    part = article_id // 1000
    
    # Определяем номер корзины по алгоритму Wildberries
    if vol <= 143:
        basket = "01"
    elif vol <= 287:
        basket = "02"
    elif vol <= 431:
        basket = "03"
    elif vol <= 719:
        basket = "04"
    elif vol <= 1007:
        basket = "05"
    elif vol <= 1061:
        basket = "06"
    elif vol <= 1115:
        basket = "07"
    elif vol <= 1169:
        basket = "08"
    elif vol <= 1313:
        basket = "09"
    elif vol <= 1601:
        basket = "10"
    elif vol <= 1655:
        basket = "11"
    elif vol <= 1919:
        basket = "12"
    elif vol <= 2045:
        basket = "13"
    elif vol <= 2189:
        basket = "14"
    elif vol <= 2405:
        basket = "15"
    elif vol <= 2621:
        basket = "16"
    elif vol <= 2837:
        basket = "17"
    elif vol <= 3053:
        basket = "18"
    elif vol <= 3269:
        basket = "19"
    elif vol <= 3485:
        basket = "20"
    elif vol <= 3701:
        basket = "21"
    else:
        basket = "22"
    
    # Формируем URL изображения
    return f"https://basket-{basket}.wbbasket.ru/vol{vol}/part{part}/{article_id}/images/big/1.webp"

def format_product_data(product):
    """
    Форматирование и обогащение данных товара
    
    Args:
        product (dict): Сырые данные о товаре от API
        
    Returns:
        dict: Обогащенный и структурированный словарь с данными о товаре
    """
    if "error" in product:
        return product
    
    # Базовая информация
    result = {
        "id": product.get('id'),
        "name": product.get('name'),
        "brand": product.get('brand'),
        "supplier": product.get('supplier'),
        "supplierRating": product.get('supplierRating'),
        "image_url": generate_image_url(product.get('id')),
        "url": f"https://www.wildberries.ru/catalog/{product.get('id')}/detail.aspx",
    }
    
    # Цены и скидки
    sale_price = product.get('salePriceU', 0) / 100
    original_price = product.get('priceU', 0) / 100
    discount = product.get('sale', 0)
    
    result["prices"] = {
        "current": sale_price,
        "original": original_price,
        "discount": discount
    }
    
    # Рейтинги и отзывы
    result["ratings"] = {
        "rating": product.get('reviewRating'),
        "feedbacks": product.get('feedbacks', 0)
    }
    
    # Анализ наличия и складов
    if 'sizes' in product and product['sizes']:
        # Инициализация данных о наличии
        availability = {
            "total_quantity": 0,
            "fbw_quantity": 0,  # FBW (Wildberries)
            "fbs_quantity": 0,  # FBS (Продавец)
            "sizes": {},
            "warehouses": []
        }
        
        # Временные переменные для расчета
        warehouse_data = {}
        min_delivery_time = float('inf')
        fastest_delivery = None
        
        # Проходим по всем размерам
        for size in product['sizes']:
            size_name = size.get('name') or size.get('origName') or 'Без размера'
            
            if size_name not in availability["sizes"]:
                availability["sizes"][size_name] = 0
            
            # Анализ остатков на складах
            if 'stocks' in size and size['stocks']:
                for stock in size['stocks']:
                    qty = stock.get('qty', 0)
                    availability["total_quantity"] += qty
                    
                    # FBW или FBS
                    if stock.get('dtype') == 4:
                        availability["fbw_quantity"] += qty
                    else:
                        availability["fbs_quantity"] += qty
                    
                    # Количество по размерам
                    availability["sizes"][size_name] += qty
                    
                    # Информация о складе
                    wh_id = stock.get('wh', 'Неизвестный склад')
                    
                    if wh_id not in warehouse_data:
                        warehouse_data[wh_id] = {
                            'id': wh_id,
                            'total': 0,
                            'sizes': {},
                            'delivery_time': stock.get('time2', 0),
                            'preparation_time': stock.get('time1', 0)
                        }
                    
                    warehouse_data[wh_id]['total'] += qty
                    
                    if size_name not in warehouse_data[wh_id]['sizes']:
                        warehouse_data[wh_id]['sizes'][size_name] = 0
                    
                    warehouse_data[wh_id]['sizes'][size_name] += qty
                    
                    # Проверка минимального времени доставки
                    total_time = stock.get('time1', 0) + stock.get('time2', 0)
                    if total_time < min_delivery_time:
                        min_delivery_time = total_time
                        fastest_delivery = {
                            'type': 'FBW' if stock.get('dtype') == 4 else 'FBS',
                            'preparation_time': stock.get('time1', 0),
                            'delivery_time': stock.get('time2', 0),
                            'total_time': total_time
                        }
        
        # Сортируем склады по количеству товара
        availability["warehouses"] = sorted(
            warehouse_data.values(), 
            key=lambda x: x['total'], 
            reverse=True
        )
        
        result["availability"] = availability
        
        if fastest_delivery:
            result["logistics"] = fastest_delivery
    else:
        result["availability"] = {"total_quantity": 0}
    
    # Добавляем метаданные
    result["meta"] = {
        "timestamp": datetime.now().isoformat(),
        "api_version": "1.0"
    }
    
    return result 