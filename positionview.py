import requests
import json
from tabulate import tabulate
import sys
from colorama import init, Fore, Style
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import seaborn as sns
import schedule
import time
import os
from datetime import datetime, timedelta
import csv

# Инициализация colorama для цветного вывода
init()

# Создание директории для графиков и отчетов
os.makedirs("reports", exist_ok=True)
os.makedirs("data", exist_ok=True)  # Директория для хранения данных о позициях

# Функция для сохранения данных в CSV файл вместо базы данных
def save_position_to_csv(sku, query, organic_position, promo_position, price, cpm, ad_type, page, position_on_page, boost_cost):
    """Сохраняет данные о позиции товара в CSV файл"""
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
        print(f"{Fore.RED}Ошибка при сохранении данных: {e}{Style.RESET_ALL}")
        return False

def get_position_history(sku, query=None, days=30):
    """Получает историю позиций товара из CSV файлов"""
    import pandas as pd
    
    filename = f"data/positions_{sku}.csv"
    if not os.path.isfile(filename):
        print(f"{Fore.RED}Файл с историей позиций не найден{Style.RESET_ALL}")
        return pd.DataFrame()
    
    try:
        # Загружаем данные из CSV
        df = pd.read_csv(filename, parse_dates=['timestamp'])
        
        # Фильтруем по дате
        date_limit = datetime.now() - timedelta(days=days)
        df = df[df['timestamp'] > date_limit]
        
        # Фильтруем по запросу, если указан
        if query:
            df = df[df['query'] == query]
        
        return df
    except Exception as e:
        print(f"{Fore.RED}Ошибка при получении истории позиций: {e}{Style.RESET_ALL}")
        return pd.DataFrame()

def get_ad_type(tp):
    """Определение типа рекламы по коду"""
    if tp == 'c':
        return 'Аукцион'
    elif tp == 'b':
        return 'АРК'
    else:
        return 'Органика'

def search_wildberries(query, page=1):
    """Выполняет поисковый запрос к API Wildberries"""
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
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Ошибка при запросе к API: {e}")
        return None

def find_product_by_sku(data, target_sku):
    """Ищет товар с заданным SKU в данных"""
    if not data or 'data' not in data or 'products' not in data['data']:
        return None, 0
    
    products = data['data']['products']
    total_products = len(products)
    
    for index, product in enumerate(products):
        sku = str(product.get('id', ''))
        if sku == str(target_sku):
            return product, index + 1
    
    return None, 0

def search_product_on_pages(query, target_sku, max_pages=10):
    """Ищет товар с заданным SKU на нескольких страницах выдачи"""
    print(f"\n{Fore.YELLOW}Поиск товара с артикулом {target_sku} по запросу '{query}'...{Style.RESET_ALL}")
    
    for page in range(1, max_pages + 1):
        print(f"Проверка страницы {page}...")
        result = search_wildberries(query, page)
        
        if not result:
            print(f"Не удалось получить данные со страницы {page}")
            continue
            
        product, position = find_product_by_sku(result, target_sku)
        
        if product:
            print(f"{Fore.GREEN}Товар найден на странице {page}, позиция {position}{Style.RESET_ALL}")
            
            # Сохраняем информацию о странице и позиции в объекте товара для дальнейшего использования
            product['page'] = page
            product['position_on_page'] = position
            product['global_position'] = (page-1)*100 + position
            
            return product, position, page
    
    print(f"{Fore.RED}Товар с артикулом {target_sku} не найден в первых {max_pages} страницах выдачи{Style.RESET_ALL}")
    return None, 0, 0

def analyze_product(product, position, page, query, save_to_csv=True):
    """Анализирует информацию о конкретном товаре и опционально сохраняет в CSV"""
    if not product:
        return
    
    sku = product.get('id', 'Н/Д')
    brand = product.get('brand', 'Н/Д')
    name = product.get('name', 'Н/Д')
    
    # DEBUG: Вывод сырых данных о рекламе
    print(f"\n{Fore.MAGENTA}===== ОТЛАДКА: СЫРЫЕ ДАННЫЕ О ТОВАРЕ И РЕКЛАМЕ ====={Style.RESET_ALL}")
    if 'log' in product:
        print(f"log = {json.dumps(product['log'], indent=2, ensure_ascii=False)}")
    else:
        print("Объект 'log' отсутствует в данных товара")
    
    if 'promo' in product:
        print(f"promo = {json.dumps(product['promo'], indent=2, ensure_ascii=False)}")
    
    if 'logsList' in product:
        print(f"logsList = {json.dumps(product['logsList'], indent=2, ensure_ascii=False)}")
    
    print(f"Все ключи товара: {', '.join(product.keys())}\n")
    
    # Отображаем весь объект товара в формате JSON
    print(f"Полные данные товара:\n{json.dumps({k: v for k, v in product.items() if k != 'colors'}, indent=2, ensure_ascii=False)}")
    print(f"{Fore.MAGENTA}===== КОНЕЦ ОТЛАДОЧНОЙ ИНФОРМАЦИИ ====={Style.RESET_ALL}\n")
    
    # Извлечение цены (обновлено для новой структуры API v13)
    price = None
    
    # Проверяем сначала старый формат (для обратной совместимости)
    if 'salePriceU' in product:
        price = product['salePriceU'] / 100
    # Проверяем новый формат, где цена находится в размерах
    elif 'sizes' in product and len(product['sizes']) > 0:
        first_size = product['sizes'][0]
        if 'price' in first_size and 'total' in first_size['price']:
            price = first_size['price']['total'] / 100
        # Запасной вариант - basic
        elif 'price' in first_size and 'basic' in first_size['price']:
            price = first_size['price']['basic'] / 100
    
    # Анализ рекламной информации
    has_ads = 'log' in product and product['log']
    original_position = None
    promo_position = None
    position_str = ""
    boost_cost = None
    ad_type = "Органика"
    cpm = None
    
    # Добавляем проверку на наличие log
    if has_ads:
        if product['log'].get('tp') == 'c':
            ad_type = "Аукцион"
        elif product['log'].get('tp') == 'b':
            ad_type = "АРК"
        
        # Извлекаем оригинальную и рекламную позиции
        original_position = product['log'].get('position', '')
        promo_position = product['log'].get('promoPosition', '')
        
        # Если обе позиции найдены, формируем строку смещения
        if original_position and promo_position:
            position_str = f"{original_position}→{promo_position}"
            
            # Расчет стоимости буста
            if 'cpm' in product['log']:
                cpm_value = float(product['log']['cpm'])
                position_diff = abs(int(original_position) - int(promo_position))
                if position_diff > 0:
                    boost_cost = cpm_value / position_diff
                cpm = product['log']['cpm']
    
    # Сохраняем данные в CSV, если нужно
    if save_to_csv:
        saved = save_position_to_csv(
            sku=sku,
            query=query,
            organic_position=original_position,
            promo_position=promo_position,
            price=price,
            cpm=cpm,
            ad_type=ad_type,
            page=page,
            position_on_page=position,
            boost_cost=boost_cost
        )
        if saved:
            print(f"{Fore.GREEN}Данные о позиции сохранены в CSV файл{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Не удалось сохранить данные в CSV файл{Style.RESET_ALL}")
    
    # Вывод основной информации о товаре
    print(f"\n{Fore.CYAN}===== Информация о товаре в выдаче ====={Style.RESET_ALL}")
    print(f"Артикул: {sku}")
    print(f"Бренд: {brand}")
    print(f"Название: {name}")
    print(f"Цена: {price:.0f} ₽" if price else "Цена: Н/Д")
    
    # Используем информацию о глобальной позиции
    global_position = product.get('global_position', (page-1)*100 + position)
    print(f"Глобальная позиция: {global_position} (страница {page}, позиция {position})")
    print(f"Тип размещения: {ad_type}")
    
    # Если есть информация о рекламе, выводим подробности
    if has_ads:
        print(f"Изменение позиции: {position_str}")
        if cpm:
            print(f"CPM: {cpm}")
        if boost_cost:
            print(f"Стоимость буста на позицию: {boost_cost:.0f} ₽")
    
    # Вывод таблицы с детальной информацией
    table_data = [[
        position,
        position_str,
        f"{boost_cost:.0f} ₽" if boost_cost else "",
        sku,
        brand,
        f"{price:.0f} ₽" if price else "Н/Д",
        ad_type,
        cpm
    ]]
    
    headers = ["№", "Буст", "Цена буста", "SKU", "Бренд", "Цена", "Тип", "CPM"]
    print(f"\n{Fore.GREEN}Детальная информация:{Style.RESET_ALL}")
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Дополнительная информация о конкурентах в выдаче
    print(f"\n{Fore.CYAN}===== Анализ конкурентов вокруг позиции ====={Style.RESET_ALL}")
    print(f"Позиция товара в выдаче: {position}")
    
    # Проверяем есть ли рекламное размещение
    if has_ads:
        print(f"Оригинальная позиция: {original_position}")
        print(f"Позиция с рекламой: {promo_position}")
        if original_position and promo_position:
            boost = abs(int(original_position) - int(promo_position))
            print(f"Буст: {boost} позиций")
            if boost_cost:
                print(f"Стоимость буста: {boost_cost:.0f} ₽ за позицию")

def plot_position_history(sku, query=None, days=30):
    """Строит график истории позиций товара"""
    # Получаем историю позиций из CSV файлов
    df = get_position_history(sku, query, days)
    
    if df.empty:
        print(f"{Fore.RED}Нет данных для построения графика{Style.RESET_ALL}")
        return
    
    # Создаем директорию для отчетов, если ее нет
    os.makedirs("reports", exist_ok=True)
    
    # Настраиваем стиль графика
    sns.set_style("darkgrid")
    plt.figure(figsize=(12, 8))
    
    # График позиций
    ax1 = plt.subplot(2, 1, 1)
    if 'organic_position' in df.columns:
        ax1.plot(df['timestamp'], df['organic_position'], 'o-', color='green', label='Органическая позиция')
    if 'promo_position' in df.columns:
        ax1.plot(df['timestamp'], df['promo_position'], 'o-', color='red', label='Рекламная позиция')
    
    # Инвертируем ось Y, так как меньшие позиции лучше
    ax1.invert_yaxis()
    ax1.set_ylabel('Позиция в выдаче')
    ax1.set_title(f'История позиций товара {sku} за {days} дней')
    ax1.legend()
    ax1.xaxis.set_major_formatter(DateFormatter('%d.%m %H:%M'))
    
    # График цены и CPM
    ax2 = plt.subplot(2, 1, 2)
    if 'price' in df.columns:
        ax2.plot(df['timestamp'], df['price'], 'o-', color='blue', label='Цена товара')
    
    # Создаем вторую ось Y для CPM
    if 'cpm' in df.columns and not df['cpm'].isna().all():
        ax3 = ax2.twinx()
        ax3.plot(df['timestamp'], df['cpm'], 'o-', color='purple', label='CPM')
        ax3.set_ylabel('CPM, руб.')
        ax3.legend(loc='upper right')
    
    ax2.set_xlabel('Дата и время')
    ax2.set_ylabel('Цена, руб.')
    ax2.legend(loc='upper left')
    ax2.xaxis.set_major_formatter(DateFormatter('%d.%m %H:%M'))
    
    # Форматирование
    plt.tight_layout()
    
    # Сохраняем график
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    query_str = f"_{query}" if query else ""
    filename = f"reports/position_history_{sku}{query_str}_{timestamp}.png"
    plt.savefig(filename)
    
    print(f"{Fore.GREEN}График сохранен в файл: {filename}{Style.RESET_ALL}")
    
    # Показываем график, если запускается локально
    if not os.getenv('NON_INTERACTIVE', False):
        plt.show()

def setup_scheduled_tracking(query, sku, interval=60, interval_type="minutes", max_pages=10):
    """Настраивает регулярное отслеживание позиций товара
    
    Args:
        query: Поисковый запрос
        sku: Артикул товара для отслеживания
        interval: Интервал отслеживания (по умолчанию 60)
        interval_type: Тип интервала ("minutes" или "hours")
        max_pages: Максимальное количество страниц для поиска
    """
    def job():
        print(f"{Fore.CYAN}[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Запуск отслеживания позиции...{Style.RESET_ALL}")
        product, position, page = search_product_on_pages(query, sku, max_pages)
        if product:
            analyze_product(product, position, page, query, save_to_csv=True)
        
        # Выводим информацию о следующем запуске
        if interval_type == "minutes":
            print(f"{Fore.CYAN}Следующее обновление через {interval} минут(ы){Style.RESET_ALL}")
        else:
            print(f"{Fore.CYAN}Следующее обновление через {interval} часа(ов){Style.RESET_ALL}")
    
    # Выполняем первый раз сразу
    job()
    
    # Настраиваем расписание в зависимости от типа интервала
    if interval_type == "minutes":
        if interval < 1:
            print(f"{Fore.YELLOW}Внимание: Слишком частые запросы могут привести к блокировке со стороны Wildberries!{Style.RESET_ALL}")
            interval = 1  # Минимальный интервал - 1 минута
        schedule.every(interval).minutes.do(job)
        time_str = f"{interval} минут(ы)"
    else:
        schedule.every(interval).hours.do(job)
        time_str = f"{interval} часа(ов)"
    
    print(f"{Fore.GREEN}Настроено автоматическое отслеживание каждые {time_str}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Нажмите Ctrl+C для остановки{Style.RESET_ALL}")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(10)  # Проверяем расписание каждые 10 секунд
    except KeyboardInterrupt:
        print(f"{Fore.RED}Отслеживание остановлено пользователем{Style.RESET_ALL}")

def auto_mode():
    """Интерактивный режим для настройки автоматического отслеживания"""
    print(f"{Fore.CYAN}===== Настройка автоматического отслеживания ====={Style.RESET_ALL}")
    query = input("Введите поисковый запрос: ")
    sku = input("Введите артикул для отслеживания: ")
    
    interval_type = input("Выберите тип интервала (m - минуты, h - часы, по умолчанию часы): ").lower()
    
    if interval_type == "m":
        interval_prompt = "Введите интервал в минутах (по умолчанию 60): "
        default_interval = 60
        interval_type = "minutes"
    else:
        interval_prompt = "Введите интервал в часах (по умолчанию 3): "
        default_interval = 3
        interval_type = "hours"
    
    try:
        interval = int(input(interval_prompt) or str(default_interval))
        max_pages = int(input("Введите максимальное количество страниц для поиска (по умолчанию 10): ") or "10")
    except ValueError:
        print(f"{Fore.RED}Ошибка ввода. Будут использованы значения по умолчанию.{Style.RESET_ALL}")
        interval = default_interval
        max_pages = 10
    
    setup_scheduled_tracking(query, sku, interval, interval_type, max_pages)

def history_mode():
    """Интерактивный режим для просмотра истории позиций"""
    print(f"{Fore.CYAN}===== Просмотр истории позиций ====={Style.RESET_ALL}")
    sku = input("Введите артикул для просмотра истории: ")
    query = input("Введите поисковый запрос (оставьте пустым для всех запросов): ") or None
    
    try:
        days = int(input("Введите период в днях (по умолчанию 30): ") or "30")
    except ValueError:
        print(f"{Fore.RED}Ошибка ввода. Будет использовано значение по умолчанию.{Style.RESET_ALL}")
        days = 30
    
    plot_position_history(sku, query, days)

if __name__ == "__main__":
    print(f"{Fore.CYAN}===== Wildberries Position Tracker ====={Style.RESET_ALL}")
    print("1. Отследить позицию товара")
    print("2. Настроить автоматическое отслеживание")
    print("3. Показать историю позиций")
    
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == "auto":
            if len(sys.argv) > 3:
                query = sys.argv[2]
                sku = sys.argv[3]
                
                # Проверяем наличие флага минут
                if len(sys.argv) > 4 and sys.argv[4].endswith('m'):
                    # Интервал в минутах
                    interval = int(sys.argv[4].rstrip('m'))
                    interval_type = "minutes"
                else:
                    # Интервал в часах
                    interval = int(sys.argv[4]) if len(sys.argv) > 4 else 3
                    interval_type = "hours"
                
                max_pages = int(sys.argv[5]) if len(sys.argv) > 5 else 10
                setup_scheduled_tracking(query, sku, interval, interval_type, max_pages)
            else:
                auto_mode()
        elif mode == "history":
            if len(sys.argv) > 2:
                sku = sys.argv[2]
                query = sys.argv[3] if len(sys.argv) > 3 else None
                days = int(sys.argv[4]) if len(sys.argv) > 4 else 30
                plot_position_history(sku, query, days)
            else:
                history_mode()
        else:
            # Стандартный режим отслеживания позиции
            query = sys.argv[2] if len(sys.argv) > 2 else input("Введите поисковый запрос: ")
            sku = sys.argv[3] if len(sys.argv) > 3 else input("Введите артикул для поиска: ")
            max_pages = int(sys.argv[4]) if len(sys.argv) > 4 else 10
            product, position, page = search_product_on_pages(query, sku, max_pages)
            if product:
                analyze_product(product, position, page, query, save_to_csv=True)
    else:
        try:
            choice = input("Выберите режим (1-3): ")
            if choice == "1":
                query = input("Введите поисковый запрос: ")
                sku = input("Введите артикул для поиска: ")
                max_pages_input = input("Введите максимальное количество страниц для поиска (по умолчанию 10): ")
                max_pages = int(max_pages_input) if max_pages_input.isdigit() else 10
                product, position, page = search_product_on_pages(query, sku, max_pages)
                if product:
                    analyze_product(product, position, page, query, save_to_csv=True)
            elif choice == "2":
                auto_mode()
            elif choice == "3":
                history_mode()
            else:
                print(f"{Fore.RED}Неверный выбор{Style.RESET_ALL}")
        except KeyboardInterrupt:
            print(f"\n{Fore.RED}Программа прервана пользователем{Style.RESET_ALL}")