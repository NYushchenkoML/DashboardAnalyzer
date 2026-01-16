#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Клиент для работы с внешними API
"""
import requests
from typing import Optional, Dict, Any
from urllib.parse import urljoin


class APIClient:
    """Клиент для работы с внешними API"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация клиента
        
        Args:
            config: Конфигурация API
        """
        api_config = config.get('api', {})
        self.base_url = api_config.get('base_url', '')
        self.timeout = api_config.get('timeout', 30)
        self.retry_count = api_config.get('retry_count', 3)
        
        # Настройка аутентификации
        auth_config = api_config.get('auth', {})
        self.auth_type = auth_config.get('type', 'bearer')
        self.auth_token = auth_config.get('token', '')
        
        # Создаем сессию
        self.session = requests.Session()
        if self.auth_type == 'bearer' and self.auth_token:
            self.session.headers.update({
                'Authorization': f'Bearer {self.auth_token}'
            })
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Выполняет GET запрос
        
        Args:
            endpoint: Конечная точка API
            params: Параметры запроса
            
        Returns:
            JSON ответ или None при ошибке
        """
        url = urljoin(self.base_url, endpoint)
        
        for attempt in range(self.retry_count):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if attempt == self.retry_count - 1:
                    print(f"Ошибка при выполнении GET запроса к {url}: {e}")
                    return None
                continue
        
        return None
    
    def post(self, endpoint: str, data: Optional[Dict] = None, json_data: Optional[Dict] = None) -> Optional[Dict]:
        """
        Выполняет POST запрос
        
        Args:
            endpoint: Конечная точка API
            data: Данные для отправки (form-data)
            json_data: JSON данные для отправки
            
        Returns:
            JSON ответ или None при ошибке
        """
        url = urljoin(self.base_url, endpoint)
        
        for attempt in range(self.retry_count):
            try:
                if json_data:
                    response = self.session.post(url, json=json_data, timeout=self.timeout)
                else:
                    response = self.session.post(url, data=data, timeout=self.timeout)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if attempt == self.retry_count - 1:
                    print(f"Ошибка при выполнении POST запроса к {url}: {e}")
                    return None
                continue
        
        return None
