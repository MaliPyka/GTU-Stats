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
        [InlineKeyboardButton(text=get_text('btn_change_login', lang), callback_data="reset_account")],
        [InlineKeyboardButton(text=get_text('btn_change_language', lang), callback_data="change_language")]
    ])

    return keyboard


def choose_language_keyboard() -> InlineKeyboardMarkup:
    Keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 русский", callback_data="ru"),
         InlineKeyboardButton(text="🇬🇪 ქართული", callback_data="ka"),
         InlineKeyboardButton(text="🇬🇧 english", callback_data="en")]
    ])

    return Keyboard


def admin_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Рассылка всем", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="📥 Обращения юзеров (0)", callback_data="admin_feedback")]
    ])

    return keyboard


def get_admin_reply_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Ответить", callback_data=f"reply_{user_id}")]
    ])


def get_cancel_support_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text('btn_cancel', lang), callback_data="cancel_support")]
    ])


def get_cancel_broadcast_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_broadcast")]
    ])


def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Рассылка всем", callback_data="admin_broadcast")]
    ])
    

def get_back_to_admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_admin")]
    ])