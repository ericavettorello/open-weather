"""
Модуль конфигурации проекта OpenWeather
"""
import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# API ключ
API_KEY = os.getenv("API_KEY")

# Базовые URL для OpenWeather API
GEOCODING_URL = "http://api.openweathermap.org/geo/1.0/direct"
WEATHER_URL = "http://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "http://api.openweathermap.org/data/2.5/forecast"
AIR_POLLUTION_URL = "http://api.openweathermap.org/data/2.5/air_pollution"
UV_INDEX_URL = "http://api.openweathermap.org/data/2.5/uvi"

# Файл для кэширования (legacy)
CACHE_FILE = "weather_cache.json"

# Настройки ретраев
MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]  # Экспоненциальная пауза в секундах

# Настройки кэширования
CACHE_TTL = 600  # 10 минут в секундах

