"""
Модуль для работы с данными о загрязнении воздуха
"""
from logger import get_logger
from config import API_KEY, AIR_POLLUTION_URL
from api_client import make_request_with_retry
from cache import get_cache_key, get_from_cache, save_to_cache
from i18n import t

# Настройка логирования
logger = get_logger("OpenWeather.AirPollution")


def get_air_pollution(lat: float, lon: float) -> dict | None:
    """
    Получает данные о загрязнении воздуха через OpenWeather Air Pollution API
    
    Args:
        lat: Широта
        lon: Долгота
        
    Returns:
        dict | None: Словарь с данными о загрязнении воздуха или None при ошибке
    """
    if not API_KEY:
        logger.warning(t("api_key_missing"))
        return None
    
    logger.info(t("getting_pollution", lat=lat, lon=lon))
    params = {
        "lat": lat,
        "lon": lon,
        "appid": API_KEY
    }
    
    # Проверяем кэш
    cache_key = get_cache_key(AIR_POLLUTION_URL, params)
    cached_data = get_from_cache(cache_key)
    if cached_data is not None:
        logger.debug("Использованы данные о загрязнении из кэша")
        return cached_data
    
    try:
        response = make_request_with_retry(AIR_POLLUTION_URL, params, timeout=10)
        
        # Проверка статуса ответа
        if response.status_code != 200:
            logger.warning(f"Ошибка получения данных о загрязнении, статус: {response.status_code}")
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
        
        # Извлечение данных из list[0]
        pollution_list = data.get("list", [])
        
        if not pollution_list or len(pollution_list) == 0:
            logger.warning("Список данных о загрязнении пуст")
            return None
        
        # Получаем первый элемент списка с components
        pollution_data = pollution_list[0]
        components = pollution_data.get("components", {})
        
        # Формируем результат с components
        result = {
            "dt": pollution_data.get("dt"),
            "main": pollution_data.get("main", {}),
            "components": components,
            "aqi": pollution_data.get("main", {}).get("aqi")
        }
        
        # Сохраняем в кэш
        save_to_cache(cache_key, result)
        logger.info("Данные о загрязнении воздуха успешно получены")
        
        return result
        
    except (KeyError, ValueError, Exception) as e:
        # Сетевые ошибки и ошибки обработки - возвращаем None без трейсбека
        logger.error(f"Ошибка при получении данных о загрязнении: {str(e)}")
        return None


def analyze_air_pollution(components: dict, extended: bool = False) -> dict:
    """
    Анализирует компоненты загрязнения воздуха и возвращает сводный статус и детали
    
    Args:
        components: Словарь с компонентами загрязнения (co, no, no2, o3, so2, pm2_5, pm10, nh3)
        extended: Если True, возвращает расширенную информацию
        
    Returns:
        dict: Словарь со сводным статусом и деталями по каждому компоненту
    """
    # Нормативы качества воздуха (µg/m³) на основе рекомендаций ВОЗ
    thresholds = {
        "pm2_5": {"good": 12, "moderate": 35, "unhealthy": 70},
        "pm10": {"good": 50, "moderate": 100, "unhealthy": 200},
        "co": {"good": 10000, "moderate": 15000, "unhealthy": 30000},
        "no2": {"good": 200, "moderate": 400, "unhealthy": 800},
        "o3": {"good": 100, "moderate": 160, "unhealthy": 240},
        "so2": {"good": 125, "moderate": 250, "unhealthy": 500},
        "nh3": {"good": 200, "moderate": 400, "unhealthy": 800},
        "no": {"good": 50, "moderate": 100, "unhealthy": 200}
    }
    
    # Названия компонентов на русском
    component_names = {
        "co": "Угарный газ (CO)",
        "no": "Оксид азота (NO)",
        "no2": "Диоксид азота (NO₂)",
        "o3": "Озон (O₃)",
        "so2": "Диоксид серы (SO₂)",
        "pm2_5": "Твердые частицы PM2.5",
        "pm10": "Твердые частицы PM10",
        "nh3": "Аммиак (NH₃)"
    }
    
    # Единицы измерения
    units = {
        "co": "µg/m³",
        "no": "µg/m³",
        "no2": "µg/m³",
        "o3": "µg/m³",
        "so2": "µg/m³",
        "pm2_5": "µg/m³",
        "pm10": "µg/m³",
        "nh3": "µg/m³"
    }
    
    def get_status(value: float, component: str) -> str:
        """Определяет статус компонента на основе его значения"""
        if component not in thresholds:
            return "unknown"
        
        thresh = thresholds[component]
        if value <= thresh["good"]:
            return "good"
        elif value <= thresh["moderate"]:
            return "moderate"
        elif value <= thresh["unhealthy"]:
            return "unhealthy"
        else:
            return "very_unhealthy"
    
    def get_status_name(status: str) -> str:
        """Возвращает название статуса на текущем языке"""
        status_names = {
            "good": t("pollution_good"),
            "moderate": t("pollution_moderate"),
            "unhealthy": t("pollution_unhealthy"),
            "very_unhealthy": t("pollution_very_unhealthy"),
            "unknown": t("pollution_unknown")
        }
        return status_names.get(status, t("pollution_unknown"))
    
    # Анализ каждого компонента
    details = {}
    statuses = []
    
    for component, value in components.items():
        if value is None:
            continue
            
        status = get_status(value, component)
        statuses.append(status)
        
        component_detail = {
            "value": value,
            "unit": units.get(component, "µg/m³"),
            "status": status,
            "status_name": get_status_name(status)
        }
        
        if extended and component in thresholds:
            thresh = thresholds[component]
            component_detail["thresholds"] = {
                "good": thresh["good"],
                "moderate": thresh["moderate"],
                "unhealthy": thresh["unhealthy"]
            }
        
        details[component] = component_detail
    
    # Определение сводного статуса (берем худший)
    status_priority = {
        "very_unhealthy": 4,
        "unhealthy": 3,
        "moderate": 2,
        "good": 1,
        "unknown": 0
    }
    
    if not statuses:
        overall_status = "unknown"
    else:
        overall_status = max(statuses, key=lambda s: status_priority.get(s, 0))
    
    # Формирование результата
    result = {
        "overall_status": overall_status,
        "overall_status_name": get_status_name(overall_status),
        "components": details
    }
    
    if extended:
        result["summary"] = {
            "total_components": len(components),
            "analyzed_components": len(details),
            "good_count": sum(1 for s in statuses if s == "good"),
            "moderate_count": sum(1 for s in statuses if s == "moderate"),
            "unhealthy_count": sum(1 for s in statuses if s in ["unhealthy", "very_unhealthy"])
        }
    
    return result

