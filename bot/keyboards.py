from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from bot.texts import get_text

def refresh_button(lang: str = 'en') -> InlineKeyboardMarkup:

    refresh_button = InlineKeyboardButton(text=get_text('btn_refresh', lang),
                                          callback_data="refresh")

    first_semester_button = InlineKeyboardButton(text=get_text('btn_first_sem', lang),
                                                 callback_data="first_semester")

    current_semester_button = InlineKeyboardButton(text=get_text('btn_current_sem', lang),
                                                   callback_data="current_semester")

    return InlineKeyboardMarkup(inline_keyboard=[[refresh_button], [first_semester_button, current_semester_button]])


def get_main_menu(lang: str = 'en') -> ReplyKeyboardMarkup:
    btn_stats = KeyboardButton(text="/stats")
    btn_profile = KeyboardButton(text="/profile")

    keyboard = ReplyKeyboardMarkup(
        keyboard=[[btn_stats, btn_profile]],
        resize_keyboard=True,
        input_field_placeholder=get_text('menu_placeholder', lang)
    )

    return keyboard

def get_profile_keyboard(lang: str = 'en') -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text('btn_change_login', lang), callback_data="reset_account")]
    ])

    return keyboard


def choose_language_keyboard() -> InlineKeyboardMarkup:
    Keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 русский", callback_data="ru"),
         InlineKeyboardButton(text="🇬🇪 ქართული", callback_data="ka"),
         InlineKeyboardButton(text="🇬🇧 english", callback_data="en")]
    ])

    return Keyboard