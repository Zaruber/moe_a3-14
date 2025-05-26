# Wildberries API

API для анализа товаров и позиций на маркетплейсе Wildberries.

## Описание

Wildberries API - это Flask-приложение, объединяющее функциональность двух инструментов:
1. **Анализ товаров** - получение детальной информации о товарах на Wildberries
2. **Отслеживание позиций** - поиск и мониторинг позиций товаров в поисковой выдаче

API предоставляет возможность:
- Получать подробные данные о товаре по артикулу
- Искать позицию товара в поисковой выдаче по заданному запросу
- Настраивать регулярное отслеживание позиций с заданным интервалом
- Анализировать историю изменения позиций

## Установка

### Предварительные требования

- Python 3.8 или выше
- pip (менеджер пакетов Python)

### Шаги установки

1. Клонируйте репозиторий:
```
git clone https://github.com/yourusername/wildberries-api.git
cd wildberries-api
```

2. Создайте и активируйте виртуальное окружение:
```
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. Установите зависимости:
```
pip install -r requirements.txt
```

## Запуск

### Запуск в режиме разработки

```
python app.py
```

По умолчанию, сервер будет доступен по адресу http://localhost:5000

### Запуск в production-режиме с Gunicorn

```
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Использование API

### Получение информации о товаре

```
GET /api/product/{article_id}
```

Пример:
```
GET /api/product/12345678
```

### Поиск позиции товара

```
GET /api/position?sku={sku}&query={query}&max_pages={max_pages}
```

Параметры:
- `sku` - Артикул товара (обязательный)
- `query` - Поисковый запрос (обязательный)
- `max_pages` - Максимальное количество страниц для поиска (по умолчанию 10)

Пример:
```
GET /api/position?sku=12345678&query=платье&max_pages=5
```

### Настройка отслеживания позиции

```
POST /api/tracking
```

Тело запроса (JSON):
```json
{
  "sku": "12345678",
  "query": "платье",
  "interval": 60,
  "interval_type": "minutes",
  "max_pages": 10
}
```

### Получение истории позиций

```
GET /api/history?sku={sku}&query={query}&days={days}
```

Параметры:
- `sku` - Артикул товара (обязательный)
- `query` - Поисковый запрос (опциональный)
- `days` - Количество дней для выборки (по умолчанию 30)

Пример:
```
GET /api/history?sku=12345678&query=платье&days=7
```

## Структура проекта

```
wildberries-api/
├── app.py                   # Основной файл приложения
├── requirements.txt         # Зависимости проекта
├── services/                # Модули сервисов
│   ├── __init__.py
│   ├── product_service.py   # Сервис для работы с товарами
│   └── position_service.py  # Сервис для работы с позициями
├── static/                  # Статические файлы
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── script.js
├── templates/               # HTML шаблоны
│   └── index.html           # Главная страница с документацией
├── data/                    # Директория для хранения данных
└── logs/                    # Директория для логов
```

## Примеры использования

### JavaScript

```javascript
// Получение информации о товаре
fetch('/api/product/12345678')
  .then(response => response.json())
  .then(data => console.log(data))
  .catch(error => console.error('Ошибка:', error));

// Поиск позиции товара
fetch('/api/position?sku=12345678&query=платье')
  .then(response => response.json())
  .then(data => console.log(data))
  .catch(error => console.error('Ошибка:', error));
```

### Python

```python
import requests

# Получение информации о товаре
response = requests.get('http://localhost:5000/api/product/12345678')
data = response.json()
print(data)

# Настройка отслеживания
tracking_data = {
    "sku": "12345678",
    "query": "платье",
    "interval": 60,
    "interval_type": "minutes"
}
response = requests.post('http://localhost:5000/api/tracking', json=tracking_data)
result = response.json()
print(result)
```

## Лицензия

MIT 