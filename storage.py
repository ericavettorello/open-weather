import json
import os
from typing import Optional
from logger import get_logger

# Настройка логирования
logger = get_logger("OpenWeather.Storage")

# Файл для хранения данных пользователей
USER_DATA_FILE = "User_Data.json"


def load_user(user_id: int) -> dict:
    """
    Загружает данные пользователя из файла
    
    Args:
        user_id: ID пользователя
        
    Returns:
        dict: Словарь с данными пользователя или пустой словарь, если пользователь не найден
    """
    user_id_str = str(user_id)
    
    # Проверка существования файла
    if not os.path.exists(USER_DATA_FILE):
        logger.debug(f"Файл {USER_DATA_FILE} не существует для пользователя {user_id}")
        return {}
    
    try:
        with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Возвращаем данные пользователя или пустой словарь
        user_data = data.get(user_id_str, {})
        if user_data:
            logger.debug(f"Данные пользователя {user_id} загружены")
        else:
            logger.debug(f"Пользователь {user_id} не найден в файле")
        return user_data
        
    except (json.JSONDecodeError, IOError, Exception) as e:
        # При ошибке чтения возвращаем пустой словарь
        logger.warning(f"Ошибка загрузки данных пользователя {user_id}: {str(e)}")
        return {}


def save_user(user_id: int, data: dict) -> None:
    """
    Сохраняет данные пользователя в файл
    
    Args:
        user_id: ID пользователя
        data: Словарь с данными пользователя
            Формат: {"city": "...", "lat": ..., "lon": ..., "notifications": {"enabled": true, "interval_h": 2}}
    """
    user_id_str = str(user_id)
    
    # Загружаем существующие данные
    all_data = {}
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
                all_data = json.load(f)
        except (json.JSONDecodeError, IOError, Exception) as e:
            # Если файл поврежден, создаем новый
            logger.warning(f"Ошибка чтения файла {USER_DATA_FILE} при сохранении пользователя {user_id}: {str(e)}")
            all_data = {}
    
    # Обновляем данные пользователя
    all_data[user_id_str] = data
    
    # Сохраняем обратно в файл
    try:
        with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        logger.debug(f"Данные пользователя {user_id} сохранены")
    except (IOError, Exception) as e:
        # При ошибке записи логируем
        logger.error(f"Ошибка сохранения данных пользователя {user_id}: {str(e)}")
        pass

