import requests
import colorama
from dotenv import load_dotenv
import os
import json
from http_client import get
from logger import get_logger

# Настройка логирования
logger = get_logger("OpenWeather.Main")

# Инициализация colorama
colorama.init()

# Загрузка переменных окружения
load_dotenv()


def make_get_request(url, headers=None, params=None, timeout=10):
    """
    Выполняет GET запрос к указанному URL (тестовая функция с выводом)
    
    Args:
        url: URL для запроса
        headers: Заголовки запроса (опционально)
        params: Параметры запроса (опционально)
        timeout: Таймаут запроса в секундах (по умолчанию 10)
    """
    logger.info(f"GET запрос к {url}")
    logger.debug(f"Параметры: {params}, Заголовки: {headers}, Таймаут: {timeout}с")
    
    print(colorama.Fore.CYAN + f"\n[GET] Отправка запроса к: {url}")
    print(colorama.Fore.YELLOW + f"Параметры: {params}")
    print(colorama.Fore.YELLOW + f"Заголовки: {headers}")
    print(colorama.Fore.YELLOW + f"Таймаут: {timeout}с")
    print(colorama.Style.RESET_ALL)
    
    try:
        # Используем функцию из http_client для базовой проверки статуса
        response = get(url, params=params, headers=headers, timeout=timeout)
        
        logger.info(f"Успешный GET запрос, статус: {response.status_code}")
        print(colorama.Fore.GREEN + f"\n[Статус] {response.status_code} (OK)")
        print(colorama.Fore.GREEN + f"[Заголовки ответа] {dict(response.headers)}")
        print(colorama.Style.RESET_ALL)
        
        try:
            json_response = response.json()
            logger.debug("Получен JSON ответ")
            print(colorama.Fore.CYAN + "\n[Ответ JSON]:")
            print(colorama.Style.RESET_ALL)
            print(response.json())
        except:
            logger.debug("Получен текстовый ответ")
            print(colorama.Fore.CYAN + "\n[Ответ текст]:")
            print(colorama.Style.RESET_ALL)
            print(response.text)
            
        return response
        
    except (requests.exceptions.RequestException, requests.exceptions.Timeout, ValueError) as e:
        logger.error(f"Ошибка GET запроса: {str(e)}")
        print(colorama.Fore.RED + f"\n[Ошибка] {e}")
        print(colorama.Style.RESET_ALL)
        return None


def make_post_request(url, headers=None, data=None, json=None):
    """
    Выполняет POST запрос к указанному URL
    
    Args:
        url: URL для запроса
        headers: Заголовки запроса (опционально)
        data: Данные для отправки (опционально)
        json: JSON данные для отправки (опционально)
    """
    logger.info(f"POST запрос к {url}")
    logger.debug(f"Данные: {data}, JSON: {json}, Заголовки: {headers}")
    
    try:
        print(colorama.Fore.CYAN + f"\n[POST] Отправка запроса к: {url}")
        print(colorama.Fore.YELLOW + f"Данные: {data}")
        print(colorama.Fore.YELLOW + f"JSON: {json}")
        print(colorama.Fore.YELLOW + f"Заголовки: {headers}")
        print(colorama.Style.RESET_ALL)
        
        response = requests.post(url, headers=headers, data=data, json=json)
        
        logger.info(f"Успешный POST запрос, статус: {response.status_code}")
        print(colorama.Fore.GREEN + f"\n[Статус] {response.status_code}")
        print(colorama.Fore.GREEN + f"[Заголовки ответа] {dict(response.headers)}")
        print(colorama.Style.RESET_ALL)
        
        try:
            json_response = response.json()
            logger.debug("Получен JSON ответ")
            print(colorama.Fore.CYAN + "\n[Ответ JSON]:")
            print(colorama.Style.RESET_ALL)
            print(response.json())
        except:
            logger.debug("Получен текстовый ответ")
            print(colorama.Fore.CYAN + "\n[Ответ текст]:")
            print(colorama.Style.RESET_ALL)
            print(response.text)
            
        return response
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка POST запроса: {str(e)}")
        print(colorama.Fore.RED + f"\n[Ошибка] {e}")
        print(colorama.Style.RESET_ALL)
        return None


def main():
    """
    Основная функция для выбора типа запроса
    """
    logger.info("Запуск тестового модуля для API запросов")
    print(colorama.Fore.MAGENTA + "=" * 50)
    print("Тестовый модуль для API запросов")
    print("=" * 50)
    print(colorama.Style.RESET_ALL)
    
    print("\nВыберите тип запроса:")
    print("1. GET запрос")
    print("2. POST запрос")
    print("0. Выход")
    
    choice = input("\nВведите номер (0-2): ").strip()
    
    if choice == "0":
        print(colorama.Fore.YELLOW + "Выход из программы")
        print(colorama.Style.RESET_ALL)
        return
    
    url = input("Введите URL: ").strip()
    
    if not url:
        print(colorama.Fore.RED + "URL не может быть пустым!")
        print(colorama.Style.RESET_ALL)
        return
    
    if choice == "1":
        # GET запрос
        params_input = input("Параметры запроса (через &, например: key1=value1&key2=value2) [Enter для пропуска]: ").strip()
        params = None
        if params_input:
            params = {}
            for param in params_input.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    params[key] = value
        
        headers_input = input("Заголовки (через &, например: Content-Type=application/json) [Enter для пропуска]: ").strip()
        headers = None
        if headers_input:
            headers = {}
            for header in headers_input.split('&'):
                if '=' in header:
                    key, value = header.split('=', 1)
                    headers[key] = value
        
        make_get_request(url, headers=headers, params=params)
        
    elif choice == "2":
        # POST запрос
        data_type = input("Тип данных (1 - JSON, 2 - Form data) [Enter для пропуска]: ").strip()
        
        json_data = None
        form_data = None
        
        if data_type == "1":
            json_input = input("JSON данные (например: {\"key\": \"value\"}) [Enter для пропуска]: ").strip()
            if json_input:
                try:
                    json_data = json.loads(json_input)
                except json.JSONDecodeError:
                    print(colorama.Fore.RED + "Ошибка: Неверный формат JSON")
                    print(colorama.Style.RESET_ALL)
                    return
        elif data_type == "2":
            data_input = input("Form data (через &, например: key1=value1&key2=value2) [Enter для пропуска]: ").strip()
            if data_input:
                form_data = {}
                for param in data_input.split('&'):
                    if '=' in param:
                        key, value = param.split('=', 1)
                        form_data[key] = value
        
        headers_input = input("Заголовки (через &, например: Content-Type=application/json) [Enter для пропуска]: ").strip()
        headers = None
        if headers_input:
            headers = {}
            for header in headers_input.split('&'):
                if '=' in header:
                    key, value = header.split('=', 1)
                    headers[key] = value
        
        make_post_request(url, headers=headers, data=form_data, json=json_data)
        
    else:
        print(colorama.Fore.RED + "Неверный выбор!")
        print(colorama.Style.RESET_ALL)


if __name__ == "__main__":
    main()