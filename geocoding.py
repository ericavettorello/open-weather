"""
Модуль для работы с геокодированием (поиск координат городов)
"""
from logger import get_logger
from config import API_KEY, GEOCODING_URL
from api_client import make_request_with_retry
from i18n import get_language, t

# Настройка логирования
logger = get_logger("OpenWeather.Geocoding")


def get_coordinates(city: str, limit: int = 1) -> tuple[float, float] | None:
    """
    Получает координаты города через OpenWeather Geocoding API
    
    Args:
        city: Название города на русском языке
        limit: Максимальное количество результатов (по умолчанию 1)
        
    Returns:
        tuple[float, float] | None: Кортеж (широта, долгота) или None, если город не найден
    """
    if not API_KEY:
        logger.warning(t("api_key_missing"))
        return None
    
    # Определяем язык для API запроса
    lang = get_language()
    api_lang = "ru" if lang == "ru" else "en"
    
    logger.info(t("searching_coords", city=city))
    params = {
        "q": city,
        "limit": limit,
        "lang": api_lang,
        "appid": API_KEY
    }
    
    try:
        response = make_request_with_retry(GEOCODING_URL, params, timeout=10)
        
        # Проверка статуса ответа
        if response.status_code != 200:
            logger.warning(f"Не удалось получить координаты для города {city}, статус: {response.status_code}")
            return None
        
        data = response.json()
        
        # Проверка на пустой ответ
        if not data or len(data) == 0:
            logger.warning(t("coords_not_found", city=city))
            return None
        
        # Извлечение координат
        lat = data[0].get("lat")
        lon = data[0].get("lon")
        
        if lat is None or lon is None:
            logger.warning(t("coords_not_found", city=city))
            return None
        
        logger.info(t("coords_found", city=city, lat=lat, lon=lon))
        return (float(lat), float(lon))
        
    except (KeyError, IndexError, ValueError, Exception) as e:
        logger.error(f"Ошибка при получении координат для города {city}: {str(e)}")
        return None


def get_cities_list(city: str, limit: int = 5) -> list[dict] | None:
    """
    Получает список городов с совпадающим названием через OpenWeather Geocoding API
    
    Args:
        city: Название города на русском языке
        limit: Максимальное количество результатов (по умолчанию 5)
        
    Returns:
        list[dict] | None: Список словарей с информацией о городах или None при ошибке
        Каждый словарь содержит: name, country, state (если есть), lat, lon
    """
    if not API_KEY:
        logger.warning(t("api_key_missing"))
        return None
    
    # Определяем язык для API запроса
    lang = get_language()
    api_lang = "ru" if lang == "ru" else "en"
    
    logger.info(f"Поиск списка городов для: {city}")
    params = {
        "q": city,
        "limit": limit,
        "lang": api_lang,
        "appid": API_KEY
    }
    
    try:
        response = make_request_with_retry(GEOCODING_URL, params, timeout=10)
        
        if response.status_code != 200:
            logger.warning(f"Не удалось получить список городов для {city}, статус: {response.status_code}")
            return None
        
        data = response.json()
        
        if not data or len(data) == 0:
            logger.warning(t("coords_not_found", city=city))
            return None
        
        cities = []
        for item in data:
            city_info = {
                "name": item.get("name", ""),
                "country": item.get("country", ""),
                "state": item.get("state", ""),
                "lat": item.get("lat"),
                "lon": item.get("lon")
            }
            cities.append(city_info)
        
        logger.info(f"Найдено {len(cities)} городов для {city}")
        return cities
        
    except (KeyError, IndexError, ValueError, Exception) as e:
        logger.error(f"Ошибка при получении списка городов для {city}: {str(e)}")
        return None

