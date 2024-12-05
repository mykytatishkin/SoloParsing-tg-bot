import asyncio
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from utils.settings import load_settings
from utils.generator import generate_name_from_db, generate_phone_from_db, generate_quantity
from playwright.async_api import async_playwright
import random
from datetime import datetime, timedelta

# Глобальный флаг для управления выполнением запросов
stop_random_requests_flag = False
current_task = None  # Переменная для хранения текущей задачи


async def run_random_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Выполняет случайные запросы с точным соблюдением расписания."""
    global stop_random_requests_flag
    stop_random_requests_flag = True  # Устанавливаем флаг перед запуском

    settings = load_settings()
    url = settings["url"]
    min_requests = settings["min_requests"]
    max_requests = settings["max_requests"]

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            context_browser = await browser.new_context()
            page = await context_browser.new_page()

            # Генерация общего числа запросов
            total_requests = random.randint(min_requests, max_requests)

            # Распределение запросов по времени
            requests_in_night = int(total_requests * 0.3)  # 30% в ночное время
            requests_in_day = total_requests - requests_in_night  # 70% в дневное время

            now = datetime.now()
            time_intervals = []

            # Генерация времени для ночных запросов (00:00–07:00)
            for _ in range(requests_in_night):
                hours = random.randint(max(0, now.hour if now.hour < 7 else 0), 6)
                minutes = random.randint(0, 59)
                seconds = random.randint(0, 59)
                if hours == now.hour:
                    minutes = random.randint(now.minute, 59)
                    if minutes == now.minute:
                        seconds = random.randint(now.second, 59)
                time_intervals.append(datetime(now.year, now.month, now.day, hours, minutes, seconds))

            # Генерация времени для дневных запросов (07:00–23:59)
            for _ in range(requests_in_day):
                hours = random.randint(max(7, now.hour if now.hour >= 7 else 7), 23)
                minutes = random.randint(0, 59)
                seconds = random.randint(0, 59)
                if hours == now.hour:
                    minutes = random.randint(now.minute, 59)
                    if minutes == now.minute:
                        seconds = random.randint(now.second, 59)
                time_intervals.append(datetime(now.year, now.month, now.day, hours, minutes, seconds))

            # Сортируем временные интервалы
            time_intervals.sort()
            time_intervals_str = [time.strftime("%H:%M:%S") for time in time_intervals]

            # Отправляем список временных интервалов пользователю
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Schedule of requests (starting from current time):\n" + "\n".join(time_intervals_str)
            )

            for target_time in time_intervals:
                if not stop_random_requests_flag:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="Random requests stopped by user."
                    )
                    return

                now = datetime.now()
                if target_time < now:
                    target_time += timedelta(days=1)

                pause_time = (target_time - now).total_seconds()
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Next request will be executed at {target_time.strftime('%H:%M:%S')} "
                         f"(in {int(pause_time // 60)} minutes and {int(pause_time % 60)} seconds)."
                )

                # Ждем до следующего запроса
                await asyncio.sleep(pause_time)

                # Выполнение запроса
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Executing request..."
                )

                try:
                    await page.goto(url)

                    # Генерация и заполнение данных
                    await page.fill('#full-name', generate_name_from_db())
                    await page.fill('#phone', generate_phone_from_db())
                    quantity = generate_quantity()
                    await page.select_option('#qty', quantity)
                    await page.click('//button[contains(text(), "Оформити замовлення")]')

                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"Request sent:\nName: {generate_name_from_db()}\n"
                             f"Phone: {generate_phone_from_db()}\nQuantity: {quantity}"
                    )

                except Exception as e:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"Error during request execution: {e}"
                    )

    except Exception as main_exception:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Critical error: {main_exception}"
        )
    finally:
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