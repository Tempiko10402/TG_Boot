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
        types.InlineKeyboardButton(locale.get("my_profile", "Мой профиль"), callback_data="my_profile"),
        types.InlineKeyboardButton(locale["language"], callback_data="change_lang"),
    )
    keyboard.row(
        types.InlineKeyboardButton(locale["address"], callback_data="show_address"),
    )
    keyboard.row(
        types.InlineKeyboardButton(locale.get("register", "Регистрация"), callback_data="register"),
        types.InlineKeyboardButton(locale["support"], url="https://t.me/username"),
        types.InlineKeyboardButton(locale["instruction"], callback_data="instruction"),
    )
    return keyboard

def get_profile_menu(locale: dict):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton(locale["profile"], callback_data="edit_profile"),
    )
    keyboard.row(
        types.InlineKeyboardButton(locale.get("back", "Назад"), callback_data="back_to_main"),
    )
    return keyboard

def get_lang_kb():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("Русский 🇷🇺", callback_data="lang_ru"),
        types.InlineKeyboardButton("Кыргызский 🇰🇬", callback_data="lang_kg"),
    )
    print(f"[DEBUG] get_lang_kb: Клавиатура языков создана")
    return keyboard

def get_profile_info(user_data: dict, loc: dict) -> str:
    name = user_data.get("name", loc.get("no_name", "Имя не указано"))
    address = user_data.get("address", loc.get("no_address", "Адрес не указан"))
    lang = "Русский 🇷🇺" if user_data["lang"] == "ru" else "Кыргызский 🇰🇬"
    return (
        f"**{loc.get('profile_info', 'Ваш профиль')}:**\n\n"
        f"📛 {loc.get('your_name', 'Ваше имя')}: `{name}`\n"
        f"🏠 {loc.get('your_address', 'Ваш адрес')}: `{address}`\n"
        f"🌐 {loc.get('your_language', 'Ваш язык')}: `{lang}`"
    )

# Обработчики
@bot.message_handler(commands=["start"])
def start_handler(message: types.Message):
    user_id = message.from_user.id
    print(f"[DEBUG] Start handler for user_id {user_id}")
    try:
        if not db.user_exists(user_id):
            db.add_user(user_id)
            print(f"[DEBUG] Новый пользователь зарегистрирован: {user_id}")

        user_data = db.get_user(user_id)
        if not user_data:
            raise Exception(f"Данные пользователя {user_id} не найдены в базе")

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
        import traceback
        print(f"[ERROR] Start handler error for user_id {user_id}: {e}\n{traceback.format_exc()}")
        bot.send_message(message.chat.id, "⚠️ Произошла ошибка. Попробуйте позже.")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    data = call.data
    print(f"[DEBUG] Callback: user_id={user_id}, data={data}")
    user = db.get_user(user_id)
    loc = load_locale(user["lang"] if user else "ru")

    try:
        if data == "edit_profile":
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton(loc["change_name"], callback_data="set_name"))
            keyboard.add(types.InlineKeyboardButton(loc["change_address"], callback_data="set_address"))
            bot.send_message(call.message.chat.id, loc["edit_profile"], reply_markup=keyboard)

        elif data == "set_name":
            bot.set_state(user_id, ProfileStates.waiting_for_name, call.message.chat.id)
            print(f"[DEBUG] Set name state set for {user_id}")
            bot.send_message(call.message.chat.id, loc["enter_name"])

        elif data == "set_address":
            bot.set_state(user_id, ProfileStates.waiting_for_address, call.message.chat.id)
            print(f"[DEBUG] Set address state set for {user_id}")
            bot.send_message(call.message.chat.id, loc["enter_address"])

        elif data == "change_lang":
            print(f"[DEBUG] Change language button pressed for {user_id}")
            bot.send_message(call.message.chat.id, loc.get("select_lang", "Выберите язык:"), reply_markup=get_lang_kb())

        elif data == "show_address":
            print(f"[DEBUG] Show address button pressed for {user_id}")
            if not user:
                bot.send_message(call.message.chat.id, "⚠️ Сначала зарегистрируйтесь.")
                return
            address = user.get("address", loc.get("no_address", "Адрес не указан"))
            your_address_text = loc.get("your_address", "Ваш адрес")
            bot.send_message(
                call.message.chat.id,
                f"**{your_address_text}:**\n\n`{address}`",
                parse_mode="Markdown"
            )

        elif data == "my_profile":
            print(f"[DEBUG] My profile button pressed for {user_id}")
            if not user:
                bot.send_message(call.message.chat.id, "⚠️ Сначала зарегистрируйтесь.")
                return
            profile_info = get_profile_info(user, loc)
            bot.send_message(call.message.chat.id, profile_info, parse_mode="Markdown", reply_markup=get_profile_menu(loc))

        elif data == "back_to_main":
            bot.send_message(call.message.chat.id, loc.get("help", "Используйте кнопки ниже:"), reply_markup=get_main_kb(loc))

        elif data == "instruction":
            bot.send_message(call.message.chat.id, loc.get("instruction_text", "Инструкция недоступна"))

        elif data == "register":
            print(f"[DEBUG] Register button pressed for {user_id}")
            if not db.user_exists(user_id):
                db.add_user(user_id)
                print(f"[DEBUG] Пользователь {user_id} зарегистрирован")
                bot.send_message(call.message.chat.id, loc.get("registration_success", "Вы успешно зарегистрированы!"))
            else:
                bot.send_message(call.message.chat.id, loc.get("already_registered", "Вы уже зарегистрированы."))
            user_data = db.get_user(user_id)
            loc = load_locale(user_data["lang"] if user_data else "ru")
            bot.send_message(call.message.chat.id, loc.get("help", "Используйте кнопки ниже:"), reply_markup=get_main_kb(loc))

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
    except Exception as e:
        print(f"[ERROR] Callback handler error: {e}")
        bot.answer_callback_query(call.id, "⚠️ Произошла ошибка.")

@bot.message_handler(state=ProfileStates.waiting_for_name)
def set_name(message):
    user_id = message.from_user.id
    print(f"[DEBUG] set_name: Получено сообщение от {user_id}, текст: {message.text}")
    try:
        if not db.user_exists(user_id):
            print(f"[DEBUG] set_name: Пользователь {user_id} не найден, регистрируем...")
            db.add_user(user_id)

        db.update_name(user_id, message.text)
        user_data = db.get_user(user_id)
        print(f"[DEBUG] set_name: Данные после обновления: {user_data}")

        bot.delete_state(user_id, message.chat.id)
        loc = load_locale(user_data["lang"])
        bot.send_message(message.chat.id, loc["name_updated"])
    except Exception as e:
        print(f"[ERROR] set_name: Ошибка - {e}")
        bot.send_message(message.chat.id, "⚠️ Произошла ошибка при обновлении имени. Проверьте интернет или повторите попытку.")

@bot.message_handler(state=ProfileStates.waiting_for_address)
def set_address(message):
    user_id = message.from_user.id
    print(f"[DEBUG] set_address: Получено сообщение от {user_id}, текст: {message.text}")
    try:
        if not db.user_exists(user_id):
            print(f"[DEBUG] set_address: Пользователь {user_id} не найден, регистрируем...")
            db.add_user(user_id)

        db.update_address(user_id, message.text)
        user_data = db.get_user(user_id)
        print(f"[DEBUG] set_address: Данные после обновления: {user_data}")

        bot.delete_state(user_id, message.chat.id)
        loc = load_locale(user_data["lang"])
        bot.send_message(message.chat.id, loc["address_updated"])
    except Exception as e:
        print(f"[ERROR] set_address: Ошибка - {e}")
        bot.send_message(message.chat.id, "⚠️ Произошла ошибка при обновлении адреса. Проверьте интернет или повторите попытку.")

if __name__ == "__main__":
    try:
        bot.polling(none_stop=True, interval=5, timeout=30)
    except Exception as e:
        print(f"[ERROR] Polling error: {e}")
    finally:
        db.close()