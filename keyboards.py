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