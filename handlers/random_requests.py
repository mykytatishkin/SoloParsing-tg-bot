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
    """Генерация расписания запросов начиная с текущего времени (по Киеву).

    Базовый алгоритм сохранён: 30% заказов ночью (0..7 часов от текущего момента),
    70% — днём (7:00..23:59 от текущего момента).

    Для дневных заказов добавлено ограничение: разница между соседними дневными
    заказами случайная, но не менее 1 минуты и не более 2 часов.
    """
    now_kyiv = datetime.now(KYIV_TZ)  # Текущее время в Киеве

    night_count = int(request_count * 0.3)
    day_count = request_count - night_count

    # Ночные интервалы — как раньше: от сейчас до +7 часов
    night_intervals = [
        now_kyiv + timedelta(seconds=random.randint(0, 7 * 3600))
        for _ in range(night_count)
    ]

    # Дневное окно
    day_start = now_kyiv + timedelta(seconds=7 * 3600)
    day_end = now_kyiv + timedelta(seconds=23 * 3600 + 59 * 60)

    # Сначала генерируем дневные точки как раньше (равномерно по окну),
    # затем упорядочиваем и корректируем, чтобы соседние дневные шли с шагом 1м..2ч
    raw_day_intervals = [
        now_kyiv + timedelta(seconds=random.randint(7 * 3600, 23 * 3600 + 59 * 60))
        for _ in range(day_count)
    ]
    day_intervals_sorted = sorted(raw_day_intervals)

    adjusted_day_intervals = []
    prev_day_time = None
    for t in day_intervals_sorted:
        # Приводим в границы дневного окна
        if t < day_start:
            t = day_start
        if t > day_end:
            t = day_end

        if prev_day_time is None:
            # Первую дневную точку оставляем (в пределах окна)
            adjusted = t
        else:
            min_step = 60  # 1 минута
            max_step = 2 * 60 * 60  # 2 часа

            # Минимально допустимое и максимально допустимое время
            min_allowed = prev_day_time + timedelta(seconds=min_step)
            max_allowed = prev_day_time + timedelta(seconds=max_step)

            # Если исходная точка t слишком рано — сдвигаем вверх до min_allowed
            if t < min_allowed:
                t = min_allowed

            # Если всё ещё выходит за максимум — выбираем случайный шаг в диапазоне
            if t > max_allowed:
                step = random.randint(min_step, max_step)
                t = prev_day_time + timedelta(seconds=step)

            # Гарантируем, что не выйдем за пределы дневного окна
            if t > day_end:
                t = day_end

            adjusted = t

        adjusted_day_intervals.append(adjusted)
        prev_day_time = adjusted

    full_schedule = sorted(night_intervals + adjusted_day_intervals)
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