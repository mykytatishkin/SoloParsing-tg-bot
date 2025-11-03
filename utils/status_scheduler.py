"""
Модуль для отправки ежедневного статуса в группу Telegram.
"""
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from utils.cycle_status import cycle_status
from utils.settings import load_settings


KYIV_TZ = pytz.timezone("Europe/Kiev")


async def send_daily_status(bot):
    """Отправляет статус цикла запросов в группу Telegram."""
    try:
        settings = load_settings()
        group_chat_id = settings.get("status_group_chat_id")
        
        if not group_chat_id:
            print("Warning: status_group_chat_id not configured in settings.json")
            return
        
        status_message = cycle_status.get_status_message()
        
        await bot.send_message(
            chat_id=group_chat_id,
            text=status_message,
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Error sending daily status: {e}")


async def send_status_manually(bot, chat_id=None):
    """Отправляет статус цикла запросов в указанный чат или в группу из настроек."""
    try:
        if chat_id is None:
            settings = load_settings()
            chat_id = settings.get("status_group_chat_id")
            
            if not chat_id:
                return False, "Группа для отправки статуса не настроена. Используйте /set_status_group в группе."
        
        status_message = cycle_status.get_status_message()
        
        await bot.send_message(
            chat_id=chat_id,
            text=status_message,
            parse_mode="Markdown"
        )
        return True, "Статус отправлен."
    except Exception as e:
        return False, f"Ошибка отправки статуса: {e}"


def setup_daily_status_scheduler(application):
    """Настраивает планировщик для отправки статуса каждый день в 7:00 по Киеву."""
    scheduler = AsyncIOScheduler(timezone=KYIV_TZ)
    
    # Настраиваем задачу на выполнение каждый день в 7:00 по Киеву
    scheduler.add_job(
        send_daily_status,
        trigger=CronTrigger(hour=7, minute=0, timezone=KYIV_TZ),
        args=[application.bot],
        id="daily_status",
        name="Daily status report at 7:00 AM Kyiv time",
        replace_existing=True
    )
    
    scheduler.start()
    print("Daily status scheduler started. Status will be sent every day at 7:00 AM (Kyiv time).")
    
    return scheduler

