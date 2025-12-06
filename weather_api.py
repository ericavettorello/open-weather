"""
Модуль для работы с API погоды OpenWeather
"""
from logger import get_logger
from config import API_KEY, WEATHER_URL, FORECAST_URL, UV_INDEX_URL
from api_client import make_request_with_retry
from cache import get_cache_key, get_from_cache, save_to_cache
from i18n import get_language, t

# Настройка логирования
logger = get_logger("OpenWeather.WeatherAPI")


def get_current_weather(lat: float, lon: float) -> dict | None:
    """
    Получает текущую погоду по координатам через OpenWeather Current Weather API
    
    Args:
        lat: Широта
        lon: Долгота
        
    Returns:
        dict | None: Словарь с данными о погоде или None при ошибке
    """
    if not API_KEY:
        logger.warning(t("api_key_missing"))
        return None
    
    # Определяем язык для API запроса
    lang = get_language()
    api_lang = "ru" if lang == "ru" else "en"
    
    logger.info(t("getting_current_weather", lat=lat, lon=lon))
    params = {
        "lat": lat,
        "lon": lon,
        "units": "metric",
        "lang": api_lang,
        "appid": API_KEY
    }
    
    # Проверяем кэш
    cache_key = get_cache_key(WEATHER_URL, params)
    cached_data = get_from_cache(cache_key)
    if cached_data is not None:
        logger.debug("Использованы данные из кэша")
        return cached_data
    
    try:
        response = make_request_with_retry(WEATHER_URL, params, timeout=10)
        
        # Проверка статуса ответа
        if response.status_code != 200:
            logger.warning(f"Ошибка получения погоды, статус: {response.status_code}")
            if 400 <= response.status_code < 500:
                return None  # Клиентская ошибка
            elif response.status_code >= 500:
                return None  # Серверная ошибка
            return None
        
        data = response.json()
        
        # Проверка на пустой ответ
        if not data:
            logger.warning("Получен пустой ответ от API")
            return None
        
        # Сохраняем в кэш
        save_to_cache(cache_key, data)
        logger.info("Данные о погоде успешно получены")
        
        return data
        
    except (KeyError, ValueError, Exception) as e:
        # Сетевые ошибки и ошибки обработки - возвращаем None без трейсбека
        logger.error(f"Ошибка при получении погоды: {str(e)}")
        return None


def get_forecast_5d3h(lat: float, lon: float) -> list[dict] | None:
    """
    Получает 5-дневный прогноз погоды с шагом 3 часа через OpenWeather Forecast API
    
    Args:
        lat: Широта
        lon: Долгота
        
    Returns:
        list[dict] | None: Список словарей с данными прогноза погоды или None при ошибке
    """
    if not API_KEY:
        logger.warning(t("api_key_missing"))
        return None
    
    # Определяем язык для API запроса
    lang = get_language()
    api_lang = "ru" if lang == "ru" else "en"
    
    logger.info(t("getting_forecast_5d", lat=lat, lon=lon))
    params = {
        "lat": lat,
        "lon": lon,
        "units": "metric",
        "lang": api_lang,
        "appid": API_KEY
    }
    
    # Проверяем кэш
    cache_key = get_cache_key(FORECAST_URL, params)
    cached_data = get_from_cache(cache_key)
    if cached_data is not None:
        # Кэш содержит полный ответ API, извлекаем list
        forecast_list = cached_data.get("list", [])
        if forecast_list:
            logger.debug("Использованы данные прогноза из кэша")
            return forecast_list
    
    try:
        response = make_request_with_retry(FORECAST_URL, params, timeout=10)
        
        # Проверка статуса ответа
        if response.status_code != 200:
            logger.warning(f"Ошибка получения прогноза, статус: {response.status_code}")
            if 400 <= response.status_code < 500:
                return None  # Клиентская ошибка
            elif response.status_code >= 500:
                return None  # Серверная ошибка
            return None
        
        data = response.json()
        
        # Проверка на пустой ответ
        if not data:
            logger.warning("Получен пустой ответ от API")
            return None
        
        # Сохраняем в кэш полный ответ
        save_to_cache(cache_key, data)
        
        # Извлечение списка прогнозов
        forecast_list = data.get("list", [])
        
        if not forecast_list:
            logger.warning("Список прогнозов пуст")
            return None
        
        logger.info(f"Получено {len(forecast_list)} записей прогноза")
        return forecast_list
        
    except (KeyError, ValueError, Exception) as e:
        # Сетевые ошибки и ошибки обработки - возвращаем None без трейсбека
        logger.error(f"Ошибка при получении прогноза: {str(e)}")
        return None


def get_uv_index(lat: float, lon: float) -> dict | None:
    """
    Получает индекс ультрафиолета через OpenWeather UV Index API
    
    Args:
        lat: Широта
        lon: Долгота
        
    Returns:
        dict | None: Словарь с данными об UV индексе или None при ошибке
        Формат: {"value": float, "dt": int}
    """
    if not API_KEY:
        logger.warning(t("api_key_missing"))
        return None
    
    logger.info(t("getting_uv_index", lat=lat, lon=lon))
    params = {
        "lat": lat,
        "lon": lon,
        "appid": API_KEY
    }
    
    # Проверяем кэш
    cache_key = get_cache_key(UV_INDEX_URL, params)
    cached_data = get_from_cache(cache_key)
    if cached_data is not None:
        logger.debug("Использованы данные UV индекса из кэша")
        return cached_data
    
    try:
        response = make_request_with_retry(UV_INDEX_URL, params, timeout=10)
        
        # Проверка статуса ответа
        if response.status_code != 200:
            logger.warning(f"Ошибка получения UV индекса, статус: {response.status_code}")
            if 400 <= response.status_code < 500:
                return None  # Клиентская ошибка
            elif response.status_code >= 500:
                return None  # Серверная ошибка
            return None
        
        data = response.json()
        
        # Проверка на пустой ответ
        if not data:
            logger.warning("Получен пустой ответ от API")
            return None
        
        # Извлечение UV индекса
        uv_value = data.get("value")
        dt = data.get("dt")
        
        if uv_value is None:
            logger.warning("UV индекс не найден в ответе")
            return None
        
        result = {
            "value": float(uv_value),
            "dt": dt
        }
        
        # Сохраняем в кэш
        save_to_cache(cache_key, result)
        logger.info(f"UV индекс получен: {uv_value}")
        
        return result
        
    except (KeyError, ValueError, Exception) as e:
        # Сетевые ошибки и ошибки обработки - возвращаем None без трейсбека
        logger.error(f"Ошибка при получении UV индекса: {str(e)}")
        return None

