"""
Модуль для отслеживания статуса цикла запросов.
"""
from datetime import datetime
from typing import Optional
import pytz

KYIV_TZ = pytz.timezone("Europe/Kiev")


class CycleStatus:
    """Класс для хранения статуса цикла запросов."""
    
    def __init__(self):
        self.cycle_start_time: Optional[datetime] = None
        self.completed_requests: int = 0
        self.total_requests: int = 0
        self.next_update_time: Optional[datetime] = None
        self.is_running: bool = False
    
    def start_cycle(self, total_requests: int, next_update_time: Optional[datetime] = None):
        """Запускает новый цикл запросов."""
        self.cycle_start_time = datetime.now(KYIV_TZ)
        self.completed_requests = 0
        self.total_requests = total_requests
        self.next_update_time = next_update_time
        self.is_running = True
    
    def increment_completed(self):
        """Увеличивает счетчик выполненных запросов."""
        self.completed_requests += 1
    
    def update_next_update_time(self, next_update_time: datetime):
        """Обновляет время следующего обновления."""
        self.next_update_time = next_update_time
    
    def stop_cycle(self):
        """Останавливает цикл."""
        self.is_running = False
    
    def get_status_message(self) -> str:
        """Возвращает текстовое сообщение со статусом."""
        if not self.is_running or self.cycle_start_time is None:
            return "❌ Цикл запросов не запущен."
        
        cycle_start_str = self.cycle_start_time.strftime("%Y-%m-%d %H:%M:%S")
        
        status_parts = [
            "📊 **Статус цикла запросов**",
            "",
            f"🕐 **Запуск цикла:** {cycle_start_str} (Киев)",
            f"✅ **Выполнено запросов:** {self.completed_requests} из {self.total_requests}",
        ]
        
        if self.next_update_time:
            next_update_str = self.next_update_time.strftime("%Y-%m-%d %H:%M:%S")
            status_parts.append(f"⏰ **Следующее обновление:** {next_update_str} (Киев)")
        else:
            status_parts.append("⏰ **Следующее обновление:** Не запланировано")
        
        return "\n".join(status_parts)


# Глобальный экземпляр статуса
cycle_status = CycleStatus()

