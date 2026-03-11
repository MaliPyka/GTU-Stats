from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command

from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.markdown import hbold, hcode, hitalic

from db.requests import add_user, check_user_exists, update_lessons_and_grades, get_user_data, sync_semesters, \
    get_all_semesters
from core.security import encrypt_password, decrypt_password
from core.scraper import get_gtu_grades
from bot.keyboards import refresh_button
from bot.cache import update_cache, semester_cache

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



@router.message(Command("stats"))
@router.callback_query(F.data == "refresh")
async def stats_cmd(event: Message | CallbackQuery):

    wait_msg_text = "⏳ Собираю данные c портала, подожди немного..."

    if isinstance(event, Message):
        wait_msg = await event.answer(wait_msg_text)
        user_id = event.from_user.id
    else:
        wait_msg = await event.message.edit_text(wait_msg_text)
        user_id = event.from_user.id

    user_data = await get_user_data(user_id)
    decrypted_password = decrypt_password(user_data.encrypted_password)

    try:
        data = await get_gtu_grades(user_data.login, decrypted_password)

        if not data:
            await wait_msg.edit_text("❌ Предметы не найдены или сайт вернул пустоту.")
            return

        result_grades = []

        for item in data:
            sem_name = item['semester']
            subject_name = item['subject']
            score_float = float(item['score'])

            if sem_name not in semester_cache:
                await sync_semesters(sem_name, user_id)
                await update_cache()

            semester_id = semester_cache.get(sem_name)

            # Вызываем обновление
            res = await update_lessons_and_grades(user_id, subject_name, score_float, semester_id)

            # ПРОВЕРКА: Если вернулся список и он не пустой — берем первый элемент
            if res and isinstance(res, list):
                # Ищем наш предмет в списке, который вернула база
                for db_item in res:
                    if db_item.lesson_name == subject_name:
                        result_grades.append(db_item)
                        break  # Нашли нужный — выходим из внутреннего цикла

            elif res and not isinstance(res, list):
                # На случай, если функция вернет один объект
                result_grades.append(res)

        text_lines = ["📊 <b>Твои баллы за семестр:</b>\n"]

        for grade_obj in result_grades:
            name = grade_obj.lesson_name.strip()

            if name.endswith(')') and name.count(')') > name.count('('):
                name = name[:-1].strip()

            score_str = f"{grade_obj.score:2.1f}"

            diff = round(grade_obj.score - grade_obj.old_score, 1)
            status = ""

            if diff > 0:
                status = f" <b>📈 +{diff}</b>"
            elif diff < 0:
                status = f" <b>📉 {diff}</b>"

            line = f"📚 <code>{score_str:>4}</code> | {name}{status}"
            text_lines.append(line)

        final_text = "\n".join(text_lines)

        if isinstance(event, CallbackQuery):
            await wait_msg.edit_text(final_text, parse_mode="HTML", reply_markup=refresh_button())
        elif isinstance(event, Message):
            await wait_msg.edit_text(final_text, parse_mode="HTML", reply_markup=refresh_button())

    except Exception as e:
        if isinstance(event, CallbackQuery):
            await wait_msg.edit_text(f"❌ Упс, произошла ошибка: {e}")
        elif isinstance(event, Message):
            await wait_msg.edit_text(f"❌ Упс, произошла ошибка: {e}")


