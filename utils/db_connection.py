#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утилита для подключения к базе данных
"""
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, Engine
from sqlalchemy.pool import QueuePool


def get_db_connection(config: Dict[str, Any]) -> Optional[Engine]:
    """
    Создает подключение к базе данных
    
    Args:
        config: Конфигурация БД
        
    Returns:
        SQLAlchemy Engine или None при ошибке
    """
    try:
        db_config = config.get('database', {})
        
        if not db_config:
            print("Предупреждение: Конфигурация БД не найдена")
            return None
        
        # Формируем строку подключения
        host = db_config.get('host', 'localhost')
        port = db_config.get('port', 5432)
        database = db_config.get('database')
        user = db_config.get('user')
        password = db_config.get('password')
        
        if not all([database, user, password]):
            print("Предупреждение: Не все параметры подключения к БД указаны")
            return None
        
        connection_string = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        
        # Создаем engine с пулом соединений
        pool_size = db_config.get('pool_size', 10)
        max_overflow = db_config.get('max_overflow', 20)
        
        engine = create_engine(
            connection_string,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True  # Проверка соединения перед использованием
        )
        
        return engine
        
    except Exception as e:
        print(f"Ошибка при создании подключения к БД: {e}")
        return None
