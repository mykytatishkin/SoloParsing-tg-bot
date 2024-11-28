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

async def start_url_setting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает процесс добавления новой ссылки."""
    context.user_data["adding_urls"] = True  # Флаг для добавления списка ссылок
    await update.message.reply_text(
        "Введите одну или несколько ссылок (каждую на новой строке):"
    )
    return NEW_VALUE

async def add_urls(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Добавляет одну или несколько ссылок в список."""
    new_urls = update.message.text.split("\n")  # Разделяем по строкам
    settings = load_settings()

    # Проверяем наличие списка ссылок
    if "urls" not in settings:
        settings["urls"] = []

    # Проверяем лимит на количество ссылок
    if len(settings["urls"]) + len(new_urls) > 10:
        await update.message.reply_text(
            f"Ошибка: Максимум можно хранить 10 ссылок. Сейчас добавлено {len(settings['urls'])}."
        )
        return NEW_VALUE

    # Добавляем ссылки в список
    settings["urls"].extend(new_urls)
    save_settings(settings)

    urls_text = "\n".join([f"- {url}" for url in new_urls])
    await update.message.reply_text(f"Добавлены ссылки:\n{urls_text}")
    return ConversationHandler.END

async def list_urls(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выводит список текущих ссылок."""
    settings = load_settings()
    urls = settings.get("urls", [])
    if not urls:
        await update.message.reply_text("Список ссылок пуст.")
    else:
        url_list = "\n".join([f"{i+1}. {url}" for i, url in enumerate(urls)])
        await update.message.reply_text(f"Текущие ссылки:\n{url_list}")

async def remove_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает процесс удаления ссылки."""
    settings = load_settings()
    urls = settings.get("urls", [])
    if not urls:
        await update.message.reply_text("Список ссылок пуст. Нечего удалять.")
        return ConversationHandler.END

    url_list = "\n".join([f"{i+1}. {url}" for i, url in enumerate(urls)])
    await update.message.reply_text(
        f"Текущие ссылки:\n{url_list}\nВведите номер ссылки для удаления:"
    )
    context.user_data["setting_key"] = "urls"
    return NEW_VALUE

async def delete_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Удаляет выбранную ссылку из списка."""
    settings = load_settings()
    urls = settings.get("urls", [])

    # Проверяем, что ссылки есть
    if not urls:
        await update.message.reply_text("Список ссылок пуст. Нечего удалять.")
        return ConversationHandler.END

    try:
        # Преобразуем ввод пользователя в индекс
        index = int(update.message.text) - 1

        # Проверяем, что индекс в пределах списка
        if index < 0 or index >= len(urls):
            raise ValueError("Неверный индекс")

        # Удаляем ссылку
        removed_url = urls.pop(index)
        save_settings(settings)

        await update.message.reply_text(f"Ссылка удалена:\n{removed_url}")
    except ValueError:
        await update.message.reply_text("Ошибка: Введите корректный номер ссылки.")
        return NEW_VALUE

    return ConversationHandler.END

def get_settings_conversation_handler():
    """Обновляем обработчик для управления ссылками и другими настройками."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("set_min_requests", start_setting),
            CommandHandler("set_max_requests", start_setting),
            CommandHandler("set_min_quantity", start_setting),
            CommandHandler("set_max_quantity", start_setting),
            CommandHandler("set_request_count", start_request_count_setting),
            CommandHandler("add_url", start_url_setting),
            CommandHandler("list_urls", list_urls),
            CommandHandler("remove_url", remove_url),
        ],
        states={
            NEW_VALUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex(r'^\d+$'), delete_url),  # Только числа обрабатываются для удаления
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(r'^\d+$'), add_urls),  # Только текст для добавления ссылок
                MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex(r'^\d+$'), set_value),  # Только числа для других значений
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )