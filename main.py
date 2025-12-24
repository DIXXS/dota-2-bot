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

# Вспомогательные функции для работы с OpenDota API 

async def get_player_data(player_id: str):
    """Получает общие данные игрока по ID."""
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
    """Получает список всех героев с их ID и именами."""
    try:
        response = requests.get(f"{OPENDOTA_API_BASE}heroes")
        response.raise_for_status()
        heroes_data = response.json()
        return {hero['localized_name'].lower(): str(hero['id']) for hero in heroes_data}
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка при запросе списка героев: {e}")
        return {}

#  Обработчики команд 

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    
    #Обрабатывает команду /start.
    #Выводит приветственное сообщение и основную клавиатуру.
    
    await message.answer(
        f"Привет, {hbold(message.from_user.full_name)}! Я Dota 2 Stats Bot.\n"
        "Я помогу тебе получить статистику игроков и героев.\n"
        "Используй команды ниже или /help для справки.",
        parse_mode="HTML"
    )
    # Здесь можно добавить основную клавиатуру, если она нужна
    # Например:
    # keyboard = InlineKeyboardMarkup(inline_keyboard=[
    #     [InlineKeyboardButton(text="Мой профиль", callback_data="my_profile")],
    #     [InlineKeyboardButton(text="Помощь", callback_data="help_command")]
    # ])
    # await message.answer("Выбери действие:", reply_markup=keyboard)


@dp.message(Command("help"))
async def command_help_handler(message: Message) -> None:
    """
    Обрабатывает команду /help.
    Выводит справочную информацию.
    """
    help_text = (
        f"{hbold('Доступные команды:')}\n"
        f"/profile [ID] - Общая статистика игрока (никнейм, MMR, винрейт).\n"
        f"/top [ID] - Топ-3 героя игрока по винрейту (минимум 5 матчей).\n"
        f"/hero [ID] [Имя героя] - Детальная статистика по герою для игрока.\n"
        f"/help - Эта справка.\n\n"
        f"{hbold('Тестовые ID игроков:')}\n"
        f"70388657 (Miracle-)\n"
        f"106869122 (Dendi)\n\n"
        f"{hbold('Решение проблем:')}\n"
        "Если бот сообщает 'Профиль не найден или статистика скрыта.', "
        "убедитесь, что у игрока включена 'Общедоступная история матчей' в настройках Dota 2.\n"
        "Настройки -> Сообщество -> Общедоступная история матчей."
    )
    await message.answer(help_text, parse_mode="HTML")


@dp.message(Command("profile"))
async def command_profile_handler(message: Message) -> None:
    """
    Обрабатывает команду /profile [ID].
    Отображает общую статистику игрока.
    """
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Пожалуйста, укажите ID игрока. Пример: `/profile 70388657`", parse_mode="Markdown")
        return

    player_id = args[1]
    await message.answer(f"Загружаю профиль игрока {player_id}...")

    player_data = await get_player_data(player_id)
    player_wl = await get_player_win_loss(player_id)

    if not player_data or not player_wl:
        await message.answer("Профиль не найден или статистика скрыта. "
                             "Убедитесь, что ID верен и история матчей игрока открыта.")
        return

    profile = player_data.get('profile')
    if not profile:
        await message.answer("Профиль не найден или статистика скрыта. "
                             "Убедитесь, что ID верен и история матчей игрока открыта.")
        return

    personaname = profile.get('personaname', 'Неизвестно')
    mmr_estimate = player_data.get('mmr_estimate', {}).get('estimate', 'N/A')
    wins = player_wl.get('win', 0)
    losses = player_wl.get('lose', 0)
    total_matches = wins + losses
    winrate = (wins / total_matches * 100) if total_matches > 0 else 0

    profile_text = (
        f"{hbold('Профиль игрока:')} {hlink(personaname, f'https://www.opendota.com/players/{player_id}')}\n"
        f"MMR (оценка): {mmr_estimate}\n"
        f"Всего матчей: {total_matches}\n"
        f"Побед: {wins}\n"
        f"Поражений: {losses}\n"
        f"Винрейт: {winrate:.2f}%"
    )
    await message.answer(profile_text, parse_mode="HTML")


@dp.message(Command("top"))
async def command_top_handler(message: Message) -> None:
    """
    Обрабатывает команду /top [ID].
    Показывает трех героев с лучшим винрейтом.
    """
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Пожалуйста, укажите ID игрока. Пример: `/top 70388657`", parse_mode="Markdown")
        return

    player_id = args[1]
    await message.answer(f"Загружаю топгероев игрока {player_id}...")

    player_heroes = await get_player_heroes(player_id)
    hero_names_map = await get_hero_names() # Получаем карту ID-имя героя

    if not player_heroes:
        await message.answer("Не удалось получить статистику по героям. "
                             "Убедитесь, что ID верен и история матчей игрока открыта.")
        return

    # Фильтруем героев с минимум 5 матчами и считаем винрейт
    filtered_heroes = []
    for hero in player_heroes:
        games = hero.get('games', 0)
        if games >= 5:
            wins = hero.get('win', 0)
            hero_id = str(hero.get('hero_id'))
            winrate = (wins / games * 100) if games > 0 else 0
            hero_name = next((name for name, hid in hero_names_map.items() if hid == hero_id), f"Неизвестный герой ({hero_id})")
            filtered_heroes.append({'name': hero_name.title(), 'winrate': winrate, 'games': games})

    if not filtered_heroes:
        await message.answer(f"У игрока {player_id} нет героев с минимум 5 сыгранными матчами или статистика скрыта.")
        return

    # Сортируем по винрейту и берем топ-3
    top_heroes = sorted(filtered_heroes, key=lambda x: x['winrate'], reverse=True)[:3]

    top_text = f"{hbold('Топ-3 героя игрока ')}{player_id}:\n"
    for i, hero in enumerate(top_heroes):
        top_text += f"{i+1}. {hero['name']}: {hero['winrate']:.2f}% винрейт ({hero['games']} матчей)\n"

    await message.answer(top_text, parse_mode="HTML")


@dp.message(Command("hero"))
async def command_hero_handler(message: Message) -> None:
    """
    Обрабатывает команду /hero [ID] [Имя героя].
    Предоставляет детальную статистику по выбранному герою для указанного игрока.
    """
    args = message.text.split(maxsplit=2) # Разделяем на 3 части: /hero, ID, Имя героя
    if len(args) < 3:
        await message.answer("Пожалуйста, укажите ID игрока и имя героя. Пример: `/hero 70388657 Pudge`", parse_mode="Markdown")
        return

    player_id = args[1]
    hero_name_input = args[2].lower()
    await message.answer(f"Загружаю статистику по герою '{hero_name_input.title()}' для игрока {player_id}...")

    hero_names_map = await get_hero_names()
    hero_id = hero_names_map.get(hero_name_input)

    if not hero_id:
        await message.answer(f"Герой '{hero_name_input.title()}' не найден. Проверьте правильность написания.")
        return

    player_heroes = await get_player_heroes(player_id)
    if not player_heroes:
        await message.answer("Не удалось получить статистику по героям. "
                             "Убедитесь, что ID верен и история матчей игрока открыта.")
        return

    hero_stats = next((h for h in player_heroes if str(h.get('hero_id')) == hero_id), None)

    if not hero_stats:
        await message.answer(f"Игрок {player_id} не играл на герое '{hero_name_input.title()}' или статистика скрыта.")
        return

    wins = hero_stats.get('win', 0)
    games = hero_stats.get('games', 0)
    losses = games - wins
    winrate = (wins / games * 100) if games > 0 else 0

    hero_stat_text = (
        f"{hbold('Статистика по герою ')}{hero_name_input.title()} для игрока {player_id}:\n"
        f"Сыграно матчей: {games}\n"
        f"Побед: {wins}\n"
        f"Поражений: {losses}\n"
        f"Винрейт: {winrate:.2f}%"
    )
    await message.answer(hero_stat_text, parse_mode="HTML")


async def main() -> None:
    """Запускает бота."""
    # Запускаем получение обновлений
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
