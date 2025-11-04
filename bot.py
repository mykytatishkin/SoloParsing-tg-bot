from telegram.ext import Application
from handlers.basic import get_basic_handlers
from handlers.settings import get_settings_conversation_handler, get_status_group_handlers
from handlers.requests import get_request_handlers
from handlers.random_requests import get_random_request_handlers
from utils.settings import load_telegram_token
from utils.status_scheduler import setup_daily_status_scheduler

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
        # Создаем экземпляр приложения с настройками для обработки сетевых ошибок
        application = Application.builder().token(token).build()
        
        # Настраиваем обработку ошибок сети
        from telegram.error import NetworkError, TimedOut
        
        async def error_handler(update, context):
            """Обработчик ошибок"""
            error = context.error
            if isinstance(error, (NetworkError, TimedOut)):
                print(f"⚠️ Сетевая ошибка: {error}. Переподключение...")
                return
            print(f"❌ Ошибка: {error}")
        
        application.add_error_handler(error_handler)

        # Добавляем обработчики
        application.add_handlers(get_basic_handlers())  # Базовые команды (/start, /menu)
        application.add_handler(get_settings_conversation_handler())  # Настройки
        application.add_handlers(get_status_group_handlers())  # Настройка группы для статуса
        application.add_handlers(get_request_handlers())  # Запросы
        application.add_handlers(get_random_request_handlers())  # Случайные запросы
        
        # Настраиваем планировщик для отправки ежедневного статуса
        scheduler = setup_daily_status_scheduler(application)
        
    except Exception as e:
        print(f"Error while setting up the bot: {e}")
        return

    print("Bot is running... Press Ctrl+C to stop.")

    # Запускаем бота
    try:
        application.run_polling(
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True,
            close_loop=False
        )
    except KeyboardInterrupt:
        print("\nStopping bot...")
        scheduler.shutdown(wait=False)
    except Exception as e:
        print(f"Error while running the bot: {e}")
        import traceback
        print(f"Traceback:\n{traceback.format_exc()}")
        scheduler.shutdown(wait=False)

if __name__ == "__main__":
    main()