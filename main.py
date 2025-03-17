import os
import json
import telebot
from telebot import types
from dotenv import load_dotenv
from database import Database

load_dotenv()
bot = telebot.TeleBot(os.getenv("BOT_TOKEN"))
db = Database()

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
        types.InlineKeyboardButton(locale.get("my_history", "Моя история"), callback_data="my_history"),
    )
    keyboard.row(
        types.InlineKeyboardButton(locale.get("register", "Регистрация"), callback_data="register"),
        types.InlineKeyboardButton(locale["support"], url="https://t.me/username"),
        types.InlineKeyboardButton(locale["instruction"], callback_data="instruction"),
        types.InlineKeyboardButton(locale.get("pay", "Оплатить"), callback_data="pay"),
    )
    return keyboard

def get_profile_menu(locale: dict):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton(locale["profile"], callback_data="edit_profile"),
        types.InlineKeyboardButton(locale.get("pay", "Оплатить"), callback_data="pay"),
        types.InlineKeyboardButton(locale.get("my_history", "Моя история"), callback_data="my_history"),
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
    print("[DEBUG] get_lang_kb: Клавиатура языков создана")
    return keyboard

def get_payment_kb(locale: dict):
    keyboard = types.InlineKeyboardMarkup()
    # Кыргызские банки
    keyboard.row(types.InlineKeyboardButton("Aiyl Bank", callback_data="pay_aiyl"))
    keyboard.row(types.InlineKeyboardButton("RSK Bank", callback_data="pay_rsk"))
    keyboard.row(types.InlineKeyboardButton("Bakai Bank", callback_data="pay_bakai"))
    keyboard.row(types.InlineKeyboardButton("MBank", callback_data="pay_mbank"))
    keyboard.row(types.InlineKeyboardButton("O!Bank (О деньги)", callback_data="pay_obank"))
    keyboard.row(types.InlineKeyboardButton("Optima Bank", callback_data="pay_odeneg"))
    # Российские банки и Mir
    keyboard.row(types.InlineKeyboardButton("Сбербанк (Mir)", callback_data="pay_sber"))
    keyboard.row(types.InlineKeyboardButton("Тинькофф (Mir)", callback_data="pay_tinkoff"))
    keyboard.row(types.InlineKeyboardButton(locale.get("back", "Назад"), callback_data="back_to_main"))
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

# Реквизиты для банков (локальные пути к файлам)
BANK_REQUISITES = {
    "pay_aiyl": {
        "name": "Aiyl Bank",
        "image_path": "requisites/aiyl_bank.jpg"
    },
    "pay_rsk": {
        "name": "RSK Bank",
        "image_path": "requisites/rsk_bank.jpg"
    },
    "pay_bakai": {
        "name": "Bakai Bank",
        "image_path": "requisites/bakai_bank.jpg"
    },
    "pay_mbank": {
        "name": "MBank",
        "image_path": "requisites/mbank.jpg"
    },
    "pay_obank": {
        "name": "O!Bank (O деньги)",
        "image_path": "requisites/obank.jpg"
    },
    "pay_odeneg": {
        "name": "Optima Bank",
        "image_path": "requisites/optimabank.jpg"
    },
    "pay_sber": {
        "name": "Сбербанк (Mir)",
        "image_path": "requisites/sberbank.jpg"
    },
    "pay_tinkoff": {
        "name": "Тинькофф (Mir)",
        "image_path": "requisites/tinkoff.jpg"
    },
  
}

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
            print(f"[DEBUG] Requesting name for user_id {user_id}")
            msg = bot.send_message(call.message.chat.id, loc["enter_name"])
            bot.register_next_step_handler(msg, handle_name_input)

        elif data == "set_address":
            print(f"[DEBUG] Requesting address for user_id {user_id}")
            msg = bot.send_message(call.message.chat.id, loc["enter_address"])
            bot.register_next_step_handler(msg, handle_address_input)

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

        elif data == "pay":
            print(f"[DEBUG] Pay button pressed for user_id {user_id}")
            bot.send_message(call.message.chat.id, loc.get("select_payment_method", "Выберите способ оплаты:"), reply_markup=get_payment_kb(loc))

        elif data == "my_history":
            print(f"[DEBUG] My history button pressed for {user_id}")
            if not user:
                bot.send_message(call.message.chat.id, "⚠️ Сначала зарегистрируйтесь.")
                return
            transactions = db.get_transactions(user_id)
            if not transactions:
                bot.send_message(call.message.chat.id, loc.get("no_transactions", "У вас нет транзакций."))
            else:
                history_text = f"**{loc.get('transaction_history', 'Ваша история транзакций')}:**\n\n"
                for trans in transactions:
                    bank, amount, date = trans
                    history_text += f"- {loc.get('bank', 'Банк')}: {bank}, {loc.get('amount', 'Сумма')}: {amount} KGS, {loc.get('date', 'Дата')}: {date}\n"
                bot.send_message(call.message.chat.id, history_text, parse_mode="Markdown", reply_markup=get_profile_menu(loc))

        elif data in ["pay_aiyl", "pay_rsk", "pay_bakai", "pay_mbank", "pay_obank", "pay_odeneg", "pay_sber", "pay_tinkoff", "pay_vtb"]:
            bank_info = BANK_REQUISITES[data]
            bank_name = bank_info["name"]
            image_path = bank_info["image_path"]
            
            # Запрос суммы оплаты
            msg = bot.send_message(call.message.chat.id, loc.get("enter_amount", "Введите сумму оплаты (в KGS):"))
            bot.register_next_step_handler(msg, lambda m: handle_payment(m, data, bank_info))

        else:
            bot.answer_callback_query(call.id, "⚠️ Эта функция в разработке")
    except Exception as e:
        print(f"[ERROR] Callback handler error: {e}")
        bot.answer_callback_query(call.id, "⚠️ Произошла ошибка.")

def handle_payment(message, data, bank_info):
    user_id = message.from_user.id
    try:
        amount = float(message.text)
        if amount <= 0:
            bot.send_message(user_id, "⚠️ Сумма должна быть положительной. Попробуйте снова.")
            return

        bank_name = bank_info["name"]
        image_path = bank_info["image_path"]

        # Сохранение транзакции
        db.add_transaction(user_id, bank_name, amount)

        # Сообщение с инструкцией
        if "Mir" in bank_name or data == "pay_mbank":
            warning = ("⚠️ Оплата через {bank} возможна, но из-за санкций некоторые банки в Кыргызстане могут ограничивать поддержку Mir и переводы через российские банки (Сбербанк, Тинькофф, ВТБ). "
                      "Используйте приложение банка для оплаты.")
            bot.send_message(user_id, warning.format(bank=bank_name))
        else:
            instruction = f"Оплата через {bank_name} на сумму {amount} KGS. Откройте приложение {bank_name} или посетите ближайшее отделение для завершения транзакции."
            bot.send_message(user_id, instruction)

        # Отправка фото с реквизитами
        try:
            with open(image_path, "rb") as photo:
                bot.send_photo(user_id, photo=photo, caption=f"Реквизиты для оплаты через {bank_name} на сумму {amount} KGS")
        except FileNotFoundError:
            bot.send_message(user_id, f"⚠️ Изображение с реквизитами для {bank_name} не найдено. Пожалуйста, обратитесь в поддержку.")

        bot.send_message(user_id, "Назад в главное меню", reply_markup=get_main_kb(load_locale(db.get_user(user_id)["lang"])))
    except ValueError:
        bot.send_message(user_id, "⚠️ Введите корректную сумму (например, 100.50).")
    except Exception as e:
        print(f"[ERROR] handle_payment error: {e}")
        bot.send_message(user_id, "⚠️ Произошла ошибка при обработке оплаты.")

def handle_name_input(message):
    user_id = message.from_user.id
    print(f"[DEBUG] handle_name_input: Получено сообщение от {user_id}, текст: {message.text}")
    try:
        if not db.user_exists(user_id):
            print(f"[DEBUG] handle_name_input: Пользователь {user_id} не найден, регистрируем...")
            db.add_user(user_id)

        db.update_name(user_id, message.text)
        user_data = db.get_user(user_id)
        print(f"[DEBUG] handle_name_input: Данные после обновления: {user_data}")

        loc = load_locale(user_data["lang"])
        bot.send_message(message.chat.id, loc["name_updated"])
    except Exception as e:
        print(f"[ERROR] handle_name_input: Ошибка - {e}")
        bot.send_message(message.chat.id, "⚠️ Произошла ошибка при обновлении имени. Проверьте интернет или повторите попытку.")

def handle_address_input(message):
    user_id = message.from_user.id
    print(f"[DEBUG] handle_address_input: Получено сообщение от {user_id}, текст: {message.text}")
    try:
        if not db.user_exists(user_id):
            print(f"[DEBUG] handle_address_input: Пользователь {user_id} не найден, регистрируем...")
            db.add_user(user_id)

        db.update_address(user_id, message.text)
        user_data = db.get_user(user_id)
        print(f"[DEBUG] handle_address_input: Данные после обновления: {user_data}")

        loc = load_locale(user_data["lang"])
        bot.send_message(message.chat.id, loc["address_updated"])
    except Exception as e:
        print(f"[ERROR] handle_address_input: Ошибка - {e}")
        bot.send_message(message.chat.id, "⚠️ Произошла ошибка при обновлении адреса. Проверьте интернет или повторите попытку.")

@bot.message_handler(content_types=['text'])
def debug_text_handler(message):
    user_id = message.from_user.id
    print(f"[DEBUG] Text message received: user_id={user_id}, text={message.text}")
    bot.send_message(message.chat.id, "⚠️ Пожалуйста, выберите действие из меню.")

if __name__ == "__main__":
    try:
        bot.polling(none_stop=True, interval=5, timeout=30)
    except Exception as e:
        print(f"[ERROR] Polling error: {e}")
    finally:
        db.close()