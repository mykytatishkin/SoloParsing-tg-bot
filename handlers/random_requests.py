import asyncio
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from utils.settings import load_settings
from utils.generator import generate_name_from_db, generate_phone_from_db, generate_quantity
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
import random
from datetime import datetime

# Глобальный флаг для управления выполнением запросов
stop_random_requests_flag = False
current_task = None  # Переменная для хранения текущей задачи


async def run_random_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Выполняет случайные запросы с обновлением количества запросов сразу после завершения цикла."""
    global stop_random_requests_flag
    stop_random_requests_flag = True  # Устанавливаем флаг перед запуском

    settings = load_settings()
    url = settings["url"]
    min_requests = settings["min_requests"]
    max_requests = settings["max_requests"]

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = None

    try:
        driver = webdriver.Chrome(options=options)

        while stop_random_requests_flag:  # Бесконечный цикл выполнения
            # Генерация нового числа запросов для текущего цикла
            total_requests = random.randint(min_requests, max_requests)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Starting a new cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                     f"Total requests for this cycle: {total_requests}"
            )

            for i in range(total_requests):
                if not stop_random_requests_flag:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="Random requests stopped by user."
                    )
                    return

                # Случайное время ожидания между запросами (от 1 секунды до 60 минут)
                pause_time = random.randint(1, 3600)

                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Next request will be executed in {pause_time // 60} minutes "
                         f"and {pause_time % 60} seconds."
                )

                # Ожидание перед выполнением следующего запроса
                elapsed_time = 0
                while elapsed_time < pause_time:
                    if not stop_random_requests_flag:
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text="Random requests stopped by user."
                        )
                        return
                    sleep_duration = min(10, pause_time - elapsed_time)
                    await asyncio.sleep(sleep_duration)
                    elapsed_time += sleep_duration

                # Выполнение запроса
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Executing random request #{i + 1} for this cycle..."
                )

                try:
                    driver.get(url)

                    # Генерация и заполнение данных
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

                    name = generate_name_from_db()
                    phone = generate_phone_from_db()
                    quantity = generate_quantity()

                    input_name.send_keys(name)
                    input_phone.send_keys(phone)
                    Select(input_quantity).select_by_value(quantity)
                    order_button.click()

                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"Random request sent:\nName: {name}\nPhone: {phone}\nQuantity: {quantity}"
                    )

                except Exception as e:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"Error during random request execution: {e}"
                    )

    finally:
        if driver:
            driver.quit()
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Random requests execution finished."
        )


async def stop_random_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Останавливает выполнение случайных запросов."""
    global stop_random_requests_flag
    stop_random_requests_flag = False  # Устанавливаем флаг остановки
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Random requests have been stopped."
    )


async def handle_random_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик запуска случайных запросов."""
    global current_task
    current_task = asyncio.create_task(run_random_requests(update, context))


def get_random_request_handlers():
    """Возвращает список обработчиков для управления случайными запросами."""
    return [
        CommandHandler("random_requests", handle_random_requests),
        CommandHandler("stop_random_requests", stop_random_requests),
    ]