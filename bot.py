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
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

TOKEN = "7934568684:AAHsKoficbDtOhA3oYjveRozQPoItFlqYRk"
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class Registration(StatesGroup):
    enter_fa_username = State()

nav_keyboard = InlineKeyboardMarkup(inline_keyboard=[
])

@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT fa_username FROM users WHERE telegram_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    
    if not user or not user[0]:
        await message.answer("Привет! Введи свой ник на FurAffinity:", reply_markup=nav_keyboard)
        await state.set_state(Registration.enter_fa_username)
    else:
        await message.answer("Вы уже зарегистрированы! Используйте /profile для управления профилем.", reply_markup=nav_keyboard)
    
    conn.close()

@dp.message(Registration.enter_fa_username)
async def enter_fa_username(message: types.Message, state: FSMContext):
    fa_username = message.text.strip()
    fa_link = f"https://www.furaffinity.net/user/{fa_username}"
    
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (telegram_id, username, fa_username, fa_link) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(telegram_id) DO UPDATE SET fa_username = ?, fa_link = ?",
        (message.from_user.id, message.from_user.username, fa_username, fa_link, fa_username, fa_link)
    )
    conn.commit()
    conn.close()
    
    await state.clear()
    await message.answer(f"✅ Ник зарегистрирован: **{fa_username}**\n 🔥 Добро пожаловать в наш бот! Здесь вы сможете найти художников которые хотят взаимныйх подписок и лайков! 🔗 Ваша страница: [FurAffinity]({fa_link})", parse_mode="Markdown", reply_markup=nav_keyboard)

class ProfileEdit(StatesGroup):
    edit_name = State()
    edit_fa_link = State()

def init_db():
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()
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
    conn.commit()
    conn.close()

@dp.callback_query(F.data == "profile")
@dp.message(Command("profile"))
async def profile(event: types.Message | types.CallbackQuery):
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT fa_username, fa_link FROM users WHERE telegram_id = ?", (event.from_user.id,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        fa_username, fa_link = user
        profile_info = f"🦊Ваш ник: **{fa_username}**\n🔗 [Ссылка на профиль]({fa_link})"
    else:
        profile_info = "Вы еще не зарегистрированы. Введите /start."
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить имя", callback_data="edit_name")],
    ])
    
    if isinstance(event, types.Message):
        await event.answer(profile_info, reply_markup=keyboard, parse_mode="Markdown")
    elif isinstance(event, types.CallbackQuery):
        await event.message.edit_text(profile_info, reply_markup=keyboard, parse_mode="Markdown")
        await event.answer()

@dp.callback_query(F.data == "edit_name")
async def edit_name(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(ProfileEdit.edit_name)
    await callback.message.answer("Введите новый ник на FurAffinity:", reply_markup=nav_keyboard)
    await callback.answer()

@dp.message(ProfileEdit.edit_name)
async def handle_name_input(message: types.Message, state: FSMContext):
    fa_username = message.text.strip()
    fa_link = f"https://www.furaffinity.net/user/{fa_username}"
    
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET fa_username = ?, fa_link = ? WHERE telegram_id = ?", (fa_username, fa_link, message.from_user.id))
    conn.commit()
    conn.close()
    
    await state.clear()
    await message.answer("✅ Имя успешно обновлено!", reply_markup=nav_keyboard)
    
    # Автоматически открываем личный кабинет после смены имени
    await profile(message)

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


async def main():
    init_db()
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())