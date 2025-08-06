from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import CommandHandler, ContextTypes
from utils.settings import load_settings

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет стартовое сообщение и отображает меню."""
    keyboard = [
        ["/run", "/random_requests"],
        ["/stop_requests", "/stop_random_requests"],
        ["/set_min_requests", "/set_max_requests"],
        ["/set_min_quantity", "/set_max_quantity"],
        ["/set_request_count", "/show_settings"]  # Добавлена кнопка для set_request_count
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Welcome! Use the menu below to select a command.",
        reply_markup=reply_markup
    )

async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает текущие настройки."""
    settings = load_settings()
    await update.message.reply_text(
        f"Current settings:\n"
        f"- URLs: {settings['urls']}\n"
        f"- Request Count: {settings['request_count']}\n"
        f"- Min Requests: {settings['min_requests']}\n"
        f"- Max Requests: {settings['max_requests']}\n"
        f"- Min Quantity: {settings['min_quantity']}\n"
        f"- Max Quantity: {settings['max_quantity']}"
    )

def get_basic_handlers():
    """Возвращает обработчики для базовых команд."""
    return [
        CommandHandler("start", start),
        CommandHandler("show_settings", show_settings),
    ]