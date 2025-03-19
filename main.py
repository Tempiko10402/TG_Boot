import os
import json
import telebot
from telebot import types
from dotenv import load_dotenv
from database import Database
import re
import time
import requests
from datetime import datetime
import logging
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('log.txt', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

load_dotenv()
bot = telebot.TeleBot(os.getenv("BOT_TOKEN"))
db = Database()

# ID администратора
ADMIN_ID = 1406374607  # Укажите ваш Telegram ID

# Загрузка локализаций
def load_locale(lang: str) -> dict:
    try:
        with open(f"locales/{lang}.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"Locale file for {lang} not found, falling back to 'ru'")
        return load_locale("ru")

# Валидация ввода
def validate_name(name: str) -> bool:
    return bool(re.match(r'^[A-Za-zА-Яа-я\s]{2,}$', name))

def validate_address(address: str) -> bool:
    return len(address) >= 5

# Клавиатуры
def get_main_kb(locale: dict):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton(locale["my_profile"], callback_data="my_profile"),
        types.InlineKeyboardButton(locale["language"], callback_data="change_lang"),
    )
    keyboard.row(
        types.InlineKeyboardButton(locale["address"], callback_data="show_address"),
        types.InlineKeyboardButton(locale["my_history"], callback_data="my_history"),
    )
    keyboard.row(
        types.InlineKeyboardButton(locale["faq"], callback_data="faq"),  # Добавляем кнопку FAQ
    )
    keyboard.row(
        types.InlineKeyboardButton(locale["register"], callback_data="register"),
        types.InlineKeyboardButton(locale["support"], callback_data="contact_support"),
        types.InlineKeyboardButton(locale["instruction"], callback_data="instruction"),
        types.InlineKeyboardButton(locale["pay"], callback_data="pay"),
    )
    return keyboard

def get_profile_menu(locale: dict):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton(locale["profile"], callback_data="edit_profile"),
        types.InlineKeyboardButton(locale["pay"], callback_data="pay"),
        types.InlineKeyboardButton(locale["my_history"], callback_data="my_history"),
    )
    keyboard.row(
        types.InlineKeyboardButton(locale["back"], callback_data="back_to_main"),
    )
    return keyboard

def get_lang_kb():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("Русский 🇷🇺", callback_data="lang_ru"),
        types.InlineKeyboardButton("Кыргызский 🇰🇬", callback_data="lang_kg"),
        types.InlineKeyboardButton("English 🇬🇧", callback_data="lang_en"),
    )
    logging.debug("get_lang_kb: Клавиатура языков создана")
    return keyboard

def get_payment_kb(locale: dict, user_address: str):
    keyboard = types.InlineKeyboardMarkup()
    if "Бишкек" in user_address:
        keyboard.row(
            types.InlineKeyboardButton("MBank", callback_data="pay_mbank"),
            types.InlineKeyboardButton("O!Bank (О деньги)", callback_data="pay_obank"),
            types.InlineKeyboardButton("Optima Bank", callback_data="pay_odeneg"),
        )
    else:
        keyboard.row(
            types.InlineKeyboardButton("Aiyl Bank", callback_data="pay_aiyl"),
            types.InlineKeyboardButton("RSK Bank", callback_data="pay_rsk"),
            types.InlineKeyboardButton("Bakai Bank", callback_data="pay_bakai"),
        )
    if "Бишкек" not in user_address:
        keyboard.row(
            types.InlineKeyboardButton("MBank", callback_data="pay_mbank"),
            types.InlineKeyboardButton("O!Bank (О деньги)", callback_data="pay_obank"),
            types.InlineKeyboardButton("Optima Bank", callback_data="pay_odeneg"),
        )
    else:
        keyboard.row(
            types.InlineKeyboardButton("Aiyl Bank", callback_data="pay_aiyl"),
            types.InlineKeyboardButton("RSK Bank", callback_data="pay_rsk"),
            types.InlineKeyboardButton("Bakai Bank", callback_data="pay_bakai"),
        )
    keyboard.row(
        types.InlineKeyboardButton("Сбербанк (Mir)", callback_data="pay_sber"),
        types.InlineKeyboardButton("Тинькофф (Mir)", callback_data="pay_tinkoff"),
    )
    keyboard.row(
        types.InlineKeyboardButton(locale["back"], callback_data="back_to_main")
    )
    return keyboard

def get_confirm_kb(locale: dict, action: str):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton(locale["confirm_yes"], callback_data=f"confirm_{action}_yes"),
        types.InlineKeyboardButton(locale["confirm_no"], callback_data=f"confirm_{action}_no"),
    )
    return keyboard

def get_receipt_kb(locale: dict, transaction_id: int):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton(locale["upload_receipt"], callback_data=f"upload_receipt_{transaction_id}"),
        types.InlineKeyboardButton(locale["skip"], callback_data="skip_receipt"),
    )
    return keyboard

def get_profile_info(user_data: dict, loc: dict) -> str:
    name = user_data.get("name", loc.get("no_name", "Имя не указано"))
    address = user_data.get("address", loc.get("no_address", "Адрес не указан"))
    lang = {"ru": "Русский 🇷🇺", "kg": "Кыргызский 🇰🇬", "en": "English 🇬🇧"}.get(user_data["lang"], "Русский 🇷🇺")
    return (
        f"**{loc.get('profile_info', 'Ваш профиль')}:**\n\n"
        f"📛 {loc.get('your_name', 'Ваше имя')}: `{name}`\n"
        f"🏠 {loc.get('your_address', 'Ваш адрес')}: `{address}`\n"
        f"🌐 {loc.get('your_language', 'Ваш язык')}: `{lang}`"
    )

# Реквизиты для банков
BANK_REQUISITES = {
    "pay_aiyl": {
        "name": "Aiyl Bank",
        "image_path": "requisites/aiyl_bank.jpg",
        "location": "https://www.google.com/maps/search/Aiyl+Bank+branches+Bishkek/"
    },
    "pay_rsk": {
        "name": "RSK Bank",
        "image_path": "requisites/rsk_bank.jpg",
        "location": "https://www.google.com/maps/search/RSK+Bank+branches+Bishkek/"
    },
    "pay_bakai": {
        "name": "Bakai Bank",
        "image_path": "requisites/bakai_bank.jpg",
        "location": "https://www.google.com/maps/search/Bakai+Bank+branches+Bishkek/"
    },
    "pay_mbank": {
        "name": "MBank",
        "image_path": "requisites/mbank.jpg",
        "location": "https://www.google.com/maps/search/MBank+branches+Bishkek/"
    },
    "pay_obank": {
        "name": "O!Bank",
        "image_path": "requisites/obank.jpg",
        "location": "https://www.google.com/maps/search/O!Bank+branches+Bishkek/"
    },
    "pay_odeneg": {
        "name": "Optima Bank",
        "image_path": "requisites/optimabank.jpg",
        "location": "https://www.google.com/maps/search/Optima+Bank+branches+Bishkek/"
    },
    "pay_sber": {
        "name": "Сбербанк (Mir)",
        "image_path": "requisites/sberbank.jpg",
        "location": "https://www.google.com/maps/search/Sberbank+branches/"
    },
    "pay_tinkoff": {
        "name": "Тинькофф (Mir)",
        "image_path": "requisites/tinkoff.jpg",
        "location": "https://www.google.com/maps/search/Tinkoff+branches/"
    },
}

# Генерация PDF-отчёта
def generate_pdf_report():
    filename = "report.pdf"
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    c.setFont("Helvetica", 12)

    # Заголовок
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, height - 50, "Bot Usage Report")
    c.setFont("Helvetica", 12)
    c.drawString(100, height - 70, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Пользователи
    c.setFont("Helvetica-Bold", 14)
    c.drawString(100, height - 100, "Users")
    y = height - 120
    users = db.get_all_users()
    for user in users:
        if y < 50:
            c.showPage()
            y = height - 50
        text = f"ID: {user['user_id']}, Name: {user['name']}, Address: {user['address']}"
        c.drawString(100, y, text)
        y -= 20

    # Транзакции
    c.setFont("Helvetica-Bold", 14)
    c.drawString(100, y - 20, "Transactions")
    y -= 40
    transactions = db.get_all_transactions()
    for trans in transactions:
        if y < 50:
            c.showPage()
            y = height - 50
        trans_id, user_id, bank, amount, date = trans
        text = f"ID: {trans_id}, User ID: {user_id}, Bank: {bank}, Amount: {amount} KGS, Date: {date}"
        c.drawString(100, y, text)
        y -= 20

    c.save()
    return filename

# Обработчики
@bot.message_handler(commands=["start"])
def start_handler(message: types.Message):
    user_id = message.from_user.id
    if not db.check_request_limit(user_id):
        bot.send_message(user_id, "⚠️ Слишком много запросов. Пожалуйста, подождите минуту.")
        return
    logging.debug(f"Start handler for user_id {user_id}")
    try:
        if not db.user_exists(user_id):
            db.add_user(user_id)
            logging.info(f"Новый пользователь зарегистрирован: {user_id}")

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
        logging.error(f"Start handler error for user_id {user_id}: {e}", exc_info=True)
        bot.send_message(message.chat.id, loc.get("error_generic", "⚠️ Произошла ошибка. Попробуйте позже."))

@bot.message_handler(commands=["stats"])
def stats_handler(message: types.Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(user_id, "⚠️ Эта команда доступна только администратору.")
        return
    logging.info(f"Stats requested by admin {user_id}")
    stats = db.get_bank_stats()
    if not stats:
        bot.send_message(user_id, "Нет данных о статистике.")
        return
    stats_text = "📊 **Статистика использования банков:**\n\n"
    for bank, count in stats:
        stats_text += f"- {bank}: {count} раз(а)\n"
    bot.send_message(user_id, stats_text, parse_mode="Markdown")

@bot.message_handler(commands=["report"])
def report_handler(message: types.Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(user_id, "⚠️ Эта команда доступна только администратору.")
        return
    logging.info(f"Report requested by admin {user_id}")
    try:
        bot.send_message(user_id, "Генерация отчёта...")
        filename = generate_pdf_report()
        with open(filename, "rb") as f:
            bot.send_document(user_id, f, caption="Отчёт по пользователям и транзакциям")
        os.remove(filename)
        logging.info("PDF report sent successfully")
    except Exception as e:
        logging.error(f"Error generating PDF report: {e}", exc_info=True)
        bot.send_message(user_id, "⚠️ Ошибка при генерации отчёта.")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    data = call.data
    if not db.check_request_limit(user_id):
        bot.send_message(user_id, "⚠️ Слишком много запросов. Пожалуйста, подождите минуту.")
        return
    logging.debug(f"Callback: user_id={user_id}, data={data}")
    user = db.get_user(user_id)
    loc = load_locale(user["lang"] if user else "ru")

    try:
        if data == "edit_profile":
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton(loc["change_name"], callback_data="set_name"))
            keyboard.add(types.InlineKeyboardButton(loc["change_address"], callback_data="set_address"))
            bot.send_message(call.message.chat.id, loc["edit_profile"], reply_markup=keyboard)

        elif data == "set_name":
            logging.debug(f"Requesting name for user_id {user_id}")
            msg = bot.send_message(call.message.chat.id, loc["enter_name"])
            bot.register_next_step_handler(msg, handle_name_input)

        elif data == "set_address":
            logging.debug(f"Requesting address for user_id {user_id}")
            msg = bot.send_message(call.message.chat.id, loc["enter_address"])
            bot.register_next_step_handler(msg, handle_address_input)

        elif data == "change_lang":
            logging.debug(f"Change language button pressed for {user_id}")
            bot.send_message(call.message.chat.id, loc["select_lang"], reply_markup=get_lang_kb())

        elif data == "show_address":
            logging.debug(f"Show address button pressed for {user_id}")
            if not user:
                bot.send_message(call.message.chat.id, loc["not_registered"])
                return
            address = user.get("address", loc["no_address"])
            your_address_text = loc["your_address"]
            bot.send_message(
                call.message.chat.id,
                f"**{your_address_text}:**\n\n`{address}`",
                parse_mode="Markdown"
            )

        elif data == "my_profile":
            logging.debug(f"My profile button pressed for {user_id}")
            if not user:
                bot.send_message(call.message.chat.id, loc["not_registered"])
                return
            profile_info = get_profile_info(user, loc)
            bot.send_message(call.message.chat.id, profile_info, parse_mode="Markdown", reply_markup=get_profile_menu(loc))

        elif data == "back_to_main":
            bot.send_message(call.message.chat.id, loc["help"], reply_markup=get_main_kb(loc))

        elif data == "instruction":
            bot.send_message(call.message.chat.id, loc["instruction_text"])

        elif data == "register":
            logging.debug(f"Register button pressed for {user_id}")
            if not db.user_exists(user_id):
                db.add_user(user_id)
                logging.info(f"Пользователь {user_id} зарегистрирован")
                bot.send_message(call.message.chat.id, loc["registration_success"])
            else:
                bot.send_message(call.message.chat.id, loc["already_registered"])
            user_data = db.get_user(user_id)
            loc = load_locale(user_data["lang"] if user_data else "ru")
            bot.send_message(call.message.chat.id, loc["help"], reply_markup=get_main_kb(loc))

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
            logging.debug(f"Pay button pressed for user_id {user_id}")
            user_data = db.get_user(user_id)
            bot.send_message(call.message.chat.id, loc["select_payment_method"], reply_markup=get_payment_kb(loc, user_data["address"]))

        elif data == "my_history":
            logging.debug(f"My history button pressed for {user_id}")
            if not user:
                bot.send_message(call.message.chat.id, loc["not_registered"])
                return
            transactions = db.get_transactions(user_id)
            if not transactions:
                bot.send_message(call.message.chat.id, loc["no_transactions"])
            else:
                history_text = f"**{loc['transaction_history']}:**\n\n"
                for trans in transactions:
                    bank, amount, date = trans
                    history_text += f"- {loc['bank']}: {bank}, {loc['amount']}: {amount} KGS, {loc['date']}: {date}\n"
                bot.send_message(call.message.chat.id, history_text, parse_mode="Markdown", reply_markup=get_profile_menu(loc))

        elif data == "faq":
            faq_text = f"**{loc['faq']}:**\n\n"
            faq_text += f"1. {loc['faq_how_to_pay']}\n{loc['faq_how_to_pay_answer']}\n\n"
            faq_text += f"2. {loc['faq_where_requisites']}\n{loc['faq_where_requisites_answer']}"
            bot.send_message(call.message.chat.id, faq_text, parse_mode="Markdown")

        elif data == "contact_support":
            user_data = db.get_user(user_id)
            support_text = f"Пользователь {user_id} обратился в поддержку:\n"
            support_text += f"Имя: {user_data['name']}\n"
            support_text += f"Адрес: {user_data['address']}\n"
            bot.send_message(ADMIN_ID, support_text)
            bot.send_message(call.message.chat.id, loc["support_contacted"])

        elif data.startswith("confirm_name_"):
            action = data.split("_")[-1]
            if action == "yes":
                name = call.message.text.split(": ")[1].strip()
                db.update_name(user_id, name)
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=loc["name_updated"]
                )
            else:
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=loc["action_cancelled"]
                )

        elif data.startswith("confirm_address_"):
            action = data.split("_")[-1]
            if action == "yes":
                address = call.message.text.split(": ")[1].strip()
                db.update_address(user_id, address)
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=loc["address_updated"]
                )
            else:
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=loc["action_cancelled"]
                )

        elif data.startswith("confirm_payment_"):
            action = data.split("_")[-1]
            if action == "yes":
                amount = float(call.message.text.split(": ")[1].split()[0])
                bank_data = call.message.text.split("data: ")[1]
                bank_info = BANK_REQUISITES[bank_data]
                bank_name = bank_info["name"]
                image_path = bank_info["image_path"]
                location_url = bank_info["location"]

                transaction_id = db.add_transaction(user_id, bank_name, amount)

                bot.send_message(call.message.chat.id, loc["processing"])
                time.sleep(1)
                if "Mir" in bank_name or bank_data == "pay_mbank":
                    warning = loc["payment_warning"].format(bank=bank_name)
                    bot.send_message(call.message.chat.id, warning)
                else:
                    instruction = loc["payment_instruction"].format(bank=bank_name, amount=amount)
                    bot.send_message(call.message.chat.id, instruction)

                try:
                    with open(image_path, "rb") as photo:
                        bot.send_photo(user_id, photo=photo, caption=loc["requisites_caption"].format(bank=bank_name, amount=amount))
                except FileNotFoundError:
                    bot.send_message(user_id, loc["error_image_not_found"].format(bank=bank_name))

                location_kb = types.InlineKeyboardMarkup()
                location_kb.add(types.InlineKeyboardButton(loc["find_branch"], url=location_url))
                bot.send_message(user_id, loc["find_branch_prompt"], reply_markup=location_kb)

                bot.send_message(user_id, loc["upload_receipt_prompt"], reply_markup=get_receipt_kb(loc, transaction_id))
            else:
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=loc["action_cancelled"]
                )

        elif data.startswith("upload_receipt_"):
            transaction_id = int(data.split("_")[-1])
            msg = bot.send_message(call.message.chat.id, loc["send_receipt_photo"])
            bot.register_next_step_handler(msg, lambda m: handle_receipt_upload(m, transaction_id))

        elif data == "skip_receipt":
            bot.send_message(call.message.chat.id, loc["receipt_skipped"], reply_markup=get_main_kb(loc))

        elif data in BANK_REQUISITES:
            bank_info = BANK_REQUISITES[data]
            msg = bot.send_message(call.message.chat.id, loc["enter_amount"])
            bot.register_next_step_handler(msg, lambda m: handle_payment(m, data, bank_info))

        else:
            bot.answer_callback_query(call.id, loc["feature_in_development"])
    except Exception as e:
        logging.error(f"Callback handler error: {e}", exc_info=True)
        bot.answer_callback_query(call.id, loc["error_generic"])

def handle_payment(message, data, bank_info):
    user_id = message.from_user.id
    try:
        amount = float(message.text)
        if amount <= 0:
            bot.send_message(user_id, loc["error_invalid_amount"])
            return

        loc = load_locale(db.get_user(user_id)["lang"])
        confirm_text = f"{loc['confirm_payment']}: {amount} KGS\ndata: {data}"
        bot.send_message(user_id, confirm_text, reply_markup=get_confirm_kb(loc, "payment"))
    except ValueError:
        bot.send_message(user_id, loc["error_invalid_amount"])
    except Exception as e:
        logging.error(f"handle_payment error: {e}", exc_info=True)
        bot.send_message(user_id, loc["error_generic"])

def handle_receipt_upload(message, transaction_id):
    user_id = message.from_user.id
    loc = load_locale(db.get_user(user_id)["lang"])
    if message.photo:
        file_id = message.photo[-1].file_id
        db.add_receipt(user_id, transaction_id, file_id)
        bot.send_message(user_id, loc["receipt_uploaded"], reply_markup=get_main_kb(loc))
    else:
        bot.send_message(user_id, loc["error_not_a_photo"])

def handle_name_input(message):
    user_id = message.from_user.id
    loc = load_locale(db.get_user(user_id)["lang"] if db.user_exists(user_id) else "ru")
    try:
        if not db.user_exists(user_id):
            logging.debug(f"handle_name_input: Пользователь {user_id} не найден, регистрируем...")
            db.add_user(user_id)

        name = message.text.strip()
        if not validate_name(name):
            bot.send_message(user_id, loc["error_invalid_name"])
            return

        confirm_text = f"{loc['confirm_name']}: {name}"
        bot.send_message(user_id, confirm_text, reply_markup=get_confirm_kb(loc, "name"))
    except Exception as e:
        logging.error(f"handle_name_input: Ошибка - {e}", exc_info=True)
        bot.send_message(user_id, loc["error_generic"])

def handle_address_input(message):
    user_id = message.from_user.id
    loc = load_locale(db.get_user(user_id)["lang"] if db.user_exists(user_id) else "ru")
    try:
        if not db.user_exists(user_id):
            logging.debug(f"handle_address_input: Пользователь {user_id} не найден, регистрируем...")
            db.add_user(user_id)

        address = message.text.strip()
        if not validate_address(address):
            bot.send_message(user_id, loc["error_invalid_address"])
            return

        confirm_text = f"{loc['confirm_address']}: {address}"
        bot.send_message(user_id, confirm_text, reply_markup=get_confirm_kb(loc, "address"))
    except Exception as e:
        logging.error(f"handle_address_input: Ошибка - {e}", exc_info=True)
        bot.send_message(user_id, loc["error_generic"])

@bot.message_handler(content_types=['text'])
def debug_text_handler(message):
    user_id = message.from_user.id
    logging.debug(f"Text message received: user_id={user_id}, text={message.text}")
    bot.send_message(message.chat.id, "⚠️ Пожалуйста, выберите действие из меню.")

if __name__ == "__main__":
    try:
        bot.polling(none_stop=True, interval=5, timeout=30)
    except Exception as e:
        logging.error(f"Polling error: {e}", exc_info=True)
    finally:
        db.close()