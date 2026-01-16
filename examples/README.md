# Примеры использования

## Базовое встраивание

Самый простой способ - добавить скрипт на страницу:

```html
<script src="https://your-domain.com/bi_analysis/embed.js"></script>
<script>
  window.BIAnalyzerConfig = {
    apiUrl: 'https://your-api.com'
  };
</script>
```

## Адаптация под ваш дашборд

### Пример 1: Использование data-атрибутов

Если ваши метрики имеют data-атрибуты:

```html
<div class="metric" data-metric="Себестоимость" data-value="45.5" data-change="+1.2%">
  Себестоимость: 45.5% (+1.2%)
</div>
```

Скрипт автоматически их найдет.

### Пример 2: Кастомный сбор данных

Если нужна кастомная логика сбора данных:

```javascript
document.addEventListener('DOMContentLoaded', function() {
  if (window.BIAnalyzer) {
    // Переопределяем метод сбора метрик
    const original = window.BIAnalyzer.prototype.collectMetrics;
    window.BIAnalyzer.prototype.collectMetrics = function(data) {
      // Ваша логика сбора метрик
      const myMetrics = document.querySelectorAll('.my-metric-class');
      myMetrics.forEach((el, idx) => {
        data.metrics.push({
          id: `metric_${idx}`,
          name: el.dataset.name,
          value: parseFloat(el.dataset.value),
          change: { type: 'percent', value: parseFloat(el.dataset.change) }
        });
      });
    };
  }
});
```

### Пример 3: Интеграция с React/Vue

Для React компонента:

```jsx
import { useEffect } from 'react';

function Dashboard() {
  useEffect(() => {
    // Загружаем скрипт
    const script = document.createElement('script');
    script.src = 'https://your-domain.com/bi_analysis/embed.js';
    script.onload = () => {
      window.BIAnalyzerConfig = {
        apiUrl: 'https://your-api.com'
      };
    };
    document.body.appendChild(script);
    
    return () => {
      // Очистка при размонтировании
      document.body.removeChild(script);
    };
  }, []);
  
  return <div>Your Dashboard</div>;
}
```

## Настройка UI

### Изменение позиции кнопки

```javascript
window.BIAnalyzerConfig = {
  apiUrl: 'https://your-api.com',
  buttonPosition: 'bottom-left'  // top-right, top-left, bottom-right, bottom-left
};
```

### Кастомный текст кнопки

```javascript
window.BIAnalyzerConfig = {
  apiUrl: 'https://your-api.com',
  buttonText: 'Почему изменилось?'
};
```

## Работа с Backend API

### Настройка подключения

Система требует внешний Backend API для выполнения SQL запросов:

```javascript
window.BIAnalyzerConfig = {
  apiUrl: 'https://your-backend-api.com',  // URL вашего Backend API
  sqlEndpoint: '/api/v1/query',  // Endpoint для SQL запросов
  apiHeaders: {
    'Authorization': 'Bearer YOUR_TOKEN'  // Заголовки авторизации
  }
};
```

### Настройка CORS

Убедитесь, что ваш Backend API разрешает запросы с домена дашборда.

### Требования к Backend API

- Должен поддерживать выполнение SQL запросов (только SELECT)
- Должен принимать запросы в формате: `{"query": "SELECT ...", "params": {...}}`
- Должен возвращать результаты в формате: `{"result": [...]}` или `[...]`

Подробнее см. [docs/EXTERNAL_API_INTEGRATION.md](../docs/EXTERNAL_API_INTEGRATION.md)

## Отладка

Включите логирование в консоли:

```javascript
window.BIAnalyzerConfig = {
  apiUrl: 'https://your-api.com',
  debug: true  // Показывает подробные логи
};
```

Откройте консоль браузера (F12) для просмотра логов.
