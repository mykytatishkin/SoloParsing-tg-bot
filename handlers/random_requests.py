import asyncio
import pytz
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from utils.settings import load_settings
from utils.generator import generate_name_from_db, generate_phone_from_db, generate_quantity
import random
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

stop_random_requests_flag = False
KYIV_TZ = pytz.timezone("Europe/Kiev")


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


async def process_url(url, url_number, update, context, min_requests, max_requests):
    """Обработчик запросов к URL"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context_browser = await browser.new_context()
        page = await context_browser.new_page()

        try:
            while True:
                requests_count = random.randint(min_requests, max_requests)
                schedule = generate_schedule(requests_count)  # Генерация расписания

                # Форматируем расписание в строку
                schedule_str = "\n".join(time.strftime("%H:%M:%S") for time in schedule)

                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Schedule of requests for URL #{url_number} (Kyiv Time):\n{schedule_str}"
                )

                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Starting requests for URL #{url_number} ({url}). {requests_count} requests will be sent at scheduled times."
                )

                for i, request_time in enumerate(schedule):
                    await async_wait_until(request_time)

                    # Выполнение запроса
                    await page.goto(url)
                    await page.fill('#full-name', generate_name_from_db())
                    await page.fill('#phone', generate_phone_from_db())
                    quantity = generate_quantity()
                    await page.select_option('#qty', quantity)
                    await page.click('//button[contains(text(), "Оформити замовлення")]')

                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"Request {i + 1}/{requests_count} sent for URL #{url_number} ({url})."
                    )

        finally:
            await browser.close()


async def run_random_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Запуск отправки случайных запросов"""
    global stop_random_requests_flag
    stop_random_requests_flag = False  # Очищаем флаг при новом запуске

    settings = load_settings()
    urls = settings["urls"]
    min_requests = settings["min_requests"]
    max_requests = settings["max_requests"]

    if not urls:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="The list of URLs is empty. Add links using /add_url."
        )
        return

    loop = asyncio.get_running_loop()
    for i, url in enumerate(urls):
        loop.create_task(process_url(url, i + 1, update, context, min_requests, max_requests))


async def stop_random_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда для остановки работы"""
    global stop_random_requests_flag
    stop_random_requests_flag = True

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Stopping requests will not cancel ongoing ones, but no new cycles will start."
    )


def get_random_request_handlers():
    return [
        CommandHandler("random_requests", run_random_requests),
        CommandHandler("stop_random_requests", stop_random_requests),
    ]