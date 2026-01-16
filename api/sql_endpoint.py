#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API endpoint для выполнения SQL запросов с клиента
Безопасное выполнение SQL запросов через API
"""
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from sqlalchemy import text
import re

from utils.db_connection import get_db_connection
from utils.config_loader import load_config


class SQLRequest(BaseModel):
    """Запрос на выполнение SQL"""
    query: str
    params: Optional[Dict[str, Any]] = None


class SQLResponse(BaseModel):
    """Ответ с результатами SQL запроса"""
    success: bool
    result: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    row_count: Optional[int] = None


# Разрешенные SQL операции (только SELECT для безопасности)
ALLOWED_KEYWORDS = ['SELECT', 'WITH', 'FROM', 'WHERE', 'JOIN', 'GROUP BY', 'ORDER BY', 'LIMIT', 'HAVING']


def validate_sql_query(query: str) -> bool:
    """
    Валидирует SQL запрос - разрешает только SELECT запросы
    
    Args:
        query: SQL запрос
        
    Returns:
        True если запрос валиден, False иначе
    """
    # Удаляем комментарии
    query = re.sub(r'--.*', '', query)
    query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)
    
    # Проверяем, что запрос начинается с SELECT или WITH
    query_upper = query.strip().upper()
    if not (query_upper.startswith('SELECT') or query_upper.startswith('WITH')):
        return False
    
    # Проверяем на запрещенные операции
    forbidden_keywords = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE', 'EXEC', 'EXECUTE']
    for keyword in forbidden_keywords:
        if keyword in query_upper:
            return False
    
    return True


def execute_sql_safely(db_conn, query: str, params: Optional[Dict] = None) -> SQLResponse:
    """
    Безопасно выполняет SQL запрос
    
    Args:
        db_conn: Подключение к БД
        query: SQL запрос
        params: Параметры запроса
        
    Returns:
        Результаты запроса
    """
    if not validate_sql_query(query):
        return SQLResponse(
            success=False,
            error="Разрешены только SELECT запросы"
        )
    
    if not db_conn:
        return SQLResponse(
            success=False,
            error="Подключение к БД не установлено"
        )
    
    try:
        with db_conn.connect() as conn:
            result = conn.execute(text(query), params or {})
            columns = result.keys()
            rows = [dict(zip(columns, row)) for row in result]
            
            return SQLResponse(
                success=True,
                result=rows,
                row_count=len(rows)
            )
    except Exception as e:
        return SQLResponse(
            success=False,
            error=f"Ошибка выполнения SQL: {str(e)}"
        )


def get_db():
    """Dependency для получения подключения к БД"""
    db_config = load_config('db_config.json')
    if not db_config:
        return None
    return get_db_connection(db_config)


def add_sql_endpoints(app: FastAPI):
    """
    Добавляет SQL endpoints к приложению FastAPI
    
    Args:
        app: FastAPI приложение
    """
    
    @app.post("/api/sql/execute", response_model=SQLResponse)
    async def execute_sql(request: SQLRequest, db_conn = Depends(get_db)):
        """
        Выполняет SQL запрос (только SELECT)
        
        Args:
            request: Запрос с SQL и параметрами
            db_conn: Подключение к БД
            
        Returns:
            Результаты запроса
        """
        return execute_sql_safely(db_conn, request.query, request.params)
    
    @app.get("/api/analyzers/code")
    async def get_analyzer_code(analyzer_type: str = "cost"):
        """
        Возвращает Python код анализатора для выполнения на клиенте
        
        Args:
            analyzer_type: Тип анализатора (cost, revenue, financial, default)
            
        Returns:
            Python код анализатора
        """
        analyzers = {
            'universal': 'analyzers/universal_analyzer_client.py',
            'data_collector': 'analyzers/data_collector_client.py',
            'default': 'analyzers/universal_analyzer_client.py'  # Универсальный по умолчанию
        }
        
        analyzer_file = analyzers.get(analyzer_type, analyzers['default'])
        
        try:
            from pathlib import Path
            analyzer_path = Path(__file__).parent.parent / analyzer_file
            if analyzer_path.exists():
                with open(analyzer_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                return "# Анализатор не найден"
        except Exception as e:
            return f"# Ошибка загрузки анализатора: {str(e)}"
