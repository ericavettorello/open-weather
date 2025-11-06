import os
import json
import time
import requests
from dotenv import load_dotenv
from datetime import datetime

# Загрузка ключа API
load_dotenv()
API_KEY = os.getenv("API_KEY")

# Базовые URL для OpenWeather API
GEOCODING_URL = "http://api.openweathermap.org/geo/1.0/direct"
WEATHER_URL = "http://api.openweathermap.org/data/2.5/weather"

# Файл для кэширования
CACHE_FILE = "weather_cache.json"

# Настройки ретраев
MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]  # Экспоненциальная пауза в секундах


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
    last_exception = None
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            
            # Если успешный ответ или необрабатываемая ошибка - возвращаем сразу
            if response.status_code == 200:
                return response
            elif response.status_code == 401:
                raise ValueError("Неверный API ключ. Проверьте ключ в файле .env")
            elif response.status_code == 400:
                raise ValueError("Неверные параметры запроса")
            elif response.status_code == 404:
                # 404 не ретраим, это постоянная ошибка
                return response
            elif response.status_code == 429:
                # 429 - Too Many Requests, нужно ретраить
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAYS[attempt]
                    print(f"Получен статус 429 (слишком много запросов). Повтор через {delay}с... (попытка {attempt + 1}/{MAX_RETRIES})")
                    time.sleep(delay)
                    continue
                else:
                    raise ValueError(f"Превышен лимит запросов. Статус: {response.status_code}")
            else:
                # Другие ошибки 5xx - ретраим
                if response.status_code >= 500 and attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAYS[attempt]
                    print(f"Ошибка сервера {response.status_code}. Повтор через {delay}с... (попытка {attempt + 1}/{MAX_RETRIES})")
                    time.sleep(delay)
                    continue
                else:
                    return response
                    
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            # Временные сетевые ошибки - ретраим
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt]
                error_type = "таймаут" if isinstance(e, requests.exceptions.Timeout) else "сетевая ошибка"
                print(f"Временная {error_type}. Повтор через {delay}с... (попытка {attempt + 1}/{MAX_RETRIES})")
                time.sleep(delay)
                last_exception = e
                continue
            else:
                if isinstance(e, requests.exceptions.Timeout):
                    raise ValueError("Превышено время ожидания ответа от сервера после всех попыток")
                else:
                    raise ValueError(f"Сетевая ошибка после всех попыток: {str(e)}")
        except requests.exceptions.RequestException as e:
            # Другие ошибки запросов - не ретраим
            raise ValueError(f"Ошибка при выполнении запроса: {str(e)}")
    
    # Если дошли сюда - все попытки исчерпаны
    if last_exception:
        if isinstance(last_exception, requests.exceptions.Timeout):
            raise ValueError("Превышено время ожидания ответа от сервера после всех попыток")
        else:
            raise ValueError(f"Сетевая ошибка после всех попыток: {str(last_exception)}")
    
    # Если дошли сюда без исключений - это не должно произойти
    raise ValueError("Не удалось выполнить запрос после всех попыток")


def get_coordinates(city: str, country: str) -> tuple[float, float]:
    """
    Получает координаты города через OpenWeather Geocoding API
    
    Args:
        city: Название города на русском языке
        country: Название страны на русском языке (например, "Россия", "США", "Великобритания")
        
    Returns:
        tuple[float, float]: Кортеж (широта, долгота)
        
    Raises:
        ValueError: При ошибках API или пустом ответе
    """
    if not API_KEY:
        raise ValueError("API ключ не найден. Проверьте файл .env и переменную API_KEY")
    
    # Формируем запрос с указанием города и страны на русском языке
    city_query = f"{city},{country}"
    
    params = {
        "q": city_query,
        "limit": 1,
        "lang": "ru",
        "appid": API_KEY
    }
    
    try:
        response = make_request_with_retry(GEOCODING_URL, params, timeout=10)
        
        # Проверка статуса ответа
        if response.status_code != 200:
            if response.status_code == 404:
                raise ValueError(f"Город '{city}' не найден в стране '{country}'")
            else:
                raise ValueError(f"Ошибка API: статус {response.status_code}")
        
        data = response.json()
        
        # Проверка на пустой ответ
        if not data or len(data) == 0:
            raise ValueError(f"Город '{city}' не найден в стране '{country}'. Проверьте правильность написания")
        
        # Извлечение координат
        lat = data[0].get("lat")
        lon = data[0].get("lon")
        
        if lat is None or lon is None:
            raise ValueError("Не удалось получить координаты города")
        
        return (float(lat), float(lon))
        
    except (KeyError, IndexError, ValueError) as e:
        raise ValueError(f"Ошибка при обработке ответа API: некорректный формат данных")


def get_weather_by_coordinates(lat: float, lon: float) -> dict:
    """
    Получает текущую погоду по координатам через OpenWeather Current Weather API
    
    Args:
        lat: Широта
        lon: Долгота
        
    Returns:
        dict: Словарь с данными о погоде
        
    Raises:
        ValueError: При ошибках API или невалидном ключе
    """
    if not API_KEY:
        raise ValueError("API ключ не найден. Проверьте файл .env и переменную API_KEY")
    
    params = {
        "lat": lat,
        "lon": lon,
        "units": "metric",
        "lang": "ru",
        "appid": API_KEY
    }
    
    try:
        response = make_request_with_retry(WEATHER_URL, params, timeout=10)
        
        # Проверка статуса ответа
        if response.status_code != 200:
            if response.status_code == 400:
                raise ValueError("Неверные координаты")
            else:
                raise ValueError(f"Ошибка API: статус {response.status_code}")
        
        data = response.json()
        
        # Проверка на пустой ответ
        if not data:
            raise ValueError("Получен пустой ответ от API")
        
        return data
        
    except (KeyError, ValueError) as e:
        raise ValueError(f"Ошибка при обработке ответа API: некорректный формат данных")


def save_weather_cache(city: str, country: str, weather_data: dict):
    """
    Сохраняет последний успешный ответ о погоде в кэш
    
    Args:
        city: Название города
        country: Название страны
        weather_data: Данные о погоде
    """
    try:
        cache_data = {
            "city": city,
            "country": country,
            "fetched_at": datetime.now().isoformat(),
            "weather_data": weather_data
        }
        
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        # Не прерываем выполнение программы при ошибке сохранения кэша
        print(f"Предупреждение: Не удалось сохранить кэш: {e}")


def main():
    """
    CLI интерфейс для получения погоды
    """
    print("=" * 50)
    print("Программа прогноза погоды")
    print("=" * 50)
    
    try:
        # Запрос города у пользователя
        city = input("\nВведите название города (на русском языке): ").strip()
        
        if not city:
            print("Ошибка: Название города не может быть пустым")
            return
        
        # Запрос страны у пользователя
        country = input("Введите название страны (на русском языке, например: Россия, США, Великобритания): ").strip()
        
        if not country:
            print("Ошибка: Название страны не может быть пустым")
            return
        
        # Получение координат
        print(f"\nПоиск координат для города '{city}' в стране '{country}'...")
        lat, lon = get_coordinates(city, country)
        
        # Получение погоды
        print(f"Получение данных о погоде...")
        weather_data = get_weather_by_coordinates(lat, lon)
        
        # Сохранение в кэш
        save_weather_cache(city, country, weather_data)
        
        # Извлечение данных
        temperature = weather_data.get("main", {}).get("temp")
        description = weather_data.get("weather", [{}])[0].get("description", "нет данных")
        
        if temperature is None:
            print("Ошибка: Не удалось получить данные о температуре")
            return
        
        # Вывод результата
        print(f"\nПогода в {city}: {temperature}°C, {description}")
        
    except ValueError as e:
        print(f"\nОшибка: {e}")
    except Exception as e:
        print(f"\nНеожиданная ошибка: {e}")


if __name__ == "__main__":
    main()

