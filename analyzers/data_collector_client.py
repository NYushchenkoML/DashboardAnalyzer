"""
Сборщик данных для анализатора
Собирает данные из всех вкладок, виджетов, дрилл-даунов и связанных страниц
"""
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List


class DashboardDataCollector:
    """
    Собирает данные из дашборда, имитируя поведение пользователя:
    - Переключение между вкладками
    - Сбор данных из всех виджетов
    - Выполнение дрилл-даунов
    - Переход на связанные страницы
    """
    
    def __init__(self, api_client: Any):
        """
        Args:
            api_client: Клиент для работы с API (для запросов данных)
        """
        self.api_client = api_client
        self.collected_data = {
            'tabs': {},
            'widgets': {},
            'drilldowns': {},
            'related_pages': {},
            'all_metrics': []
        }
    
    async def collect_all_data(
        self,
        dashboard: Dict[str, Any],
        filters: Dict[str, Any],
        period: Optional[Dict[str, Any]],
        selected_metric: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Собирает все доступные данные из дашборда
        
        Args:
            dashboard: Данные дашборда
            filters: Фильтры
            period: Период анализа
            selected_metric: Выбранная метрика для анализа
            
        Returns:
            Собранные данные со всех источников
        """
        # 1. Собираем данные из текущей вкладки
        current_tab_data = await self._collect_current_tab_data(dashboard, filters, period)
        self.collected_data['tabs']['current'] = current_tab_data
        
        # 2. Собираем данные из всех доступных вкладок
        if dashboard and 'tabs' in dashboard:
            for tab in dashboard.get('tabs', []):
                tab_id = tab.get('id') or tab.get('value')
                if tab_id and tab_id != current_tab_data.get('id'):
                    tab_data = await self._collect_tab_data(tab, filters, period)
                    self.collected_data['tabs'][tab_id] = tab_data
        
        # 3. Собираем данные из всех виджетов
        if dashboard and 'widgets' in dashboard:
            for widget in dashboard.get('widgets', []):
                widget_id = widget.get('id') or widget.get('widget')
                widget_data = await self._collect_widget_data(widget, filters, period)
                self.collected_data['widgets'][widget_id] = widget_data
        
        # 4. Выполняем дрилл-дауны для выбранной метрики
        drilldown_data = await self._perform_drilldowns(selected_metric, filters, period)
        self.collected_data['drilldowns'] = drilldown_data
        
        # 5. Переходим на связанные страницы (если есть)
        related_pages_data = await self._collect_related_pages_data(
            selected_metric, filters, period
        )
        self.collected_data['related_pages'] = related_pages_data
        
        # 6. Собираем все метрики в один список
        self._aggregate_all_metrics()
        
        return self.collected_data
    
    async def _collect_current_tab_data(
        self,
        dashboard: Dict[str, Any],
        filters: Dict[str, Any],
        period: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Собирает данные из текущей активной вкладки"""
        current_tab = {
            'id': dashboard.get('current_tab_id'),
            'name': dashboard.get('current_tab_name'),
            'metrics': dashboard.get('metrics', []),
            'widgets': dashboard.get('widgets', [])
        }
        return current_tab
    
    async def _collect_tab_data(
        self,
        tab: Dict[str, Any],
        filters: Dict[str, Any],
        period: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Собирает данные из конкретной вкладки
        Имитирует переключение на вкладку и сбор данных
        """
        tab_id = tab.get('id') or tab.get('value')
        tab_name = tab.get('name') or tab.get('text', '')
        
        # Если есть API для получения данных вкладки, используем его
        # Иначе возвращаем структуру вкладки
        tab_data = {
            'id': tab_id,
            'name': tab_name,
            'metrics': [],
            'widgets': []
        }
        
        # Пытаемся получить данные через API (если есть endpoint для вкладки)
        if self.api_client and hasattr(self.api_client, 'get_tab_data'):
            try:
                api_data = await self.api_client.get_tab_data(tab_id, filters, period)
                if api_data:
                    tab_data.update(api_data)
            except:
                pass
        
        return tab_data
    
    async def _collect_widget_data(
        self,
        widget: Dict[str, Any],
        filters: Dict[str, Any],
        period: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Собирает данные из виджета
        Включает детализацию виджета, если доступна
        """
        widget_id = widget.get('id') or widget.get('widget')
        widget_title = widget.get('title') or widget.get('name', '')
        
        widget_data = {
            'id': widget_id,
            'title': widget_title,
            'type': widget.get('type'),
            'metrics': [],
            'raw_data': None,
            'details': None
        }
        
        # Пытаемся получить детализацию виджета
        if self.api_client and hasattr(self.api_client, 'get_widget_details'):
            try:
                details = await self.api_client.get_widget_details(widget_id, filters, period)
                if details:
                    widget_data['details'] = details
                    widget_data['raw_data'] = details.get('data', [])
            except:
                pass
        
        # Извлекаем метрики из виджета
        if 'metrics' in widget:
            widget_data['metrics'] = widget['metrics']
        elif 'data' in widget:
            # Пытаемся извлечь метрики из данных виджета
            widget_data['metrics'] = self._extract_metrics_from_widget_data(widget.get('data'))
        
        return widget_data
    
    def _extract_metrics_from_widget_data(self, data: Any) -> List[Dict[str, Any]]:
        """Извлекает метрики из данных виджета"""
        metrics = []
        
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    # Ищем числовые значения как потенциальные метрики
                    for key, value in item.items():
                        if isinstance(value, (int, float)):
                            metrics.append({
                                'name': key,
                                'value': value
                            })
        
        return metrics
    
    async def _perform_drilldowns(
        self,
        metric: Dict[str, Any],
        filters: Dict[str, Any],
        period: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Выполняет дрилл-дауны для метрики
        Собирает детализированные данные по различным измерениям
        """
        drilldown_data = {
            'by_dimensions': {},
            'by_time': {},
            'by_filters': {}
        }
        
        metric_name = metric.get('name', '')
        
        # Дрилл-даун по измерениям (филиал, товар, поставщик и т.д.)
        dimensions = ['branch', 'product', 'supplier', 'category', 'region']
        for dimension in dimensions:
            if dimension in filters or dimension in str(filters).lower():
                try:
                    detail_data = await self._get_drilldown_by_dimension(
                        metric, dimension, filters, period
                    )
                    if detail_data:
                        drilldown_data['by_dimensions'][dimension] = detail_data
                except:
                    pass
        
        # Дрилл-даун по времени (детализация по дням, неделям)
        try:
            time_drilldown = await self._get_drilldown_by_time(metric, filters, period)
            if time_drilldown:
                drilldown_data['by_time'] = time_drilldown
        except:
            pass
        
        # Дрилл-даун по фильтрам (разные комбинации фильтров)
        try:
            filter_drilldown = await self._get_drilldown_by_filters(metric, filters, period)
            if filter_drilldown:
                drilldown_data['by_filters'] = filter_drilldown
        except:
            pass
        
        return drilldown_data
    
    async def _get_drilldown_by_dimension(
        self,
        metric: Dict[str, Any],
        dimension: str,
        filters: Dict[str, Any],
        period: Optional[Dict[str, Any]]
    ) -> Optional[List[Dict[str, Any]]]:
        """Получает детализацию по измерению"""
        if not self.api_client:
            return None
        
        # Формируем SQL запрос для детализации
        query = f"""
        SELECT 
            {dimension} as dimension_value,
            SUM(value) as total_value,
            COUNT(*) as count
        FROM metrics_table
        WHERE metric_name = :metric_name
          AND period_start >= :start
          AND period_end <= :end
        GROUP BY {dimension}
        ORDER BY total_value DESC
        LIMIT 50
        """
        
        params = {
            'metric_name': metric.get('name'),
            'start': period.get('start') if period else None,
            'end': period.get('end') if period else None
        }
        
        try:
            result = await self.api_client.execute_sql(query, params)
            return result
        except:
            return None
    
    async def _get_drilldown_by_time(
        self,
        metric: Dict[str, Any],
        filters: Dict[str, Any],
        period: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Получает детализацию по времени"""
        if not self.api_client or not period:
            return None
        
        # Детализация по дням
        daily_query = """
        SELECT 
            DATE(period_date) as date,
            SUM(value) as daily_value
        FROM metrics_table
        WHERE metric_name = :metric_name
          AND period_date >= :start
          AND period_date <= :end
        GROUP BY DATE(period_date)
        ORDER BY date
        """
        
        params = {
            'metric_name': metric.get('name'),
            'start': period.get('start'),
            'end': period.get('end')
        }
        
        try:
            daily_data = await self.api_client.execute_sql(daily_query, params)
            return {
                'daily': daily_data,
                'trend': self._calculate_trend(daily_data) if daily_data else None
            }
        except:
            return None
    
    def _calculate_trend(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Вычисляет тренд из временных данных"""
        if not data or len(data) < 2:
            return None
        
        values = [item.get('daily_value', 0) for item in data]
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        
        avg_first = sum(first_half) / len(first_half) if first_half else 0
        avg_second = sum(second_half) / len(second_half) if second_half else 0
        
        if avg_first == 0:
            trend_percent = 0
        else:
            trend_percent = ((avg_second - avg_first) / avg_first) * 100
        
        return {
            'direction': 'up' if trend_percent > 0 else 'down',
            'percent': abs(trend_percent),
            'is_significant': abs(trend_percent) > 10
        }
    
    async def _get_drilldown_by_filters(
        self,
        metric: Dict[str, Any],
        filters: Dict[str, Any],
        period: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Получает детализацию по разным комбинациям фильтров"""
        if not self.api_client:
            return None
        
        # Создаем варианты фильтров для сравнения
        filter_variants = []
        
        # Вариант 1: Все фильтры
        filter_variants.append({
            'name': 'all_filters',
            'filters': filters,
            'data': None
        })
        
        # Вариант 2: Без каждого фильтра по очереди
        for filter_key in filters.keys():
            variant_filters = {k: v for k, v in filters.items() if k != filter_key}
            filter_variants.append({
                'name': f'without_{filter_key}',
                'filters': variant_filters,
                'data': None
            })
        
        # Получаем данные для каждого варианта
        for variant in filter_variants:
            try:
                query = """
                SELECT SUM(value) as total_value
                FROM metrics_table
                WHERE metric_name = :metric_name
                  AND period_start >= :start
                  AND period_end <= :end
                """
                
                params = {
                    'metric_name': metric.get('name'),
                    'start': period.get('start') if period else None,
                    'end': period.get('end') if period else None
                }
                
                # Добавляем условия фильтров
                for key, value in variant['filters'].items():
                    query += f" AND {key} = :{key}"
                    params[key] = value
                
                result = await self.api_client.execute_sql(query, params)
                if result:
                    variant['data'] = result[0] if result else None
            except:
                pass
        
        return {
            'variants': filter_variants,
            'comparison': self._compare_filter_variants(filter_variants)
        }
    
    def _compare_filter_variants(self, variants: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Сравнивает варианты фильтров"""
        if not variants or not variants[0].get('data'):
            return None
        
        base_value = variants[0]['data'].get('total_value', 0)
        comparisons = []
        
        for variant in variants[1:]:
            if variant.get('data'):
                variant_value = variant['data'].get('total_value', 0)
                if base_value != 0:
                    change_percent = ((variant_value - base_value) / base_value) * 100
                    comparisons.append({
                        'variant': variant['name'],
                        'value': variant_value,
                        'change_percent': change_percent,
                        'impact': 'high' if abs(change_percent) > 20 else 'medium' if abs(change_percent) > 10 else 'low'
                    })
        
        return {
            'base_value': base_value,
            'comparisons': comparisons,
            'most_impactful': max(comparisons, key=lambda x: abs(x['change_percent'])) if comparisons else None
        }
    
    async def _collect_related_pages_data(
        self,
        metric: Dict[str, Any],
        filters: Dict[str, Any],
        period: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Собирает данные со связанных страниц
        Имитирует переход на страницы дрилл-дауна
        """
        related_pages = {}
        
        # Определяем связанные страницы на основе метрики
        metric_name = metric.get('name', '').lower()
        
        # Если метрика связана с закупками, переходим на страницу закупок
        if any(keyword in metric_name for keyword in ['закуп', 'purchase', 'supplier', 'поставщик']):
            purchase_page_data = await self._get_related_page_data(
                'purchases', metric, filters, period
            )
            if purchase_page_data:
                related_pages['purchases'] = purchase_page_data
        
        # Если метрика связана с продажами, переходим на страницу продаж
        if any(keyword in metric_name for keyword in ['продаж', 'sale', 'revenue', 'выручка']):
            sales_page_data = await self._get_related_page_data(
                'sales', metric, filters, period
            )
            if sales_page_data:
                related_pages['sales'] = sales_page_data
        
        # Если метрика связана с себестоимостью, переходим на страницу себестоимости
        if any(keyword in metric_name for keyword in ['себестоимость', 'cost', 'стоимость']):
            cost_page_data = await self._get_related_page_data(
                'cost', metric, filters, period
            )
            if cost_page_data:
                related_pages['cost'] = cost_page_data
        
        return related_pages
    
    async def _get_related_page_data(
        self,
        page_type: str,
        metric: Dict[str, Any],
        filters: Dict[str, Any],
        period: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Получает данные со связанной страницы"""
        if not self.api_client:
            return None
        
        # Формируем запрос для получения данных со связанной страницы
        query = self._get_page_query(page_type, metric, filters, period)
        
        if not query:
            return None
        
        try:
            result = await self.api_client.execute_sql(query, self._get_page_params(page_type, metric, filters, period))
            return {
                'page_type': page_type,
                'data': result,
                'summary': self._summarize_page_data(result) if result else None
            }
        except:
            return None
    
    def _get_page_query(self, page_type: str, metric: Dict[str, Any], filters: Dict[str, Any], period: Optional[Dict[str, Any]]) -> Optional[str]:
        """Формирует SQL запрос для связанной страницы"""
        base_query = """
        SELECT *
        FROM {table}
        WHERE period_start >= :start AND period_end <= :end
        """
        
        page_queries = {
            'purchases': base_query.format(table='purchases'),
            'sales': base_query.format(table='sales'),
            'cost': base_query.format(table='cost_details')
        }
        
        return page_queries.get(page_type)
    
    def _get_page_params(self, page_type: str, metric: Dict[str, Any], filters: Dict[str, Any], period: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Формирует параметры для запроса связанной страницы"""
        params = {
            'start': period.get('start') if period else None,
            'end': period.get('end') if period else None
        }
        
        # Добавляем фильтры
        params.update(filters)
        
        return params
    
    def _summarize_page_data(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Суммаризует данные со страницы"""
        if not data:
            return None
        
        # Вычисляем статистику
        numeric_values = []
        for item in data:
            for key, value in item.items():
                if isinstance(value, (int, float)):
                    numeric_values.append(value)
        
        if not numeric_values:
            return None
        
        return {
            'count': len(data),
            'sum': sum(numeric_values),
            'avg': sum(numeric_values) / len(numeric_values),
            'min': min(numeric_values),
            'max': max(numeric_values)
        }
    
    def _aggregate_all_metrics(self):
        """Агрегирует все метрики из всех источников"""
        all_metrics = []
        
        # Метрики из вкладок
        for tab_id, tab_data in self.collected_data['tabs'].items():
            if 'metrics' in tab_data:
                for metric in tab_data['metrics']:
                    metric['source'] = f'tab_{tab_id}'
                    all_metrics.append(metric)
        
        # Метрики из виджетов
        for widget_id, widget_data in self.collected_data['widgets'].items():
            if 'metrics' in widget_data:
                for metric in widget_data['metrics']:
                    metric['source'] = f'widget_{widget_id}'
                    all_metrics.append(metric)
        
        # Метрики из дрилл-даунов
        for dimension, drilldown_data in self.collected_data['drilldowns'].get('by_dimensions', {}).items():
            if isinstance(drilldown_data, list):
                for item in drilldown_data:
                    if 'total_value' in item:
                        all_metrics.append({
                            'name': f"{dimension}_detail",
                            'value': item['total_value'],
                            'source': f'drilldown_{dimension}',
                            'dimension_value': item.get('dimension_value')
                        })
        
        self.collected_data['all_metrics'] = all_metrics


async def collect_comprehensive_data(
    metric: Dict[str, Any],
    filters: Dict[str, Any],
    period: Optional[Dict[str, Any]],
    api_client: Any,
    dashboard: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Главная функция для сбора всех данных
    
    Args:
        metric: Выбранная метрика
        filters: Фильтры дашборда
        period: Период анализа
        api_client: Клиент для работы с API
        dashboard: Данные дашборда
        
    Returns:
        Все собранные данные
    """
    collector = DashboardDataCollector(api_client)
    collected_data = await collector.collect_all_data(dashboard, filters, period, metric)
    return collected_data
