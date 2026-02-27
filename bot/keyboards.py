from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def refresh_button() -> InlineKeyboardMarkup:

    refresh_button = InlineKeyboardButton(text="Обновить",
                                          callback_data="refresh")

    return InlineKeyboardMarkup(inline_keyboard=[[refresh_button]])
