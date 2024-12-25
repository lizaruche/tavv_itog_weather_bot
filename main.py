import os
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import requests
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Загрузка токенов и ключей из .env
load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')

# Логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Функция для получения погоды
def get_weather_by_coords(lat, lon, date=None):
    if date == "yesterday":
        # Историческая погода (платная функция OpenWeather)
        url = f"http://api.openweathermap.org/data/2.5/onecall/timemachine?lat={lat}&lon={lon}&dt={(datetime.now() - timedelta(days=1)).timestamp()}&appid={WEATHER_API_KEY}&units=metric&lang=ru"
    elif date == "tomorrow":
        # Прогноз на завтра
        url = f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric&lang=ru"
    else:
        # Погода сейчас
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric&lang=ru"

    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if date == "tomorrow":
            forecast = data['list'][8]  # Прогноз через 24 часа
            temp = forecast['main']['temp']
            weather = forecast['weather'][0]['description']
            return f"Погода завтра: {temp}°C, {weather.capitalize()}."
        else:
            temp = data['main']['temp']
            weather = data['weather'][0]['description']
            return f"Погода: {temp}°C, {weather.capitalize()}."
    else:
        return "Не удалось получить данные о погоде."

# Функция для получения данных на неделю
def get_weekly_forecast(lat, lon):
    url = f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric&lang=ru"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        forecast = []
        for entry in data['list']:
            time = datetime.fromtimestamp(entry['dt']).strftime('%d %b %H:%M')
            temp = entry['main']['temp']
            forecast.append((time, temp))
        return forecast
    else:
        return None

# Функция для построения графика
def create_temperature_chart(forecast, filepath='weekly_forecast.png'):
    times = [entry[0] for entry in forecast]
    temps = [entry[1] for entry in forecast]

    plt.figure(figsize=(10, 5))
    plt.plot(times, temps, marker='o')
    plt.title('Прогноз температуры на неделю')
    plt.xlabel('Дата и время')
    plt.ylabel('Температура (°C)')
    plt.xticks(rotation=45, fontsize=8)
    plt.tight_layout()
    plt.savefig(filepath)
    plt.close()

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("Погода сейчас"), KeyboardButton("Погода вчера")],
        [KeyboardButton("Погода завтра"), KeyboardButton("Прогноз на неделю")],
        [KeyboardButton("Отправить местоположение", request_location=True)],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Привет! Я бот для прогноза погоды. Выберите опцию ниже или отправьте местоположение.",
        reply_markup=reply_markup
    )

# Обработчик кнопки "Погода сейчас", "Погода вчера", "Погода завтра"
async def handle_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    user_data = context.user_data
    date = None

    if user_message == "Погода сейчас":
        date = None
    elif user_message == "Погода вчера":
        date = "yesterday"
    elif user_message == "Погода завтра":
        date = "tomorrow"

    if "location" in user_data:
        lat, lon = user_data["location"]
        weather_info = get_weather_by_coords(lat, lon, date)
        await update.message.reply_text(weather_info)
    else:
        await update.message.reply_text("Сначала отправьте ваше местоположение!")

# Обработчик кнопки "Прогноз на неделю"
async def handle_weekly_forecast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    if "location" in user_data:
        lat, lon = user_data["location"]
        forecast = get_weekly_forecast(lat, lon)
        if forecast:
            create_temperature_chart(forecast)
            await update.message.reply_photo(photo=open('weekly_forecast.png', 'rb'))
        else:
            await update.message.reply_text("Не удалось получить данные для прогноза на неделю.")
    else:
        await update.message.reply_text("Сначала отправьте ваше местоположение!")

# Обработчик местоположения
async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    location = update.message.location
    context.user_data["location"] = (location.latitude, location.longitude)
    await update.message.reply_text("Местоположение получено! Теперь выберите опцию: 'Погода сейчас', 'Прогноз на неделю' и другие.")

# Главная функция
def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Text(["Погода сейчас", "Погода вчера", "Погода завтра"]), handle_weather))
    application.add_handler(MessageHandler(filters.Text("Прогноз на неделю"), handle_weekly_forecast))
    application.add_handler(MessageHandler(filters.LOCATION, handle_location))

    # Запуск бота
    print("Бот запущен!")
    application.run_polling()

if __name__ == "__main__":
    main()

