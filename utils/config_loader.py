#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утилита для загрузки конфигурационных файлов
"""
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any


def load_config(config_file: str) -> Optional[Dict[str, Any]]:
    """
    Загружает конфигурационный файл
    
    Args:
        config_file: Имя конфигурационного файла
        
    Returns:
        Словарь с конфигурацией или None если файл не найден
    """
    # Определяем путь к конфигурационным файлам
    config_dir = Path(__file__).parent.parent / 'config'
    config_path = config_dir / config_file
    
    # Если файл не найден, пробуем .example версию
    if not config_path.exists():
        example_path = config_dir / f"{config_file}.example"
        if example_path.exists():
            print(f"Предупреждение: Используется пример конфигурации {config_file}.example")
            config_path = example_path
        else:
            print(f"Предупреждение: Конфигурационный файл {config_file} не найден")
            return None
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Ошибка при парсинге конфигурационного файла {config_file}: {e}")
        return None
    except Exception as e:
        print(f"Ошибка при загрузке конфигурационного файла {config_file}: {e}")
        return None
