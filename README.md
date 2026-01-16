# BI Dashboard Metrics Analysis

Система для автоматического анализа причин изменения метрик на BI-дашбордах.

## Архитектура

Система состоит из двух основных компонентов:

1. **Встраиваемый клиентский код** - JavaScript/Python код, выполняющийся в браузере (Pyodide)
2. **Backend API** - Python API для безопасного выполнения SQL запросов

## Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Настройка конфигурации

```bash
# Скопируйте примеры конфигурационных файлов
cp config/db_config.json.example config/db_config.json
cp config/api_config.json.example config/api_config.json

# Отредактируйте файлы с вашими данными
```

### 3. Запуск Backend API

```bash
cd api
python main.py
```

API будет доступен на `http://localhost:8000`

### 4. Встраивание на страницу дашборда

Добавьте на страницу вашего BI-дашборда:

```html
<script src="https://your-domain.com/client/embed.js"></script>
<script>
  window.BIAnalyzerConfig = {
    apiUrl: 'http://localhost:8000'
  };
</script>
```

**Готово!** Пользователям не нужно ничего устанавливать - просто открыть страницу.

## Использование

1. Откройте BI-дашборд в браузере (со встроенным скриптом)
2. Нажмите на кнопку "Анализировать метрику" (появляется автоматически)
3. Выберите метрику для анализа из списка
4. Получите краткий отчет о причинах изменения

**Пользователю не нужно ничего устанавливать!** Всё работает прямо в браузере.

## Как это работает

1. **Сбор данных**: Скрипт автоматически собирает метрики, фильтры и период с дашборда
2. **Загрузка Pyodide**: Python выполняется в браузере через WebAssembly
3. **Анализ**: Python код анализирует данные, запрашивая SQL через API
4. **Результат**: Пользователь видит краткий отчет о причинах изменения

## Структура проекта

```
dashboard_analyzer/
├── api/                    # Backend API
│   ├── main.py            # Главный файл API
│   └── sql_endpoint.py    # Endpoint для SQL запросов
├── client/                 # Клиентский код
│   └── embed.js           # Встраиваемый скрипт
├── analyzers/              # Анализаторы метрик (Python)
│   ├── universal_analyzer_client.py # Универсальный анализатор
│   └── data_collector_client.py # Сборщик данных с дашборда
├── utils/                  # Утилиты
│   ├── db_connection.py   # Подключение к БД
│   ├── api_client.py      # Клиент для API
│   └── config_loader.py   # Загрузка конфигурации
├── config/                 # Конфигурационные файлы
│   ├── db_config.json.example
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

## Поддерживаемые метрики

- **Себестоимость** - анализ изменения закупочных цен, цен реализации, списаний
- **Выручка** - анализ изменения количества заказов, среднего чека, популярности блюд

Вы можете создать собственные анализаторы для других метрик (см. документацию).

## Документация

См. [docs/README.md](docs/README.md) для навигации по всей документации.

**Основные разделы:**
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - Архитектура и концепция системы
- [docs/EMBEDDING_GUIDE.md](docs/EMBEDDING_GUIDE.md) - Подробное руководство по встраиванию
- [docs/UNIVERSAL_ANALYZER_GUIDE.md](docs/UNIVERSAL_ANALYZER_GUIDE.md) - Руководство по универсальному анализатору
- [docs/ARCHITECTURE_RECOMMENDATIONS.md](docs/ARCHITECTURE_RECOMMENDATIONS.md) - Рекомендации по архитектуре
- [docs/METRIC_STRUCTURE.md](docs/METRIC_STRUCTURE.md) - Структура метрик
- [examples/README.md](examples/README.md) - Примеры использования

## Преимущества

✅ **Не требует установки** - работает прямо в браузере  
✅ **Безопасность** - SQL запросы выполняются только на сервере  
✅ **Производительность** - анализ выполняется локально  
✅ **Гибкость** - легко добавлять новые анализаторы  
✅ **Изоляция** - каждый пользователь работает в своей среде
