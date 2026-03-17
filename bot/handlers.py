from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from db.requests import add_user, check_user_exists, update_lessons_and_grades, get_user_data, sync_semesters, \
    get_semester_id_by_index, get_semester_grades, delete_user, get_current_semester
from core.security import encrypt_password, decrypt_password
from core.scraper import get_gtu_grades
from bot.keyboards import refresh_button, get_main_menu, get_profile_keyboard, choose_language_keyboard
from bot.cache import update_cache, semester_cache, get_user_language, set_user_language
from bot.texts import get_text

router = Router()


class Registration(StatesGroup):
    waiting_language = State()
    waiting_login = State()
    waiting_password = State()


@router.message(CommandStart())
async def choose_language_cmd(message: Message, state: FSMContext):
    await state.set_state(Registration.waiting_language)

    text = get_text('choose_language', 'en')
    await message.answer(text, parse_mode="HTML", reply_markup=choose_language_keyboard())


@router.callback_query(Registration.waiting_language)
async def start_cmd(callback: CallbackQuery, state: FSMContext):
    lang = callback.data
    await state.update_data(language=lang)
    await callback.answer()

    if await check_user_exists(callback.from_user.id):
        await state.clear()
        status_text = get_text('already_registered', lang)
        return await callback.message.answer(status_text, parse_mode="HTML")

    welcome_text = get_text('welcome', lang)
    await callback.message.answer(welcome_text, parse_mode="HTML", reply_markup=get_main_menu(lang))
    await state.set_state(Registration.waiting_login)
    return None


@router.message(Registration.waiting_login)
async def save_login_cmd(message: Message, state: FSMContext):
    await state.update_data(login=message.text)

    data = await state.get_data()
    lang = data.get('language', 'en')

    password_request_text = get_text('login_accepted', lang)
    await message.answer(password_request_text, parse_mode="HTML")
    await state.set_state(Registration.waiting_password)


@router.message(Registration.waiting_password)
async def save_password_cmd(message: Message, state: FSMContext):
    await message.delete()
    await state.update_data(password=message.text)

    data = await state.get_data()
    lang = data.get('language', 'en')
    encrypted_password = encrypt_password(data['password'])
    tg_id = message.from_user.id

    try:
        await add_user(tg_id, data['login'], encrypted_password, lang)

        set_user_language(tg_id, lang)

        await state.clear()
        success_text = get_text('registration_success', lang)
        await message.answer(success_text, parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка при регистрации: {e}")
        error_text = get_text('registration_error', lang)
        await message.answer(error_text)
        await state.clear()


@router.message(Command("stats"))
@router.callback_query(F.data == "refresh")
async def stats_cmd(event: Message | CallbackQuery):
    user_id = event.from_user.id
    user_lang = get_user_language(user_id)

    wait_msg_text = get_text('gathering_data', user_lang)

    user = await check_user_exists(user_id)
    if not user:
        text = get_text('not_registered', user_lang)
        if isinstance(event, Message):
            return await event.answer(text)
        await event.answer()
        return await event.message.answer(text)

    if isinstance(event, Message):
        wait_msg = await event.answer(wait_msg_text)
    else:
        wait_msg = await event.message.edit_text(wait_msg_text)

    user_data = await get_user_data(user_id)
    decrypted_password = decrypt_password(user_data.encrypted_password)

    try:
        data = await get_gtu_grades(user_data.login, decrypted_password)

        unique_sems = list(dict.fromkeys(item['semester'] for item in data))
        current_semester_name = unique_sems[0] if unique_sems else None

        unique_sems.reverse()

        for sem in unique_sems:
            if (user_id, sem) not in semester_cache:
                await sync_semesters(sem, user_id)
        await update_cache(user_id)

        result_grades = []

        for item in data:
            sem_name = item['semester']
            subject_name = item['subject']
            score_float = float(item['score'])

            cache_key = (user_id, sem_name)
            semester_id = semester_cache.get(cache_key)

            if semester_id is None:
                await sync_semesters(sem_name, user_id)
                await update_cache(user_id)
                semester_id = semester_cache.get(cache_key)
                if semester_id is None:
                    continue

            res = await update_lessons_and_grades(user_id, subject_name, score_float, semester_id)

            if sem_name == current_semester_name and res is not None:
                result_grades.append(res)

        text_lines = [get_text('stats_header', user_lang)]

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

            line = f"📚 <code> {score_str:>4} </code> | {name}{status}"
            text_lines.append(line)

        final_text = "\n".join(text_lines)
        await wait_msg.edit_text(final_text, parse_mode="HTML", reply_markup=refresh_button(user_lang))

    except Exception as e:
        print(f"Ошибка в stats_cmd: {e}")
        error_text = get_text('stats_error', user_lang)
        if isinstance(event, CallbackQuery):
            await wait_msg.edit_text(error_text, parse_mode="HTML")
        else:
            await wait_msg.edit_text(error_text, parse_mode="HTML")


@router.callback_query(F.data == "first_semester")
async def get_first_semester(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_lang = get_user_language(user_id)
    sem_id = await get_semester_id_by_index(user_id, 0)

    if not sem_id:
        await callback.answer(get_text('no_first_sem_data', user_lang), show_alert=True)
        return

    first_sem_grades = await get_semester_grades(user_id, sem_id)
    text_lines = [get_text('first_sem_header', user_lang)]

    for grade_obj in first_sem_grades:
        name = grade_obj.lesson_name.strip()
        if name.endswith(')') and name.count(')') > name.count('('):
            name = name[:-1].strip()

        score_str = f"{grade_obj.score:>4.1f}"
        line = f"📚 <code> {score_str} </code> | {name}"
        text_lines.append(line)

    final_text = "\n".join(text_lines)
    await callback.answer()
    await callback.message.edit_text(final_text, parse_mode="HTML", reply_markup=refresh_button(user_lang))


@router.callback_query(F.data == "current_semester")
async def get_current_semester_cmd(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_lang = get_user_language(user_id)
    current_sem_id = await get_current_semester(user_id)

    current_sem_grades = await get_semester_grades(user_id, current_sem_id)
    text_lines = [get_text('stats_header', user_lang)]

    for grade_obj in current_sem_grades:
        name = grade_obj.lesson_name.strip()
        if name.endswith(')') and name.count(')') > name.count('('):
            name = name[:-1].strip()

        score_str = f"{grade_obj.score:>4.1f}"
        line = f"📚 <code> {score_str} </code> | {name}"
        text_lines.append(line)

    final_text = "\n".join(text_lines)
    await callback.answer()
    await callback.message.edit_text(final_text, parse_mode="HTML", reply_markup=refresh_button(user_lang))


@router.message(Command("profile"))
async def profile_cmd(message: Message):
    user_id = message.from_user.id
    user_lang = get_user_language(user_id)

    user_data = await get_user_data(user_id)

    if not user_data:
        await message.answer(get_text('not_registered', user_lang))
        return

    if user_data.created_at:
        reg_date = user_data.created_at.strftime("%d.%m.%Y")
    else:
        reg_date = get_text('profile_unknown_date', user_lang)

    text = get_text('profile_text', user_lang).format(
        login=user_data.login,
        reg_date=reg_date
    )

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=get_profile_keyboard(user_lang)
    )


@router.callback_query(F.data == "reset_account")
async def reset_account_cmd(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_lang = get_user_language(user_id)
    await callback.answer()

    reset_text = get_text('reset_ask_login', user_lang)
    await callback.message.answer(reset_text, parse_mode="HTML")
    await delete_user(user_id)

    await state.update_data(language=user_lang)
    await state.set_state(Registration.waiting_login)
    return None