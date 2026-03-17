from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

def refresh_button() -> InlineKeyboardMarkup:

    refresh_button = InlineKeyboardButton(text="Обновить",
                                          callback_data="refresh")

    first_semester_button = InlineKeyboardButton(text="1 семестр",
                                                 callback_data="first_semester")

    current_semester_button = InlineKeyboardButton(text="текущий семестр",
                                                   callback_data="current_semester")

    return InlineKeyboardMarkup(inline_keyboard=[[refresh_button], [first_semester_button, current_semester_button]])


def get_main_menu() -> ReplyKeyboardMarkup:
    btn_stats = KeyboardButton(text="/stats")
    btn_profile = KeyboardButton(text="/profile")

    keyboard = ReplyKeyboardMarkup(
        keyboard=[[btn_stats, btn_profile]],
        resize_keyboard=True,
        input_field_placeholder="Выбери действие 👇"
    )

    return keyboard

def get_profile_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Сменить логин/пароль", callback_data="reset_account")]
    ])

    return keyboard


def choose_language_keyboard() -> InlineKeyboardMarkup:
    Keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 русский", callback_data="ru"), InlineKeyboardButton(text="🇬🇪 ქართული", callback_data="ka"), InlineKeyboardButton(text="🇬🇧 english", callback_data="en")]
    ])

    return Keyboard