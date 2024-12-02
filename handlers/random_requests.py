import asyncio
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from utils.settings import load_settings
from utils.generator import generate_name_from_db, generate_phone_from_db, generate_quantity
from playwright.async_api import async_playwright
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

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context_browser = await browser.new_context()
        page = await context_browser.new_page()

        try:
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
                        await page.goto(url)

                        # Генерация и заполнение данных
                        await page.fill('#full-name', generate_name_from_db())
                        await page.fill('#phone', generate_phone_from_db())
                        quantity = generate_quantity()
                        await page.select_option('#qty', quantity)
                        await page.click('//button[contains(text(), "Оформити замовлення")]')

                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=f"Random request sent:\nName: {generate_name_from_db()}\n"
                                 f"Phone: {generate_phone_from_db()}\nQuantity: {quantity}"
                        )

                    except Exception as e:
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=f"Error during random request execution: {e}"
                        )

        finally:
            await browser.close()
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