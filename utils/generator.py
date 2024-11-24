import os
import pandas as pd
import random
from utils.settings import load_settings

# Устанавливаем путь к файлу db.xlsx относительно корневой директории
file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../db.xlsx'))

# Проверяем, существует ли файл
if not os.path.exists(file_path):
    raise FileNotFoundError(f"Файл не найден: {file_path}")

# Загружаем данные из db.xlsx
data = pd.read_excel(file_path)

# Убираем строки с отсутствующими именами или телефонами
data = data.dropna(subset=["Имя", "Телефон"])

def generate_name_from_db():
    """Генерирует имя случайным образом из db.xlsx."""
    row = data.sample(1).iloc[0]  # Случайный выбор строки
    first_name = row["Имя"]
    last_name = row["Фамилия"] if not pd.isna(row["Фамилия"]) else ""
    return f"{first_name} {last_name}".strip()

def generate_phone_from_db():
    """Генерирует телефон случайным образом из db.xlsx."""
    row = data.sample(1).iloc[0]  # Случайный выбор строки
    return str(row["Телефон"])

def generate_quantity():
    """
    Генерирует случайное количество с вероятностью 80% для 1 шт.
    """
    settings = load_settings()
    min_quantity = settings.get("min_quantity", 1)
    max_quantity = settings.get("max_quantity", 8)

    if random.random() < 0.8:  # 80% вероятность
        return str(min_quantity)  # Возвращаем минимальное количество (обычно 1)
    else:
        # Генерация случайного количества из оставшихся значений
        return str(random.randint(min_quantity + 1, max_quantity))