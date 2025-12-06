"""
Модуль для работы с кэшированием данных
"""
import json
import hashlib
from datetime import datetime
from pathlib import Path
from logger import get_logger
from config import CACHE_TTL

# Настройка логирования
logger = get_logger("OpenWeather.Cache")

# Настройки кэширования
CACHE_DIR = Path(".cache")

# Создаем директорию для кэша, если её нет
CACHE_DIR.mkdir(exist_ok=True)


def get_cache_key(url: str, params: dict) -> str:
    """
    Генерирует ключ кэша на основе URL и параметров
    
    Args:
        url: URL запроса
        params: Параметры запроса
        
    Returns:
        str: Хеш-ключ для кэша
    """
    # Создаем строку из URL и отсортированных параметров
    cache_string = f"{url}?{json.dumps(params, sort_keys=True)}"
    # Создаем MD5 хеш
    return hashlib.md5(cache_string.encode('utf-8')).hexdigest()


def get_cache_file(cache_key: str) -> Path:
    """
    Возвращает путь к файлу кэша
    
    Args:
        cache_key: Ключ кэша
        
    Returns:
        Path: Путь к файлу кэша
    """
    return CACHE_DIR / f"{cache_key}.json"


def get_from_cache(cache_key: str) -> dict | None:
    """
    Получает данные из кэша, если они еще актуальны
    
    Args:
        cache_key: Ключ кэша
        
    Returns:
        dict | None: Данные из кэша или None, если кэш устарел или отсутствует
    """
    cache_file = get_cache_file(cache_key)
    
    if not cache_file.exists():
        logger.debug(f"Кэш не найден для ключа: {cache_key}")
        return None
    
    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            cache_data = json.load(f)
        
        # Проверяем время жизни кэша
        cached_at = datetime.fromisoformat(cache_data.get("cached_at", ""))
        now = datetime.now()
        
        if (now - cached_at).total_seconds() > CACHE_TTL:
            # Кэш устарел, удаляем файл
            logger.debug(f"Кэш устарел для ключа: {cache_key}")
            cache_file.unlink()
            return None
        
        logger.debug(f"Данные получены из кэша для ключа: {cache_key}")
        return cache_data.get("data")
        
    except (json.JSONDecodeError, KeyError, ValueError, Exception) as e:
        # Если ошибка чтения, удаляем поврежденный файл
        logger.warning(f"Ошибка чтения кэша для ключа {cache_key}: {str(e)}")
        if cache_file.exists():
            cache_file.unlink()
        return None


def save_to_cache(cache_key: str, data: dict) -> None:
    """
    Сохраняет данные в кэш
    
    Args:
        cache_key: Ключ кэша
        data: Данные для сохранения
    """
    cache_file = get_cache_file(cache_key)
    
    try:
        cache_data = {
            "cached_at": datetime.now().isoformat(),
            "data": data
        }
        
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        
        logger.debug(f"Данные сохранены в кэш для ключа: {cache_key}")
            
    except (IOError, Exception) as e:
        # Игнорируем ошибки записи кэша
        logger.warning(f"Ошибка сохранения кэша для ключа {cache_key}: {str(e)}")
        pass

