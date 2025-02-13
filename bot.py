import sqlite3
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

TOKEN = "7934568684:AAHsKoficbDtOhA3oYjveRozQPoItFlqYRk"
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Определяем состояния для FSM
class ProfileEdit(StatesGroup):
    edit_name = State()
    edit_fa_link = State()
    edit_content_type = State()

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE,
        username TEXT,
        fa_username TEXT UNIQUE,
        fa_link TEXT
    )
    ''')
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

# Команда /profile
@dp.message(Command("profile"))
async def profile(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить имя", callback_data="edit_name")],
        [InlineKeyboardButton(text="🔗 Изменить ссылку на FA", callback_data="edit_fa_link")],
        [InlineKeyboardButton(text="🎨 Указать тип контента", callback_data="edit_content_type")]
    ])
    await message.answer("Личный кабинет. Выберите действие:", reply_markup=keyboard)

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
    cursor.execute(
        "INSERT OR REPLACE INTO user_profile (user_id, name) VALUES (?, ?)",
        (message.from_user.id, message.text)
    )
    conn.commit()
    conn.close()
    await state.clear()
    await message.answer("✅ Имя успешно обновлено!")

@dp.message(ProfileEdit.edit_fa_link)
async def handle_fa_link_input(message: types.Message, state: FSMContext):
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET fa_link = ? WHERE telegram_id = ?",
        (message.text, message.from_user.id)
    )
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

    
# Запуск бота
async def main():
    init_db()
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())