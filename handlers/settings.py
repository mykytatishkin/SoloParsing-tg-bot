from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
from utils.settings import load_settings, save_settings

# Определяем состояние
NEW_VALUE = 0

async def start_setting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает процесс установки настройки."""
    command = update.message.text
    key_map = {
        "/set_min_requests": "min_requests",
        "/set_max_requests": "max_requests",
        "/set_min_quantity": "min_quantity",
        "/set_max_quantity": "max_quantity",
    }
    key = key_map.get(command)

    if not key:
        await update.message.reply_text("Команда не распознана.")
        return ConversationHandler.END

    context.user_data["setting_key"] = key
    await update.message.reply_text("Введите новое значение:")
    return NEW_VALUE

async def start_request_count_setting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает процесс установки request_count."""
    context.user_data["setting_key"] = "request_count"
    await update.message.reply_text("Введите новое значение для request_count:")
    return NEW_VALUE

async def set_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохраняет новое значение настройки."""
    key = context.user_data.get("setting_key")
    value = update.message.text

    if not value.isdigit():
        await update.message.reply_text("Ошибка: Введите число.")
        return NEW_VALUE

    value = int(value)
    settings = load_settings()

    # Проверка зависимостей для min и max
    if "min" in key and settings.get(key.replace("min", "max"), float("inf")) < value:
        await update.message.reply_text("Ошибка: Значение должно быть меньше максимального.")
        return NEW_VALUE
    if "max" in key and settings.get(key.replace("max", "min"), float("-inf")) > value:
        await update.message.reply_text("Ошибка: Значение должно быть больше минимального.")
        return NEW_VALUE

    # Проверка для request_count
    if key == "request_count":
        if not (settings["min_requests"] <= value <= settings["max_requests"]):
            await update.message.reply_text(
                f"Ошибка: request_count должно быть между {settings['min_requests']} и {settings['max_requests']}."
            )
            return NEW_VALUE

    # Сохраняем значение
    settings[key] = value
    save_settings(settings)

    await update.message.reply_text(f"Настройка '{key}' обновлена до: {value}")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отменяет настройку."""
    await update.message.reply_text("Изменение настройки отменено.")
    return ConversationHandler.END

def get_settings_conversation_handler():
    """Возвращает обработчик для управления настройками через диалоги."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("set_min_requests", start_setting),
            CommandHandler("set_max_requests", start_setting),
            CommandHandler("set_min_quantity", start_setting),
            CommandHandler("set_max_quantity", start_setting),
            CommandHandler("set_request_count", start_request_count_setting),  # Новая команда
        ],
        states={
            NEW_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_value)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )