"""
Модуль для работы с многоязычностью (i18n)
"""
import os
from typing import Dict, Optional
from logger import get_logger

# Настройка логирования
logger = get_logger("OpenWeather.i18n")

# Поддерживаемые языки
SUPPORTED_LANGUAGES = ["ru", "en"]
DEFAULT_LANGUAGE = "ru"

# Глобальная переменная для текущего языка
_current_language = DEFAULT_LANGUAGE

# Словари переводов
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "ru": {
        # Общие сообщения
        "error": "Ошибка",
        "warning": "Предупреждение",
        "success": "Успешно",
        "not_found": "Не найдено",
        "unknown_error": "Неизвестная ошибка",
        
        # Language Selection
        "select_language_title": "Выберите язык / Select Language",
        "language_russian": "Русский (Russian)",
        "language_english": "English (Английский)",
        "enter_language_choice": "Введите номер (1-2) / Enter number (1-2):",
        "invalid_language_choice": "Неверный выбор. Введите 1 или 2 / Invalid choice. Enter 1 or 2",
        
        # Weather App
        "weather_app_title": "Программа прогноза погоды",
        "enter_city": "Введите название города (на русском языке):",
        "city_empty": "Ошибка: Название города не может быть пустым",
        "searching_coordinates": "Поиск координат для города '{city}'...",
        "city_not_found": "Ошибка: Город '{city}' не найден",
        "multiple_cities_found": "Найдено несколько городов с названием '{city}':",
        "select_city_number": "Выберите номер города (1-{count}):",
        "invalid_number": "Пожалуйста, введите число",
        "invalid_range": "Пожалуйста, введите число от 1 до {count}",
        "city_found": "Найден город: {location}",
        "forecast_type": "Выберите тип прогноза:",
        "current_weather": "Текущая погода",
        "forecast_5days": "Прогноз на 5 дней (с шагом 3 часа)",
        "enter_choice": "Введите номер (1 или 2):",
        "getting_weather": "Получение данных о погоде...",
        "weather_error": "Ошибка: Не удалось получить данные о погоде. Проверьте подключение к интернету и API ключ.",
        "temperature_error": "Ошибка: Не удалось получить данные о температуре",
        "weather_in": "Погода в {location}: {temp}°C, {description}",
        "getting_forecast": "Получение прогноза на 5 дней...",
        "forecast_error": "Ошибка: Не удалось получить прогноз погоды. Проверьте подключение к интернету и API ключ.",
        "forecast_for": "Прогноз погоды на 5 дней для {location}:",
        "temperature": "Температура",
        "feels_like": "ощущается как",
        "description": "Описание",
        "humidity": "Влажность",
        "wind_speed": "Скорость ветра",
        "invalid_choice": "Ошибка: Неверный выбор. Выберите 1 или 2",
        "cache_save_error": "Предупреждение: Не удалось сохранить кэш: {error}",
        
        # API Messages
        "api_key_missing": "API_KEY не установлен",
        "searching_coords": "Поиск координат для города: {city}",
        "coords_not_found": "Город {city} не найден",
        "coords_found": "Найдены координаты для {city}: ({lat}, {lon})",
        "getting_current_weather": "Получение текущей погоды для координат: ({lat}, {lon})",
        "getting_forecast_5d": "Получение прогноза на 5 дней для координат: ({lat}, {lon})",
        "getting_uv_index": "Получение UV индекса для координат: ({lat}, {lon})",
        "getting_pollution": "Получение данных о загрязнении воздуха для координат: ({lat}, {lon})",
        
        # Bot Messages
        "bot_welcome": "🌍 Добро пожаловать в бот прогноза погоды!\n\nВыберите действие из меню:",
        "bot_current_weather": "🌤️ Текущая погода",
        "bot_forecast_5days": "📅 Прогноз на 5 дней",
        "bot_my_location": "📍 Моя геолокация",
        "bot_compare_cities": "🔍 Сравнить города",
        "bot_extended_data": "📊 Расширенные данные",
        "bot_notifications": "🔔 Уведомления",
        "bot_enter_city": "Введите название города:",
        "bot_enter_city_for_forecast": "Введите название города для прогноза:",
        "bot_enter_city_1": "Введите название первого города:",
        "bot_enter_city_2": "Введите название второго города:",
        "bot_city_not_found_compare": "❌ Один из городов не найден",
        "bot_send_location": "📍 Отправить геолокацию",
        "bot_send_location_prompt": "📍 Пожалуйста, отправьте вашу геолокацию или введите название города:",
        "bot_select_weather_method": "Выберите способ получения погоды:",
        "bot_cancel": "❌ Отмена",
        "bot_cancelled": "Отменено",
        "bot_select_action": "Выберите действие:",
        "bot_city_not_found": "❌ Город '{city}' не найден. Попробуйте еще раз:",
        "bot_multiple_cities_found": "Найдено несколько городов. Выберите нужный:",
        "bot_weather_in": "🌤️ Погода в {city}:",
        "bot_temperature": "🌡️ Температура: {temp}°C",
        "bot_feels_like": "💭 Ощущается как: {feels_like}°C",
        "bot_description": "☁️ Описание: {description}",
        "bot_humidity": "💧 Влажность: {humidity}%",
        "bot_pressure": "📊 Давление: {pressure} гПа",
        "bot_wind": "💨 Скорость ветра: {wind_speed} м/с",
        "bot_weather_error": "❌ Не удалось получить данные о погоде",
        "bot_forecast_error": "❌ Не удалось получить прогноз",
        "bot_forecast_5days_for": "📅 Прогноз на 5 дней для {city}:",
        "bot_select_day": "Выберите день для детального просмотра:",
        "bot_select_day_forecast": "📅 Выберите день для просмотра прогноза:",
        "bot_difference": "Разница",
        "bot_forecast_for_date": "📅 Прогноз на {date} ({weekday}):",
        "bot_compare_cities_title": "🔍 Сравнение городов:",
        "bot_current_weather_title": "🌤️ Текущая погода:",
        "bot_location_saved": "✅ Геолокация успешно сохранена!",
        "bot_use_location": "📍 Использовать мою геолокацию",
        "bot_enter_city_btn": "🏙️ Ввести город",
        "bot_location_not_saved": "❌ Геолокация не сохранена. Пожалуйста, отправьте её сначала.",
        "bot_check_extended_data": "А теперь посмотрите Расширенные данные",
        "bot_language": "Язык / Language",
        "bot_select_language": "🌐 Выберите язык / Select language:",
        "bot_language_russian": "🇷🇺 Русский",
        "bot_language_english": "🇬🇧 English",
        "bot_language_changed": "✅ Язык изменен на: {language}",
        
        # Notifications
        "bot_notifications_settings": "🔔 Настройки уведомлений:",
        "bot_notifications_status": "Статус:",
        "bot_notifications_interval": "Интервал:",
        "bot_notifications_enable": "Включить",
        "bot_notifications_disable": "Выключить",
        "bot_hour": "час",
        "bot_hours_2_4": "часа",
        "bot_hours_5_plus": "часов",
        
        # Air Pollution
        "pollution_good": "Хорошо",
        "pollution_moderate": "Умеренно",
        "pollution_unhealthy": "Не хорошо для здоровья",
        "pollution_very_unhealthy": "Плохо для здоровья",
        "pollution_unknown": "Неизвестно",
        "bot_pollution_unavailable": "❌ Данные о загрязнении воздуха недоступны",
        "bot_air_quality": "🌬️ Качество воздуха:",
        "bot_overall_status": "📊 Общий статус:",
        "bot_components": "Компоненты:",
        "bot_weather_data_error": "❌ Не удалось получить данные о погоде",
        "bot_uv_index": "☀️ UV индекс:",
        "bot_uv_low": "Низкий",
        "bot_uv_moderate": "Умеренный",
        "bot_uv_high": "Высокий",
        "bot_uv_very_high": "Очень высокий",
        "bot_uv_extreme": "Экстремальный",
        "bot_extended_data_for": "📊 Расширенные данные для {city}:",
        "bot_extended_data_title": "📊 Расширенные данные:",
        "bot_enter_city_extended": "Введите название города для расширенных данных:",
        "bot_weather": "🌤️ Погода:",
        "bot_feels": " (ощущается {feels_like}°C)",
        "bot_wind_short": "💨 Ветер: {wind_speed} м/с",
        "bot_sunrise": "🌅 Восход: {time}",
        "bot_sunset": "🌇 Закат: {time}",
        
        # Days of week
        "monday": "Понедельник",
        "tuesday": "Вторник",
        "wednesday": "Среда",
        "thursday": "Четверг",
        "friday": "Пятница",
        "saturday": "Суббота",
        "sunday": "Воскресенье",
        "mon": "Пн",
        "tue": "Вт",
        "wed": "Ср",
        "thu": "Чт",
        "fri": "Пт",
        "sat": "Сб",
        "sun": "Вс",
    },
    "en": {
        # General messages
        "error": "Error",
        "warning": "Warning",
        "success": "Success",
        "not_found": "Not found",
        "unknown_error": "Unknown error",
        
        # Language Selection
        "select_language_title": "Select Language / Выберите язык",
        "language_russian": "Русский (Russian)",
        "language_english": "English (Английский)",
        "enter_language_choice": "Enter number (1-2) / Введите номер (1-2):",
        "invalid_language_choice": "Invalid choice. Enter 1 or 2 / Неверный выбор. Введите 1 или 2",
        
        # Weather App
        "weather_app_title": "Weather Forecast Program",
        "enter_city": "Enter city name (in English):",
        "city_empty": "Error: City name cannot be empty",
        "searching_coordinates": "Searching coordinates for city '{city}'...",
        "city_not_found": "Error: City '{city}' not found",
        "multiple_cities_found": "Found multiple cities named '{city}':",
        "select_city_number": "Select city number (1-{count}):",
        "invalid_number": "Please enter a number",
        "invalid_range": "Please enter a number from 1 to {count}",
        "city_found": "City found: {location}",
        "forecast_type": "Select forecast type:",
        "current_weather": "Current weather",
        "forecast_5days": "5-day forecast (3-hour intervals)",
        "enter_choice": "Enter number (1 or 2):",
        "getting_weather": "Getting weather data...",
        "weather_error": "Error: Failed to get weather data. Check your internet connection and API key.",
        "temperature_error": "Error: Failed to get temperature data",
        "weather_in": "Weather in {location}: {temp}°C, {description}",
        "getting_forecast": "Getting 5-day forecast...",
        "forecast_error": "Error: Failed to get weather forecast. Check your internet connection and API key.",
        "forecast_for": "5-day weather forecast for {location}:",
        "temperature": "Temperature",
        "feels_like": "feels like",
        "description": "Description",
        "humidity": "Humidity",
        "wind_speed": "Wind speed",
        "invalid_choice": "Error: Invalid choice. Select 1 or 2",
        "cache_save_error": "Warning: Failed to save cache: {error}",
        
        # API Messages
        "api_key_missing": "API_KEY is not set",
        "searching_coords": "Searching coordinates for city: {city}",
        "coords_not_found": "City {city} not found",
        "coords_found": "Found coordinates for {city}: ({lat}, {lon})",
        "getting_current_weather": "Getting current weather for coordinates: ({lat}, {lon})",
        "getting_forecast_5d": "Getting 5-day forecast for coordinates: ({lat}, {lon})",
        "getting_uv_index": "Getting UV index for coordinates: ({lat}, {lon})",
        "getting_pollution": "Getting air pollution data for coordinates: ({lat}, {lon})",
        
        # Bot Messages
        "bot_welcome": "🌍 Welcome to the weather forecast bot!\n\nSelect an action from the menu:",
        "bot_current_weather": "🌤️ Current weather",
        "bot_forecast_5days": "📅 5-day forecast",
        "bot_my_location": "📍 My location",
        "bot_compare_cities": "🔍 Compare cities",
        "bot_extended_data": "📊 Extended data",
        "bot_notifications": "🔔 Notifications",
        "bot_enter_city": "Enter city name:",
        "bot_enter_city_for_forecast": "Enter city name for forecast:",
        "bot_enter_city_1": "Enter the name of the first city:",
        "bot_enter_city_2": "Enter the name of the second city:",
        "bot_city_not_found_compare": "❌ One of the cities was not found",
        "bot_send_location": "📍 Send location",
        "bot_send_location_prompt": "📍 Please send your location or enter a city name:",
        "bot_select_weather_method": "Select weather source:",
        "bot_cancel": "❌ Cancel",
        "bot_cancelled": "Cancelled",
        "bot_select_action": "Select an action:",
        "bot_city_not_found": "❌ City '{city}' not found. Please try again:",
        "bot_multiple_cities_found": "Multiple cities found. Select the one you need:",
        "bot_weather_in": "🌤️ Weather in {city}:",
        "bot_temperature": "🌡️ Temperature: {temp}°C",
        "bot_feels_like": "💭 Feels like: {feels_like}°C",
        "bot_description": "☁️ Description: {description}",
        "bot_humidity": "💧 Humidity: {humidity}%",
        "bot_pressure": "📊 Pressure: {pressure} hPa",
        "bot_wind": "💨 Wind speed: {wind_speed} m/s",
        "bot_weather_error": "❌ Failed to get weather data",
        "bot_forecast_error": "❌ Failed to get forecast",
        "bot_forecast_5days_for": "📅 5-day forecast for {city}:",
        "bot_select_day": "Select a day for detailed view:",
        "bot_select_day_forecast": "📅 Select a day to view the forecast:",
        "bot_difference": "Difference",
        "bot_forecast_for_date": "📅 Forecast for {date} ({weekday}):",
        "bot_compare_cities_title": "🔍 City comparison:",
        "bot_current_weather_title": "🌤️ Current weather:",
        "bot_location_saved": "✅ Location successfully saved!",
        "bot_use_location": "📍 Use my location",
        "bot_enter_city_btn": "🏙️ Enter city",
        "bot_location_not_saved": "❌ Location not saved. Please send it first.",
        "bot_check_extended_data": "Now check Extended data",
        "bot_language": "Language / Язык",
        "bot_select_language": "🌐 Select language / Выберите язык:",
        "bot_language_russian": "🇷🇺 Русский",
        "bot_language_english": "🇬🇧 English",
        "bot_language_changed": "✅ Language changed to: {language}",
        
        # Notifications
        "bot_notifications_settings": "🔔 Notification settings:",
        "bot_notifications_status": "Status:",
        "bot_notifications_interval": "Interval:",
        "bot_notifications_enable": "Enable",
        "bot_notifications_disable": "Disable",
        "bot_hour": "hour",
        "bot_hours_2_4": "hours",
        "bot_hours_5_plus": "hours",
        
        # Air Pollution
        "pollution_good": "Good",
        "pollution_moderate": "Moderate",
        "pollution_unhealthy": "Unhealthy",
        "pollution_very_unhealthy": "Very unhealthy",
        "pollution_unknown": "Unknown",
        "bot_pollution_unavailable": "❌ Air pollution data unavailable",
        "bot_air_quality": "🌬️ Air quality:",
        "bot_overall_status": "📊 Overall status:",
        "bot_components": "Components:",
        "bot_weather_data_error": "❌ Failed to get weather data",
        "bot_uv_index": "☀️ UV index:",
        "bot_uv_low": "Low",
        "bot_uv_moderate": "Moderate",
        "bot_uv_high": "High",
        "bot_uv_very_high": "Very high",
        "bot_uv_extreme": "Extreme",
        "bot_extended_data_for": "📊 Extended data for {city}:",
        "bot_extended_data_title": "📊 Extended data:",
        "bot_enter_city_extended": "Enter city name for extended data:",
        "bot_weather": "🌤️ Weather:",
        "bot_feels": " (feels like {feels_like}°C)",
        "bot_wind_short": "💨 Wind: {wind_speed} m/s",
        "bot_sunrise": "🌅 Sunrise: {time}",
        "bot_sunset": "🌇 Sunset: {time}",
        
        # Days of week
        "monday": "Monday",
        "tuesday": "Tuesday",
        "wednesday": "Wednesday",
        "thursday": "Thursday",
        "friday": "Friday",
        "saturday": "Saturday",
        "sunday": "Sunday",
        "mon": "Mon",
        "tue": "Tue",
        "wed": "Wed",
        "thu": "Thu",
        "fri": "Fri",
        "sat": "Sat",
        "sun": "Sun",
    }
}


def set_language(lang: str) -> bool:
    """
    Устанавливает текущий язык интерфейса
    
    Args:
        lang: Код языка ('ru' или 'en')
        
    Returns:
        bool: True если язык установлен успешно, False если язык не поддерживается
    """
    global _current_language
    
    if lang not in SUPPORTED_LANGUAGES:
        logger.warning(f"Unsupported language: {lang}. Using default: {DEFAULT_LANGUAGE}")
        return False
    
    _current_language = lang
    logger.info(f"Language set to: {lang}")
    return True


def get_language() -> str:
    """
    Возвращает текущий язык интерфейса
    
    Returns:
        str: Код текущего языка
    """
    return _current_language


def t(key: str, **kwargs) -> str:
    """
    Получает перевод по ключу с подстановкой параметров
    
    Args:
        key: Ключ перевода
        **kwargs: Параметры для подстановки в строку
        
    Returns:
        str: Переведенная строка или ключ, если перевод не найден
    """
    lang = get_language()
    
    if lang not in TRANSLATIONS:
        logger.warning(f"Language {lang} not found in translations. Using default: {DEFAULT_LANGUAGE}")
        lang = DEFAULT_LANGUAGE
    
    translations = TRANSLATIONS.get(lang, {})
    text = translations.get(key, key)
    
    # Подстановка параметров
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Missing parameter {e} in translation key '{key}'")
    
    return text


def get_supported_languages() -> list[str]:
    """
    Возвращает список поддерживаемых языков
    
    Returns:
        list[str]: Список кодов языков
    """
    return SUPPORTED_LANGUAGES.copy()

