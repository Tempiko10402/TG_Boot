import os
import json
import logging
import telebot
from telebot import types
from telebot.handler_backends import StatesGroup, State
from dotenv import load_dotenv
from database import Database

# Настройка логирования
logging.basicConfig(
    filename='bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Загрузка переменных окружения
load_dotenv()
bot = telebot.TeleBot(os.getenv("BOT_TOKEN"))

# Инициализация базы данных
try:
    db = Database(os.path.join(os.path.dirname(__file__), "users.db"))
    logging.info("Database initialized successfully")
except Exception as e:
    logging.error(f"Failed to initialize database: {e}")
    raise

# Состояния для FSM
class ProfileStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_address = State()
    waiting_for_tracking_item = State()  # Новое состояние для отслеживания

# Загрузка локализаций
def load_locale(lang: str) -> dict:
    try:
        with open(f"locales/{lang}.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logging.warning(f"Locale file for {lang} not found, falling back to 'ru'")
        return load_locale("ru")

# Клавиатуры
def get_main_kb(locale: dict):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton(locale["profile"], callback_data="edit_profile"),
        types.InlineKeyboardButton(locale["language"], callback_data="change_lang"),
    )
    keyboard.row(
        types.InlineKeyboardButton(locale["tracking"], callback_data="tracking"),
        types.InlineKeyboardButton(locale["my_profile"], callback_data="view_profile"),
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
            db.add_user(user_id)
            logging.info(f"New user registered: {user_id}")

        user_data = db.get_user(user_id)
        if not user_data:
            raise Exception("User not found in database")

        lang = user_data["lang"]
        loc = load_locale(lang)

        text = loc.get("welcome", "Добро пожаловать!") + "\n\n"
        text += loc.get("help", "Используйте кнопки ниже:")
        
        bot.send_message(
            message.chat.id,
            text,
            reply_markup=get_main_kb(loc)
        )
    except Exception as e:
        logging.error(f"Error in /start: {e}")
        bot.send_message(message.chat.id, "⚠️ Произошла ошибка. Попробуйте позже.")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    data = call.data
    user = db.get_user(user_id)
    if not user:
        bot.send_message(call.message.chat.id, "⚠️ Пользователь не найден.")
        return
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

    elif data == "tracking":
        tracking_items = db.get_tracking_items(user_id)
        keyboard = types.InlineKeyboardMarkup()
        if tracking_items:
            for item in tracking_items:
                keyboard.add(types.InlineKeyboardButton(item, callback_data=f"track_{item}"))
        keyboard.add(types.InlineKeyboardButton(loc["add_tracking"], callback_data="add_tracking"))
        bot.send_message(call.message.chat.id, loc["tracking"], reply_markup=keyboard)

    elif data == "add_tracking":
        bot.set_state(user_id, ProfileStates.waiting_for_tracking_item, call.message.chat.id)
        bot.send_message(call.message.chat.id, loc["enter_tracking_item"])

    elif data.startswith("track_"):
        item = data.split("_", 1)[1]
        db.remove_tracking_item(user_id, item)
        bot.answer_callback_query(call.id, f"❌ {item} удален из отслеживания")

    elif data == "view_profile":
        profile_text = loc["profile_info"].format(
            name=user["name"] if user["name"] else loc["not_specified"],
            address=user["address"] if user["address"] else loc["not_specified"],
            lang="Русский" if user["lang"] == "ru" else "Кыргызский"
        )
        bot.send_message(call.message.chat.id, profile_text)

    else:
        bot.answer_callback_query(call.id, "⚠️ Эта функция в разработке")

@bot.message_handler(state=ProfileStates.waiting_for_name)
def set_name(message):
    user_id = message.from_user.id
    name = message.text.strip()
    loc = load_locale(db.get_user(user_id)["lang"])
    if len(name) > 50:
        bot.send_message(message.chat.id, loc["name_too_long"])
        return
    db.update_name(user_id, name)
    bot.delete_state(user_id, message.chat.id)
    bot.send_message(message.chat.id, loc["name_updated"])

@bot.message_handler(state=ProfileStates.waiting_for_address)
def set_address(message):
    user_id = message.from_user.id
    address = message.text.strip()
    loc = load_locale(db.get_user(user_id)["lang"])
    if len(address) > 200:
        bot.send_message(message.chat.id, loc["address_too_long"])
        return
    db.update_address(user_id, address)
    bot.delete_state(user_id, message.chat.id)
    bot.send_message(message.chat.id, loc["address_updated"])

@bot.message_handler(state=ProfileStates.waiting_for_tracking_item)
def set_tracking_item(message):
    user_id = message.from_user.id
    item = message.text.strip()
    loc = load_locale(db.get_user(user_id)["lang"])
    if len(item) > 50 or not item.isalnum():
        bot.send_message(message.chat.id, loc["tracking_item_invalid"])
        return
    db.add_tracking_item(user_id, item)
    bot.delete_state(user_id, message.chat.id)
    bot.send_message(message.chat.id, loc["tracking_item_added"])

if __name__ == "__main__":
    logging.info("Starting bot...")
    bot.polling(none_stop=True)