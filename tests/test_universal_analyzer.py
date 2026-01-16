#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для демонстрации универсального анализатора
на моковых данных
"""
import json
import asyncio
import sys
import io
from datetime import datetime
from typing import Dict, Any, List, Optional

# Устанавливаем UTF-8 для вывода
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Импортируем универсальный анализатор
import sys
sys.path.insert(0, 'analyzers')
from universal_analyzer_client import analyze_metric


class MockAPIClient:
    """Моковый API клиент для тестирования"""
    
    async def execute_sql(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """Моковый метод для выполнения SQL запросов"""
        # Симулируем коррекции себестоимости для тестирования
        if 'cost_corrections' in query.lower():
            period_start = params.get('start', '') if params else ''
            
            # Июль 2025 - коррекция +2,050,214.84 руб.
            if period_start == '2025-07-01':
                return [{'total_correction': 2050214.84}]
            # Август 2025 - коррекция -5,259,272.40 руб.
            elif period_start == '2025-08-01':
                return [{'total_correction': -5259272.40}]
            # Сентябрь 2025 - коррекция (отрицательная себестоимость продолжается)
            elif period_start == '2025-09-01':
                return [{'total_correction': -1000000.00}]
        
        return []


def load_mock_data() -> Dict[str, Any]:
    """Загружает моковые данные"""
    with open('archive/mock_data_year.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def calculate_financial_metrics(mock_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Вычисляет финансовые метрики из моковых данных
    и преобразует их в формат для анализатора
    Симулирует коррекции себестоимости для демонстрации проблем
    """
    metrics_list = []
    monthly_data = mock_data.get('monthly_data', [])
    
    for month_data in monthly_data:
        month = month_data.get('month')
        month_name = month_data.get('month_name')
        metrics = month_data.get('metrics', {})
        
        # Извлекаем базовые метрики
        revenue = metrics.get('dm_order.dish_discount_sum_int', 0)  # Выручка
        foodcost_percent = metrics.get('dm_order.foodcost_perc_of_dish_discount_sum_int', 0)
        
        # Симулируем коррекции себестоимости для проблемных месяцев
        # Июль 2025 - коррекция +2,050,214.84 руб. (себестоимость выросла с 0)
        if month == '2025-07':
            # До коррекции себестоимость была близка к 0, после коррекции стала 2,050,214.84
            cost = 2050214.84
        # Август 2025 - коррекция -5,259,272.40 руб. (отрицательная себестоимость)
        elif month == '2025-08':
            # Базовая себестоимость около 5,940,000 (33% от 18,000,000)
            # Но коррекция -5,259,272.40 делает её отрицательной: 5,940,000 - 5,259,272.40 = 680,727.60
            # Чтобы сделать отрицательной, нужно больше коррекции
            # Или можно установить себестоимость напрямую как отрицательную
            cost = -5259272.40  # Отрицательная себестоимость (как в примере)
        # Сентябрь 2025 - продолжение отрицательной себестоимости
        elif month == '2025-09':
            cost = -1000000.00  # Отрицательная себестоимость
        else:
            cost = revenue * (foodcost_percent / 100)  # Нормальная себестоимость
        
        gross_profit = revenue - cost  # Валовая прибыль
        
        # Для демонстрации добавляем реалистичные значения других метрик
        expenses = revenue * 0.15  # Расходы (15% от выручки)
        other_expenses = revenue * 0.05  # Прочие расходы (5% от выручки)
        net_profit = gross_profit - expenses - other_expenses  # Чистая прибыль
        profitability = (net_profit / revenue * 100) if revenue > 0 else 0
        
        # Формируем метрики для анализатора
        month_metrics = {
            'revenue': {
                'name': 'Сумма со скидкой',
                'value': revenue,
            },
            'cost': {
                'name': 'Себестоимость',
                'value': cost,
            },
            'gross_profit': {
                'name': 'Валовая прибыль',
                'value': gross_profit,
            },
            'expenses': {
                'name': 'Расходы',
                'value': expenses,
            },
            'other_expenses': {
                'name': 'Прочие расходы',
                'value': other_expenses,
            },
            'net_profit': {
                'name': 'Чистая прибыль',
                'value': net_profit,
            },
            'profitability': {
                'name': 'Рентабельность',
                'value': profitability,
            }
        }
        
        metrics_list.append({
            'month': month,
            'month_name': month_name,
            'metrics': month_metrics
        })
    
    return metrics_list


def prepare_dashboard_data(
    all_metrics: List[Dict[str, Any]],
    current_month: str,
    comparison_month: Optional[str] = None
) -> Dict[str, Any]:
    """Подготавливает данные дашборда для анализатора"""
    current_data = next((m for m in all_metrics if m['month'] == current_month), None)
    comparison_data = next((m for m in all_metrics if m['month'] == comparison_month), None) if comparison_month else None
    
    if not current_data:
        return {'metrics': []}
    
    # Формируем список метрик для дашборда
    dashboard_metrics = []
    
    for metric_key, metric_info in current_data['metrics'].items():
        metric_dict = {
            'name': metric_info['name'],
            'value': metric_info['value']
        }
        
        # Добавляем значение для сравнения, если есть
        if comparison_data and metric_key in comparison_data['metrics']:
            metric_dict['comparison_value'] = comparison_data['metrics'][metric_key]['value']
        
        dashboard_metrics.append(metric_dict)
    
    return {'metrics': dashboard_metrics}


async def test_metric_analysis(
    all_metrics: List[Dict[str, Any]],
    metric_name: str,
    current_month: str,
    comparison_month: Optional[str] = None,
    api_client: MockAPIClient = None,
    thresholds: Optional[Dict[str, Any]] = None,
    positive_direction: Optional[str] = None
) -> str:
    """Тестирует анализ конкретной метрики"""
    
    current_data = next((m for m in all_metrics if m['month'] == current_month), None)
    comparison_data = next((m for m in all_metrics if m['month'] == comparison_month), None) if comparison_month else None
    
    if not current_data:
        return f"Данные за {current_month} не найдены"
    
    # Находим метрику
    metric_info = None
    for metric_key, metric_data in current_data['metrics'].items():
        if metric_data['name'].lower() == metric_name.lower():
            metric_info = metric_data
            break
    
    if not metric_info:
        return f"Метрика '{metric_name}' не найдена"
    
    # Формируем объект метрики для анализатора
    metric = {
        'name': metric_info['name'],
        'value': metric_info['value'],
        'comparison_value': None
    }
    
    # Добавляем значение для сравнения
    if comparison_data:
        for metric_key, metric_data in comparison_data['metrics'].items():
            if metric_data['name'].lower() == metric_name.lower():
                metric['comparison_value'] = metric_data['value']
                break
    
    # Добавляем thresholds и positive_direction, если указаны
    if thresholds:
        metric['thresholds'] = thresholds
    if positive_direction:
        metric['positive_direction'] = positive_direction
    
    # Подготавливаем данные дашборда
    dashboard = prepare_dashboard_data(all_metrics, current_month, comparison_month)
    
    # Подготавливаем период
    period = {
        'start': f"{current_month}-01",
        'end': f"{current_month}-31"
    }
    if comparison_month:
        period['comparison'] = {
            'start': f"{comparison_month}-01",
            'end': f"{comparison_month}-31"
        }
    
    # Выполняем анализ
    result = await analyze_metric(
        metric=metric,
        filters={'branch': 'ОШ'},
        period=period,
        api_client=api_client,
        dashboard=dashboard
    )
    
    return result


async def main():
    """Главная функция для демонстрации"""
    print("=" * 80)
    print("ДЕМОНСТРАЦИЯ УНИВЕРСАЛЬНОГО АНАЛИЗАТОРА")
    print("=" * 80)
    print()
    
    # Загружаем моковые данные
    print("Загрузка моковых данных...")
    mock_data = load_mock_data()
    
    # Вычисляем финансовые метрики
    print("Вычисление финансовых метрик...")
    all_metrics = calculate_financial_metrics(mock_data)
    print(f"Загружено {len(all_metrics)} месяцев данных")
    print()
    
    # Создаем API клиент
    api_client = MockAPIClient()
    
    # Пример 1: Анализ финансовой метрики "Сумма со скидкой" (Август vs Июль)
    print("\n" + "=" * 80)
    print("ПРИМЕР 1: Анализ метрики 'Сумма со скидкой' (Август 2025 vs Июль 2025)")
    print("=" * 80)
    print()
    
    result1 = await test_metric_analysis(
        all_metrics,
        metric_name='Сумма со скидкой',
        current_month='2025-08',
        comparison_month='2025-07',
        api_client=api_client,
        thresholds={
            'change_threshold': 10,
            'critical_change_threshold': 50
        },
        positive_direction='up'
    )
    
    print(result1)
    
    # Пример 2: Анализ себестоимости с коррекциями
    print("\n" + "=" * 80)
    print("ПРИМЕР 2: Анализ метрики 'Себестоимость' (Август 2025 vs Июль 2025)")
    print("С коррекциями себестоимости")
    print("=" * 80)
    print()
    
    result2 = await test_metric_analysis(
        all_metrics,
        metric_name='Себестоимость',
        current_month='2025-08',
        comparison_month='2025-07',
        api_client=api_client,
        thresholds={
            'critical_min': 0,
            'warning_min': 0
        },
        positive_direction='down'
    )
    
    print(result2)
    
    # Пример 3: Анализ валовой прибыли
    print("\n" + "=" * 80)
    print("ПРИМЕР 3: Анализ метрики 'Валовая прибыль' (Август 2025 vs Июль 2025)")
    print("=" * 80)
    print()
    
    result3 = await test_metric_analysis(
        all_metrics,
        metric_name='Валовая прибыль',
        current_month='2025-08',
        comparison_month='2025-07',
        api_client=api_client,
        thresholds={
            'critical_min': 0,
            'change_threshold': 20,
            'critical_change_threshold': 50
        },
        positive_direction='up'
    )
    
    print(result3)
    
    # Пример 4: Анализ рентабельности
    print("\n" + "=" * 80)
    print("ПРИМЕР 4: Анализ метрики 'Рентабельность' (Август 2025 vs Июль 2025)")
    print("=" * 80)
    print()
    
    result4 = await test_metric_analysis(
        all_metrics,
        metric_name='Рентабельность',
        current_month='2025-08',
        comparison_month='2025-07',
        api_client=api_client,
        thresholds={
            'critical_min': -100,
            'warning_min': 0,
            'change_threshold': 10,
            'critical_change_threshold': 50
        },
        positive_direction='up'
    )
    
    print(result4)
    
    # Пример 5: Анализ себестоимости в июле (резкий рост с 0)
    print("\n" + "=" * 80)
    print("ПРИМЕР 5: Анализ метрики 'Себестоимость' (Июль 2025 vs Июнь 2025)")
    print("Резкий рост себестоимости с 0 из-за коррекции")
    print("=" * 80)
    print()
    
    result5 = await test_metric_analysis(
        all_metrics,
        metric_name='Себестоимость',
        current_month='2025-07',
        comparison_month='2025-06',
        api_client=api_client,
        thresholds={
            'critical_min': 0,
            'warning_min': 0,
            'change_threshold': 10,
            'critical_change_threshold': 50
        },
        positive_direction='down'
    )
    
    print(result5)


if __name__ == "__main__":
    asyncio.run(main())
