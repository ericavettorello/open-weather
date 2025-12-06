import os
import asyncio
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from geocoding import get_coordinates, get_cities_list
from weather_api import get_current_weather, get_forecast_5d3h, get_uv_index
from air_pollution import get_air_pollution, analyze_air_pollution
from storage import load_user, save_user
from logger import get_logger
from i18n import t, set_language, get_language

# Настройка логирования
logger = get_logger("OpenWeather.Bot")

# Загрузка переменных окружения
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Состояния для FSM
WAITING_CITY = "waiting_city"
WAITING_CITY_1 = "waiting_city_1"
WAITING_CITY_2 = "waiting_city_2"
WAITING_NOTIFICATION_INTERVAL = "waiting_notification_interval"
WAITING_LOCATION = "waiting_location"  # Ожидание геолокации или города для сохранения

# Хранилище состояний пользователей
user_states = {}
user_temp_data = {}  # Временные данные для многошаговых операций


def set_user_language(user_id: int):
    """
    Устанавливает язык для пользователя на основе сохраненных данных
    
    Args:
        user_id: ID пользователя
    """
    user_data = load_user(user_id)
    user_lang = user_data.get("language", "ru")
    set_language(user_lang)
    return user_lang


def format_hours(hours: int) -> str:
    """
    Форматирует число часов с правильным склонением
    
    Args:
        hours: Количество часов
        
    Returns:
        str: Строка с правильным склонением (час/часа/часов) или (hour/hours)
    """
    current_lang = get_language()
    if current_lang == "ru":
        if hours % 10 == 1 and hours % 100 != 11:
            return f"{hours} {t('bot_hour')}"
        elif 2 <= hours % 10 <= 4 and (hours % 100 < 10 or hours % 100 >= 20):
            return f"{hours} {t('bot_hours_2_4')}"
        else:
            return f"{hours} {t('bot_hours_5_plus')}"
    else:
        # English: use "hour" for 1, "hours" for others
        if hours == 1:
            return f"{hours} {t('bot_hour')}"
        else:
            return f"{hours} {t('bot_hours_5_plus')}"


def format_5day_forecast(forecast_list: list[dict], city_name: str) -> str:
    """
    Форматирует прогноз на 5 дней в сводку
    
    Args:
        forecast_list: Список прогнозов
        city_name: Название города
        
    Returns:
        str: Отформатированная строка с прогнозом на 5 дней
    """
    # Группируем по дням
    days_forecast = {}
    for forecast in forecast_list:
        dt_txt = forecast.get("dt_txt", "")
        if dt_txt:
            date = dt_txt.split()[0]
            if date not in days_forecast:
                days_forecast[date] = []
            days_forecast[date].append(forecast)
    
    # Получаем переводы для дней недели
    weekdays = [
        t("monday"), t("tuesday"), t("wednesday"), t("thursday"),
        t("friday"), t("saturday"), t("sunday")
    ]
    
    text = t("bot_forecast_5days_for", city=city_name) + "\n\n"
    
    # Формируем сводку по каждому дню
    for date in sorted(days_forecast.keys())[:5]:
        day_forecasts = days_forecast[date]
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        date_str = date_obj.strftime("%d.%m")
        weekday = weekdays[date_obj.weekday()]
        
        # Находим минимальную и максимальную температуру за день
        temps = [f.get("main", {}).get("temp") for f in day_forecasts if f.get("main", {}).get("temp") is not None]
        if temps:
            min_temp = min(temps)
            max_temp = max(temps)
        else:
            min_temp = max_temp = 0
        
        # Берем описание из первого прогноза дня
        description = day_forecasts[0].get("weather", [{}])[0].get("description", "") if day_forecasts else ""
        
        text += f"📆 {date_str} ({weekday})\n"
        text += f"   🌡️ {min_temp:.0f}°C / {max_temp:.0f}°C\n"
        text += f"   ☁️ {description}\n\n"
    
    text += t("bot_select_day")
    
    return text


def get_main_keyboard(user_lang: str = "ru"):
    """Создает основную клавиатуру с учетом языка пользователя"""
    # Временно устанавливаем язык для получения переводов
    old_lang = get_language()
    set_language(user_lang)
    
    keyboard = [
        [t("bot_current_weather"), t("bot_forecast_5days")],
        [t("bot_my_location"), t("bot_compare_cities")],
        [t("bot_extended_data"), t("bot_notifications")],
        [f"🌐 {t('bot_language')}"]
    ]
    
    # Восстанавливаем язык
    set_language(old_lang)
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user_id = update.effective_user.id
    logger.info(f"Пользователь {user_id} запустил бота")
    
    # Загружаем данные пользователя
    user_data = load_user(user_id)
    if not user_data:
        # Создаем начальные данные
        user_data = {
            "city": "",
            "lat": None,
            "lon": None,
            "language": "ru",  # Язык по умолчанию
            "notifications": {
                "enabled": False,
                "interval_h": 2
            }
        }
        save_user(user_id, user_data)
        logger.debug(f"Создан новый профиль для пользователя {user_id}")
    
    # Устанавливаем язык пользователя
    user_lang = user_data.get("language", "ru")
    set_language(user_lang)
    
    welcome_text = t("bot_welcome")
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard(user_lang)
    )
    user_states[user_id] = None


async def handle_current_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Текущая погода'"""
    user_id = update.effective_user.id
    user_data = load_user(user_id)
    # Устанавливаем язык пользователя
    user_lang = user_data.get("language", "ru")
    set_language(user_lang)
    
    # Проверяем, есть ли сохраненная геолокация
    if user_data.get("lat") and user_data.get("lon"):
        keyboard = [
            [KeyboardButton(t("bot_use_location"))],
            [KeyboardButton(t("bot_enter_city_btn"))]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(
            t("bot_select_weather_method"),
            reply_markup=reply_markup
        )
        user_states[user_id] = WAITING_CITY
    else:
        await update.message.reply_text(
            t("bot_enter_city"),
            reply_markup=ReplyKeyboardMarkup([[t("bot_cancel")]], resize_keyboard=True, one_time_keyboard=True)
        )
        user_states[user_id] = WAITING_CITY


async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик геолокации"""
    user_id = update.effective_user.id
    location = update.message.location
    
    # Устанавливаем язык пользователя
    user_lang = set_user_language(user_id)
    
    if location:
        lat = location.latitude
        lon = location.longitude
        logger.info(f"Пользователь {user_id} отправил геолокацию: ({lat}, {lon})")
        
        # Сохраняем геолокацию
        user_data = load_user(user_id)
        user_data["lat"] = lat
        user_data["lon"] = lon
        save_user(user_id, user_data)
        
        # Проверяем, откуда пришла геолокация - для сохранения или для текущей погоды
        state = user_states.get(user_id)
        
        if state == WAITING_CITY:
            # Геолокация для текущей погоды
            weather_data = get_current_weather(lat, lon)
            
            if weather_data:
                temp = weather_data.get("main", {}).get("temp")
                feels_like = weather_data.get("main", {}).get("feels_like")
                description = weather_data.get("weather", [{}])[0].get("description", "")
                humidity = weather_data.get("main", {}).get("humidity")
                pressure = weather_data.get("main", {}).get("pressure")
                wind_speed = weather_data.get("wind", {}).get("speed")
                
                text = (
                    f"{t('bot_current_weather')}:\n\n"
                    f"{t('bot_temperature', temp=temp)}\n"
                    f"{t('bot_feels_like', feels_like=feels_like)}\n"
                    f"{t('bot_description', description=description)}\n"
                    f"{t('bot_humidity', humidity=humidity)}\n"
                    f"{t('bot_pressure', pressure=pressure)}\n"
                    f"{t('bot_wind', wind_speed=wind_speed)}"
                )
            else:
                text = t("bot_weather_error")
            
            await update.message.reply_text(text, reply_markup=get_main_keyboard(user_lang))
        else:
            # Геолокация для сохранения (кнопка "Моя геолокация")
            await update.message.reply_text(
                f"{t('bot_location_saved')}\n\n"
                f"{t('bot_check_extended_data')}",
                reply_markup=get_main_keyboard(user_lang)
            )
        
        user_states[user_id] = None


async def handle_city_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ввода города"""
    user_id = update.effective_user.id
    # Устанавливаем язык пользователя
    user_lang = set_user_language(user_id)
    state = user_states.get(user_id)
    
    if state == WAITING_LOCATION:
        # Ввод города для сохранения геолокации
        city = update.message.text.strip()
        
        if city == t("bot_cancel") or city == "❌ Отмена":
            await update.message.reply_text(t("bot_cancelled"), reply_markup=get_main_keyboard(user_lang))
            user_states[user_id] = None
            user_temp_data[user_id] = {}
            return
        
        # Ищем город
        cities_list = get_cities_list(city, limit=1)
        
        if not cities_list or len(cities_list) == 0:
            await update.message.reply_text(
                t("bot_city_not_found", city=city),
                reply_markup=ReplyKeyboardMarkup([[t("bot_cancel")]], resize_keyboard=True, one_time_keyboard=True)
            )
            return
        
        # Сохраняем координаты города как геолокацию
        selected_city = cities_list[0]
        lat = selected_city["lat"]
        lon = selected_city["lon"]
        city_name = selected_city["name"]
        
        user_data = load_user(user_id)
        user_data["lat"] = lat
        user_data["lon"] = lon
        user_data["city"] = city_name
        save_user(user_id, user_data)
        
        await update.message.reply_text(
            f"{t('bot_location_saved')}\n\n"
            f"{t('bot_check_extended_data')}",
            reply_markup=get_main_keyboard(user_lang)
        )
        user_states[user_id] = None
        user_temp_data[user_id] = {}
    
    elif state == WAITING_CITY:
        city = update.message.text.strip()
        
        if city == t("bot_cancel") or city == "❌ Отмена":
            await update.message.reply_text(t("bot_cancelled"), reply_markup=get_main_keyboard(user_lang))
            user_states[user_id] = None
            user_temp_data[user_id] = {}
            return
        
        # Ищем город
        cities_list = get_cities_list(city, limit=5)
        
        if not cities_list or len(cities_list) == 0:
            await update.message.reply_text(
                t("bot_city_not_found", city=city),
                reply_markup=ReplyKeyboardMarkup([[t("bot_cancel")]], resize_keyboard=True, one_time_keyboard=True)
            )
            return
        
        # Если один город - используем его, иначе показываем список
        if len(cities_list) == 1:
            selected_city = cities_list[0]
            lat = selected_city["lat"]
            lon = selected_city["lon"]
            city_name = selected_city["name"]
            
            # Проверяем, это запрос для прогноза, расширенных данных или текущей погоды
            temp_data = user_temp_data.get(user_id, {})
            is_forecast = temp_data.get("forecast", False)
            is_extended = temp_data.get("extended", False)
            
            if is_forecast:
                # Показываем прогноз на 5 дней
                forecast_list = get_forecast_5d3h(lat, lon)
                
                if not forecast_list:
                    await update.message.reply_text(t("bot_forecast_error"), reply_markup=get_main_keyboard(user_lang))
                    user_states[user_id] = None
                    user_temp_data[user_id] = {}
                    return
                
                # Формируем сводку по 5 дням
                text = format_5day_forecast(forecast_list, city_name)
                
                # Сохраняем координаты для детального просмотра
                temp_data = user_temp_data.get(user_id, {})
                temp_data["forecast_lat"] = lat
                temp_data["forecast_lon"] = lon
                temp_data["forecast_city"] = city_name
                user_temp_data[user_id] = temp_data
                
                # Группируем по дням для клавиатуры
                days_forecast = {}
                for forecast in forecast_list:
                    dt_txt = forecast.get("dt_txt", "")
                    if dt_txt:
                        date = dt_txt.split()[0]
                        if date not in days_forecast:
                            days_forecast[date] = []
                        days_forecast[date].append(forecast)
                
                # Создаем клавиатуру с днями для детального просмотра
                keyboard = []
                weekdays_short = [t("mon"), t("tue"), t("wed"), t("thu"), t("fri"), t("sat"), t("sun")]
                for date in sorted(days_forecast.keys())[:5]:
                    date_obj = datetime.strptime(date, "%Y-%m-%d")
                    date_str = date_obj.strftime("%d.%m")
                    weekday = weekdays_short[date_obj.weekday()]
                    keyboard.append([InlineKeyboardButton(f"{date_str} ({weekday})", callback_data=f"forecast_{date}")])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(text, reply_markup=reply_markup)
                user_states[user_id] = None
                user_temp_data[user_id] = {}
            elif is_extended:
                # Показываем расширенные данные
                weather_data = get_current_weather(lat, lon)
                pollution_data = get_air_pollution(lat, lon)
                uv_data = get_uv_index(lat, lon)
                
                text = t("bot_extended_data_for", city=city_name) + "\n\n"
                
                if weather_data:
                    temp = weather_data.get("main", {}).get("temp")
                    feels_like = weather_data.get("main", {}).get("feels_like")
                    description = weather_data.get("weather", [{}])[0].get("description", "")
                    humidity = weather_data.get("main", {}).get("humidity")
                    pressure = weather_data.get("main", {}).get("pressure")
                    wind_speed = weather_data.get("wind", {}).get("speed")
                    
                    # Время восхода и заката
                    sys_data = weather_data.get("sys", {})
                    sunrise = sys_data.get("sunrise")
                    sunset = sys_data.get("sunset")
                    timezone_offset = weather_data.get("timezone", 0)  # Смещение в секундах
                    
                    text += t("bot_weather") + "\n"
                    text += f"🌡️ {temp}°C{t('bot_feels', feels_like=feels_like)}\n"
                    text += f"☁️ {description}\n"
                    text += t("bot_humidity", humidity=humidity) + "\n"
                    text += t("bot_pressure", pressure=pressure) + "\n"
                    text += t("bot_wind_short", wind_speed=wind_speed) + "\n"
                    
                    # Добавляем время восхода и заката
                    if sunrise and sunset:
                        local_tz = timezone(timedelta(seconds=timezone_offset))
                        sunrise_time = datetime.fromtimestamp(sunrise, tz=local_tz)
                        sunset_time = datetime.fromtimestamp(sunset, tz=local_tz)
                        text += t("bot_sunrise", time=sunrise_time.strftime('%H:%M')) + "\n"
                        text += t("bot_sunset", time=sunset_time.strftime('%H:%M')) + "\n"
                    
                    # Добавляем UV индекс
                    if uv_data:
                        uv_value = uv_data.get("value", 0)
                        # Определяем уровень UV
                        if uv_value <= 2:
                            uv_level = t("bot_uv_low")
                        elif uv_value <= 5:
                            uv_level = t("bot_uv_moderate")
                        elif uv_value <= 7:
                            uv_level = t("bot_uv_high")
                        elif uv_value <= 10:
                            uv_level = t("bot_uv_very_high")
                        else:
                            uv_level = t("bot_uv_extreme")
                        
                        text += t("bot_uv_index") + f" {uv_value:.1f} ({uv_level})\n"
                    
                    text += "\n"
                else:
                    text += t("bot_weather_data_error") + "\n\n"
                
                if pollution_data:
                    components = pollution_data.get("components", {})
                    analysis = analyze_air_pollution(components, extended=False)
                    
                    text += t("bot_air_quality") + "\n"
                    overall_status = analysis.get('overall_status_name', t("pollution_unknown"))
                    text += t("bot_overall_status") + f" {overall_status}\n\n"
                    
                    text += t("bot_components") + "\n"
                    for comp, details in analysis.get("components", {}).items():
                        comp_names = {
                            "pm2_5": "PM2.5",
                            "pm10": "PM10",
                            "co": "CO",
                            "no2": "NO₂",
                            "o3": "O₃",
                            "so2": "SO₂",
                            "nh3": "NH₃",
                            "no": "NO"
                        }
                        comp_name = comp_names.get(comp, comp)
                        value = details.get("value", 0)
                        status = details.get("status_name", "")
                        text += f"  {comp_name}: {value} µg/m³ ({status})\n"
                else:
                    text += t("bot_pollution_unavailable")
                
                await update.message.reply_text(text, reply_markup=get_main_keyboard(user_lang))
                user_states[user_id] = None
                user_temp_data[user_id] = {}
            else:
                # Показываем текущую погоду
                weather_data = get_current_weather(lat, lon)
                
                if weather_data:
                    temp = weather_data.get("main", {}).get("temp")
                    feels_like = weather_data.get("main", {}).get("feels_like")
                    description = weather_data.get("weather", [{}])[0].get("description", "")
                    humidity = weather_data.get("main", {}).get("humidity")
                    pressure = weather_data.get("main", {}).get("pressure")
                    wind_speed = weather_data.get("wind", {}).get("speed")
                    
                    text = (
                        f"{t('bot_weather_in', city=city_name)}\n\n"
                        f"{t('bot_temperature', temp=temp)}\n"
                        f"{t('bot_feels_like', feels_like=feels_like)}\n"
                        f"{t('bot_description', description=description)}\n"
                        f"{t('bot_humidity', humidity=humidity)}\n"
                        f"{t('bot_pressure', pressure=pressure)}\n"
                        f"{t('bot_wind', wind_speed=wind_speed)}"
                    )
                else:
                    text = t("bot_weather_error")
                
                await update.message.reply_text(text, reply_markup=get_main_keyboard(user_lang))
                user_states[user_id] = None
        else:
            # Показываем список городов
            keyboard = []
            # Сохраняем cities и forecast флаг
            temp_data = user_temp_data.get(user_id, {})
            temp_data["cities"] = cities_list
            user_temp_data[user_id] = temp_data
            
            for i, city_info in enumerate(cities_list[:5], 1):
                location = city_info["name"]
                if city_info.get("state"):
                    location += f", {city_info['state']}"
                location += f", {city_info['country']}"
                keyboard.append([InlineKeyboardButton(f"{i}. {location}", callback_data=f"city_{i}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                t("bot_multiple_cities_found"),
                reply_markup=reply_markup
            )
    
    elif state == WAITING_CITY_1:
        city = update.message.text.strip()
        
        if city == t("bot_cancel") or city == "❌ Отмена":
            await update.message.reply_text(t("bot_cancelled"), reply_markup=get_main_keyboard(user_lang))
            user_states[user_id] = None
            user_temp_data[user_id] = {}
            return
        
        user_temp_data[user_id] = {"city1": city}
        await update.message.reply_text(t("bot_enter_city_2"))
        user_states[user_id] = WAITING_CITY_2
    
    elif state == WAITING_CITY_2:
        city2 = update.message.text.strip()
        
        if city2 == t("bot_cancel") or city2 == "❌ Отмена":
            await update.message.reply_text(t("bot_cancelled"), reply_markup=get_main_keyboard(user_lang))
            user_states[user_id] = None
            user_temp_data[user_id] = {}
            return
        
        city1 = user_temp_data[user_id].get("city1", "")
        
        # Получаем координаты городов
        cities1 = get_cities_list(city1, limit=1)
        cities2 = get_cities_list(city2, limit=1)
        
        if not cities1 or not cities2:
            await update.message.reply_text(t("bot_city_not_found_compare"), reply_markup=get_main_keyboard(user_lang))
            user_states[user_id] = None
            return
        
        city1_data = cities1[0]
        city2_data = cities2[0]
        
        # Получаем погоду
        weather1 = get_current_weather(city1_data["lat"], city1_data["lon"])
        weather2 = get_current_weather(city2_data["lat"], city2_data["lon"])
        
        if weather1 and weather2:
            temp1 = weather1.get("main", {}).get("temp")
            temp2 = weather2.get("main", {}).get("temp")
            desc1 = weather1.get("weather", [{}])[0].get("description", "")
            desc2 = weather2.get("weather", [{}])[0].get("description", "")
            
            text = (
                f"{t('bot_compare_cities_title')}\n\n"
                f"📍 {city1_data['name']}:\n"
                f"   🌡️ {temp1}°C, {desc1}\n\n"
                f"📍 {city2_data['name']}:\n"
                f"   🌡️ {temp2}°C, {desc2}\n\n"
                f"📊 {t('bot_difference')}: {abs(temp1 - temp2):.1f}°C"
            )
        else:
            text = t("bot_weather_error")
        
        await update.message.reply_text(text, reply_markup=get_main_keyboard(user_lang))
        user_states[user_id] = None


async def handle_city_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора города из списка"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    # Устанавливаем язык пользователя
    user_lang = set_user_language(user_id)
    
    if query.data.startswith("city_"):
        city_index = int(query.data.split("_")[1]) - 1
        temp_data = user_temp_data.get(user_id, {})
        cities_list = temp_data.get("cities", [])
        is_forecast = temp_data.get("forecast", False)
        is_extended = temp_data.get("extended", False)
        
        if city_index < len(cities_list):
            selected_city = cities_list[city_index]
            lat = selected_city["lat"]
            lon = selected_city["lon"]
            city_name = selected_city["name"]
            
            if is_forecast:
                # Показываем прогноз на 5 дней
                forecast_list = get_forecast_5d3h(lat, lon)
                
                if not forecast_list:
                    await query.edit_message_text(t("bot_forecast_error"))
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=t("bot_select_action"),
                        reply_markup=get_main_keyboard(user_lang)
                    )
                    user_states[user_id] = None
                    user_temp_data[user_id] = {}
                    return
                
                # Формируем сводку по 5 дням
                text = format_5day_forecast(forecast_list, city_name)
                
                # Сохраняем координаты для детального просмотра
                temp_data = user_temp_data.get(user_id, {})
                temp_data["forecast_lat"] = lat
                temp_data["forecast_lon"] = lon
                temp_data["forecast_city"] = city_name
                user_temp_data[user_id] = temp_data
                
                # Группируем по дням для клавиатуры
                days_forecast = {}
                for forecast in forecast_list:
                    dt_txt = forecast.get("dt_txt", "")
                    if dt_txt:
                        date = dt_txt.split()[0]
                        if date not in days_forecast:
                            days_forecast[date] = []
                        days_forecast[date].append(forecast)
                
                # Создаем клавиатуру с днями для детального просмотра
                keyboard = []
                weekdays_short = [t("mon"), t("tue"), t("wed"), t("thu"), t("fri"), t("sat"), t("sun")]
                for date in sorted(days_forecast.keys())[:5]:
                    date_obj = datetime.strptime(date, "%Y-%m-%d")
                    date_str = date_obj.strftime("%d.%m")
                    weekday = weekdays_short[date_obj.weekday()]
                    keyboard.append([InlineKeyboardButton(f"{date_str} ({weekday})", callback_data=f"forecast_{date}")])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(text, reply_markup=reply_markup)
                user_states[user_id] = None
                user_temp_data[user_id] = {}
            elif is_extended:
                # Показываем расширенные данные
                weather_data = get_current_weather(lat, lon)
                pollution_data = get_air_pollution(lat, lon)
                uv_data = get_uv_index(lat, lon)
                
                text = f"📊 Расширенные данные для {city_name}:\n\n"
                
                if weather_data:
                    temp = weather_data.get("main", {}).get("temp")
                    feels_like = weather_data.get("main", {}).get("feels_like")
                    description = weather_data.get("weather", [{}])[0].get("description", "")
                    humidity = weather_data.get("main", {}).get("humidity")
                    pressure = weather_data.get("main", {}).get("pressure")
                    wind_speed = weather_data.get("wind", {}).get("speed")
                    
                    # Время восхода и заката
                    sys_data = weather_data.get("sys", {})
                    sunrise = sys_data.get("sunrise")
                    sunset = sys_data.get("sunset")
                    timezone_offset = weather_data.get("timezone", 0)  # Смещение в секундах
                    
                    text += f"🌤️ Погода:\n"
                    text += f"🌡️ {temp}°C (ощущается {feels_like}°C)\n"
                    text += f"☁️ {description}\n"
                    text += f"💧 Влажность: {humidity}%\n"
                    text += f"📊 Давление: {pressure} гПа\n"
                    text += f"💨 Ветер: {wind_speed} м/с\n"
                    
                    # Добавляем время восхода и заката
                    if sunrise and sunset:
                        local_tz = timezone(timedelta(seconds=timezone_offset))
                        sunrise_time = datetime.fromtimestamp(sunrise, tz=local_tz)
                        sunset_time = datetime.fromtimestamp(sunset, tz=local_tz)
                        text += f"🌅 Восход: {sunrise_time.strftime('%H:%M')}\n"
                        text += f"🌇 Закат: {sunset_time.strftime('%H:%M')}\n"
                    
                    # Добавляем UV индекс
                    if uv_data:
                        uv_value = uv_data.get("value", 0)
                        # Определяем уровень UV
                        if uv_value <= 2:
                            uv_level = "Низкий"
                        elif uv_value <= 5:
                            uv_level = "Умеренный"
                        elif uv_value <= 7:
                            uv_level = "Высокий"
                        elif uv_value <= 10:
                            uv_level = "Очень высокий"
                        else:
                            uv_level = "Экстремальный"
                        
                        text += f"☀️ UV индекс: {uv_value:.1f} ({uv_level})\n"
                    
                    text += "\n"
                else:
                    text += "❌ Не удалось получить данные о погоде\n\n"
                
                if pollution_data:
                    components = pollution_data.get("components", {})
                    analysis = analyze_air_pollution(components, extended=False)
                    
                    text += f"🌬️ Качество воздуха:\n"
                    text += f"📊 Общий статус: {analysis.get('overall_status_name', 'Неизвестно')}\n\n"
                    
                    text += "Компоненты:\n"
                    for comp, details in analysis.get("components", {}).items():
                        comp_names = {
                            "pm2_5": "PM2.5",
                            "pm10": "PM10",
                            "co": "CO",
                            "no2": "NO₂",
                            "o3": "O₃",
                            "so2": "SO₂",
                            "nh3": "NH₃",
                            "no": "NO"
                        }
                        comp_name = comp_names.get(comp, comp)
                        value = details.get("value", 0)
                        status = details.get("status_name", "")
                        text += f"  {comp_name}: {value} µg/m³ ({status})\n"
                else:
                    text += "❌ Данные о загрязнении воздуха недоступны"
                
                await query.edit_message_text(text)
                user_lang = set_user_language(user_id)
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=t("bot_select_action"),
                    reply_markup=get_main_keyboard(user_lang)
                )
                user_states[user_id] = None
                user_temp_data[user_id] = {}
            else:
                # Показываем текущую погоду
                weather_data = get_current_weather(lat, lon)
                
                if weather_data:
                    temp = weather_data.get("main", {}).get("temp")
                    feels_like = weather_data.get("main", {}).get("feels_like")
                    description = weather_data.get("weather", [{}])[0].get("description", "")
                    humidity = weather_data.get("main", {}).get("humidity")
                    pressure = weather_data.get("main", {}).get("pressure")
                    wind_speed = weather_data.get("wind", {}).get("speed")
                    
                    text = (
                        f"{t('bot_weather_in', city=city_name)}\n\n"
                        f"{t('bot_temperature', temp=temp)}\n"
                        f"{t('bot_feels_like', feels_like=feels_like)}\n"
                        f"{t('bot_description', description=description)}\n"
                        f"{t('bot_humidity', humidity=humidity)}\n"
                        f"{t('bot_pressure', pressure=pressure)}\n"
                        f"{t('bot_wind', wind_speed=wind_speed)}"
                    )
                else:
                    text = t("bot_weather_error")
                
                await query.edit_message_text(text)
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=t("bot_select_action"),
                    reply_markup=get_main_keyboard(user_lang)
                )
                user_states[user_id] = None


async def handle_forecast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Прогноз на 5 дней'"""
    user_id = update.effective_user.id
    user_data = load_user(user_id)
    # Устанавливаем язык пользователя
    user_lang = set_user_language(user_id)
    
    # Всегда запрашиваем город (или используем сохраненную геолокацию)
    if user_data.get("lat") and user_data.get("lon"):
        # Если есть сохраненная геолокация, сразу показываем прогноз
        lat = user_data["lat"]
        lon = user_data["lon"]
        city_name = user_data.get("city", "Ваша геолокация")
        
        # Получаем прогноз
        forecast_list = get_forecast_5d3h(lat, lon)
        
        if not forecast_list:
            await update.message.reply_text(t("bot_forecast_error"), reply_markup=get_main_keyboard(user_lang))
            return
        
        # Формируем сводку по 5 дням
        text = format_5day_forecast(forecast_list, city_name)
        
        # Сохраняем координаты для детального просмотра
        temp_data = user_temp_data.get(user_id, {})
        temp_data["forecast_lat"] = lat
        temp_data["forecast_lon"] = lon
        temp_data["forecast_city"] = city_name
        user_temp_data[user_id] = temp_data
        
        # Создаем клавиатуру с днями для детального просмотра
        keyboard = []
        days_forecast = {}
        for forecast in forecast_list:
            dt_txt = forecast.get("dt_txt", "")
            if dt_txt:
                date = dt_txt.split()[0]
                if date not in days_forecast:
                    days_forecast[date] = []
                days_forecast[date].append(forecast)
        
        weekdays_short = [t("mon"), t("tue"), t("wed"), t("thu"), t("fri"), t("sat"), t("sun")]
        for date in sorted(days_forecast.keys())[:5]:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            date_str = date_obj.strftime("%d.%m")
            weekday = weekdays_short[date_obj.weekday()]
            keyboard.append([InlineKeyboardButton(f"{date_str} ({weekday})", callback_data=f"forecast_{date}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup)
    else:
        # Запрашиваем город
        await update.message.reply_text(
            t("bot_enter_city_for_forecast"),
            reply_markup=ReplyKeyboardMarkup([[t("bot_cancel")]], resize_keyboard=True, one_time_keyboard=True)
        )
        user_states[user_id] = WAITING_CITY
        user_temp_data[user_id] = {"forecast": True}


async def handle_forecast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора дня прогноза"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("forecast_") and query.data != "forecast_back":
        date = query.data.split("_", 1)[1]
        user_id = query.from_user.id
        user_data = load_user(user_id)
        # Устанавливаем язык пользователя
        user_lang = set_user_language(user_id)
        
        # Проверяем сначала временные данные (для выбранного города), потом сохраненную геолокацию
        temp_data = user_temp_data.get(user_id, {})
        lat = temp_data.get("forecast_lat") or user_data.get("lat")
        lon = temp_data.get("forecast_lon") or user_data.get("lon")
        
        if not lat or not lon:
            # Если нет координат, запрашиваем город
            await query.edit_message_text(t("bot_enter_city_for_forecast"))
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=t("bot_enter_city"),
                reply_markup=ReplyKeyboardMarkup([[t("bot_cancel")]], resize_keyboard=True, one_time_keyboard=True)
            )
            user_states[user_id] = WAITING_CITY
            user_temp_data[user_id] = {"forecast": True, "callback_message_id": query.message.message_id}
            return
        
        forecast_list = get_forecast_5d3h(lat, lon)
        
        if not forecast_list:
            await query.edit_message_text(t("bot_forecast_error"))
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=t("bot_select_action"),
                reply_markup=get_main_keyboard(user_lang)
            )
            return
        
        # Фильтруем по дате
        day_forecasts = [f for f in forecast_list if f.get("dt_txt", "").startswith(date)]
        
        if not day_forecasts:
            # Если данные за день не найдены, возвращаемся к списку дней
            days_forecast = {}
            for forecast in forecast_list:
                dt_txt = forecast.get("dt_txt", "")
                if dt_txt:
                    date_key = dt_txt.split()[0]
                    if date_key not in days_forecast:
                        days_forecast[date_key] = []
                    days_forecast[date_key].append(forecast)
            
            keyboard = []
            weekdays_short = [t("mon"), t("tue"), t("wed"), t("thu"), t("fri"), t("sat"), t("sun")]
            for date_key in sorted(days_forecast.keys())[:5]:
                date_obj = datetime.strptime(date_key, "%Y-%m-%d")
                date_str = date_obj.strftime("%d.%m")
                weekday = weekdays_short[date_obj.weekday()]
                keyboard.append([InlineKeyboardButton(f"{date_str} ({weekday})", callback_data=f"forecast_{date_key}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                t("bot_select_day_forecast"),
                reply_markup=reply_markup
            )
            return
        
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        date_str = date_obj.strftime("%d.%m.%Y")
        weekdays_full = [t("monday"), t("tuesday"), t("wednesday"), t("thursday"), t("friday"), t("saturday"), t("sunday")]
        weekday = weekdays_full[date_obj.weekday()]
        
        text = t("bot_forecast_for_date", date=date_str, weekday=weekday) + "\n\n"
        
        for forecast in day_forecasts:
            dt_txt = forecast.get("dt_txt", "")
            time_str = dt_txt.split()[1][:5] if len(dt_txt.split()) > 1 else ""
            temp = forecast.get("main", {}).get("temp")
            feels_like = forecast.get("main", {}).get("feels_like")
            description = forecast.get("weather", [{}])[0].get("description", "")
            humidity = forecast.get("main", {}).get("humidity")
            wind_speed = forecast.get("wind", {}).get("speed")
            
            text += f"🕐 {time_str}\n"
            text += f"   🌡️ {temp}°C (ощущается {feels_like}°C)\n"
            text += f"   ☁️ {description}\n"
            text += f"   💧 {humidity}% | 💨 {wind_speed} м/с\n\n"
        
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="forecast_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    elif query.data == "forecast_back":
        user_id = query.from_user.id
        user_data = load_user(user_id)
        
        # Проверяем сначала временные данные (для выбранного города), потом сохраненную геолокацию
        temp_data = user_temp_data.get(user_id, {})
        lat = temp_data.get("forecast_lat") or user_data.get("lat")
        lon = temp_data.get("forecast_lon") or user_data.get("lon")
        
        if not lat or not lon:
            # Если нет координат, запрашиваем город
            await query.edit_message_text(t("bot_enter_city_for_forecast"))
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=t("bot_enter_city"),
                reply_markup=ReplyKeyboardMarkup([[t("bot_cancel")]], resize_keyboard=True, one_time_keyboard=True)
            )
            user_states[user_id] = WAITING_CITY
            user_temp_data[user_id] = {"forecast": True}
            return
        
        forecast_list = get_forecast_5d3h(lat, lon)
        
        if not forecast_list:
            await query.edit_message_text(t("bot_forecast_error"))
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=t("bot_select_action"),
                reply_markup=get_main_keyboard(user_lang)
            )
            return
        
        days_forecast = {}
        for forecast in forecast_list:
            dt_txt = forecast.get("dt_txt", "")
            if dt_txt:
                date = dt_txt.split()[0]
                if date not in days_forecast:
                    days_forecast[date] = []
                days_forecast[date].append(forecast)
        
        keyboard = []
        weekdays_short = [t("mon"), t("tue"), t("wed"), t("thu"), t("fri"), t("sat"), t("sun")]
        for date in sorted(days_forecast.keys())[:5]:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            date_str = date_obj.strftime("%d.%m")
            weekday = weekdays_short[date_obj.weekday()]
            keyboard.append([InlineKeyboardButton(f"{date_str} ({weekday})", callback_data=f"forecast_{date}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            t("bot_select_day_forecast"),
            reply_markup=reply_markup
        )


async def handle_save_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Моя геолокация'"""
    user_id = update.effective_user.id
    # Устанавливаем язык пользователя
    user_lang = set_user_language(user_id)
    
    keyboard = [
        [KeyboardButton(t("bot_send_location", default="📍 Отправить геолокацию"), request_location=True)],
        [KeyboardButton(t("bot_cancel"))]
    ]
    await update.message.reply_text(
        t("bot_send_location_prompt", default="📍 Пожалуйста, отправьте вашу геолокацию или введите название города:"),
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    user_states[user_id] = WAITING_LOCATION  # Устанавливаем состояние для обработки ввода города


async def handle_compare_cities(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Сравнить города'"""
    user_id = update.effective_user.id
    # Устанавливаем язык пользователя
    user_lang = set_user_language(user_id)
    
    await update.message.reply_text(
        t("bot_enter_city_1", default="Введите название первого города:"),
        reply_markup=ReplyKeyboardMarkup([[t("bot_cancel")]], resize_keyboard=True, one_time_keyboard=True)
    )
    user_states[user_id] = WAITING_CITY_1


async def handle_extended_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Расширенные данные'"""
    user_id = update.effective_user.id
    user_data = load_user(user_id)
    # Устанавливаем язык пользователя
    user_lang = set_user_language(user_id)
    
    if not user_data.get("lat") or not user_data.get("lon"):
        # Если геолокация не сохранена, запрашиваем город
        await update.message.reply_text(
            t("bot_enter_city_extended"),
            reply_markup=ReplyKeyboardMarkup([[t("bot_cancel")]], resize_keyboard=True, one_time_keyboard=True)
        )
        user_states[user_id] = WAITING_CITY
        user_temp_data[user_id] = {"extended": True}
        return
    
    lat = user_data["lat"]
    lon = user_data["lon"]
    
    # Получаем погоду, загрязнение воздуха и UV индекс
    weather_data = get_current_weather(lat, lon)
    pollution_data = get_air_pollution(lat, lon)
    uv_data = get_uv_index(lat, lon)
    
    text = t("bot_extended_data_title") + "\n\n"
    
    if weather_data:
        temp = weather_data.get("main", {}).get("temp")
        feels_like = weather_data.get("main", {}).get("feels_like")
        description = weather_data.get("weather", [{}])[0].get("description", "")
        humidity = weather_data.get("main", {}).get("humidity")
        pressure = weather_data.get("main", {}).get("pressure")
        wind_speed = weather_data.get("wind", {}).get("speed")
        
        # Время восхода и заката
        sys_data = weather_data.get("sys", {})
        sunrise = sys_data.get("sunrise")
        sunset = sys_data.get("sunset")
        timezone_offset = weather_data.get("timezone", 0)  # Смещение в секундах
        
        text += t("bot_weather") + "\n"
        text += f"🌡️ {temp}°C{t('bot_feels', feels_like=feels_like)}\n"
        text += f"☁️ {description}\n"
        text += t("bot_humidity", humidity=humidity) + "\n"
        text += t("bot_pressure", pressure=pressure) + "\n"
        text += t("bot_wind_short", wind_speed=wind_speed) + "\n"
        
        # Добавляем время восхода и заката
        if sunrise and sunset:
            local_tz = timezone(timedelta(seconds=timezone_offset))
            sunrise_time = datetime.fromtimestamp(sunrise, tz=local_tz)
            sunset_time = datetime.fromtimestamp(sunset, tz=local_tz)
            text += t("bot_sunrise", time=sunrise_time.strftime('%H:%M')) + "\n"
            text += t("bot_sunset", time=sunset_time.strftime('%H:%M')) + "\n"
        
        # Добавляем UV индекс
        if uv_data:
            uv_value = uv_data.get("value", 0)
            # Определяем уровень UV
            if uv_value <= 2:
                uv_level = t("bot_uv_low")
            elif uv_value <= 5:
                uv_level = t("bot_uv_moderate")
            elif uv_value <= 7:
                uv_level = t("bot_uv_high")
            elif uv_value <= 10:
                uv_level = t("bot_uv_very_high")
            else:
                uv_level = t("bot_uv_extreme")
            
            text += t("bot_uv_index") + f" {uv_value:.1f} ({uv_level})\n"
        
        text += "\n"
    else:
        text += t("bot_weather_data_error") + "\n\n"
    
    if pollution_data:
        components = pollution_data.get("components", {})
        analysis = analyze_air_pollution(components, extended=False)
        
        text += t("bot_air_quality") + "\n"
        overall_status = analysis.get('overall_status_name', t("pollution_unknown"))
        text += t("bot_overall_status") + f" {overall_status}\n\n"
        
        text += t("bot_components") + "\n"
        for comp, details in analysis.get("components", {}).items():
            comp_names = {
                "pm2_5": "PM2.5",
                "pm10": "PM10",
                "co": "CO",
                "no2": "NO₂",
                "o3": "O₃",
                "so2": "SO₂",
                "nh3": "NH₃",
                "no": "NO"
            }
            comp_name = comp_names.get(comp, comp)
            value = details.get("value", 0)
            status = details.get("status_name", "")
            text += f"  {comp_name}: {value} µg/m³ ({status})\n"
    else:
        text += t("bot_pollution_unavailable")
    
    await update.message.reply_text(text, reply_markup=get_main_keyboard(user_lang))


async def handle_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Уведомления'"""
    user_id = update.effective_user.id
    user_data = load_user(user_id)
    # Устанавливаем язык пользователя
    user_lang = set_user_language(user_id)
    
    notifications = user_data.get("notifications", {"enabled": False, "interval_h": 2})
    enabled = "✅" if notifications.get("enabled") else "❌"
    interval = notifications.get("interval_h", 2)
    
    is_enabled = notifications.get("enabled", False)
    toggle_text = t("bot_notifications_disable") if is_enabled else t("bot_notifications_enable")
    toggle_icon = "❌" if is_enabled else "✅"
    
    keyboard = [
        [
            InlineKeyboardButton(
                f"{toggle_icon} {toggle_text}",
                callback_data="notif_toggle"
            )
        ],
        [
            InlineKeyboardButton(f"1 {t('bot_hour')}", callback_data="notif_interval_1"),
            InlineKeyboardButton(f"2 {t('bot_hours_2_4') if user_lang == 'ru' else t('bot_hours_5_plus')}", callback_data="notif_interval_2"),
            InlineKeyboardButton(f"3 {t('bot_hours_2_4') if user_lang == 'ru' else t('bot_hours_5_plus')}", callback_data="notif_interval_3"),
            InlineKeyboardButton(f"6 {t('bot_hours_5_plus')}", callback_data="notif_interval_6")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        f"{t('bot_notifications_settings')}\n\n"
        f"{t('bot_notifications_status')} {enabled}\n"
        f"{t('bot_notifications_interval')} {format_hours(interval)}"
    )
    
    await update.message.reply_text(text, reply_markup=reply_markup)


async def handle_notification_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback для уведомлений"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = load_user(user_id)
    # Устанавливаем язык пользователя
    user_lang = set_user_language(user_id)
    
    if query.data == "notif_toggle":
        notifications = user_data.get("notifications", {"enabled": False, "interval_h": 2})
        notifications["enabled"] = not notifications.get("enabled", False)
        user_data["notifications"] = notifications
        save_user(user_id, user_data)
        
        # Обновляем сообщение
        enabled = "✅" if notifications.get("enabled") else "❌"
        interval = notifications.get("interval_h", 2)
        
        is_enabled = notifications.get("enabled", False)
        toggle_text = t("bot_notifications_disable") if is_enabled else t("bot_notifications_enable")
        toggle_icon = "❌" if is_enabled else "✅"
        
        keyboard = [
            [
                InlineKeyboardButton(
                    f"{toggle_icon} {toggle_text}",
                    callback_data="notif_toggle"
                )
            ],
            [
                InlineKeyboardButton(f"1 {t('bot_hour')}", callback_data="notif_interval_1"),
                InlineKeyboardButton(f"2 {t('bot_hours_2_4') if user_lang == 'ru' else t('bot_hours_5_plus')}", callback_data="notif_interval_2"),
                InlineKeyboardButton(f"3 {t('bot_hours_2_4') if user_lang == 'ru' else t('bot_hours_5_plus')}", callback_data="notif_interval_3"),
                InlineKeyboardButton(f"6 {t('bot_hours_5_plus')}", callback_data="notif_interval_6")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = (
            f"{t('bot_notifications_settings')}\n\n"
            f"{t('bot_notifications_status')} {enabled}\n"
            f"{t('bot_notifications_interval')} {format_hours(interval)}"
        )
        
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    elif query.data.startswith("notif_interval_"):
        interval = int(query.data.split("_")[2])
        notifications = user_data.get("notifications", {"enabled": False, "interval_h": 2})
        notifications["interval_h"] = interval
        user_data["notifications"] = notifications
        save_user(user_id, user_data)
        
        enabled = "✅" if notifications.get("enabled") else "❌"
        
        is_enabled = notifications.get("enabled", False)
        toggle_text = t("bot_notifications_disable") if is_enabled else t("bot_notifications_enable")
        toggle_icon = "❌" if is_enabled else "✅"
        
        keyboard = [
            [
                InlineKeyboardButton(
                    f"{toggle_icon} {toggle_text}",
                    callback_data="notif_toggle"
                )
            ],
            [
                InlineKeyboardButton(f"1 {t('bot_hour')}", callback_data="notif_interval_1"),
                InlineKeyboardButton(f"2 {t('bot_hours_2_4') if user_lang == 'ru' else t('bot_hours_5_plus')}", callback_data="notif_interval_2"),
                InlineKeyboardButton(f"3 {t('bot_hours_2_4') if user_lang == 'ru' else t('bot_hours_5_plus')}", callback_data="notif_interval_3"),
                InlineKeyboardButton(f"6 {t('bot_hours_5_plus')}", callback_data="notif_interval_6")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = (
            f"{t('bot_notifications_settings')}\n\n"
            f"{t('bot_notifications_status')} {enabled}\n"
            f"{t('bot_notifications_interval')} {format_hours(interval)}"
        )
        
        await query.edit_message_text(text, reply_markup=reply_markup)


async def check_notifications(context: ContextTypes.DEFAULT_TYPE):
    """Проверка и отправка уведомлений (имитация планировщика)"""
    # Загружаем всех пользователей
    import json
    import os
    
    if not os.path.exists("User_Data.json"):
        return
    
    logger.debug("Проверка уведомлений")
    try:
        with open("User_Data.json", "r", encoding="utf-8") as f:
            all_users = json.load(f)
        
        for user_id_str, user_data in all_users.items():
            notifications = user_data.get("notifications", {})
            
            if not notifications.get("enabled", False):
                continue
            
            if not user_data.get("lat") or not user_data.get("lon"):
                continue
            
            # Проверяем, нужно ли отправлять уведомление
            last_notification = user_data.get("last_notification_time")
            interval_h = notifications.get("interval_h", 2)
            
            now = datetime.now()
            should_send = False
            
            if not last_notification:
                should_send = True
            else:
                last_time = datetime.fromisoformat(last_notification)
                if (now - last_time).total_seconds() >= interval_h * 3600:
                    should_send = True
            
            if should_send:
                lat = user_data["lat"]
                lon = user_data["lon"]
                
                weather_data = get_current_weather(lat, lon)
                
                if weather_data:
                    temp = weather_data.get("main", {}).get("temp")
                    description = weather_data.get("weather", [{}])[0].get("description", "")
                    
                    text = (
                        f"🔔 Уведомление о погоде:\n\n"
                        f"🌡️ {temp}°C\n"
                        f"☁️ {description}"
                    )
                    
                    try:
                        await context.bot.send_message(chat_id=int(user_id_str), text=text)
                        user_data["last_notification_time"] = now.isoformat()
                        save_user(int(user_id_str), user_data)
                        logger.debug(f"Уведомление отправлено пользователю {user_id_str}")
                    except Exception as e:
                        logger.warning(f"Ошибка отправки уведомления пользователю {user_id_str}: {str(e)}")
                        pass  # Игнорируем ошибки отправки
    except Exception as e:
        logger.error(f"Ошибка при проверке уведомлений: {str(e)}")
        pass  # Игнорируем ошибки


async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора языка"""
    user_id = update.effective_user.id
    user_data = load_user(user_id)
    user_lang = user_data.get("language", "ru")
    set_language(user_lang)
    
    keyboard = [
        [InlineKeyboardButton(t("bot_language_russian"), callback_data="lang_ru")],
        [InlineKeyboardButton(t("bot_language_english"), callback_data="lang_en")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        t("bot_select_language"),
        reply_markup=reply_markup
    )


async def handle_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback для выбора языка"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = load_user(user_id)
    
    if query.data == "lang_ru":
        user_data["language"] = "ru"
        set_language("ru")
        lang_name = "Русский"
    elif query.data == "lang_en":
        user_data["language"] = "en"
        set_language("en")
        lang_name = "English"
    else:
        return
    
    save_user(user_id, user_data)
    
    # Устанавливаем язык для получения переводов
    set_language(user_data["language"])
    
    # Удаляем старое сообщение и отправляем новое с обновленным меню
    await query.delete_message()
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=t("bot_language_changed", language=lang_name) + "\n\n" + t("bot_welcome"),
        reply_markup=get_main_keyboard(user_data["language"])
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    text = update.message.text
    user_id = update.effective_user.id
    
    # Загружаем язык пользователя
    user_data = load_user(user_id)
    user_lang = user_data.get("language", "ru")
    set_language(user_lang)
    
    # Обработка кнопки отмены - всегда возвращает в главное меню
    if text == t("bot_cancel"):
        await update.message.reply_text(t("bot_cancelled"), reply_markup=get_main_keyboard(user_lang))
        user_states[user_id] = None
        user_temp_data[user_id] = {}
        return
    
    # Проверяем кнопки с учетом языка
    if text == t("bot_current_weather") or text == "🌤️ Текущая погода":
        await handle_current_weather(update, context)
    elif text == t("bot_forecast_5days") or text == "📅 Прогноз на 5 дней":
        await handle_forecast(update, context)
    elif text == t("bot_my_location") or text == "📍 Моя геолокация":
        await handle_save_location(update, context)
    elif text == t("bot_compare_cities") or text == "🔍 Сравнить города":
        await handle_compare_cities(update, context)
    elif text == t("bot_extended_data") or text == "📊 Расширенные данные":
        await handle_extended_data(update, context)
    elif text == t("bot_notifications") or text == "🔔 Уведомления":
        await handle_notifications(update, context)
    elif text.startswith("🌐") or text == t("bot_language"):
        await handle_language_selection(update, context)
    elif text == "📍 Использовать мою геолокацию":
        # Используем сохраненную геолокацию для текущей погоды
        user_data = load_user(user_id)
        if user_data.get("lat") and user_data.get("lon"):
            lat = user_data["lat"]
            lon = user_data["lon"]
            
            weather_data = get_current_weather(lat, lon)
            
            if weather_data:
                temp = weather_data.get("main", {}).get("temp")
                feels_like = weather_data.get("main", {}).get("feels_like")
                description = weather_data.get("weather", [{}])[0].get("description", "")
                humidity = weather_data.get("main", {}).get("humidity")
                pressure = weather_data.get("main", {}).get("pressure")
                wind_speed = weather_data.get("wind", {}).get("speed")
                
                text = (
                    f"{t('bot_current_weather_title')}\n\n"
                    f"{t('bot_temperature', temp=temp)}\n"
                    f"{t('bot_feels_like', feels_like=feels_like)}\n"
                    f"{t('bot_description', description=description)}\n"
                    f"{t('bot_humidity', humidity=humidity)}\n"
                    f"{t('bot_pressure', pressure=pressure)}\n"
                    f"{t('bot_wind', wind_speed=wind_speed)}"
                )
            else:
                text = t("bot_weather_error")
            
            await update.message.reply_text(text, reply_markup=get_main_keyboard(user_lang))
            user_states[user_id] = None
        else:
            await update.message.reply_text(
                t("bot_location_not_saved"),
                reply_markup=get_main_keyboard(user_lang)
            )
    elif text == "🏙️ Ввести город" or text == t("bot_enter_city_btn"):
        await update.message.reply_text(
            t("bot_enter_city"),
            reply_markup=ReplyKeyboardMarkup([[t("bot_cancel")]], resize_keyboard=True, one_time_keyboard=True)
        )
        user_states[user_id] = WAITING_CITY
    else:
        # Обрабатываем ввод города
        await handle_city_input(update, context)


def main():
    """Главная функция запуска бота"""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не найден в .env")
        print("Ошибка: TELEGRAM_BOT_TOKEN не найден в .env")
        return
    
    logger.info("Запуск Telegram бота")
    
    # Создаем приложение
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.LOCATION, handle_location))
    application.add_handler(CallbackQueryHandler(handle_city_callback, pattern="^city_"))
    application.add_handler(CallbackQueryHandler(handle_forecast_callback, pattern="^forecast"))
    application.add_handler(CallbackQueryHandler(handle_notification_callback, pattern="^notif"))
    application.add_handler(CallbackQueryHandler(handle_language_callback, pattern="^lang_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Добавляем задачу для проверки уведомлений (каждую минуту)
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(check_notifications, interval=60, first=10)
        logger.info("Планировщик уведомлений запущен")
    
    # Запускаем бота
    logger.info("Бот запущен и готов к работе")
    print("Бот запущен...")
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.critical(f"Критическая ошибка при работе бота: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()

