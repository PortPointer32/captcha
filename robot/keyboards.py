from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(KeyboardButton("♻️ Каталог"), KeyboardButton("⚙️ Мой кабинет"))
    keyboard.row(KeyboardButton("🔥 НОВЫЕ КОНТАКТЫ"))
    keyboard.row(KeyboardButton("🤷‍♂️ Поддержка"))
    return keyboard

