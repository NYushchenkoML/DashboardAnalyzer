/**
 * Встраиваемый скрипт для анализа метрик BI-дашбордов
 * Подключается на страницу дашборда и выполняет анализ на стороне клиента
 * 
 * Использование:
 * <script src="https://your-domain.com/bi_analysis/embed.js"></script>
 * <script>
 *   BIAnalyzer.init({
 *     apiUrl: 'https://your-api.com',
 *     dashboardId: 'dashboard-123'
 *   });
 * </script>
 */

(function() {
  'use strict';

  // Конфигурация по умолчанию
  const DEFAULT_CONFIG = {
    apiUrl: 'http://localhost:8000',
    pyodideUrl: 'https://cdn.jsdelivr.net/pyodide/v0.24.1/full/',
    autoInit: true,
    buttonText: 'Анализировать метрики',
    buttonPosition: 'top-right'
  };

  class BIAnalyzer {
    constructor(config) {
      this.config = { ...DEFAULT_CONFIG, ...config };
      this.pyodide = null;
      this.initialized = false;
      this.currentMetric = null;
      this.dashboardData = null;
    }

    /**
     * Инициализация анализатора
     */
    async init() {
      if (this.initialized) return;

      try {
        // Загружаем Pyodide для выполнения Python кода
        console.log('Загрузка Pyodide...');
        this.pyodide = await loadPyodide({
          indexURL: this.config.pyodideUrl
        });

        // Устанавливаем необходимые Python пакеты
        await this.pyodide.loadPackage(['micropip']);
        const micropip = this.pyodide.pyimport('micropip');
        await micropip.install(['pandas', 'numpy']);

        // Загружаем Python модули анализа
        await this.loadPythonModules();

        // Собираем данные с дашборда
        this.dashboardData = this.collectDashboardData();

        // Добавляем UI элементы
        this.createUI();

        this.initialized = true;
        console.log('BIAnalyzer инициализирован');
      } catch (error) {
        console.error('Ошибка инициализации BIAnalyzer:', error);
        this.showError('Ошибка инициализации анализатора');
      }
    }

    /**
     * Загружает Python модули для анализа
     */
    async loadPythonModules() {
      // Загружаем анализаторы из API или встраиваем в код
      const response = await fetch(`${this.config.apiUrl}/api/analyzers/code`);
      if (response.ok) {
        const code = await response.text();
        this.pyodide.runPython(code);
      } else {
        // Используем встроенные анализаторы
        await this.loadEmbeddedAnalyzers();
      }
    }

    /**
     * Загружает встроенные анализаторы (если API недоступен)
     */
    async loadEmbeddedAnalyzers() {
      // Загружаем базовый анализатор
      const analyzerCode = `
import json
from datetime import datetime, timedelta

class MetricAnalyzer:
    def __init__(self, api_client):
        self.api_client = api_client
    
    async def analyze_cost(self, metric_data, filters, period):
        """Анализирует себестоимость"""
        # Получаем данные через API
        purchase_data = await self.api_client.get_purchase_prices(filters, period)
        sales_data = await self.api_client.get_sales_prices(filters, period)
        
        # Анализируем изменения
        analysis = self._analyze_changes(purchase_data, sales_data)
        return analysis
    
    def _analyze_changes(self, purchase_data, sales_data):
        """Анализирует изменения цен"""
        changes = []
        for item in purchase_data:
            if item.get('price_change_percent', 0) > 1:
                changes.append({
                    'supplier': item.get('supplier'),
                    'product': item.get('product'),
                    'price_change': item.get('price_change_percent'),
                    'sales_price_changed': item.get('sales_price_changed', False)
                })
        return changes

analyzer = MetricAnalyzer(None)
      `;
      this.pyodide.runPython(analyzerCode);
    }

    /**
     * Собирает данные с дашборда
     * Собирает данные из всех вкладок, виджетов, фильтров и периодов
     */
    collectDashboardData() {
      const data = {
        metrics: [],
        filters: {},
        period: null,
        granularity: null,
        tabs: [],
        widgets: [],
        current_tab_id: null,
        current_tab_name: null,
        timestamp: new Date().toISOString()
      };

      // Собираем вкладки
      this.collectTabs(data);
      
      // Собираем виджеты
      this.collectWidgets(data);
      
      // Собираем метрики (адаптируйте под ваш BI-инструмент)
      this.collectMetrics(data);
      
      // Собираем фильтры
      this.collectFilters(data);
      
      // Собираем период
      this.collectPeriod(data);

      return data;
    }

    /**
     * Собирает информацию о вкладках
     */
    collectTabs(data) {
      // Ищем вкладки по различным селекторам
      const tabSelectors = [
        '.v-tab.tab-item',
        '.v-tab[role="tab"]',
        '[class*="tab"][class*="item"]',
        'button[role="tab"]'
      ];

      tabSelectors.forEach(selector => {
        const tabs = document.querySelectorAll(selector);
        tabs.forEach((tab, index) => {
          const tabId = tab.getAttribute('value') || 
                       tab.getAttribute('data-tab-id') || 
                       tab.getAttribute('id') ||
                       `tab_${index}`;
          
          const tabName = tab.textContent?.trim() || 
                        tab.getAttribute('data-tab-name') ||
                        `Вкладка ${index + 1}`;
          
          const isActive = tab.classList.contains('v-tab-item--selected') ||
                          tab.classList.contains('selected') ||
                          tab.getAttribute('aria-selected') === 'true' ||
                          tab.style.display !== 'none';

          if (!data.tabs.find(t => t.id === tabId)) {
            data.tabs.push({
              id: tabId,
              name: tabName,
              isActive: isActive,
              element: tab
            });

            if (isActive) {
              data.current_tab_id = tabId;
              data.current_tab_name = tabName;
            }
          }
        });
      });
    }

    /**
     * Собирает информацию о виджетах
     */
    collectWidgets(data) {
      // Ищем виджеты по различным селекторам
      const widgetSelectors = [
        '.widget-container',
        '.v-card[class*="widget"]',
        '[class*="widget-container"]',
        'section[widget]'
      ];

      widgetSelectors.forEach(selector => {
        const widgets = document.querySelectorAll(selector);
        widgets.forEach((widget, index) => {
          const widgetId = widget.getAttribute('widget') ||
                          widget.getAttribute('data-widget-id') ||
                          widget.getAttribute('id') ||
                          `widget_${index}`;
          
          // Ищем заголовок виджета
          const titleElement = widget.querySelector('.widget-title') ||
                              widget.querySelector('.v-card-title') ||
                              widget.querySelector('[class*="title"]');
          
          const widgetTitle = titleElement?.textContent?.trim() ||
                            widget.getAttribute('data-widget-title') ||
                            `Виджет ${index + 1}`;
          
          // Ищем содержимое виджета
          const contentElement = widget.querySelector('.widget-content') ||
                                widget.querySelector('[class*="content"]');
          
          // Извлекаем метрики из виджета
          const widgetMetrics = this.extractMetricsFromWidget(widget);
          
          // Определяем тип виджета
          const widgetType = this.detectWidgetType(widget);

          if (!data.widgets.find(w => w.id === widgetId)) {
            data.widgets.push({
              id: widgetId,
              title: widgetTitle,
              type: widgetType,
              metrics: widgetMetrics,
              tab_id: data.current_tab_id, // Привязываем к текущей вкладке
              element: widget
            });
          }
        });
      });
    }

    /**
     * Извлекает метрики из виджета
     */
    extractMetricsFromWidget(widgetElement) {
      const metrics = [];
      
      // Ищем числовые значения в виджете
      const textElements = widgetElement.querySelectorAll('span, div, td, th');
      textElements.forEach(element => {
        const text = element.textContent?.trim() || '';
        
        // Ищем паттерны типа "Название: 123.45" или просто числа
        const metricMatch = text.match(/(.+?):\s*([\d,]+\.?\d*)/);
        if (metricMatch) {
          const metricName = metricMatch[1].trim();
          const metricValue = parseFloat(metricMatch[2].replace(/,/g, ''));
          
          if (!isNaN(metricValue)) {
            metrics.push({
              name: metricName,
              value: metricValue
            });
          }
        } else {
          // Ищем просто большие числа (потенциальные метрики)
          const numberMatch = text.match(/^([\d,]+\.?\d*)$/);
          if (numberMatch && numberMatch[1].length > 3) {
            const metricValue = parseFloat(numberMatch[1].replace(/,/g, ''));
            if (!isNaN(metricValue) && metricValue > 0) {
              // Пытаемся найти название метрики в родительском элементе
              const parent = element.parentElement;
              const parentText = parent?.textContent || '';
              const nameMatch = parentText.match(/(.+?)\s*[\d,]+\.?\d*/);
              
              metrics.push({
                name: nameMatch ? nameMatch[1].trim() : 'Метрика',
                value: metricValue
              });
            }
          }
        }
      });
      
      return metrics;
    }

    /**
     * Определяет тип виджета
     */
    detectWidgetType(widgetElement) {
      const classes = widgetElement.className || '';
      const text = widgetElement.textContent || '';
      
      if (classes.includes('chart') || classes.includes('graph')) {
        return 'chart';
      }
      if (classes.includes('table')) {
        return 'table';
      }
      if (text.includes('сумма') || text.includes('сумма')) {
        return 'summary';
      }
      if (text.includes('график') || text.includes('chart')) {
        return 'chart';
      }
      
      return 'unknown';
    }

    /**
     * Собирает метрики со страницы
     */
    collectMetrics(data) {
      // Универсальный подход - ищем элементы с метриками
      const metricSelectors = [
        '[data-metric]',
        '[class*="metric"]',
        '[class*="kpi"]',
        '[class*="indicator"]'
      ];

      metricSelectors.forEach(selector => {
        const elements = document.querySelectorAll(selector);
        elements.forEach((element, index) => {
          const metricName = element.getAttribute('data-metric') ||
                           element.getAttribute('data-title') ||
                           element.textContent.trim().split('\n')[0];
          
          const metricValue = this.extractMetricValue(element);
          const metricChange = this.extractMetricChange(element);

          if (metricName && metricValue !== null) {
            data.metrics.push({
              id: `metric_${index}`,
              name: metricName,
              value: metricValue,
              change: metricChange,
              element: element
            });
          }
        });
      });
    }

    /**
     * Извлекает значение метрики
     */
    extractMetricValue(element) {
      const text = element.textContent || element.innerText;
      const numberMatch = text.match(/[\d,]+\.?\d*/);
      return numberMatch ? parseFloat(numberMatch[0].replace(/,/g, '')) : null;
    }

    /**
     * Извлекает изменение метрики
     */
    extractMetricChange(element) {
      const text = element.textContent || element.innerText;
      const percentMatch = text.match(/([+-]?\d+\.?\d*)\s*%/);
      if (percentMatch) {
        return {
          type: 'percent',
          value: parseFloat(percentMatch[1])
        };
      }
      return null;
    }

    /**
     * Собирает фильтры
     */
    collectFilters(data) {
      const filterElements = document.querySelectorAll(
        '[data-filter], select, input[type="date"], [class*="filter"]'
      );

      filterElements.forEach(element => {
        const filterName = element.getAttribute('data-filter') ||
                          element.getAttribute('name') ||
                          element.getAttribute('id');
        
        let filterValue = null;
        if (element.tagName === 'SELECT') {
          filterValue = element.value;
        } else if (element.tagName === 'INPUT') {
          filterValue = element.value || element.checked;
        } else {
          filterValue = element.textContent || element.getAttribute('data-value');
        }

        if (filterName && filterValue) {
          data.filters[filterName] = filterValue;
        }
      });
    }

    /**
     * Собирает период
     */
    collectPeriod(data) {
      const periodElements = document.querySelectorAll(
        '[data-period], [class*="period"], [class*="date-range"]'
      );

      if (periodElements.length > 0) {
        const periodText = periodElements[0].textContent || 
                          periodElements[0].getAttribute('data-value');
        data.period = this.parsePeriod(periodText);
      }
    }

    /**
     * Парсит период
     */
    parsePeriod(text) {
      if (!text) return null;

      const dateRegex = /(\d{4}-\d{2}-\d{2})/g;
      const dates = text.match(dateRegex);
      
      if (dates && dates.length >= 2) {
        return {
          start: dates[0],
          end: dates[1]
        };
      }

      return { raw: text };
    }

    /**
     * Создает UI элементы
     */
    createUI() {
      // Создаем кнопку анализа
      const button = document.createElement('button');
      button.id = 'bi-analyzer-btn';
      button.textContent = this.config.buttonText;
      button.className = 'bi-analyzer-button';
      button.style.cssText = `
        position: fixed;
        ${this.config.buttonPosition.includes('right') ? 'right: 20px;' : 'left: 20px;'}
        ${this.config.buttonPosition.includes('top') ? 'top: 20px;' : 'bottom: 20px;'}
        z-index: 10000;
        padding: 12px 24px;
        background: #2196f3;
        color: white;
        border: none;
        border-radius: 6px;
        cursor: pointer;
        font-size: 14px;
        font-weight: 500;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
      `;
      
      button.addEventListener('click', () => this.showAnalysisModal());
      document.body.appendChild(button);

      // Добавляем стили
      this.injectStyles();
    }

    /**
     * Внедряет CSS стили
     */
    injectStyles() {
      const style = document.createElement('style');
      style.textContent = `
        .bi-analyzer-button:hover {
          background: #1976d2 !important;
        }
        .bi-analyzer-modal {
          position: fixed;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          width: 600px;
          max-width: 90vw;
          max-height: 80vh;
          background: white;
          border-radius: 8px;
          box-shadow: 0 4px 20px rgba(0,0,0,0.3);
          z-index: 10001;
          display: none;
          flex-direction: column;
        }
        .bi-analyzer-modal.active {
          display: flex;
        }
        .bi-analyzer-modal-header {
          padding: 20px;
          border-bottom: 1px solid #e0e0e0;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .bi-analyzer-modal-body {
          padding: 20px;
          overflow-y: auto;
          flex: 1;
        }
        .bi-analyzer-modal-close {
          background: none;
          border: none;
          font-size: 24px;
          cursor: pointer;
          color: #666;
        }
        .bi-analyzer-metric-item {
          padding: 12px;
          margin: 8px 0;
          border: 1px solid #e0e0e0;
          border-radius: 4px;
          cursor: pointer;
        }
        .bi-analyzer-metric-item:hover {
          background: #f5f5f5;
        }
        .bi-analyzer-metric-item.selected {
          background: #e3f2fd;
          border-color: #2196f3;
        }
        .bi-analyzer-result {
          margin-top: 20px;
          padding: 15px;
          background: #f9f9f9;
          border-radius: 4px;
          white-space: pre-wrap;
          line-height: 1.6;
        }
        .bi-analyzer-loading {
          text-align: center;
          padding: 40px;
        }
        .bi-analyzer-spinner {
          border: 3px solid #f3f3f3;
          border-top: 3px solid #2196f3;
          border-radius: 50%;
          width: 40px;
          height: 40px;
          animation: spin 1s linear infinite;
          margin: 0 auto 20px;
        }
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        .bi-analyzer-metric-result {
          margin-bottom: 30px;
          padding-bottom: 20px;
          border-bottom: 1px solid #e0e0e0;
        }
        .bi-analyzer-metric-result:last-child {
          border-bottom: none;
        }
        .bi-analyzer-metric-result h4 {
          margin-bottom: 10px;
          color: #2196f3;
        }
      `;
      document.head.appendChild(style);
    }

    /**
     * Показывает модальное окно анализа
     * Автоматически анализирует все метрики дашборда
     */
    showAnalysisModal() {
      const modal = document.createElement('div');
      modal.className = 'bi-analyzer-modal active';
      modal.innerHTML = `
        <div class="bi-analyzer-modal-header">
          <h2>Анализ метрик дашборда</h2>
          <button class="bi-analyzer-modal-close">&times;</button>
        </div>
        <div class="bi-analyzer-modal-body" id="bi-analyzer-modal-body">
          <div class="bi-analyzer-loading">
            <div class="bi-analyzer-spinner"></div>
            <p>Выполняется анализ всех метрик...</p>
          </div>
        </div>
      `;

      document.body.appendChild(modal);

      // Обработчики событий
      modal.querySelector('.bi-analyzer-modal-close').addEventListener('click', () => {
        modal.remove();
      });

      // Сразу запускаем анализ всех метрик
      this.analyzeAllMetrics(modal);
    }

    /**
     * Анализирует все метрики дашборда
     */
    async analyzeAllMetrics(modal) {
      const body = modal.querySelector('#bi-analyzer-modal-body');
      
      if (!this.dashboardData || !this.dashboardData.metrics.length) {
        body.innerHTML = '<p>Метрики не найдены на странице</p>';
        return;
      }

      const metrics = this.dashboardData.metrics;
      const results = [];
      let completed = 0;

      // Обновляем прогресс
      const updateProgress = () => {
        const progress = Math.round((completed / metrics.length) * 100);
        body.innerHTML = `
          <div class="bi-analyzer-loading">
            <div class="bi-analyzer-spinner"></div>
            <p>Выполняется анализ метрик...</p>
            <p><small>Обработано: ${completed} из ${metrics.length} (${progress}%)</small></p>
          </div>
        `;
      };

      // Анализируем каждую метрику
      for (const metric of metrics) {
        try {
          updateProgress();
          const analysis = await this.runPythonAnalysis(metric);
          results.push({
            metric: metric,
            analysis: analysis,
            success: true
          });
        } catch (error) {
          console.error(`Ошибка анализа метрики ${metric.name}:`, error);
          results.push({
            metric: metric,
            analysis: `Ошибка анализа: ${error.message}`,
            success: false
          });
        }
        completed++;
      }

      // Показываем результаты
      this.renderAllResults(body, results);
    }

    /**
     * Рендерит результаты анализа всех метрик
     */
    renderAllResults(body, results) {
      const successfulResults = results.filter(r => r.success);
      const failedResults = results.filter(r => !r.success);

      let html = `
        <div>
          <h3>Результаты анализа метрик</h3>
          <p><strong>Проанализировано:</strong> ${results.length} метрик</p>
          ${successfulResults.length > 0 ? `<p><strong>Успешно:</strong> ${successfulResults.length}</p>` : ''}
          ${failedResults.length > 0 ? `<p><strong>Ошибок:</strong> ${failedResults.length}</p>` : ''}
          <hr style="margin: 20px 0;">
      `;

      // Показываем успешные результаты
      successfulResults.forEach((result, index) => {
        html += `
          <div class="bi-analyzer-metric-result" style="margin-bottom: 30px; padding-bottom: 20px; border-bottom: 1px solid #e0e0e0;">
            <h4 style="margin-bottom: 10px; color: #2196f3;">
              ${index + 1}. ${this.escapeHtml(result.metric.name)}
            </h4>
            ${result.metric.value !== undefined ? `<p><strong>Значение:</strong> ${this.formatNumber(result.metric.value)}</p>` : ''}
            ${result.metric.change ? `<p><strong>Изменение:</strong> ${this.formatChange(result.metric.change)}</p>` : ''}
            <div class="bi-analyzer-result" style="margin-top: 10px;">
              ${this.escapeHtml(result.analysis)}
            </div>
          </div>
        `;
      });

      // Показываем ошибки
      if (failedResults.length > 0) {
        html += `
          <div style="margin-top: 30px; padding-top: 20px; border-top: 2px solid #f44336;">
            <h4 style="color: #f44336;">Метрики с ошибками:</h4>
        `;
        failedResults.forEach(result => {
          html += `
            <div style="margin-bottom: 15px; padding: 10px; background: #ffebee; border-radius: 4px;">
              <strong>${this.escapeHtml(result.metric.name)}</strong>
              <p style="margin: 5px 0 0 0; color: #c62828;">${this.escapeHtml(result.analysis)}</p>
            </div>
          `;
        });
        html += `</div>`;
      }

      html += `</div>`;
      body.innerHTML = html;
    }

    /**
     * Анализирует одну метрику (используется внутри analyzeAllMetrics)
     */
    async analyzeMetric(metricId, modal) {
      const metric = this.dashboardData.metrics.find(m => m.id === metricId);
      if (!metric) return;

      this.currentMetric = metric;

      // Показываем загрузку
      const body = modal.querySelector('#bi-analyzer-modal-body');
      body.innerHTML = `
        <div class="bi-analyzer-loading">
          <div class="bi-analyzer-spinner"></div>
          <p>Выполняется анализ...</p>
        </div>
      `;

      try {
        // Выполняем анализ через Python
        const analysis = await this.runPythonAnalysis(metric);

        // Показываем результат
        body.innerHTML = `
          <div>
            <h3>Результаты анализа: ${this.escapeHtml(metric.name)}</h3>
            <div class="bi-analyzer-result">${this.escapeHtml(analysis)}</div>
          </div>
        `;
      } catch (error) {
        console.error('Ошибка анализа:', error);
        body.innerHTML = `
          <div>
            <h3>Ошибка</h3>
            <p>Не удалось выполнить анализ: ${error.message}</p>
          </div>
        `;
      }
    }

    /**
     * Выполняет анализ через Python (Pyodide)
     */
    async runPythonAnalysis(metric) {
      // Создаем API клиент для Python
      const apiClientCode = `
import json
from js import fetch

class APIClient:
    def __init__(self, base_url):
        self.base_url = base_url
    
    async def execute_sql(self, query, params=None):
        """Выполняет SQL запрос через API"""
        response = await fetch(
            f"{self.base_url}/api/sql/execute",
            {
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"query": query, "params": params or {}})
            }
        )
        data = await response.json()
        return data.get("result", [])
    
    async def get_purchase_prices(self, filters, period):
        """Получает данные о закупочных ценах"""
        query = """
        SELECT 
            s.name as supplier_name,
            p.name as product_name,
            AVG(CASE WHEN po.date BETWEEN :prev_start AND :prev_end 
                THEN po.price ELSE NULL END) as prev_price,
            AVG(CASE WHEN po.date BETWEEN :curr_start AND :curr_end 
                THEN po.price ELSE NULL END) as curr_price
        FROM purchase_orders po
        JOIN products p ON po.product_id = p.id
        JOIN suppliers s ON po.supplier_id = s.id
        WHERE po.date BETWEEN :prev_start AND :curr_end
        GROUP BY s.name, p.name
        HAVING 
            AVG(CASE WHEN po.date BETWEEN :prev_start AND :prev_end THEN po.price END) IS NOT NULL
            AND AVG(CASE WHEN po.date BETWEEN :curr_start AND :curr_end THEN po.price END) IS NOT NULL
        ORDER BY ABS(AVG(CASE WHEN po.date BETWEEN :curr_start AND :curr_end THEN po.price END) - 
                    AVG(CASE WHEN po.date BETWEEN :prev_start AND :prev_end THEN po.price END)) DESC
        LIMIT 20
        """
        
        from datetime import datetime, timedelta
        start = datetime.strptime(period['start'], '%Y-%m-%d')
        end = datetime.strptime(period['end'], '%Y-%m-%d')
        period_days = (end - start).days
        prev_end = start - timedelta(days=1)
        prev_start = prev_end - timedelta(days=period_days)
        
        params = {
            'prev_start': prev_start.strftime('%Y-%m-%d'),
            'prev_end': prev_end.strftime('%Y-%m-%d'),
            'curr_start': period['start'],
            'curr_end': period['end']
        }
        
        return await self.execute_sql(query, params)

api_client = APIClient("${this.config.apiUrl}")
      `;

      this.pyodide.runPython(apiClientCode);

      // Загружаем анализатор
      const analyzerCode = await this.loadAnalyzerCode(metric);

      // Выполняем анализ
      const analysisCode = `
import json
from datetime import datetime

metric_data = ${JSON.stringify(metric)}
filters = ${JSON.stringify(this.dashboardData.filters)}
period = ${JSON.stringify(this.dashboardData.period)}
dashboard_data = ${JSON.stringify(this.dashboardData)}

${analyzerCode}

result = await analyze_metric(metric_data, filters, period, api_client, dashboard_data)
result
      `;

      const result = await this.pyodide.runPythonAsync(analysisCode);
      return result;
    }

    /**
     * Загружает код анализатора для метрики
     */
    async loadAnalyzerCode(metric) {
      const metricName = metric.name.toLowerCase();
      
      // Проверяем, есть ли у метрики thresholds и positive_direction
      // Если есть - используем универсальный анализатор
      if (metric.thresholds || metric.positive_direction !== undefined) {
        return await this.getUniversalAnalyzerCode();
      }
      
      // По умолчанию используем универсальный анализатор для всех метрик
      return await this.getUniversalAnalyzerCode();
    }

    /**
     * Получает код универсального анализатора
     */
    async getUniversalAnalyzerCode() {
      // Загружаем с API или используем встроенный
      try {
        // Загружаем универсальный анализатор
        const analyzerResponse = await fetch(`${this.config.apiUrl}/api/analyzers/code?analyzer_type=universal`);
        let analyzerCode = '';
        if (analyzerResponse.ok) {
          analyzerCode = await analyzerResponse.text();
        }
        
        // Загружаем сборщик данных
        try {
          const collectorResponse = await fetch(`${this.config.apiUrl}/api/analyzers/code?analyzer_type=data_collector`);
          if (collectorResponse.ok) {
            const collectorCode = await collectorResponse.text();
            // Объединяем код анализатора и сборщика
            return collectorCode + '\n\n' + analyzerCode;
          }
        } catch (e) {
          console.warn('Не удалось загрузить сборщик данных, используем только анализатор');
        }
        
        if (analyzerCode) {
          return analyzerCode;
        }
      } catch (e) {
        console.warn('Не удалось загрузить универсальный анализатор с API, используем встроенный');
      }

      // Встроенный универсальный анализатор
      return await this.getDefaultAnalyzerCode();
    }

    async getDefaultAnalyzerCode() {
      // Загружаем универсальный анализатор с API или используем встроенный
      try {
        const response = await fetch(`${this.config.apiUrl}/api/analyzers/code?analyzer_type=universal`);
        if (response.ok) {
          return await response.text();
        }
      } catch (e) {
        console.warn('Не удалось загрузить универсальный анализатор с API, используем встроенный');
      }

      // Встроенный универсальный анализатор (упрощенная версия)
      return `
async def analyze_metric(metric, filters, period, api_client, dashboard=None):
    """Универсальный анализатор метрик"""
    from datetime import datetime
    
    metric_name = metric.get('name', 'Метрика')
    current_value = metric.get('value')
    previous_value = metric.get('comparison_value')
    
    # Анализ на основе трешхолдов
    thresholds = metric.get('thresholds', {})
    positive_direction = metric.get('positive_direction', 'up')
    
    report_parts = []
    report_parts.append(f"Анализ метрики '{metric_name}'")
    report_parts.append("")
    
    if current_value is not None:
        report_parts.append(f"Текущее значение: {current_value:,.2f}")
    
    # Проверка трешхолдов
    issues = []
    if thresholds:
        critical_min = thresholds.get('critical_min')
        critical_max = thresholds.get('critical_max')
        warning_min = thresholds.get('warning_min')
        warning_max = thresholds.get('warning_max')
        
        if critical_min is not None and current_value is not None and current_value < critical_min:
            issues.append(f"КРИТИЧНО: Значение {current_value:,.2f} ниже критического минимума {critical_min:,.2f}")
        if critical_max is not None and current_value is not None and current_value > critical_max:
            issues.append(f"КРИТИЧНО: Значение {current_value:,.2f} выше критического максимума {critical_max:,.2f}")
        if warning_min is not None and current_value is not None and current_value < warning_min:
            if critical_min is None or current_value >= critical_min:
                issues.append(f"ВНИМАНИЕ: Значение {current_value:,.2f} ниже предупреждающего минимума {warning_min:,.2f}")
        if warning_max is not None and current_value is not None and current_value > warning_max:
            if critical_max is None or current_value <= critical_max:
                issues.append(f"ВНИМАНИЕ: Значение {current_value:,.2f} выше предупреждающего максимума {warning_max:,.2f}")
    
    # Анализ изменения
    if previous_value is not None and previous_value != 0 and current_value is not None:
        change_percent = ((current_value - previous_value) / abs(previous_value)) * 100
        change_abs = current_value - previous_value
        
        is_positive = (change_percent > 0) if positive_direction == 'up' else (change_percent < 0)
        change_indicator = "↑" if is_positive else "↓"
        
        report_parts.append(f"Изменение: {change_indicator} {abs(change_percent):.2f}% ({change_abs:+,.2f})")
        
        if not is_positive and abs(change_percent) >= 10:
            issues.append(f"Негативное изменение на {abs(change_percent):.2f}%")
    
    report_parts.append("")
    
    if issues:
        report_parts.append("Выявленные проблемы:")
        for issue in issues:
            report_parts.append(f"• {issue}")
    else:
        report_parts.append("Проблем не выявлено. Метрика в пределах нормы.")
    
    return "\\n".join(report_parts)
      `;
    }

    // Утилиты
    escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }

    formatNumber(num) {
      if (num === null || num === undefined) return 'N/A';
      return new Intl.NumberFormat('ru-RU', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(num);
    }

    formatChange(change) {
      if (!change) return '';
      if (change.type === 'percent') {
        return `${change.value > 0 ? '+' : ''}${change.value.toFixed(2)}%`;
      }
      return '';
    }

    showError(message) {
      console.error(message);
      // Можно показать уведомление пользователю
    }
  }

  // Глобальный объект
  window.BIAnalyzer = BIAnalyzer;

  // Автоматическая инициализация
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      if (window.BIAnalyzerConfig && window.BIAnalyzerConfig.autoInit !== false) {
        const analyzer = new BIAnalyzer(window.BIAnalyzerConfig);
        analyzer.init();
      }
    });
  } else {
    if (window.BIAnalyzerConfig && window.BIAnalyzerConfig.autoInit !== false) {
      const analyzer = new BIAnalyzer(window.BIAnalyzerConfig);
      analyzer.init();
    }
  }
})();
