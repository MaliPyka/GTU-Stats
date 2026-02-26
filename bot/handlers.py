from aiogram import F, Router
from aiogram.types import Message
from aiogram.filters import CommandStart, Command

from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.markdown import hbold, hcode, hitalic

from db.requests import add_user, check_user_exists
from core.security import encrypt_password, decrypt_password

router = Router()

class Registration(StatesGroup):
    waiting_login = State()
    waiting_password = State()

@router.message(CommandStart())
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()

    status_text = (
        f"✅ {hbold('Ты уже зарегистрирован(а)')}\n\n"
        "Бот работает в штатном режиме и готов обновлять данные по твоим баллам.\n\n"
        "📊 Проверить баллы: /stats\n"
        "⚙️ Изменить данные: /profile"
    )

    if await check_user_exists(message.from_user.id):
        return await message.answer(status_text, parse_mode="HTML")

    welcome_text = (
        f"👋 {hbold('Привет! Я бот GTU Stats')}\n\n"
        f"Я помогу тебе удобно следить за оценками и уведомлю, когда появятся новые баллы на портале.\n\n"
        f"🔒 {hbold('Безопасность:')}\n"
        f"Твои данные шифруются по стандарту AES-256. Я не храню пароли в открытом виде, они используются "
        f"только для автоматического входа в твой личный кабинет.\n\n"
        f"⚙️ {hbold('Регистрация:')}\n"
        f"Чтобы начать, мне понадобятся твои данные от портала.\n\n"
        f"⚠️ {hbold('Важно:')} Перед отправкой убедись, что данные верны. Если ты ошибешься, "
        f"бот не сможет зайти в твой личный кабинет и собрать баллы.\n\n"
        f"⚙️ {hitalic('Изменить данные для входа или выйти из аккаунта ты всегда сможешь в разделе «Профиль».')}\n\n"
        f"{hbold('Отправь свой логин от vici.gtu:')}"
    )

    await message.answer(welcome_text, parse_mode="HTML")
    await state.set_state(Registration.waiting_login)
    return None


@router.message(Registration.waiting_login)
async def save_login_cmd(message: Message, state: FSMContext):
    await state.update_data(login=message.text)

    password_request_text = (
        f"✅ {hbold('Логин принят!')}\n\n"
        f"Теперь введи свой {hbold('пароль')} от портала:"
    )

    await message.answer(password_request_text, parse_mode="HTML")
    await state.set_state(Registration.waiting_password)


@router.message(Registration.waiting_password)
async def save_password_cmd(message: Message, state: FSMContext):
    await message.delete()
    await state.update_data(password=message.text)
    data = await state.get_data()
    encrypted_password = encrypt_password(data['password'])
    tg_id = message.from_user.id
    try:
        await add_user(tg_id, data['login'], encrypted_password)
        await state.clear()

        success_text = (
            f"🎉 {hbold('Готово! Ты успешно зарегистрирован.')}\n\n"
            "Теперь я буду периодически проверять твой портал и присылать обновления.\n\n"
            "Нажми /stats, чтобы проверить текущие баллы прямо сейчас."
        )

        await message.answer(success_text, parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка при регистрации: {e}")
        await message.answer("Произошла ошибка при сохранении данных. Попробуй позже.")
        await state.clear()
