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
from datetime import datetime, timedelta

# Глобальный флаг для управления выполнением запросов
stop_random_requests_flag = False
current_task = None  # Переменная для хранения текущей задачи


async def run_random_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Выполняет случайные запросы для каждой ссылки с учётом интервала запросов."""
    global stop_random_requests_flag
    stop_random_requests_flag = True  # Устанавливаем флаг перед запуском

    settings = load_settings()
    urls = settings["urls"]  # Загружаем список ссылок
    min_requests = settings["min_requests"]
    max_requests = settings["max_requests"]

    if not urls:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Список ссылок пуст. Добавьте ссылки через /add_url."
        )
        return

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = None

    try:
        driver = webdriver.Chrome(options=options)

        while stop_random_requests_flag:  # Бесконечный цикл выполнения
            # Генерация количества запросов для каждой ссылки
            daily_requests = {url: random.randint(min_requests, max_requests) for url in urls}
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Starting a new day cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.\n"
                     f"Daily requests for each URL:\n" +
                     "\n".join([f"{url}: {count} requests" for url, count in daily_requests.items()])
            )

            # Распределяем запросы в течение суток с максимальным интервалом 2 часа
            for url, total_requests in daily_requests.items():
                time_slots = []
                current_time = 0  # Время с начала суток (в секундах)

                for _ in range(total_requests):
                    # Добавляем случайное время в пределах 2 часов (но не превышая 24 часа)
                    next_time = current_time + random.randint(1, min(7200, 86400 - current_time))
                    time_slots.append(next_time)
                    current_time = next_time

                for i, slot in enumerate(time_slots):
                    if not stop_random_requests_flag:
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text="Random requests stopped by user."
                        )
                        return

                    # Рассчитываем время ожидания до следующего слота
                    now = datetime.now()
                    midnight_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
                    slot_time = midnight_today + timedelta(seconds=slot)
                    pause_time = (slot_time - now).total_seconds()

                    # Если текущий слот уже прошел, пропускаем паузу
                    if pause_time < 0:
                        continue

                    minutes_to_next_request = pause_time // 60
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"Next request for {url} will be executed at {slot_time.strftime('%H:%M:%S')} "
                             f"(in {minutes_to_next_request:.0f} minutes)."
                    )

                    # Ждём до следующего запроса
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

                    # Выполнение запроса для текущей ссылки
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"Executing random request #{i + 1} for {url}..."
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
                            text=f"Request sent for {url}:\nName: {name}\nPhone: {phone}\nQuantity: {quantity}"
                        )

                    except Exception as e:
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=f"Error during request execution for {url}: {e}"
                        )

            # Ждём до следующего дня ровно в 00:00
            now = datetime.now()
            next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            seconds_to_next_day = (next_midnight - now).total_seconds()
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="All requests for today completed. Waiting until 00:00 for the next cycle..."
            )
            await asyncio.sleep(seconds_to_next_day)

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