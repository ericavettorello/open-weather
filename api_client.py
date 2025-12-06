"""
Модуль для выполнения HTTP запросов с ретраями
"""
import time
import requests
from logger import get_logger
from config import MAX_RETRIES, RETRY_DELAYS

# Настройка логирования
logger = get_logger("OpenWeather.APIClient")


def make_request_with_retry(url: str, params: dict, timeout: int = 10):
    """
    Выполняет HTTP запрос с ретраями при ошибках 429 или временных сетевых ошибках
    
    Args:
        url: URL для запроса
        params: Параметры запроса
        timeout: Таймаут запроса в секундах
        
    Returns:
        requests.Response: Объект ответа
        
    Raises:
        ValueError: При ошибках API после всех попыток
    """
    logger.debug(f"Выполнение запроса: {url} с параметрами: {params}")
    last_exception = None
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            logger.debug(f"Получен ответ со статусом {response.status_code}")
            
            # Если успешный ответ или необрабатываемая ошибка - возвращаем сразу
            if response.status_code == 200:
                logger.info(f"Успешный запрос к {url}")
                return response
            elif response.status_code == 401:
                logger.error("Неверный API ключ")
                raise ValueError("Неверный API ключ. Проверьте ключ в файле .env")
            elif response.status_code == 400:
                logger.warning(f"Неверные параметры запроса: {params}")
                raise ValueError("Неверные параметры запроса")
            elif response.status_code == 404:
                # 404 не ретраим, это постоянная ошибка
                logger.warning(f"Ресурс не найден: {url}")
                return response
            elif response.status_code == 429:
                # 429 - Too Many Requests, нужно ретраить
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAYS[attempt]
                    logger.warning(f"Получен статус 429 (слишком много запросов). Повтор через {delay}с... (попытка {attempt + 1}/{MAX_RETRIES})")
                    print(f"Получен статус 429 (слишком много запросов). Повтор через {delay}с... (попытка {attempt + 1}/{MAX_RETRIES})")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"Превышен лимит запросов после {MAX_RETRIES} попыток")
                    raise ValueError(f"Превышен лимит запросов. Статус: {response.status_code}")
            else:
                # Другие ошибки 5xx - ретраим
                if response.status_code >= 500 and attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAYS[attempt]
                    logger.warning(f"Ошибка сервера {response.status_code}. Повтор через {delay}с... (попытка {attempt + 1}/{MAX_RETRIES})")
                    print(f"Ошибка сервера {response.status_code}. Повтор через {delay}с... (попытка {attempt + 1}/{MAX_RETRIES})")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"Ошибка сервера {response.status_code}")
                    return response
                    
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            # Временные сетевые ошибки - ретраим
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt]
                error_type = "таймаут" if isinstance(e, requests.exceptions.Timeout) else "сетевая ошибка"
                logger.warning(f"Временная {error_type}. Повтор через {delay}с... (попытка {attempt + 1}/{MAX_RETRIES})")
                print(f"Временная {error_type}. Повтор через {delay}с... (попытка {attempt + 1}/{MAX_RETRIES})")
                time.sleep(delay)
                last_exception = e
                continue
            else:
                logger.error(f"Сетевая ошибка после всех попыток: {str(e)}")
                if isinstance(e, requests.exceptions.Timeout):
                    raise ValueError("Превышено время ожидания ответа от сервера после всех попыток")
                else:
                    raise ValueError(f"Сетевая ошибка после всех попыток: {str(e)}")
        except requests.exceptions.RequestException as e:
            # Другие ошибки запросов - не ретраим
            logger.error(f"Ошибка при выполнении запроса: {str(e)}")
            raise ValueError(f"Ошибка при выполнении запроса: {str(e)}")
    
    # Если дошли сюда - все попытки исчерпаны
    if last_exception:
        logger.error(f"Все попытки исчерпаны. Последняя ошибка: {str(last_exception)}")
        if isinstance(last_exception, requests.exceptions.Timeout):
            raise ValueError("Превышено время ожидания ответа от сервера после всех попыток")
        else:
            raise ValueError(f"Сетевая ошибка после всех попыток: {str(last_exception)}")
    
    # Если дошли сюда без исключений - это не должно произойти
    logger.error("Не удалось выполнить запрос после всех попыток (неизвестная ошибка)")
    raise ValueError("Не удалось выполнить запрос после всех попыток")

