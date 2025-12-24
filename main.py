import os
import asyncio
import logging
import requests
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.markdown import hbold, hlink

# Загружаем переменные окружения из .env файла
load_dotenv()

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logging.error("BOT_TOKEN не найден в переменных окружения. Убедитесь, что .env файл создан и содержит токен.")
    exit(1)
    
    bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Базовый URL для OpenDota API
OPENDOTA_API_BASE = "https://api.opendota.com/api/"

async def get_player_data(player_id: str):
    #Получает общие данные игрока по ID.
    try:
        response = requests.get(f"{OPENDOTA_API_BASE}players/{player_id}")
        response.raise_for_status() # Вызывает исключение для ошибок HTTP
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка при запросе данных игрока {player_id}: {e}")
        return None

async def get_player_win_loss(player_id: str):
    #Получает статистику побед/поражений игрока.
    try:
        response = requests.get(f"{OPENDOTA_API_BASE}players/{player_id}/wl")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка при запросе статистики побед/поражений игрока {player_id}: {e}")
        return None

async def get_player_heroes(player_id: str):
    #Получает статистику по героям игрока.
    try:
        response = requests.get(f"{OPENDOTA_API_BASE}players/{player_id}/heroes")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка при запросе статистики героев игрока {player_id}: {e}")
        return None

async def get_hero_names():
    #Получает список всех героев с их ID и именами.
    try:
        response = requests.get(f"{OPENDOTA_API_BASE}heroes")
        response.raise_for_status()
        heroes_data = response.json()
        return {hero['localized_name'].lower(): str(hero['id']) for hero in heroes_data}
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка при запросе списка героев: {e}")
        return {}

# Обработчики команд 

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    Обрабатывает команду /start.
    Выводит приветственное сообщение и основную клавиатуру.
    """
    await message.answer(
        f"Привет, {hbold(message.from_user.full_name)}! Я Dota 2 Stats Bot.\n"
        "Я помогу тебе получить статистику игроков и героев.\n"
        "Используй команды ниже или /help для справки.",
        parse_mode="HTML"
    )
    # Основную клавиатура
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
         [InlineKeyboardButton(text="Мой профиль", callback_data="my_profile")],
         [InlineKeyboardButton(text="Помощь", callback_data="help_command")]
     ])
     await message.answer("Выбери действие:", reply_markup=keyboard)
    


