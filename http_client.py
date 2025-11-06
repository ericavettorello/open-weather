import requests
from requests.exceptions import RequestException, Timeout


def get(url, params=None, headers=None, timeout=10):
    """
    Выполняет GET запрос к указанному URL с базовой проверкой статуса
    
    Args:
        url: URL для запроса
        params: Параметры запроса (опционально)
        headers: Заголовки запроса (опционально)
        timeout: Таймаут запроса в секундах (по умолчанию 10)
    
    Returns:
        requests.Response: Объект ответа, если запрос успешен
    
    Raises:
        ValueError: Если статус код указывает на ошибку (не 2xx)
        Timeout: Если запрос превысил таймаут
        RequestException: Если произошла другая ошибка запроса
    """
    try:
        response = requests.get(url, params=params, headers=headers, timeout=timeout)
        
        # Базовая проверка статуса
        if not response.ok:
            raise ValueError(
                f"HTTP запрос вернул статус {response.status_code}. "
                f"URL: {url}, Ответ: {response.text[:200]}"
            )
        
        return response
        
    except Timeout:
        raise Timeout(f"Запрос к {url} превысил таймаут {timeout} секунд")
    except RequestException as e:
        raise RequestException(f"Ошибка при выполнении GET запроса к {url}: {str(e)}")

