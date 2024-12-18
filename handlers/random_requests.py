import asyncio
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from utils.settings import load_settings
from utils.generator import generate_name_from_db, generate_phone_from_db, generate_quantity
from playwright.async_api import async_playwright
import random
from datetime import datetime, timedelta
import httpx
from pytz import timezone

# Глобальный флаг для управления выполнением запросов
stop_random_requests_flag = False
current_task = None  # Переменная для хранения текущей задачи

async def is_url_accessible(url):
    """Проверяет доступность URL перед выполнением запросов."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)
            return response.status_code == 200
    except Exception:
        return False

async def run_random_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global stop_random_requests_flag
    stop_random_requests_flag = True  # Устанавливаем флаг перед запуском

    kyiv_tz = timezone("Europe/Kiev")  # Часовой пояс Киев
    while stop_random_requests_flag:
        settings = load_settings()
        url = settings["url"]
        min_requests = settings["min_requests"]
        max_requests = settings["max_requests"]

        if not await is_url_accessible(url):
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"URL is not accessible: {url}. Please check the server."
            )
            return

        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True)
                context_browser = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                )
                page = await context_browser.new_page()

                total_requests = random.randint(min_requests, max_requests)
                requests_in_night = int(total_requests * 0.3)
                requests_in_day = total_requests - requests_in_night

                now = datetime.now(kyiv_tz)
                time_intervals = []

                for _ in range(requests_in_night):
                    hours = random.randint(0, 6)
                    minutes = random.randint(0, 59)
                    seconds = random.randint(0, 59)
                    target_time = kyiv_tz.localize(datetime(now.year, now.month, now.day, hours, minutes, seconds))
                    if target_time < now:
                        target_time += timedelta(days=1)
                    time_intervals.append(target_time)

                for _ in range(requests_in_day):
                    hours = random.randint(7, 23)
                    minutes = random.randint(0, 59)
                    seconds = random.randint(0, 59)
                    target_time = kyiv_tz.localize(datetime(now.year, now.month, now.day, hours, minutes, seconds))
                    if target_time < now:
                        target_time += timedelta(days=1)
                    time_intervals.append(target_time)

                time_intervals.sort()
                time_intervals_str = [time.astimezone(kyiv_tz).strftime("%H:%M:%S") for time in time_intervals]

                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Schedule of requests (Kyiv Time):\n" + "\n".join(time_intervals_str)
                )

                for target_time in time_intervals:
                    if not stop_random_requests_flag:
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text="Random requests stopped by user."
                        )
                        return

                    now = datetime.now(kyiv_tz)
                    pause_time = (target_time - now).total_seconds()
                    if pause_time > 0:
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=f"Next request at {target_time.strftime('%H:%M:%S')} "
                                 f"(in {int(pause_time // 60)} minutes and {int(pause_time % 60)} seconds)."
                        )
                        await asyncio.sleep(pause_time)

                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="Executing request..."
                    )

                    try:
                        await page.goto(url, timeout=60000)
                        name = generate_name_from_db()
                        phone = generate_phone_from_db()
                        quantity = generate_quantity()
                        await page.fill('#full-name', name)
                        await page.fill('#phone', phone)
                        await page.select_option('#qty', quantity)
                        await page.click('//button[contains(text(), "Оформити замовлення")]')

                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=f"Request sent:\nName: {name}\nPhone: {phone}\nQuantity: {quantity}"
                        )

                    except Exception as e:
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=f"Error during request execution: {repr(e)}"
                        )

        except Exception as main_exception:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Critical error during request execution: {repr(main_exception)}"
            )
            break
        finally:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Random requests execution finished. Restarting..."
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