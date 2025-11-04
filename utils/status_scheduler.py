"""
Модуль для отправки ежедневного статуса в группу Telegram.
"""
import pytz
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from utils.cycle_status import cycle_status
from utils.settings import load_settings


KYIV_TZ = pytz.timezone("Europe/Kiev")

# ID группы для отправки отчета о цикле запросов
CYCLE_REPORT_GROUP_ID = -5049129065


def format_cycle_report() -> str:
    """Форматирует отчет о статусе цикла запросов в требуемом формате."""
    if not cycle_status.is_running or cycle_status.cycle_start_time is None:
        cycle_start_str = datetime.now(KYIV_TZ).strftime("%Y-%m-%d %H:%M:%S")
        return (
            "📊 Статус цикла запросов\n\n"
            f"🕐 Запуск цикла: {cycle_start_str} (Киев)\n"
            f"✅ Выполнено запросов: 0 из 0\n"
            f"⏰ Следующее обновление: {cycle_start_str} (Киев)"
        )
    
    cycle_start_str = cycle_status.cycle_start_time.strftime("%Y-%m-%d %H:%M:%S")
    
    if cycle_status.next_update_time:
        next_update_str = cycle_status.next_update_time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        next_update_str = datetime.now(KYIV_TZ).strftime("%Y-%m-%d %H:%M:%S")
    
    return (
        "📊 Статус цикла запросов\n\n"
        f"🕐 Запуск цикла: {cycle_start_str} (Киев)\n"
        f"✅ Выполнено запросов: {cycle_status.completed_requests} из {cycle_status.total_requests}\n"
        f"⏰ Следующее обновление: {next_update_str} (Киев)"
    )


async def send_cycle_report_to_group(bot):
    """Отправляет отчет о статусе цикла запросов в указанную группу в 7:00 по Киеву."""
    try:
        report_message = format_cycle_report()
        
        await bot.send_message(
            chat_id=CYCLE_REPORT_GROUP_ID,
            text=report_message
        )
    except Exception as e:
        print(f"Error sending cycle report to group {CYCLE_REPORT_GROUP_ID}: {e}")


async def send_cycle_report_manually(bot, chat_id=None):
    """Отправляет отчет о цикле запросов в указанный чат или в группу -5049129065."""
    try:
        target_chat_id = chat_id if chat_id is not None else CYCLE_REPORT_GROUP_ID
        report_message = format_cycle_report()
        
        await bot.send_message(
            chat_id=target_chat_id,
            text=report_message
        )
        return True, f"Отчет о цикле отправлен в чат {target_chat_id}."
    except Exception as e:
        return False, f"Ошибка отправки отчета о цикле: {e}"


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
    
    # Настраиваем задачу на выполнение каждый день в 7:00 по Киеву (существующая логика)
    scheduler.add_job(
        send_daily_status,
        trigger=CronTrigger(hour=7, minute=0, timezone=KYIV_TZ),
        args=[application.bot],
        id="daily_status",
        name="Daily status report at 7:00 AM Kyiv time",
        replace_existing=True
    )
    
    # Настраиваем задачу для отправки отчета о цикле запросов в группу -5049129065
    scheduler.add_job(
        send_cycle_report_to_group,
        trigger=CronTrigger(hour=7, minute=0, timezone=KYIV_TZ),
        args=[application.bot],
        id="cycle_report_group",
        name="Cycle report to group at 7:00 AM Kyiv time",
        replace_existing=True
    )
    
    scheduler.start()
    print("Daily status scheduler started. Status will be sent every day at 7:00 AM (Kyiv time).")
    print(f"Cycle report will be sent to group {CYCLE_REPORT_GROUP_ID} every day at 7:00 AM (Kyiv time).")
    
    return scheduler

