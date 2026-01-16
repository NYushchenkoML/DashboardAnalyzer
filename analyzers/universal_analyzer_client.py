"""
Универсальный анализатор метрик для выполнения в Pyodide
Работает с любыми метриками, используя трешхолды и направление позитивного роста
"""
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List


def parse_period(period: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """Парсит текущий период из данных дашборда"""
    if not period:
        today = datetime.now()
        start = today.replace(day=1)
        end = today
        return {
            'start': start.strftime('%Y-%m-%d'),
            'end': end.strftime('%Y-%m-%d')
        }
    
    if isinstance(period, dict):
        if 'start' in period and 'end' in period:
            return {
                'start': period['start'],
                'end': period['end']
            }
    
    return {
        'start': period.get('start', '') if isinstance(period, dict) else '',
        'end': period.get('end', '') if isinstance(period, dict) else ''
    }


def get_comparison_period(period: Optional[Dict[str, Any]], current_period: Dict[str, str]) -> Optional[Dict[str, str]]:
    """Получает период сравнения"""
    if not period:
        return get_previous_period(current_period)
    
    # Если период сравнения указан явно
    if isinstance(period, dict) and 'comparison' in period:
        comp = period['comparison']
        if 'start' in comp and 'end' in comp:
            return {
                'start': comp['start'],
                'end': comp['end']
            }
    
    # По умолчанию - предыдущий период той же длительности
    return get_previous_period(current_period)


def get_previous_period(current_period: Dict[str, str]) -> Dict[str, str]:
    """Получает предыдущий период той же длительности"""
    start = datetime.strptime(current_period['start'], '%Y-%m-%d')
    end = datetime.strptime(current_period['end'], '%Y-%m-%d')
    
    period_days = (end - start).days
    
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=period_days)
    
    return {
        'start': prev_start.strftime('%Y-%m-%d'),
        'end': prev_end.strftime('%Y-%m-%d')
    }


def get_period_name(period: Optional[Dict[str, str]]) -> Optional[str]:
    """Получает название месяца/периода"""
    if not period:
        return None
    
    try:
        start_date = datetime.strptime(period['start'], '%Y-%m-%d')
        month_names = {
            1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель',
            5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Август',
            9: 'Сентябрь', 10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'
        }
        return month_names.get(start_date.month, f'Период {start_date.month}')
    except:
        return 'Период'


def get_metric_value_from_dashboard(
    dashboard_metrics: List[Dict[str, Any]],
    metric_name: str,
    period: Optional[Dict[str, str]] = None
) -> Optional[float]:
    """Извлекает значение метрики из данных дашборда"""
    metric_name_lower = metric_name.lower()
    
    for metric in dashboard_metrics:
        if metric_name_lower in metric.get('name', '').lower():
            # Если указан период, ищем в истории
            if period and 'history' in metric:
                for hist_item in metric.get('history', []):
                    if (hist_item.get('period_start') == period['start'] and
                        hist_item.get('period_end') == period['end']):
                        return hist_item.get('value')
            
            # Иначе возвращаем текущее значение или comparison_value
            if period and period.get('is_comparison'):
                return metric.get('comparison_value')
            return metric.get('value')
    
    return None


def analyze_thresholds(
    metric: Dict[str, Any],
    current_value: Optional[float],
    previous_value: Optional[float]
) -> List[Dict[str, Any]]:
    """
    Анализирует метрику на основе трешхолдов
    
    Args:
        metric: Информация о метрике (с thresholds и positive_direction)
        current_value: Текущее значение
        previous_value: Предыдущее значение
        
    Returns:
        Список выявленных проблем
    """
    issues = []
    
    if current_value is None:
        return issues
    
    thresholds = metric.get('thresholds', {})
    positive_direction = metric.get('positive_direction', 'up')  # 'up' или 'down'
    
    # Проверяем критические пороги
    critical_min = thresholds.get('critical_min')
    critical_max = thresholds.get('critical_max')
    
    if critical_min is not None and current_value < critical_min:
        issues.append({
            'type': 'critical_below_min',
            'severity': 'critical',
            'description': f'Значение {current_value:,.2f} ниже критического минимума {critical_min:,.2f}',
            'value': current_value,
            'threshold': critical_min
        })
    
    if critical_max is not None and current_value > critical_max:
        issues.append({
            'type': 'critical_above_max',
            'severity': 'critical',
            'description': f'Значение {current_value:,.2f} выше критического максимума {critical_max:,.2f}',
            'value': current_value,
            'threshold': critical_max
        })
    
    # Проверяем предупреждающие пороги
    warning_min = thresholds.get('warning_min')
    warning_max = thresholds.get('warning_max')
    
    if warning_min is not None and current_value < warning_min:
        if critical_min is None or current_value >= critical_min:
            issues.append({
                'type': 'warning_below_min',
                'severity': 'warning',
                'description': f'Значение {current_value:,.2f} ниже предупреждающего минимума {warning_min:,.2f}',
                'value': current_value,
                'threshold': warning_min
            })
    
    if warning_max is not None and current_value > warning_max:
        if critical_max is None or current_value <= critical_max:
            issues.append({
                'type': 'warning_above_max',
                'severity': 'warning',
                'description': f'Значение {current_value:,.2f} выше предупреждающего максимума {warning_max:,.2f}',
                'value': current_value,
                'threshold': warning_max
            })
    
    # Анализируем изменение относительно предыдущего значения
    if previous_value is not None and previous_value != 0:
        change_percent = ((current_value - previous_value) / abs(previous_value)) * 100
        
        # Определяем, является ли изменение позитивным
        is_positive = False
        if positive_direction == 'up':
            is_positive = change_percent > 0
        elif positive_direction == 'down':
            is_positive = change_percent < 0
        
        # Проверяем значительные изменения
        change_threshold = thresholds.get('change_threshold', 10)  # Порог значительного изменения в %
        
        if abs(change_percent) >= change_threshold:
            if not is_positive:
                # Негативное изменение
                if abs(change_percent) >= thresholds.get('critical_change_threshold', 50):
                    issues.append({
                        'type': 'critical_negative_change',
                        'severity': 'critical',
                        'description': f'Критическое негативное изменение на {abs(change_percent):.2f}%',
                        'change_percent': change_percent,
                        'current_value': current_value,
                        'previous_value': previous_value
                    })
                else:
                    issues.append({
                        'type': 'warning_negative_change',
                        'severity': 'warning',
                        'description': f'Негативное изменение на {abs(change_percent):.2f}%',
                        'change_percent': change_percent,
                        'current_value': current_value,
                        'previous_value': previous_value
                    })
            else:
                # Позитивное изменение, но проверяем, не слишком ли резкое
                if abs(change_percent) >= thresholds.get('suspicious_positive_change', 200):
                    issues.append({
                        'type': 'suspicious_positive_change',
                        'severity': 'warning',
                        'description': f'Подозрительно резкое позитивное изменение на {change_percent:.2f}%',
                        'change_percent': change_percent,
                        'current_value': current_value,
                        'previous_value': previous_value
                    })
    
    return issues




def detect_metric_type(metric: Dict[str, Any], dashboard: Optional[Dict[str, Any]] = None) -> str:
    """
    Определяет тип метрики для применения специализированной логики анализа
    
    Args:
        metric: Информация о метрике
        dashboard: Данные дашборда
        
    Returns:
        Тип метрики: 'financial', 'sales', 'operations', 'quality', 'general'
    """
    metric_name = metric.get('name', '').lower()
    
    # Финансовые метрики
    financial_keywords = [
        'сумма со скидкой', 'выручка', 'revenue', 'доход',
        'себестоимость', 'cost', 'стоимость',
        'валовая прибыль', 'gross profit', 'gross_profit',
        'чистая прибыль', 'net profit', 'net_profit',
        'рентабельность', 'profitability',
        'расходы', 'expenses', 'прочие расходы',
        'прибыль', 'profit', 'убыток', 'loss'
    ]
    if any(keyword in metric_name for keyword in financial_keywords):
        return 'financial'
    
    # Метрики продаж
    sales_keywords = [
        'продаж', 'sale', 'заказ', 'order',
        'клиент', 'customer', 'покупатель',
        'товар', 'product', 'номенклатура',
        'конверсия', 'conversion', 'чек', 'check'
    ]
    if any(keyword in metric_name for keyword in sales_keywords):
        return 'sales'
    
    # Операционные метрики
    operations_keywords = [
        'время', 'time', 'длительность', 'duration',
        'процесс', 'process', 'операция', 'operation',
        'эффективность', 'efficiency', 'производительность', 'productivity',
        'загрузка', 'load', 'использование', 'utilization'
    ]
    if any(keyword in metric_name for keyword in operations_keywords):
        return 'operations'
    
    # Метрики качества
    quality_keywords = [
        'качество', 'quality', 'дефект', 'defect',
        'ошибка', 'error', 'брак', 'reject',
        'соответствие', 'compliance', 'стандарт', 'standard'
    ]
    if any(keyword in metric_name for keyword in quality_keywords):
        return 'quality'
    
    return 'general'


async def analyze_financial_metric(
    metric: Dict[str, Any],
    filters: Dict[str, Any],
    period: Optional[Dict[str, Any]],
    api_client: Any,
    dashboard: Optional[Dict[str, Any]],
    collected_data: Optional[Dict[str, Any]],
    current_period: Dict[str, str],
    comparison_period: Optional[Dict[str, str]]
) -> List[Dict[str, Any]]:
    """
    Специализированный анализ финансовых метрик
    Включает анализ коррекций себестоимости, искажений показателей
    """
    issues = []
    
    # Собираем все финансовые метрики из дашборда
    financial_metrics = {}
    if dashboard and 'metrics' in dashboard:
        financial_metrics = extract_financial_metrics_from_dashboard(
            dashboard['metrics'], current_period, comparison_period
        )
    
    # Анализируем коррекции себестоимости
    cost_corrections = await analyze_cost_corrections(
        api_client, filters, current_period, comparison_period
    )
    
    # Выявляем критические проблемы финансовых показателей
    cost = financial_metrics.get('cost', {})
    current_cost = cost.get('current')
    previous_cost = cost.get('previous')
    revenue = financial_metrics.get('revenue', {})
    gross_profit = financial_metrics.get('gross_profit', {})
    profitability = financial_metrics.get('profitability', {})
    
    # Проверка отрицательной себестоимости
    if current_cost is not None and current_cost < 0:
        current_profitability = profitability.get('current', 0)
        expenses = financial_metrics.get('expenses', {})
        expenses_change = expenses.get('change', 0)
        
        issues.append({
            'type': 'negative_cost',
            'severity': 'critical',
            'description': f'Себестоимость стала отрицательной {current_cost:,.2f} руб. Рентабельность {current_profitability:.2f}%, расходы выросли на {expenses_change:+.2f}%',
            'cost': current_cost,
            'profitability': current_profitability
        })
    
    # Проверка резкого роста себестоимости с 0 (коррекция)
    if (previous_cost is not None and abs(previous_cost) < 0.01 and 
        current_cost is not None and current_cost > 1000):
        revenue_prev = revenue.get('previous', 0)
        if revenue_prev > 0:
            # Валовая прибыль до коррекции ≈ выручка
            gp_before = revenue_prev
            gp_after = revenue_prev - current_cost
            gp_change = ((gp_after - gp_before) / gp_before) * 100 if gp_before > 0 else 0
            
            issues.append({
                'type': 'cost_spike_from_zero',
                'severity': 'critical',
                'description': f'Себестоимость резко выросла с 0 до {current_cost:,.2f} руб. Валовая прибыль упала на {gp_change:.2f}%',
                'cost_increase': current_cost,
                'gp_change': gp_change
            })
    
    # Проверка искажений из-за коррекций
    if cost_corrections.get('is_distorted'):
        current_correction = cost_corrections.get('current', {}).get('amount', 0)
        previous_correction = cost_corrections.get('previous', {}).get('amount', 0)
        
        issues.append({
            'type': 'cost_correction_distortion',
            'severity': 'warning',
            'description': f'Показатели искажены коррекциями себестоимости: текущий период {current_correction:,.2f} руб., предыдущий {previous_correction:,.2f} руб.',
            'current_correction': current_correction,
            'previous_correction': previous_correction
        })
    
    return issues


def extract_financial_metrics_from_dashboard(
    dashboard_metrics: List[Dict[str, Any]],
    current_period: Dict[str, str],
    comparison_period: Optional[Dict[str, str]]
) -> Dict[str, Dict[str, Any]]:
    """Извлекает финансовые метрики из данных дашборда"""
    metrics = {}
    metric_mapping = {
        'revenue': ['сумма со скидкой', 'выручка', 'revenue', 'доход'],
        'cost': ['себестоимость', 'cost', 'стоимость'],
        'gross_profit': ['валовая прибыль', 'gross profit', 'gross_profit'],
        'expenses': ['расходы', 'expenses'],
        'other_expenses': ['прочие расходы', 'other expenses', 'other_expenses'],
        'net_profit': ['чистая прибыль', 'net profit', 'net_profit'],
        'profitability': ['рентабельность', 'profitability']
    }
    
    for metric_key, keywords in metric_mapping.items():
        current_value = None
        previous_value = None
        change = None
        
        for dashboard_metric in dashboard_metrics:
            metric_name = dashboard_metric.get('name', '').lower()
            if any(keyword in metric_name for keyword in keywords):
                current_value = dashboard_metric.get('value')
                metric_change = dashboard_metric.get('change', {})
                if metric_change and metric_change.get('type') == 'percent':
                    change = metric_change.get('value', 0)
                if 'comparison_value' in dashboard_metric:
                    previous_value = dashboard_metric.get('comparison_value')
                break
        
        if change is None and current_value is not None and previous_value is not None:
            if previous_value != 0:
                change = ((current_value - previous_value) / abs(previous_value)) * 100
        
        metrics[metric_key] = {
            'current': current_value,
            'previous': previous_value,
            'change': change
        }
    
    return metrics


async def analyze_cost_corrections(
    api_client: Any,
    filters: Dict[str, Any],
    current_period: Dict[str, str],
    comparison_period: Optional[Dict[str, str]]
) -> Dict[str, Any]:
    """Анализирует коррекции себестоимости"""
    corrections = {
        'current': {'amount': 0, 'exists': False},
        'previous': {'amount': 0, 'exists': False},
        'is_distorted': False
    }
    
    if not api_client:
        return corrections
    
    try:
        # Запрос коррекций для текущего периода
        query = """
        SELECT SUM(correction_amount) as total_correction
        FROM cost_corrections
        WHERE period_start = :start AND period_end = :end
        """
        
        params = {
            'start': current_period['start'],
            'end': current_period['end']
        }
        
        if 'branch' in filters or 'branch_id' in filters:
            query += " AND branch_id = :branch_id"
            params['branch_id'] = filters.get('branch_id') or filters.get('branch')
        
        result = await api_client.execute_sql(query, params)
        
        if result and len(result) > 0:
            correction_amount = result[0].get('total_correction', 0) or 0
            corrections['current'] = {
                'amount': float(correction_amount),
                'exists': abs(correction_amount) > 0.01
            }
        
        # Аналогично для предыдущего периода
        if comparison_period:
            params_prev = {
                'start': comparison_period['start'],
                'end': comparison_period['end']
            }
            if 'branch' in filters or 'branch_id' in filters:
                params_prev['branch_id'] = filters.get('branch_id') or filters.get('branch')
            
            result_prev = await api_client.execute_sql(query, params_prev)
            
            if result_prev and len(result_prev) > 0:
                correction_amount_prev = result_prev[0].get('total_correction', 0) or 0
                corrections['previous'] = {
                    'amount': float(correction_amount_prev),
                    'exists': abs(correction_amount_prev) > 0.01
                }
        
        corrections['is_distorted'] = (
            corrections['current']['exists'] or 
            corrections['previous']['exists']
        )
    except Exception:
        pass
    
    return corrections


async def analyze_sales_metric(
    metric: Dict[str, Any],
    filters: Dict[str, Any],
    period: Optional[Dict[str, Any]],
    api_client: Any,
    dashboard: Optional[Dict[str, Any]],
    collected_data: Optional[Dict[str, Any]],
    current_period: Dict[str, str],
    comparison_period: Optional[Dict[str, str]]
) -> List[Dict[str, Any]]:
    """
    Специализированный анализ метрик продаж
    Включает анализ по товарам, клиентам, сезонности
    """
    issues = []
    
    # Анализируем дрилл-дауны по товарам/клиентам
    if collected_data:
        drilldowns = collected_data.get('drilldowns', {})
        by_dimensions = drilldowns.get('by_dimensions', {})
        
        # Анализ по товарам
        if 'product' in by_dimensions:
            product_data = by_dimensions['product']
            if isinstance(product_data, list) and len(product_data) > 0:
                # Находим товары с наибольшим падением
                products_with_changes = []
                for item in product_data:
                    if item.get('change_percent'):
                        products_with_changes.append(item)
                
                if products_with_changes:
                    worst_product = min(products_with_changes, 
                                      key=lambda x: x.get('change_percent', 0))
                    if worst_product.get('change_percent', 0) < -20:
                        issues.append({
                            'type': 'product_sales_drop',
                            'severity': 'warning',
                            'description': f'Резкое падение продаж товара "{worst_product.get("dimension_value")}": {worst_product.get("change_percent", 0):.2f}%',
                            'product': worst_product.get('dimension_value'),
                            'change_percent': worst_product.get('change_percent')
                        })
    
    return issues


async def analyze_operations_metric(
    metric: Dict[str, Any],
    filters: Dict[str, Any],
    period: Optional[Dict[str, Any]],
    api_client: Any,
    dashboard: Optional[Dict[str, Any]],
    collected_data: Optional[Dict[str, Any]],
    current_period: Dict[str, str],
    comparison_period: Optional[Dict[str, str]]
) -> List[Dict[str, Any]]:
    """
    Специализированный анализ операционных метрик
    Включает анализ процессов, времени выполнения, эффективности
    """
    issues = []
    
    # Анализ трендов по времени
    if collected_data:
        drilldowns = collected_data.get('drilldowns', {})
        by_time = drilldowns.get('by_time', {})
        trend = by_time.get('trend')
        
        if trend and trend.get('is_significant'):
            if trend['direction'] == 'down' and trend['percent'] > 30:
                issues.append({
                    'type': 'performance_degradation',
                    'severity': 'critical',
                    'description': f'Критическое ухудшение производительности: падение на {trend["percent"]:.2f}%',
                    'trend_percent': trend['percent']
                })
    
    return issues


async def analyze_quality_metric(
    metric: Dict[str, Any],
    filters: Dict[str, Any],
    period: Optional[Dict[str, Any]],
    api_client: Any,
    dashboard: Optional[Dict[str, Any]],
    collected_data: Optional[Dict[str, Any]],
    current_period: Dict[str, str],
    comparison_period: Optional[Dict[str, str]]
) -> List[Dict[str, Any]]:
    """
    Специализированный анализ метрик качества
    Включает анализ дефектов, отклонений, соответствия стандартам
    """
    issues = []
    
    # Анализ по источникам проблем
    if collected_data:
        drilldowns = collected_data.get('drilldowns', {})
        by_dimensions = drilldowns.get('by_dimensions', {})
        
        # Ищем измерения, связанные с источниками проблем
        for dimension, data in by_dimensions.items():
            if isinstance(data, list) and len(data) > 0:
                # Находим источники с наибольшим количеством проблем
                max_issues = max([item.get('total_value', 0) for item in data])
                if max_issues > 0:
                    avg_issues = sum([item.get('total_value', 0) for item in data]) / len(data)
                    if max_issues > avg_issues * 2:
                        worst_source = max(data, key=lambda x: x.get('total_value', 0))
                        issues.append({
                            'type': 'quality_issue_source',
                            'severity': 'warning',
                            'description': f'Высокая концентрация проблем в {dimension} "{worst_source.get("dimension_value")}": {worst_source.get("total_value", 0):.0f} случаев',
                            'source': worst_source.get('dimension_value'),
                            'count': worst_source.get('total_value')
                        })
    
    return issues


async def analyze_metric(
    metric: Dict[str, Any],
    filters: Dict[str, Any],
    period: Optional[Dict[str, Any]],
    api_client: Any,
    dashboard: Optional[Dict[str, Any]] = None
) -> str:
    """
    Главная функция анализа метрики
    Собирает данные из всех источников (вкладки, виджеты, дрилл-дауны, связанные страницы)
    и выполняет комплексный анализ с учетом типа метрики
    
    Args:
        metric: Информация о метрике (с thresholds и positive_direction)
        filters: Фильтры дашборда
        period: Период анализа
        api_client: Клиент для работы с API
        dashboard: Данные дашборда (опционально)
        
    Returns:
        Текстовый отчет с анализом
    """
    # Импортируем сборщик данных
    try:
        from data_collector_client import collect_comprehensive_data
        # Собираем все доступные данные
        collected_data = await collect_comprehensive_data(
            metric, filters, period, api_client, dashboard
        )
    except ImportError:
        # Если сборщик недоступен, используем базовую логику
        collected_data = None
    
    # Парсим периоды
    current_period = parse_period(period)
    comparison_period = get_comparison_period(period, current_period)
    
    # Определяем тип метрики
    metric_type = detect_metric_type(metric, dashboard)
    
    # Получаем значения метрики из всех источников
    current_value = metric.get('value')
    previous_value = metric.get('comparison_value')
    
    # Если собрали данные, используем их для получения значений
    if collected_data:
        # Ищем метрику во всех собранных данных
        all_metrics = collected_data.get('all_metrics', [])
        for m in all_metrics:
            if m.get('name', '').lower() == metric.get('name', '').lower():
                if current_value is None:
                    current_value = m.get('value')
                if previous_value is None:
                    previous_value = m.get('comparison_value')
                break
    
    # Если нет значений, пытаемся получить из дашборда
    if dashboard and 'metrics' in dashboard:
        if current_value is None:
            current_value = get_metric_value_from_dashboard(
                dashboard['metrics'], metric.get('name', ''), current_period
            )
        if previous_value is None and comparison_period:
            previous_value = get_metric_value_from_dashboard(
                dashboard['metrics'], metric.get('name', ''), comparison_period
            )
    
    # Базовый анализ на основе трешхолдов
    issues = analyze_thresholds(metric, current_value, previous_value)
    
    # Специализированный анализ в зависимости от типа метрики
    if metric_type == 'financial':
        financial_issues = await analyze_financial_metric(
            metric, filters, period, api_client, dashboard,
            collected_data, current_period, comparison_period
        )
        issues.extend(financial_issues)
    elif metric_type == 'sales':
        sales_issues = await analyze_sales_metric(
            metric, filters, period, api_client, dashboard,
            collected_data, current_period, comparison_period
        )
        issues.extend(sales_issues)
    elif metric_type == 'operations':
        operations_issues = await analyze_operations_metric(
            metric, filters, period, api_client, dashboard,
            collected_data, current_period, comparison_period
        )
        issues.extend(operations_issues)
    elif metric_type == 'quality':
        quality_issues = await analyze_quality_metric(
            metric, filters, period, api_client, dashboard,
            collected_data, current_period, comparison_period
        )
        issues.extend(quality_issues)
    
    # Общий анализ собранных данных
    if collected_data:
        # Анализируем данные из дрилл-даунов
        drilldown_issues = analyze_drilldown_data(collected_data.get('drilldowns', {}), metric)
        issues.extend(drilldown_issues)
        
        # Анализируем данные из связанных страниц
        related_issues = analyze_related_pages_data(collected_data.get('related_pages', {}), metric)
        issues.extend(related_issues)
    
    # Формируем отчет
    analysis_text = generate_analysis_report(
        metric, issues, current_period, comparison_period, collected_data, metric_type
    )
    
    return analysis_text


def analyze_drilldown_data(
    drilldowns: Dict[str, Any],
    metric: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Анализирует данные из дрилл-даунов и выявляет проблемы
    
    Args:
        drilldowns: Данные дрилл-даунов
        metric: Информация о метрике
        
    Returns:
        Список выявленных проблем
    """
    issues = []
    
    # Анализируем дрилл-даун по измерениям
    by_dimensions = drilldowns.get('by_dimensions', {})
    for dimension, data in by_dimensions.items():
        if isinstance(data, list) and len(data) > 0:
            # Проверяем на аномалии в распределении
            values = [item.get('total_value', 0) for item in data if item.get('total_value')]
            if values:
                max_value = max(values)
                avg_value = sum(values) / len(values)
                
                # Если максимальное значение сильно превышает среднее
                if avg_value > 0 and max_value > avg_value * 3:
                    issues.append({
                        'type': 'dimension_anomaly',
                        'severity': 'warning',
                        'description': f'Аномалия в распределении по {dimension}: максимальное значение в {max_value/avg_value:.1f} раз превышает среднее',
                        'dimension': dimension,
                        'max_value': max_value,
                        'avg_value': avg_value
                    })
    
    # Анализируем тренд по времени
    by_time = drilldowns.get('by_time', {})
    trend = by_time.get('trend')
    if trend and trend.get('is_significant'):
        if trend['direction'] == 'down' and trend['percent'] > 20:
            issues.append({
                'type': 'negative_trend',
                'severity': 'warning',
                'description': f'Отрицательный тренд: падение на {trend["percent"]:.2f}% во второй половине периода',
                'trend_percent': trend['percent']
            })
    
    return issues


def analyze_related_pages_data(
    related_pages: Dict[str, Any],
    metric: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Анализирует данные со связанных страниц
    
    Args:
        related_pages: Данные со связанных страниц
        metric: Информация о метрике
        
    Returns:
        Список выявленных проблем
    """
    issues = []
    
    for page_type, page_data in related_pages.items():
        summary = page_data.get('summary')
        if summary:
            # Проверяем на аномалии в данных
            if summary.get('count', 0) == 0:
                issues.append({
                    'type': 'no_data_on_related_page',
                    'severity': 'warning',
                    'description': f'На связанной странице {page_type} нет данных',
                    'page_type': page_type
                })
            elif summary.get('max', 0) > summary.get('avg', 0) * 5:
                issues.append({
                    'type': 'high_variance_on_related_page',
                    'severity': 'warning',
                    'description': f'Высокая вариативность данных на странице {page_type}: максимальное значение в {summary["max"]/summary["avg"]:.1f} раз превышает среднее',
                    'page_type': page_type
                })
    
    return issues


def generate_analysis_report(
    metric: Dict[str, Any],
    issues: List[Dict[str, Any]],
    current_period: Dict[str, str],
    comparison_period: Optional[Dict[str, str]],
    collected_data: Optional[Dict[str, Any]] = None,
    metric_type: str = 'general'
) -> str:
    """
    Генерирует отчет анализа метрики с учетом всех собранных данных и типа метрики
    
    Args:
        metric: Информация о метрике
        issues: Список выявленных проблем
        current_period: Текущий период
        comparison_period: Период сравнения
        collected_data: Все собранные данные (опционально)
        metric_type: Тип метрики ('financial', 'sales', 'operations', 'quality', 'general')
        
    Returns:
        Текстовый отчет
    """
    report_parts = []
    
    metric_name = metric.get('name', 'Метрика')
    current_value = metric.get('value')
    previous_value = metric.get('comparison_value')
    
    # Вводная часть
    period_name = get_period_name(current_period)
    comparison_name = get_period_name(comparison_period) if comparison_period else None
    
    if comparison_name:
        report_parts.append(
            f"Анализ метрики '{metric_name}' за {period_name} "
            f"(сравнение с {comparison_name})"
        )
    else:
        report_parts.append(f"Анализ метрики '{metric_name}' за {period_name}")
    
    report_parts.append("")
    
    # Информация о собранных данных
    if collected_data:
        tabs_count = len(collected_data.get('tabs', {}))
        widgets_count = len(collected_data.get('widgets', {}))
        drilldowns_count = len(collected_data.get('drilldowns', {}).get('by_dimensions', {}))
        related_pages_count = len(collected_data.get('related_pages', {}))
        
        if tabs_count > 1 or widgets_count > 0 or drilldowns_count > 0:
            report_parts.append("Собраны данные из:")
            if tabs_count > 1:
                report_parts.append(f"  • {tabs_count} вкладок")
            if widgets_count > 0:
                report_parts.append(f"  • {widgets_count} виджетов")
            if drilldowns_count > 0:
                report_parts.append(f"  • {drilldowns_count} дрилл-даунов")
            if related_pages_count > 0:
                report_parts.append(f"  • {related_pages_count} связанных страниц")
            report_parts.append("")
    
    # Текущее значение
    if current_value is not None:
        report_parts.append(f"Текущее значение: {current_value:,.2f}")
    
    # Изменение
    if previous_value is not None and previous_value != 0:
        change_percent = ((current_value - previous_value) / abs(previous_value)) * 100
        change_abs = current_value - previous_value
        
        positive_direction = metric.get('positive_direction', 'up')
        is_positive = (change_percent > 0) if positive_direction == 'up' else (change_percent < 0)
        
        change_indicator = "↑" if is_positive else "↓"
        report_parts.append(
            f"Изменение: {change_indicator} {abs(change_percent):.2f}% "
            f"({change_abs:+,.2f})"
        )
    
    report_parts.append("")
    
    # Критические проблемы
    critical_issues = [i for i in issues if i.get('severity') == 'critical']
    if critical_issues:
        report_parts.append("Критические проблемы")
        report_parts.append("")
        
        for issue in critical_issues:
            report_parts.append(f"• {issue.get('description', '')}")
        
        report_parts.append("")
    
    # Предупреждения
    warning_issues = [i for i in issues if i.get('severity') == 'warning']
    if warning_issues:
        report_parts.append("Предупреждения")
        report_parts.append("")
        
        for issue in warning_issues:
            report_parts.append(f"• {issue.get('description', '')}")
        
        report_parts.append("")
    
    # Если проблем нет
    if not issues:
        report_parts.append("Проблем не выявлено. Метрика в пределах нормы.")
    
    # Детали из дрилл-даунов
    if collected_data and collected_data.get('drilldowns'):
        drilldowns = collected_data['drilldowns']
        by_dimensions = drilldowns.get('by_dimensions', {})
        
        if by_dimensions:
            report_parts.append("Детализация по измерениям:")
            report_parts.append("")
            
            for dimension, data in by_dimensions.items():
                if isinstance(data, list) and len(data) > 0:
                    # Показываем топ-5 значений
                    top_values = sorted(data, key=lambda x: x.get('total_value', 0), reverse=True)[:5]
                    report_parts.append(f"  {dimension}:")
                    for item in top_values:
                        dim_value = item.get('dimension_value', 'N/A')
                        total = item.get('total_value', 0)
                        report_parts.append(f"    • {dim_value}: {total:,.2f}")
                    report_parts.append("")
    
    # Рекомендации
    if issues:
        report_parts.append("Рекомендации:")
        report_parts.append("")
        
        recommendations = generate_recommendations(
            issues, metric, metric_type, collected_data, current_period, comparison_period
        )
        
        for rec in recommendations:
            report_parts.append(f"• {rec}")
    
    return "\n".join(report_parts)


def generate_recommendations(
    issues: List[Dict[str, Any]],
    metric: Dict[str, Any],
    metric_type: str,
    collected_data: Optional[Dict[str, Any]],
    current_period: Dict[str, str],
    comparison_period: Optional[Dict[str, str]]
) -> List[str]:
    """
    Генерирует конкретные рекомендации на основе выявленных проблем
    
    Args:
        issues: Список выявленных проблем
        metric: Информация о метрике
        metric_type: Тип метрики
        collected_data: Собранные данные
        current_period: Текущий период
        comparison_period: Период сравнения
        
    Returns:
        Список рекомендаций (без дублирования)
    """
    recommendations = []
    seen_recommendations = set()  # Для предотвращения дублирования
    
    critical_issues = [i for i in issues if i.get('severity') == 'critical']
    warning_issues = [i for i in issues if i.get('severity') == 'warning']
    
    # Финансовые рекомендации
    if metric_type == 'financial':
        # Отрицательная себестоимость - приоритетная проблема
        negative_cost_issue = next((i for i in critical_issues if i.get('type') == 'negative_cost'), None)
        if negative_cost_issue:
            cost_value = negative_cost_issue.get('cost', 0)
            profitability = negative_cost_issue.get('profitability', 0)
            
            rec1 = (
                f"КРИТИЧЕСКАЯ ПРОБЛЕМА: Себестоимость отрицательная ({cost_value:,.2f} руб.), "
                f"рентабельность аномально высокая ({profitability:.2f}%). "
                f"Это указывает на серьезные ошибки в учете себестоимости, которые требуют немедленного исправления."
            )
            if rec1 not in seen_recommendations:
                recommendations.append(rec1)
                seen_recommendations.add(rec1)
            
            rec2 = (
                "Необходимо срочно провести детальный анализ причин коррекций себестоимости. "
                "Проверьте: ошибки в расчетах, неправильное отражение операций, "
                "проблемы в системе учета, некорректные проводки."
            )
            if rec2 not in seen_recommendations:
                recommendations.append(rec2)
                seen_recommendations.add(rec2)
            
            rec3 = (
                "После выявления причин коррекций: исправьте ошибки в учете, "
                "пересмотрите методы расчета себестоимости, внесите корректирующие проводки. "
                "Если исправление невозможно в текущем периоде, задокументируйте причины и исключите "
                "искаженные данные из операционного анализа, но обязательно проведите мероприятия "
                "по предотвращению повторения такой ситуации."
            )
            if rec3 not in seen_recommendations:
                recommendations.append(rec3)
                seen_recommendations.add(rec3)
            
            rec4 = (
                "Для временного анализа операционной деятельности используйте детализацию по себестоимости "
                "и показатели без учета коррекций, но помните: это временная мера. "
                "Основная задача - устранение причин коррекций."
            )
            if rec4 not in seen_recommendations:
                recommendations.append(rec4)
                seen_recommendations.add(rec4)
        
        # Резкий рост себестоимости с 0 (коррекция в предыдущем периоде)
        cost_spike_issue = next((i for i in critical_issues if i.get('type') == 'cost_spike_from_zero'), None)
        if cost_spike_issue and not negative_cost_issue:  # Только если нет отрицательной себестоимости
            cost_increase = cost_spike_issue.get('cost_increase', 0)
            gp_change = cost_spike_issue.get('gp_change', 0)
            
            rec1 = (
                f"КРИТИЧЕСКАЯ ПРОБЛЕМА: В предыдущем периоде себестоимость резко выросла с 0 до {cost_increase:,.2f} руб. "
                f"из-за коррекции. Валовая прибыль упала на {abs(gp_change):.2f}%. "
                f"Такие коррекции не должны происходить в нормальной работе."
            )
            if rec1 not in seen_recommendations:
                recommendations.append(rec1)
                seen_recommendations.add(rec1)
            
            rec2 = (
                "Необходимо разобраться в причинах коррекции себестоимости в предыдущем периоде. "
                "Проверьте: почему себестоимость была равна 0, что привело к необходимости коррекции, "
                "какие ошибки в учете были допущены."
            )
            if rec2 not in seen_recommendations:
                recommendations.append(rec2)
                seen_recommendations.add(rec2)
            
            rec3 = (
                "Исправьте ошибки в учете и пересмотрите процессы расчета себестоимости. "
                "Внедрите меры контроля для предотвращения повторения: регулярная проверка расчетов, "
                "автоматизация контроля корректности данных, обучение персонала."
            )
            if rec3 not in seen_recommendations:
                recommendations.append(rec3)
                seen_recommendations.add(rec3)
        
        # Искажения из-за коррекций (только если нет более критичных проблем)
        distortion_issue = next((i for i in warning_issues if i.get('type') == 'cost_correction_distortion'), None)
        if distortion_issue and not negative_cost_issue and not cost_spike_issue:
            current_corr = distortion_issue.get('current_correction', 0)
            prev_corr = distortion_issue.get('previous_correction', 0)
            
            rec1 = (
                f"ВНИМАНИЕ: Обнаружены коррекции себестоимости "
                f"(текущий период: {current_corr:,.2f} руб., предыдущий: {prev_corr:,.2f} руб.). "
                f"Коррекции искажают финансовые показатели и указывают на проблемы в учете."
            )
            if rec1 not in seen_recommendations:
                recommendations.append(rec1)
                seen_recommendations.add(rec1)
            
            rec2 = (
                "Проведите анализ причин коррекций. Коррекции себестоимости не должны быть регулярным явлением. "
                "Если они происходят систематически, это указывает на проблемы в процессах учета, "
                "которые требуют исправления."
            )
            if rec2 not in seen_recommendations:
                recommendations.append(rec2)
                seen_recommendations.add(rec2)
            
            rec3 = (
                "После выявления причин: исправьте ошибки в учете, улучшите процессы расчета себестоимости, "
                "внедрите меры контроля. Если исправление невозможно немедленно, исключите искаженные данные "
                "из операционного анализа, но обязательно проведите мероприятия по предотвращению повторения."
            )
            if rec3 not in seen_recommendations:
                recommendations.append(rec3)
                seen_recommendations.add(rec3)
        
        # Критическое падение выручки
        revenue_drop = next((i for i in critical_issues if 
                            ('выручка' in metric.get('name', '').lower() or 'revenue' in metric.get('name', '').lower() or 
                             'сумма со скидкой' in metric.get('name', '').lower()) and 
                            i.get('type') == 'critical_negative_change'), None)
        if revenue_drop:
            change_pct = revenue_drop.get('change_percent', 0)
            rec = (
                f"Выручка критически упала на {abs(change_pct):.2f}%. "
                f"Проанализируйте причины: сезонность, изменения в ассортименте, проблемы с поставками, "
                f"потеря ключевых клиентов."
            )
            if rec not in seen_recommendations:
                recommendations.append(rec)
                seen_recommendations.add(rec)
            
            if collected_data:
                rec2 = "Используйте детализацию по товарам, клиентам и филиалам для выявления основных причин падения."
                if rec2 not in seen_recommendations:
                    recommendations.append(rec2)
                    seen_recommendations.add(rec2)
        
        # Критическое падение прибыли
        profit_drop = next((i for i in critical_issues if 
                           ('прибыль' in metric.get('name', '').lower() or 'profit' in metric.get('name', '').lower()) and 
                           i.get('type') == 'critical_negative_change'), None)
        if profit_drop:
            change_pct = profit_drop.get('change_percent', 0)
            rec = (
                f"Прибыль критически упала на {abs(change_pct):.2f}%. "
                f"Проверьте: изменение себестоимости, рост расходов, падение выручки, "
                f"изменение структуры продаж."
            )
            if rec not in seen_recommendations:
                recommendations.append(rec)
                seen_recommendations.add(rec)
            
            rec2 = "Используйте детализацию по статьям расходов и себестоимости для выявления основных факторов."
            if rec2 not in seen_recommendations:
                recommendations.append(rec2)
                seen_recommendations.add(rec2)
    
    # Рекомендации для метрик продаж
    elif metric_type == 'sales':
        product_drop = next((i for i in warning_issues if i.get('type') == 'product_sales_drop'), None)
        if product_drop:
            product_name = product_drop.get('product', 'товар')
            change_pct = product_drop.get('change_percent', 0)
            rec = (
                f"Продажи товара '{product_name}' упали на {abs(change_pct):.2f}%. "
                f"Проверьте: наличие товара на складе, изменения в цене, конкуренцию, "
                f"сезонность спроса."
            )
            if rec not in seen_recommendations:
                recommendations.append(rec)
                seen_recommendations.add(rec)
            
            rec2 = (
                f"Проанализируйте продажи по клиентам для товара '{product_name}'. "
                f"Возможно, потеря ключевых клиентов или изменение их предпочтений."
            )
            if rec2 not in seen_recommendations:
                recommendations.append(rec2)
                seen_recommendations.add(rec2)
    
    # Рекомендации для операционных метрик
    elif metric_type == 'operations':
        perf_degradation = next((i for i in critical_issues if i.get('type') == 'performance_degradation'), None)
        if perf_degradation:
            trend_pct = perf_degradation.get('trend_percent', 0)
            rec = (
                f"Производительность критически ухудшилась на {abs(trend_pct):.2f}%. "
                f"Проверьте: загрузку системы, проблемы с инфраструктурой, изменения в процессах, "
                f"недостаток ресурсов."
            )
            if rec not in seen_recommendations:
                recommendations.append(rec)
                seen_recommendations.add(rec)
            
            rec2 = "Используйте детализацию по процессам и времени выполнения для выявления узких мест."
            if rec2 not in seen_recommendations:
                recommendations.append(rec2)
                seen_recommendations.add(rec2)
    
    # Рекомендации для метрик качества
    elif metric_type == 'quality':
        quality_issue = next((i for i in warning_issues if i.get('type') == 'quality_issue_source'), None)
        if quality_issue:
            source = quality_issue.get('source', 'источник')
            count = quality_issue.get('count', 0)
            rec = (
                f"Высокая концентрация проблем в источнике '{source}' ({count:.0f} случаев). "
                f"Требуется приоритетный анализ и устранение проблем в этом источнике."
            )
            if rec not in seen_recommendations:
                recommendations.append(rec)
                seen_recommendations.add(rec)
            
            rec2 = (
                f"Проведите детальный анализ процессов в источнике '{source}'. "
                f"Возможно, требуется пересмотр процедур, дополнительное обучение персонала "
                f"или улучшение контроля качества."
            )
            if rec2 not in seen_recommendations:
                recommendations.append(rec2)
                seen_recommendations.add(rec2)
    
    # Общие рекомендации на основе типов проблем
    for issue in critical_issues:
        if issue['type'] == 'critical_below_min':
            threshold = issue.get('threshold', 0)
            value = issue.get('value', 0)
            metric_name = metric.get('name', 'метрика')
            
            rec = (
                f"Значение метрики '{metric_name}' ({value:,.2f}) критически ниже нормы ({threshold:,.2f}). "
                f"Необходимо срочно принять меры для повышения показателя."
            )
            if rec not in seen_recommendations:
                recommendations.append(rec)
                seen_recommendations.add(rec)
            
            if metric_type == 'sales':
                rec2 = "Рассмотрите возможность проведения маркетинговых акций, изменения ценовой политики или улучшения качества товара."
                if rec2 not in seen_recommendations:
                    recommendations.append(rec2)
                    seen_recommendations.add(rec2)
            elif metric_type == 'operations':
                rec2 = "Проверьте эффективность процессов, возможность оптимизации или необходимость дополнительных ресурсов."
                if rec2 not in seen_recommendations:
                    recommendations.append(rec2)
                    seen_recommendations.add(rec2)
        
        elif issue['type'] == 'critical_above_max':
            threshold = issue.get('threshold', 0)
            value = issue.get('value', 0)
            metric_name = metric.get('name', 'метрика')
            
            rec = (
                f"Значение метрики '{metric_name}' ({value:,.2f}) критически выше нормы ({threshold:,.2f}). "
                f"Необходимо принять меры для снижения показателя."
            )
            if rec not in seen_recommendations:
                recommendations.append(rec)
                seen_recommendations.add(rec)
            
            if metric_type == 'operations':
                rec2 = "Проверьте загрузку системы, возможность масштабирования или необходимость оптимизации процессов."
                if rec2 not in seen_recommendations:
                    recommendations.append(rec2)
                    seen_recommendations.add(rec2)
            elif metric_type == 'quality':
                rec2 = "Требуется срочный анализ причин и внедрение корректирующих мер для снижения проблем."
                if rec2 not in seen_recommendations:
                    recommendations.append(rec2)
                    seen_recommendations.add(rec2)
        
        elif issue['type'] == 'critical_negative_change':
            change_pct = issue.get('change_percent', 0)
            metric_name = metric.get('name', 'метрика')
            
            rec = (
                f"Метрика '{metric_name}' критически упала на {abs(change_pct):.2f}%. "
                f"Требуется детальный анализ причин и разработка плана восстановления."
            )
            if rec not in seen_recommendations:
                recommendations.append(rec)
                seen_recommendations.add(rec)
            
            if collected_data:
                rec2 = "Используйте детализацию по измерениям для выявления основных факторов падения."
                if rec2 not in seen_recommendations:
                    recommendations.append(rec2)
                    seen_recommendations.add(rec2)
    
    # Рекомендации на основе дрилл-даунов
    if collected_data and collected_data.get('drilldowns'):
        drilldowns = collected_data['drilldowns']
        by_dimensions = drilldowns.get('by_dimensions', {})
        
        for dimension, data in by_dimensions.items():
            if isinstance(data, list) and len(data) > 0:
                # Находим проблемные значения
                values = [(item.get('dimension_value'), item.get('total_value', 0)) 
                         for item in data]
                avg_value = sum(v[1] for v in values) / len(values) if values else 0
                
                problematic = [v for v in values if v[1] > avg_value * 2]
                if problematic:
                    problematic_names = ', '.join([v[0] for v in problematic[:3]])
                    multiplier = max([v[1]/avg_value for v in problematic]) if avg_value > 0 else 0
                    rec = (
                        f"Обратите внимание на {dimension}: "
                        f"{problematic_names} показывают аномально высокие значения "
                        f"(в {multiplier:.1f} раз выше среднего). Требуется детальный анализ."
                    )
                    if rec not in seen_recommendations:
                        recommendations.append(rec)
                        seen_recommendations.add(rec)
                
                # Находим значения с резким падением
                values_with_changes = [
                    (item.get('dimension_value'), item.get('change_percent', 0), item.get('total_value', 0))
                    for item in data if item.get('change_percent') is not None
                ]
                if values_with_changes:
                    worst = min(values_with_changes, key=lambda x: x[1])
                    if worst[1] < -20:
                        rec = (
                            f"Критическое падение в {dimension} '{worst[0]}': "
                            f"на {abs(worst[1]):.2f}% (текущее значение: {worst[2]:,.2f}). "
                            f"Требуется срочный анализ причин."
                        )
                        if rec not in seen_recommendations:
                            recommendations.append(rec)
                            seen_recommendations.add(rec)
    
    # Если нет специфических рекомендаций, добавляем общие
    if not recommendations and issues:
        rec = "Используйте детализацию по измерениям для более глубокого понимания причин изменений."
        if rec not in seen_recommendations:
            recommendations.append(rec)
            seen_recommendations.add(rec)
        
        if comparison_period:
            rec2 = "Сравните показатели с аналогичными периодами прошлого года для выявления трендов."
            if rec2 not in seen_recommendations:
                recommendations.append(rec2)
                seen_recommendations.add(rec2)
        
        rec3 = "Проверьте влияние внешних факторов (сезонность, изменения в бизнес-процессах, рыночные условия)."
        if rec3 not in seen_recommendations:
            recommendations.append(rec3)
            seen_recommendations.add(rec3)
    
    return recommendations
