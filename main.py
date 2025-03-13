import os
import json
import telebot
from telebot import types
from telebot.handler_backends import StatesGroup, State
from dotenv import load_dotenv
from database import Database

load_dotenv()
bot = telebot.TeleBot(os.getenv("BOT_TOKEN"))
db = Database()

# Состояния для FSM
class ProfileStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_address = State()

# Загрузка локализаций
def load_locale(lang: str) -> dict:
    try:
        with open(f"locales/{lang}.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return load_locale("ru")

# Клавиатуры
def get_main_kb(locale: dict):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton(locale["profile"], callback_data="edit_profile"),
        types.InlineKeyboardButton(locale["language"], callback_data="change_lang"),
    )
    keyboard.row(
        types.InlineKeyboardButton(locale["address"], callback_data="show_address"),
    )
    keyboard.row(
        types.InlineKeyboardButton(locale["support"], url="https://t.me/username"),
        types.InlineKeyboardButton(locale["instruction"], callback_data="instruction"),
    )
    return keyboard
    
def get_lang_kb():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("Русский 🇷🇺", callback_data="lang_ru"),
        types.InlineKeyboardButton("Кыргызский 🇰🇬", callback_data="lang_kg"),
    )
    return keyboard

# Обработчики
@bot.message_handler(commands=["start"])
def start_handler(message: types.Message):
    user_id = message.from_user.id
    try:
        if not db.user_exists(user_id):
            # Регистрация нового пользователя
            db.add_user(user_id)
            db.update_lang(user_id, "ru")  # Язык по умолчанию
            print(f"Новый пользователь зарегистрирован: {user_id}")

        # Загрузка данных пользователя
        user_data = db.get_user(user_id)
        if not user_data:
            raise Exception("Пользователь не найден в базе")

        lang = user_data["lang"]
        loc = load_locale(lang)

        # Отправка приветственного сообщения
        text = loc.get("welcome", "Добро пожаловать!") + "\n\n"
        text += loc.get("help", "Используйте кнопки ниже:")
        
        bot.send_message(
            message.chat.id,
            text,
            reply_markup=get_main_kb(loc)
        )
        
    except Exception as e:
        print(f"Ошибка в /start: {e}")
        bot.send_message(message.chat.id, "⚠️ Произошла ошибка. Попробуйте позже.")
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    data = call.data
    user = db.get_user(user_id)
    loc = load_locale(user["lang"])

    if data == "edit_profile":
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(loc["change_name"], callback_data="set_name"))
        keyboard.add(types.InlineKeyboardButton(loc["change_address"], callback_data="set_address"))
        bot.send_message(call.message.chat.id, loc["edit_profile"], reply_markup=keyboard)

    elif data == "set_name":
        bot.set_state(user_id, ProfileStates.waiting_for_name, call.message.chat.id)
        bot.send_message(call.message.chat.id, loc["enter_name"])

    elif data == "set_address":
        bot.set_state(user_id, ProfileStates.waiting_for_address, call.message.chat.id)
        bot.send_message(call.message.chat.id, loc["enter_address"])

    elif data == "show_address":
        address = "AP-1805\n18727306620\n浙江省金华市义乌市北苑街道凌云八区59栋3单元AP-1805 门面仓库 AP-1805"
        bot.send_message(call.message.chat.id, f"**Нажмите чтобы скопировать:**\n\n`{address}`", parse_mode="Markdown")

    elif data == "instruction":
        bot.send_message(call.message.chat.id, loc["instruction_text"])

    elif data.startswith("lang_"):
        new_lang = data.split("_")[1]
        db.update_lang(user_id, new_lang)
        loc = load_locale(new_lang)
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=loc["lang_changed"],
            reply_markup=get_main_kb(loc)
        )

    else:
        bot.answer_callback_query(call.id, "⚠️ Эта функция в разработке")
@bot.message_handler(state=ProfileStates.waiting_for_name)
def set_name(message):
    user_id = message.from_user.id
    db.update_name(user_id, message.text)
    bot.delete_state(user_id, message.chat.id)
    loc = load_locale(db.get_user(user_id)["lang"])
    bot.send_message(message.chat.id, loc["name_updated"])

@bot.message_handler(state=ProfileStates.waiting_for_address)
def set_address(message):
    user_id = message.from_user.id
    db.update_address(user_id, message.text)
    bot.delete_state(user_id, message.chat.id)
    loc = load_locale(db.get_user(user_id)["lang"])
    bot.send_message(message.chat.id, loc["address_updated"])

if __name__ == "__main__":
    bot.polling(none_stop=True)