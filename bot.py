from telegram.ext import Application
from handlers.basic import get_basic_handlers
from handlers.settings import get_settings_conversation_handler
from handlers.requests import get_request_handlers
from handlers.random_requests import get_random_request_handlers
from utils.settings import load_telegram_token

def main():
    try:
        # Загружаем токен Telegram
        token = load_telegram_token()
    except FileNotFoundError:
        print("Error: 'settings.json' file not found. Make sure the file exists in the expected location.")
        return
    except KeyError:
        print("Error: Telegram bot token not found in 'settings.json'. Please check your configuration.")
        return

    try:
        # Создаем экземпляр приложения
        application = Application.builder().token(token).build()

        # Добавляем обработчики
        application.add_handlers(get_basic_handlers())  # Базовые команды (/start, /menu)
        application.add_handler(get_settings_conversation_handler())  # Настройки
        application.add_handlers(get_request_handlers())  # Запросы
        application.add_handlers(get_random_request_handlers())  # Случайные запросы
    except Exception as e:
        print(f"Error while setting up the bot: {e}")
        return

    print("Bot is running... Press Ctrl+C to stop.")

    # Запускаем бота
    try:
        application.run_polling()
    except Exception as e:
        print(f"Error while running the bot: {e}")

if __name__ == "__main__":
    main()