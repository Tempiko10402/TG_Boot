def get_main_kb(locale: dict):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton(locale["profile"], callback_data="edit_profile"),
        types.InlineKeyboardButton(locale["language"], callback_data="change_lang"),
    )
    keyboard.row(
        types.InlineKeyboardButton(locale["tracking"], callback_data="tracking"),  # Новая кнопка
        types.InlineKeyboardButton(locale["my_profile"], callback_data="view_profile"),  # Новая кнопка
    )
    keyboard.row(
        types.InlineKeyboardButton(locale["address"], callback_data="show_address"),
    )
    return keyboard