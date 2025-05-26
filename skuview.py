import requests
import json
from datetime import datetime

def get_product_info(article_id):
    """Получение информации о товаре по артикулу с API Wildberries"""
    
    # URL для запроса информации о товаре
    url = f"https://card.wb.ru/cards/detail?appType=0&curr=rub&dest=-1257786&spp=30&nm={article_id}"
    
    try:
        # Выполняем запрос к API
        response = requests.get(url)
        response.raise_for_status()
        
        # Парсим ответ в JSON
        data = response.json()
        
        # Проверяем, что продукт найден
        if not data.get('data') or not data['data'].get('products') or len(data['data']['products']) == 0:
            return {"error": "Товар не найден"}
        
        # Получаем данные о первом продукте (всегда должен быть один, т.к. запрос по конкретному артикулу)
        product = data['data']['products'][0]
        
        return product
    
    except requests.exceptions.RequestException as e:
        return {"error": f"Ошибка при запросе: {str(e)}"}
    except json.JSONDecodeError:
        return {"error": "Ошибка при парсинге ответа"}
    except Exception as e:
        return {"error": f"Непредвиденная ошибка: {str(e)}"}

def generate_image_url(article_id):
    """Генерация URL изображения товара на основе артикула"""
    
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

def format_product_info(product):
    """Форматирование информации о товаре для отображения в текстовом виде"""
    
    if "error" in product:
        return f"ОШИБКА: {product['error']}"
    
    # Форматируем основную информацию
    result = []
    result.append("=" * 50)
    result.append("ОСНОВНАЯ ИНФОРМАЦИЯ О ТОВАРЕ")
    result.append("=" * 50)
    result.append(f"Артикул: {product['id']}")
    result.append(f"Название: {product['name']}")
    result.append(f"Бренд: {product['brand']}")
    result.append(f"Продавец: {product['supplier']} (рейтинг: {product.get('supplierRating', 'н/д')})")
    
    # Генерируем и добавляем ссылку на изображение
    image_url = generate_image_url(product['id'])
    result.append(f"Изображение: {image_url}")
    
    # Форматируем цены
    result.append("\n" + "=" * 50)
    result.append("ИНФОРМАЦИЯ О ЦЕНАХ")
    result.append("=" * 50)
    sale_price = product['salePriceU'] / 100 if 'salePriceU' in product else 0
    original_price = product['priceU'] / 100 if 'priceU' in product else 0
    discount = product.get('sale', 0)
    
    result.append(f"Текущая цена: {sale_price:.2f} ₽")
    result.append(f"Оригинальная цена: {original_price:.2f} ₽")
    result.append(f"Скидка: {discount}%")
    
    # Рейтинги и отзывы
    result.append("\n" + "=" * 50)
    result.append("РЕЙТИНГИ И ОТЗЫВЫ")
    result.append("=" * 50)
    result.append(f"Рейтинг товара: {product.get('reviewRating', 'н/д')} ★")
    result.append(f"Количество отзывов: {product.get('feedbacks', 0)}")
    
    # Анализируем наличие и склады
    result.append("\n" + "=" * 50)
    result.append("НАЛИЧИЕ И СКЛАДЫ")
    result.append("=" * 50)
    
    if 'sizes' not in product or not product['sizes']:
        result.append("Нет данных о размерах и остатках")
        return "\n".join(result)
    
    # Агрегируем данные по размерам и складам
    total_quantity = 0
    total_fbw = 0
    total_fbs = 0
    
    warehouse_data = {}
    size_data = {}
    
    for size in product['sizes']:
        size_name = size.get('name') or size.get('origName') or 'Без размера'
        
        if size_name not in size_data:
            size_data[size_name] = 0
        
        if 'stocks' in size and size['stocks']:
            for stock in size['stocks']:
                qty = stock.get('qty', 0)
                total_quantity += qty
                
                if stock.get('dtype') == 4:
                    total_fbw += qty
                else:
                    total_fbs += qty
                
                size_data[size_name] += qty
                
                # Информация о складе
                wh_id = stock.get('wh', 'Неизвестный склад')
                if wh_id not in warehouse_data:
                    warehouse_data[wh_id] = {
                        'total': 0,
                        'sizes': {},
                        'delivery_time': stock.get('time2', 0)
                    }
                
                warehouse_data[wh_id]['total'] += qty
                
                if size_name not in warehouse_data[wh_id]['sizes']:
                    warehouse_data[wh_id]['sizes'][size_name] = 0
                
                warehouse_data[wh_id]['sizes'][size_name] += qty
    
    # Выводим общую информацию о количестве
    result.append(f"Всего товаров: {total_quantity} шт.")
    result.append(f"FBW (со склада WB): {total_fbw} шт.")
    result.append(f"FBS (от продавца): {total_fbs} шт.")
    
    # Распределение по размерам
    result.append("\n-- Распределение по размерам --")
    for size_name, qty in size_data.items():
        percentage = round((qty / total_quantity) * 100) if total_quantity else 0
        result.append(f"{size_name}: {qty} шт. ({percentage}%)")
    
    # Топ складов по количеству
    result.append("\n-- Распределение по складам --")
    sorted_warehouses = sorted(warehouse_data.items(), key=lambda x: x[1]['total'], reverse=True)
    
    for wh_id, data in sorted_warehouses[:10]:  # Показываем только топ-10 складов
        percentage = round((data['total'] / total_quantity) * 100) if total_quantity else 0
        result.append(f"Склад {wh_id}: {data['total']} шт. ({percentage}%) - Время доставки: {data['delivery_time']} ч.")
    
    # Информация о логистике
    result.append("\n" + "=" * 50)
    result.append("ЛОГИСТИКА")
    result.append("=" * 50)
    
    # Находим склад с минимальным временем доставки
    min_delivery_warehouse = None
    min_total_time = float('inf')
    
    for size in product['sizes']:
        if 'stocks' in size and size['stocks']:
            for stock in size['stocks']:
                total_time = stock.get('time1', 0) + stock.get('time2', 0)
                if total_time < min_total_time:
                    min_total_time = total_time
                    min_delivery_warehouse = stock
    
    if min_delivery_warehouse:
        result.append(f"Метод доставки: {'FBW (со склада WB)' if min_delivery_warehouse.get('dtype') == 4 else 'FBS (от продавца)'}")
        result.append(f"Время сборки: {min_delivery_warehouse.get('time1', 0)} ч.")
        result.append(f"Время доставки: {min_delivery_warehouse.get('time2', 0)} ч.")
        result.append(f"Общее время: {min_delivery_warehouse.get('time1', 0) + min_delivery_warehouse.get('time2', 0)} ч.")
    else:
        result.append("Нет данных о логистике")
    
    # Ссылка на товар на сайте
    result.append("\n" + "=" * 50)
    result.append("ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ")
    result.append("=" * 50)
    result.append(f"Ссылка на товар: https://www.wildberries.ru/catalog/{product['id']}/detail.aspx")
    result.append(f"Данные получены: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    
    return "\n".join(result)

def main():
    """Основная функция для взаимодействия с пользователем"""
    
    print("WB Аналитика (консольная версия)")
    print("Введите артикул товара Wildberries для получения информации")
    print("Для выхода введите 'exit' или 'q'\n")
    
    while True:
        article = input("Введите артикул: ").strip()
        
        if article.lower() in ['exit', 'q', 'выход']:
            print("Работа программы завершена.")
            break
        
        if not article.isdigit():
            print("Ошибка: Артикул должен содержать только цифры")
            continue
        
        print("\nПолучение информации о товаре...")
        product = get_product_info(article)
        info = format_product_info(product)
        
        print(info)
        print("\n" + "-" * 70 + "\n")

if __name__ == "__main__":
    main()