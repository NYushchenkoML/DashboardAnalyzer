# BI Dashboard Metrics Analysis

Система для автоматического анализа причин изменения метрик на BI-дашбордах.

## Архитектура

Система работает полностью на клиенте:

1. **Встраиваемый клиентский код** - JavaScript/Python код, выполняющийся в браузере (Pyodide)
   - Весь анализ метрик выполняется на клиенте
   - Не требует серверной обработки
   - Для получения данных из БД использует внешний Backend API

**Важно:** Система требует внешний Backend API для выполнения SQL запросов. Анализ метрик выполняется полностью в браузере.

## Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Настройка внешнего Backend API

Система требует внешний Backend API для выполнения SQL запросов к базе данных.

Настройте подключение к вашему Backend API:

```javascript
window.BIAnalyzerConfig = {
  apiUrl: 'https://your-backend-api.com',  // URL вашего Backend API
  sqlEndpoint: '/api/v1/query',  // Endpoint для SQL запросов
  apiHeaders: {
    'Authorization': 'Bearer YOUR_TOKEN'  // Заголовки авторизации
  }
};
```

**Требования к Backend API:**
- Должен поддерживать выполнение SQL запросов (только SELECT)
- Должен принимать запросы в формате: `{"query": "SELECT ...", "params": {...}}`
- Должен возвращать результаты в формате: `{"result": [...]}` или `[...]`
- Должен поддерживать CORS (если API на другом домене)

Подробнее см. [docs/EXTERNAL_API_INTEGRATION.md](docs/EXTERNAL_API_INTEGRATION.md)

### 3. Встраивание на страницу дашборда

Добавьте на страницу вашего BI-дашборда:

```html
<script src="https://your-domain.com/client/embed.js"></script>
<script>
  window.BIAnalyzerConfig = {
    apiUrl: 'https://your-backend-api.com',  // URL вашего Backend API
    sqlEndpoint: '/api/v1/query',  // Endpoint для SQL запросов
    apiHeaders: {
      'Authorization': 'Bearer YOUR_TOKEN'
    }
  };
</script>
```

**Готово!** Пользователям не нужно ничего устанавливать - просто открыть страницу.

## Использование

1. Откройте BI-дашборд в браузере (со встроенным скриптом)
2. Нажмите на кнопку "Анализировать метрики" (появляется автоматически)
3. Скрипт автоматически анализирует **все метрики** на дашборде
4. Получите краткий отчет о причинах изменения для каждой метрики

**Пользователю не нужно ничего устанавливать!** Всё работает прямо в браузере.

## Как это работает

1. **Сбор данных**: Скрипт автоматически собирает метрики, фильтры и период с дашборда
2. **Загрузка Pyodide**: Python выполняется в браузере через WebAssembly
3. **Получение данных**: Python код запрашивает дополнительные данные через API (SQL запросы к БД)
4. **Анализ на клиенте**: Python код анализирует данные **прямо в браузере** (не на сервере!)
5. **Результат**: Пользователь видит краткий отчет о причинах изменения

**Ключевой момент:** Весь анализ выполняется в браузере пользователя, Backend только предоставляет данные из БД.

## Структура проекта

```
dashboard_analyzer/
├── client/                 # Клиентский код
│   └── embed.js           # Встраиваемый скрипт
├── analyzers/              # Анализаторы метрик (Python)
│   ├── universal_analyzer_client.py # Универсальный анализатор
│   └── data_collector_client.py # Сборщик данных с дашборда
├── utils/                  # Утилиты
│   └── config_loader.py   # Загрузка конфигурации
├── config/                 # Конфигурационные файлы
│   └── api_config.json.example
├── docs/                   # Документация
│   ├── ARCHITECTURE_RECOMMENDATIONS.md
│   ├── EMBEDDING_GUIDE.md
│   ├── UNIVERSAL_ANALYZER_GUIDE.md
│   └── ...
├── examples/               # Примеры использования
│   ├── embed_example.html
│   └── README.md
├── tests/                  # Тесты
│   └── test_universal_analyzer.py
├── archive/                # Архивные файлы
└── requirements.txt       # Зависимости Python
```


