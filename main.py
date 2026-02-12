# --- Импорты библиотек ---
import logging
import os
import aiohttp # Для асинхронных HTTP-запросов к API
from dotenv import load_dotenv # Для загрузки переменных окружения из .env

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage # Для хранения состояний FSM в памяти
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# --- Настройка логирования ---
# Это поможет видеть, что происходит с ботом в консоли
logging.basicConfig(level=logging.INFO)

# --- Загрузка переменных окружения ---
# Ищет файл .env в корне проекта и загружает из него переменные
load_dotenv()

# Получаем токен бота из переменной окружения TELEGRAM_BOT_TOKEN
# Если переменная не найдена, выдаст ошибку, чтобы ты не забыл её добавить
API_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
# Получаем ключ OpenDota API из переменной окружения OPEN_DOTA_API_KEY
OPEN_DOTA_API_KEY = os.getenv('OPEN_DOTA_API_KEY')

# Проверяем, что токены загружены
if not API_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в .env файле!")
if not OPEN_DOTA_API_KEY:
    raise ValueError("OPEN_DOTA_API_KEY не найден в .env файле!")

# --- Инициализация бота и диспетчера ---
# Bot - это сам экземпляр бота, через который отправляются запросы к Telegram API
bot = Bot(token=API_TOKEN, parse_mode=types.ParseMode.HTML) # parse_mode=HTML для жирного текста и т.д.
# MemoryStorage - хранилище состояний FSM (для учебного проекта достаточно)
storage = MemoryStorage()
# Dispatcher - обрабатывает входящие обновления от Telegram
dp = Dispatcher(bot, storage=storage)

# --- Определение состояний для FSM ---
# Используется для пошагового ввода данных от пользователя
class Form(StatesGroup):
    player_id = State() # Состояние ожидания ID игрока

# --- Вспомогательные функции для работы с OpenDota API ---

# Функция для получения статистики игрока
async def get_player_stats(player_id: int):
    """
    Получает общую статистику игрока по его ID из OpenDota API.
    Обрабатывает возможные ошибки API.
    """
    url = f"https://api.opendota.com/api/players/{player_id}?api_key={OPEN_DOTA_API_KEY}"
    try:
        async with aiohttp.ClientSession() as session: # Создаем асинхронную сессию
            async with session.get(url) as response: # Отправляем GET-запрос
                if response.status == 200: # Если запрос успешен (код 200 OK)
                    data = await response.json() # Парсим JSON-ответ
                    return data
                elif response.status == 404: # Если игрок не найден
                    return {"error": "Игрок с таким ID не найден в OpenDota. Проверьте ID."}
                else: # Другие ошибки API
                    return {"error": f"Ошибка OpenDota API: {response.status}. Попробуйте позже."}
    except aiohttp.ClientError: # Ошибка сетевого подключения
        return {"error": "Не удалось подключиться к OpenDota API. Проверьте интернет-соединение."}
    except Exception as e: # Любая другая непредвиденная ошибка
        logging.error(f"Непредвиденная ошибка при получении статистики игрока: {e}")
        return {"error": "Произошла непредвиденная ошибка. Попробуйте позже."}

# Функция для получения винрейта игрока
async def get_player_win_loss(player_id: int):
    """
    Получает количество побед и поражений игрока.
    """
    url = f"https://api.opendota.com/api/players/{player_id}/wl?api_key={OPEN_DOTA_API_KEY}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
return data
                else:
                    return {"error": f"Ошибка API при получении W/L: {response.status}"}
    except aiohttp.ClientError:
        return {"error": "Ошибка сети при получении W/L."}

# Функция для получения списка героев игрока
async def get_player_heroes(player_id: int):
    """
    Получает список героев, на которых играл игрок, с их статистикой.
    """
    url = f"https://api.opendota.com/api/players/{player_id}/heroes?api_key={OPEN_DOTA_API_KEY}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    return {"error": f"Ошибка API при получении героев: {response.status}"}
    except aiohttp.ClientError:
        return {"error": "Ошибка сети при получении героев."}

# Функция для получения статистики по конкретному герою
async def get_hero_stats_by_id(hero_id: int):
    """
    Получает общую информацию о герое по его ID.
    """
    url = f"https://api.opendota.com/api/heroes/{hero_id}?api_key={OPEN_DOTA_API_KEY}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    return {"error": f"Ошибка API при получении данных героя: {response.status}"}
    except aiohttp.ClientError:
        return {"error": "Ошибка сети при получении данных героя."}

# --- Вспомогательные функции для форматирования данных ---

# Функция для преобразования rank_tier в читабельный ранг
def get_rank_tier_name(rank_tier: int):
    """
    Преобразует числовой rank_tier из OpenDota в название ранга.
    """
    if rank_tier is None:
        return "Неизвестно"
    
    # OpenDota rank_tier: 0-8 для рангов, 0-7 для звезд
    # Пример: 11 = Herald 1, 87 = Divine 7
    rank_names = ["Herald", "Guardian", "Crusader", "Archon", "Legend", "Ancient", "Divine", "Immortal"]
    
    tier = rank_tier // 10 # Получаем номер ранга (0-8)
    stars = rank_tier % 10 # Получаем количество звезд (0-7)

    if tier >= 0 and tier < len(rank_names):
        if tier == 8: # Immortal не имеет звезд
            return "Immortal"
        return f"{rank_names[tier]} {stars}"
    return "Неизвестно"

# --- Обработчики команд Telegram ---

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    """
    Обработчик команды /start. Отправляет приветствие и инструкцию.
    """
    await message.reply(
        "Привет! Я бот для получения статистики по Dota 2.\n"
        "Используй команду /help для получения списка команд."
    )

@dp.message_handler(commands=['help'])
async def send_help(message: types.Message):
    """
    Обработчик команды /help. Отправляет список доступных команд.
    """
    await message.reply(
        "<b>Доступные команды:</b>\n"
        "/profile [ID игрока] - получить общую статистику игрока.\n"
        "/top [ID игрока] - получить статистику по лучшим героям игрока.\n"
        "/hero [ID игрока] [Имя героя] - получить статистику по конкретному герою.\n"
        "<i>ID игрока можно найти на сайте OpenDota или в клиенте Dota 2.</i>"
    )

# --- Обработчик для команды /profile ---
@dp.message_handler(commands=['profile'])
async def cmd_profile(message: types.Message, state: FSMContext):
    """
    Обработчик команды /profile. Запрашивает ID игрока или обрабатывает его, если он передан сразу.
    """
    args = message.get_args() # Получаем аргументы команды (то, что после /profile)
    if args: # Если ID передан сразу
        try:
            player_id = int(args)
            await process_player_profile(message, player_id)
        except ValueError:
            await message.reply("Неверный формат ID игрока. ID должен быть числом.")
    else: # Если ID не передан, запрашиваем его await message.reply("Пожалуйста, введите ID игрока для получения профиля.")
        await Form.player_id.set() # Устанавливаем состояние ожидания ID

# Обработчик для получения ID игрока, когда бот находится в состоянии Form.player_id
@dp.message_handler(state=Form.player_id)
async def process_player_id_for_profile(message: types.Message, state: FSMContext):
    """
    Обрабатывает введенный ID игрока для команды /profile.
    """
    try:
        player_id = int(message.text)
        await state.finish() # Завершаем состояние FSM
        await process_player_profile(message, player_id)
    except ValueError:
        await message.reply("Неверный формат ID игрока. ID должен быть числом. Попробуйте еще раз.")

# Вспомогательная функция для обработки и вывода профиля игрока
async def process_player_profile(message: types.Message, player_id: int):
    """
    Получает и форматирует статистику игрока, затем отправляет её.
    """
    await message.reply(f"Загружаю статистику для игрока с ID: <code>{player_id}</code>...")
    
    stats_data = await get_player_stats(player_id)
    if "error" in stats_data:
        await message.reply(stats_data["error"])
        return

    wl_data = await get_player_win_loss(player_id)
    if "error" in wl_data:
        await message.reply(wl_data["error"])
        return

    profile = stats_data.get("profile", {})
    mmr_estimate = stats_data.get("mmr_estimate", {})

    player_name = profile.get("personaname", "Неизвестный игрок")
    steam_id = profile.get("steamid", "N/A")
    solo_mmr = mmr_estimate.get("solo_estimate", "N/A")
    rank_tier = profile.get("rank_tier")
    
    wins = wl_data.get("win", 0)
    losses = wl_data.get("lose", 0)
    total_matches = wins + losses
    win_rate = (wins / total_matches * 100) if total_matches > 0 else 0

    message_text = (
        f"<b>Статистика игрока: {player_name}</b>\n"
        f"Steam ID: <code>{steam_id}</code>\n"
        f"Примерный Solo MMR: {solo_mmr}\n"
        f"Ранг: {get_rank_tier_name(rank_tier)}\n"
        f"Всего матчей: {total_matches}\n"
        f"Побед: {wins}, Поражений: {losses}\n"
        f"Винрейт: {win_rate:.2f}%" # Форматируем до двух знаков после запятой
    )
    await message.reply(message_text)

# --- Обработчик для команды /top (лучшие герои) ---
@dp.message_handler(commands=['top'])
async def cmd_top_heroes(message: types.Message, state: FSMContext):
    """
    Обработчик команды /top. Запрашивает ID игрока или обрабатывает его, если он передан сразу.
    """
    args = message.get_args()
    if args:
        try:
            player_id = int(args)
            await process_player_top_heroes(message, player_id)
        except ValueError:
            await message.reply("Неверный формат ID игрока. ID должен быть числом.")
    else:
        await message.reply("Пожалуйста, введите ID игрока для получения списка лучших героев.")
        await Form.player_id.set() # Используем то же состояние, но для другой команды

# Обработчик для получения ID игрока, когда бот находится в состоянии Form.player_id для /top
@dp.message_handler(state=Form.player_id)
async def process_player_id_for_top(message: types.Message, state: FSMContext):
    """
    Обрабатывает введенный ID игрока для команды /top.
    """
    try:
        player_id = int(message.text)
        await state.finish()
        await process_player_top_heroes(message, player_id)
    except ValueError:
        await message.reply("Неверный формат ID игрока. ID должен быть числом. Попробуйте еще раз.")

# Вспомогательная функция для обработки и вывода лучших героев
async def process_player_top_heroes(message: types.Message, player_id: int):
    """
    Получает и форматирует статистику по лучшим героям игрока, затем отправляет её.
    """
    await message.reply(f"Загружаю лучших героев для игрока с ID: <code>{player_id}</code>...")
    
    heroes_data = await get_player_heroes(player_id)
    if "error" in heroes_data:
        await message.reply(heroes_data["error"])
        return
    
    if not heroes_data:
        await message.reply("Не найдено данных по героям для этого игрока.")
        return

    # Сортируем героев по количеству игр и берем топ-5
    top_heroes = sorted(heroes_data, key=lambda x: x.get('games', 0), reverse=True)[:5]

    message_text = f"<b>Топ-5 героев игрока (по количеству игр):</b>\n"
    for hero in top_heroes:
        hero_id = hero.get('hero_id')
        games = hero.get('games', 0)
        wins = hero.get('win', 0)
        losses = games - wins
        win_rate = (wins / games * 100) if games > 0 else 0
        
        # Нужно получить имя героя по ID. OpenDota API не дает имя героя в этом запросе.
        # Для простоты, пока будем выводить ID героя. В реальном проекте нужно было бы
        # загрузить список всех героев с их ID и именами.
        message_text += (
            f"  - Герой ID: {hero_id} (Игр: {games}, Винрейт: {win_rate:.2f}%)\n"
        )
    await message.reply(message_text)

# --- Обработчик для команды /hero (статистика по конкретному герою) ---
@dp.message_handler(commands=['hero'])
async def cmd_hero_stats(message: types.Message, state: FSMContext):
    """
    Обработчик команды /hero. Запрашивает ID игрока и имя героя.
    """
    args = message.get_args().split(maxsplit=1) # Разделяем аргументы: ID и остальное как имя героя
    if len(args) >= 2: # Если ID и имя героя переданы сразу
        try:
            player_id = int(args[0])
            hero_name = args[1]
            await process_player_hero_stats(message, player_id, hero_name)
        except ValueError:
            await message.reply("Неверный формат ID игрока. ID должен быть числом.")
    else: # Если не хватает аргументов, запрашиваем
        await message.reply("Пожалуйста, введите ID игрока и имя героя (например: /hero 123456789 Pudge).")
        # Можно создать отдельное FSM состояние для этого, но для простоты пока так.
        # Или можно использовать FSM для последовательного запроса ID, потом имени героя.

# Вспомогательная функция для обработки и вывода статистики по герою
async def process_player_hero_stats(message: types.Message, player_id: int, hero_name: str):
    """
    Получает и форматирует статистику игрока по конкретному герою, затем отправляет её.
    """
    await message.reply(f"Загружаю статистику для игрока <code>{player_id}</code> на герое {hero_name}...")
    
    # В OpenDota API нет прямого запроса "статистика игрока на герое по имени".
    # Нужно сначала получить всех героев игрока, потом найти нужного по имени.
    # Для этого нужен список всех героев Dota 2 с их ID и именами.
    # Это сложнее, чем кажется, так как API возвращает hero_id, а не имя.
    # Для простоты, пока будем искать по hero_id, если пользователь его знает.
    # Или нужно загрузить полный список героев OpenDota и сопоставлять имена.

    # Пример упрощенной логики:
    # Предположим, что hero_name - это hero_id для простоты
    try:
        target_hero_id = int(hero_name) # Если пользователь ввел ID героя
    except ValueError:
        await message.reply("Для команды /hero пока поддерживается только ID героя вместо имени. Например: /hero 123456789 1 (где 1 - ID Антимага).")
        return

    heroes_data = await get_player_heroes(player_id)
    if "error" in heroes_data:
        await message.reply(heroes_data["error"])
        return
    
    found_hero_stats = None
    for hero in heroes_data:
        if hero.get('hero_id') == target_hero_id:
            found_hero_stats = hero
            break
    
    if not found_hero_stats:
        await message.reply(f"Игрок <code>{player_id}</code> не играл на герое с ID {target_hero_id} или данные не найдены.")
        return

    games = found_hero_stats.get('games', 0)
    wins = found_hero_stats.get('win', 0)
    losses = games - wins
    win_rate = (wins / games * 100) if games > 0 else 0

    # В реальном проекте здесь нужно получить имя героя по ID
    hero_name_display = f"Герой ID {target_hero_id}" # Заглушка

    message_text = (
        f"<b>Статистика игрока <code>{player_id}</code> на {hero_name_display}:</b>\n"
        f"Игр: {games}\n"
        f"Побед: {wins}, Поражений: {losses}\n"
        f"Винрейт: {win_rate:.2f}%"
    )
    await message.reply(message_text)    
