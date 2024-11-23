import os
import json
import random
import asyncio
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Определяем абсолютный путь к settings.json
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
settings_path = os.path.join(BASE_DIR, "settings.json")

# Проверяем, существует ли файл settings.json
if not os.path.exists(settings_path):
    raise FileNotFoundError(f"Settings file not found at: {settings_path}")

# Загрузка настроек из settings.json
with open(settings_path, "r") as file:
    settings = json.load(file)

URL = settings["url"]
REQUEST_COUNT = settings["request_count"]
MIN_REQUESTS = settings.get("min_requests", 1)
MAX_REQUESTS = settings.get("max_requests", 10)
TELEGRAM_BOT_TOKEN = settings["telegram_bot_token"]

# Глобальные флаги
stop_requests_flag = False
stop_random_requests_flag = False

# Сохранение настроек в файл
def save_settings():
    with open(settings_path, "w") as file:
        json.dump(settings, file, indent=4)

# Функции генерации данных
def generate_name():
    names = ["Ivan", "Anna", "Petro", "Maria", "Serhiy", "Olena", "Dmytro", "Olha"]
    surnames = ["Ivanenko", "Petrenko", "Sidorenko", "Kuznetsov", "Novikov", "Morozov", "Fedorov"]
    return f"{random.choice(names)} {random.choice(surnames)}"

def generate_phone():
    return f"+380{random.randint(100000000, 999999999)}"

def generate_quantity():
    options = ["1", "2", "3", "4", "5", "6", "7", "8"]
    return random.choice(options)

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        ["/run", "/stop_requests"],
        ["/random_requests", "/stop_random_requests"],
        ["/set_url", "/set_request_count"],
        ["/set_min_max_requests", "/show_settings"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Welcome! Use the menu below to select a command.",
        reply_markup=reply_markup
    )

# Обработчик команды /show_settings
async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        f"Current settings:\n"
        f"- URL: {settings['url']}\n"
        f"- Request Count: {settings['request_count']}\n"
        f"- Min Requests: {settings['min_requests']}\n"
        f"- Max Requests: {settings['max_requests']}"
    )

# Обработчик команды /set_url
async def set_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.args:
        new_url = " ".join(context.args)
        settings["url"] = new_url
        save_settings()
        await update.message.reply_text(f"URL updated to: {new_url}")
    else:
        await update.message.reply_text("Usage: /set_url <new_url>")

# Обработчик команды /set_request_count
async def set_request_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.args and context.args[0].isdigit():
        new_count = int(context.args[0])
        settings["request_count"] = new_count
        save_settings()
        await update.message.reply_text(f"Request count updated to: {new_count}")
    else:
        await update.message.reply_text("Usage: /set_request_count <number>")

# Обработчик команды /set_min_max_requests
async def set_min_max_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) == 2 and all(arg.isdigit() for arg in context.args):
        min_requests = int(context.args[0])
        max_requests = int(context.args[1])

        if min_requests > max_requests:
            await update.message.reply_text("Error: Min requests cannot be greater than Max requests.")
            return

        settings["min_requests"] = min_requests
        settings["max_requests"] = max_requests
        save_settings()
        await update.message.reply_text(f"Min requests set to {min_requests}, Max requests set to {max_requests}.")
    else:
        await update.message.reply_text("Usage: /set_min_max_requests <min_requests> <max_requests>")

# Обработчик команды /run
async def run_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global stop_requests_flag
    stop_requests_flag = False

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)

    try:
        for i in range(settings["request_count"]):
            if stop_requests_flag:
                await update.message.reply_text("Requests stopped by user.")
                break

            await update.message.reply_text(f"Executing request #{i + 1}...")

            driver.get(settings["url"])

            input_name = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, 'full-name'))
            )
            input_phone = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, 'phone'))
            )
            input_quantity = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, 'qty'))
            )
            order_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Оформити замовлення")]'))
            )

            name = generate_name()
            phone = generate_phone()
            quantity = generate_quantity()

            input_name.send_keys(name)
            input_phone.send_keys(phone)
            Select(input_quantity).select_by_value(quantity)
            order_button.click()

            await update.message.reply_text(f"Request sent: Name - {name}, Phone - {phone}, Quantity - {quantity}")

            time.sleep(3)

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

    finally:
        driver.quit()

# Обработчик команды /stop_requests
async def stop_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global stop_requests_flag
    stop_requests_flag = True
    await update.message.reply_text("Stopping all requests...")

# Обработчик команды /random_requests
async def random_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global stop_random_requests_flag
    stop_random_requests_flag = False

    await update.message.reply_text("Starting random requests for 24 hours...")

    now = datetime.now()
    end_time = now + timedelta(days=1)

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)

    try:
        while datetime.now() < end_time:
            if stop_random_requests_flag:
                await update.message.reply_text("Random requests stopped by user.")
                break

            request_count = random.randint(settings["min_requests"], settings["max_requests"])
            await update.message.reply_text(f"Sending {request_count} requests...")

            for _ in range(request_count):
                if stop_random_requests_flag:
                    break

                driver.get(settings["url"])

                input_name = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, 'full-name'))
                )
                input_phone = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, 'phone'))
                )
                input_quantity = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, 'qty'))
                )
                order_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Оформити замовлення")]'))
                )

                name = generate_name()
                phone = generate_phone()
                quantity = generate_quantity()

                input_name.send_keys(name)
                input_phone.send_keys(phone)
                Select(input_quantity).select_by_value(quantity)
                order_button.click()

                await asyncio.sleep(random.randint(2, 5))

            await asyncio.sleep(random.randint(300, 1800))  # 5-30 минут паузы

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

    finally:
        driver.quit()

# Обработчик команды /stop_random_requests
async def stop_random_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global stop_random_requests_flag
    stop_random_requests_flag = True
    await update.message.reply_text("Stopping random requests...")

# Запуск бота
def main() -> None:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("show_settings", show_settings))
    application.add_handler(CommandHandler("set_url", set_url))
    application.add_handler(CommandHandler("set_request_count", set_request_count))
    application.add_handler(CommandHandler("set_min_max_requests", set_min_max_requests))
    application.add_handler(CommandHandler("run", run_requests))
    application.add_handler(CommandHandler("stop_requests", stop_requests))
    application.add_handler(CommandHandler("random_requests", random_requests))
    application.add_handler(CommandHandler("stop_random_requests", stop_random_requests))

    application.run_polling()

if __name__ == "__main__":
    main()