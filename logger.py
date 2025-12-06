"""
Модуль для настройки системы логирования проекта OpenWeather
"""
import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Создаем директорию для логов, если её нет
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Имя файла лога с датой
LOG_FILE = LOGS_DIR / f"openweather_{datetime.now().strftime('%Y%m%d')}.log"

# Формат логов
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(name: str = "OpenWeather", level: str = None) -> logging.Logger:
    """
    Настраивает и возвращает логгер с заданным именем
    
    Args:
        name: Имя логгера (по умолчанию "OpenWeather")
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
               Если не указан, берется из переменной окружения LOG_LEVEL или INFO
    
    Returns:
        logging.Logger: Настроенный логгер
    """
    # Получаем уровень логирования из переменной окружения или используем INFO
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Преобразуем строку в константу уровня логирования
    log_level = getattr(logging, level, logging.INFO)
    
    # Создаем логгер
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Избегаем дублирования обработчиков
    if logger.handlers:
        return logger
    
    # Создаем форматтер
    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    
    # Обработчик для записи в файл с ротацией
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10 МБ
        backupCount=5,  # Храним 5 резервных копий
        encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    
    # Обработчик для вывода в консоль
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # Добавляем обработчики к логгеру
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """
    Получает существующий логгер или создает новый
    
    Args:
        name: Имя логгера (по умолчанию "OpenWeather")
    
    Returns:
        logging.Logger: Логгер
    """
    if name is None:
        name = "OpenWeather"
    
    logger = logging.getLogger(name)
    
    # Если логгер еще не настроен, настраиваем его
    if not logger.handlers:
        return setup_logger(name)
    
    return logger

