import asyncio
import random
import httpx
from datetime import datetime, timedelta
from pytz import timezone
from asyncio import Semaphore
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from playwright.async_api import async_playwright
from utils.settings import load_settings
from utils.generator import generate_name_from_db, generate_phone_from_db, generate_quantity

# Глобальный флаг для управления выполнением запросов
stop_random_requests_flag = False
running_task = None  # Переменная для хранения фоновой задачи
semaphore = Semaphore(3)  # Ограничиваем количество одновременных задач
KYIV_TZ = timezone("Europe/Kiev")  # Часовой пояс Киев


async def is_url_accessible(url):
    """Проверяет доступность URL перед выполнением запросов."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)
            return response.status_code == 200
    except Exception:
        return False


def generate_schedule(request_count):
    """Генерация расписания запросов начиная с текущего времени (по Киеву)."""
    now_kyiv = datetime.now(KYIV_TZ)  # Текущее время в Киеве
    night_count = int(request_count * 0.3)
    day_count = request_count - night_count

    night_intervals = [
        now_kyiv + timedelta(seconds=random.randint(0, 7 * 3600))
        for _ in range(night_count)
    ]
    day_intervals = [
        now_kyiv + timedelta(seconds=random.randint(7 * 3600, 23 * 3600 + 59 * 60))
        for _ in range(day_count)
    ]

    full_schedule = sorted(night_intervals + day_intervals)
    return full_schedule


async def async_wait_until(target_time):
    """Функция ожидания точного времени запроса"""
    while True:
        now_kyiv = datetime.now(KYIV_TZ)
        delay = (target_time - now_kyiv).total_seconds()
        if delay <= 0:
            break  # Если уже наступило время — отправляем запрос
        await asyncio.sleep(min(60, delay))  # Ждать максимум 60 секунд за раз


async def execute_request(browser, url, context, update):
    """Выполняет единичный запрос."""
    async with semaphore:
        context_browser = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context_browser.new_page()

        try:
            await page.goto(url, timeout=60000)
            await page.wait_for_load_state("networkidle")

            # Ввод данных
            name = generate_name_from_db()
            phone = generate_phone_from_db()
            quantity = generate_quantity()

            await page.fill("#full-name", name)
            await page.fill("#phone", phone)
            await page.select_option("#qty", quantity)

            # Клик по кнопке "Оформити замовлення"
            order_button = await page.wait_for_selector('//button[contains(text(), "Оформити замовлення")]', timeout=30000)
            await order_button.click()

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Request sent:\nName: {name}\nPhone: {phone}\nQuantity: {quantity}"
            )

        finally:
            # Освобождаем память
            await context_browser.close()


async def run_random_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Функция запуска случайных запросов"""
    global stop_random_requests_flag
    stop_random_requests_flag = False  # Устанавливаем флаг перед запуском

    settings = load_settings()
    url = settings.get("url")  # Одна ссылка
    min_requests = settings["min_requests"]
    max_requests = settings["max_requests"]

    if not url:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="No URL provided in settings. Please add a URL."
        )
        return

    if not await is_url_accessible(url):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"URL is not accessible: {url}. Please check the server."
        )
        return

    try:
        total_requests = random.randint(min_requests, max_requests)
        schedule = generate_schedule(total_requests)  # Генерация расписания

        schedule_str = "\n".join(time.strftime("%H:%M:%S") for time in schedule)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Schedule of requests (Kyiv Time):\n" + schedule_str
        )

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=True,
                args=["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"]
            )

            for target_time in schedule:
                if stop_random_requests_flag:
                    return  # Выход, если бот остановлен

                await async_wait_until(target_time)
                await execute_request(browser, url, context, update)

    except Exception as e:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Critical error during request execution: {repr(e)}"
        )


async def stop_random_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Останавливает выполнение случайных запросов."""
    global stop_random_requests_flag, running_task
    stop_random_requests_flag = True  # Устанавливаем флаг остановки

    if running_task and not running_task.done():
        running_task.cancel()  # Отменяем задачу, если она выполняется
        running_task = None

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Random requests have been stopped."
    )


async def handle_random_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Запуск run_random_requests в фоне"""
    global running_task

    if running_task and not running_task.done():
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Random requests are already running!"
        )
        return

    running_task = asyncio.create_task(run_random_requests(update, context))


def get_random_request_handlers():
    """Возвращает список обработчиков для управления случайными запросами."""
    return [
        CommandHandler("random_requests", handle_random_requests),
        CommandHandler("stop_random_requests", stop_random_requests),
    ]
