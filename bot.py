import sqlite3
import logging
import asyncio
import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

TOKEN = "7934568684:AAHsKoficbDtOhA3oYjveRozQPoItFlqYRk"
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# FSM-состояние для ввода ника
class Registration(StatesGroup):
    enter_fa_username = State()

# Команда /start (проверка регистрации)
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()

    # Проверяем, есть ли пользователь в БД
    cursor.execute("SELECT fa_username FROM users WHERE telegram_id = ?", (message.from_user.id,))
    user = cursor.fetchone()

    if not user or not user[0]:  # Если пользователя нет или нет ника FA
        await message.answer("Привет! Введи свой ник на FurAffinity:")
        await state.set_state(Registration.enter_fa_username)
    else:
        await message.answer("Вы уже зарегистрированы! Используйте /profile для управления профилем.")

    conn.close()

# Обработчик ввода ника FA
@dp.message(Registration.enter_fa_username)
async def enter_fa_username(message: types.Message, state: FSMContext):
    fa_username = message.text.strip()
    fa_link = f"https://www.furaffinity.net/user/{fa_username}"

    # Сохраняем в БД
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO users (telegram_id, username, fa_username, fa_link) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(telegram_id) DO UPDATE SET fa_username = ?, fa_link = ?",
        (message.from_user.id, message.from_user.username, fa_username, fa_link, fa_username, fa_link)
    )

    conn.commit()
    conn.close()

    await state.clear()  # Сбрасываем состояние
    await message.answer(f"✅ Ник зарегистрирован: **{fa_username}**\n🔗 Ваша страница: [FurAffinity]({fa_link})", parse_mode="Markdown")

# Определяем состояния для FSM
class ProfileEdit(StatesGroup):
    edit_name = State()
    edit_fa_link = State()
    edit_content_type = State()

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()

    # Создание таблицы пользователей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE,
        username TEXT,
        fa_username TEXT UNIQUE,
        fa_link TEXT,
        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Создание таблицы профилей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_profile (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        name TEXT,
        content_type TEXT,
        FOREIGN KEY (user_id) REFERENCES users (telegram_id)
    )
    ''')

    conn.commit()
    conn.close()

# Команда /start
@dp.message(Command("start"))
async def start(message: types.Message):
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (message.from_user.id,))
    user = cursor.fetchone()

    if not user:
        cursor.execute(
            "INSERT INTO users (telegram_id, username) VALUES (?, ?)",
            (message.from_user.id, message.from_user.username)
        )
        conn.commit()
        await message.answer("Привет! Введи свой ник на FurAffinity, чтобы зарегистрироваться.")
    else:
        await message.answer("Вы уже зарегистрированы! Используйте /profile для управления профилем.")

    conn.close()

# Обновляем время последней активности пользователя
def update_last_activity(user_id):
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()
    
    # Проверяем, есть ли колонка last_activity в таблице users
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if "last_activity" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

    # Обновляем время последней активности
    cursor.execute(
        "UPDATE users SET last_activity = CURRENT_TIMESTAMP WHERE telegram_id = ?",
        (user_id,)
    )

    conn.commit()
    conn.close()

# Вычисление дней с последней активности
def get_last_activity_days(user_id):
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT last_activity FROM users WHERE telegram_id = ?", (user_id,)
    )
    result = cursor.fetchone()
    conn.close()
    
    if result and result[0]:
        last_activity = datetime.datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
        days_ago = (datetime.datetime.now() - last_activity).days
        return f"{days_ago} дн. назад" if days_ago > 0 else "Сегодня"
    return "Нет данных"

# Команда /profile
@dp.message(Command("profile"))
async def profile(message: types.Message):
    update_last_activity(message.from_user.id)

    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT fa_username FROM users WHERE telegram_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    
    if user and user[0]:
        fa_username = user[0]
        fa_link = f"https://www.furaffinity.net/user/{fa_username}"
    else:
        fa_username = "Не указан"
        fa_link = "Не указана"
    
    profile_info = f"🦊 **{fa_username}**\n🔗 [Ссылка на профиль]({fa_link})\n📅 **Последняя активность**: {get_last_activity_days(message.from_user.id)}\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить имя", callback_data="edit_name")],
        [InlineKeyboardButton(text="🔗 Изменить ссылку на FA", callback_data="edit_fa_link")],
        [InlineKeyboardButton(text="🎨 Указать тип контента", callback_data="edit_content_type")]
    ])

    await message.answer(profile_info, reply_markup=keyboard, parse_mode="Markdown")
    conn.close()

# Обработка нажатий на кнопки
@dp.callback_query(F.data == "edit_name")
async def edit_name(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(ProfileEdit.edit_name)
    await callback.message.answer("Введите ваше имя:")
    await callback.answer()

@dp.callback_query(F.data == "edit_fa_link")
async def edit_fa_link(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(ProfileEdit.edit_fa_link)
    await callback.message.answer("Введите новую ссылку на ваш профиль FurAffinity:")
    await callback.answer()

@dp.callback_query(F.data == "edit_content_type")
async def edit_content_type(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(ProfileEdit.edit_content_type)
    await callback.message.answer("Укажите, какой контент вы создаете:")
    await callback.answer()

# Обработка ввода данных
@dp.message(ProfileEdit.edit_name)
async def handle_name_input(message: types.Message, state: FSMContext):
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO user_profile (user_id, name) VALUES (?, ?)",(message.from_user.id, message.text))
    conn.commit()
    conn.close()
    await state.clear()
    await message.answer("✅ Имя успешно обновлено!")

@dp.message(ProfileEdit.edit_fa_link)
async def handle_fa_link_input(message: types.Message, state: FSMContext):
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET fa_link = ? WHERE telegram_id = ?",(message.text, message.from_user.id))
    conn.commit()
    conn.close()
    await state.clear()
    await message.answer("✅ Ссылка на FurAffinity успешно обновлена!")

@dp.message(ProfileEdit.edit_content_type)
async def handle_content_type_input(message: types.Message, state: FSMContext):
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO user_profile (user_id, content_type) VALUES (?, ?)",
        (message.from_user.id, message.text)
    )
    conn.commit()
    conn.close()
    await state.clear()
    await message.answer("✅ Тип контента успешно обновлен!")
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Команда /menu
@dp.message(Command("menu"))
async def menu(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Личный кабинет")]
        ],
        resize_keyboard=True
    )
    await message.answer("Выберите действие:", reply_markup=keyboard)

# Обработка кнопки "Личный кабинет"
@dp.message(F.text == "👤 Личный кабинет")
async def profile_button(message: types.Message):
    await profile(message)  # Вызываем уже существующую команду /profile

    import datetime

# Обновляем время последней активности пользователя
def update_last_activity(user_id):
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET last_activity = CURRENT_TIMESTAMP WHERE telegram_id = ?",(user_id,))
    conn.commit()
    conn.close()

# Вычисление дней с последней активности
def get_last_activity_days(user_id):
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT last_activity FROM users WHERE telegram_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result and result[0]:
        last_activity = datetime.datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
        days_ago = (datetime.datetime.now() - last_activity).days
        return f"{days_ago} дн. назад" if days_ago > 0 else "Сегодня"
    return "Нет данных"



# Запуск бота
async def main():
    init_db()
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
