#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backend API для анализа метрик BI-дашбордов
"""
import sys
import io
from pathlib import Path

# Устанавливаем UTF-8 для вывода
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
import uvicorn

from api.sql_endpoint import add_sql_endpoints

app = FastAPI(title="BI Metrics Analyzer API", version="1.0.0")

# Настройка CORS для работы с browser extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Добавляем SQL endpoints
add_sql_endpoints(app)


@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "message": "BI Metrics Analyzer API",
        "version": "1.0.0",
        "endpoints": {
            "sql": "/api/sql/execute",
            "analyzers": "/api/analyzers/code",
            "health": "/health"
        }
    }


@app.get("/health")
async def health():
    """Проверка здоровья API"""
    return {"status": "ok"}


# Анализ метрик выполняется на клиентской стороне через Pyodide
# Сервер предоставляет только:
# - /api/sql/execute - для выполнения SQL запросов
# - /api/analyzers/code - для получения кода анализаторов


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
