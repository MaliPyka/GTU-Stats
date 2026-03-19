import asyncio

from aiogram import F, Bot, Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from html import escape

from db.requests import add_user, check_user_exists, clear_user_data_on_lang_change, get_all_user, get_language_stats, get_total_users_count, update_lessons_and_grades, get_user_data, sync_semesters, \
    get_semester_id_by_index, get_semester_grades, delete_user, get_current_semester, change_user_language
from core.security import encrypt_password, decrypt_password
from core.scraper import get_gtu_grades
from bot.keyboards import admin_keyboard, get_admin_main_keyboard, get_back_to_admin_keyboard, refresh_button, get_main_menu, get_profile_keyboard, choose_language_keyboard, get_admin_reply_keyboard, get_cancel_support_keyboard, get_cancel_broadcast_keyboard
from bot.cache import update_cache, semester_cache, get_user_language, set_user_language, clear_user_semester_cache
from bot.texts import get_text

router = Router()
ADMIN_ID = 992941959

class Registration(StatesGroup):
    change_language = State()
    waiting_language = State()
    waiting_login = State()
    waiting_password = State()

class SupportState(StatesGroup):
    waiting_for_message = State()

class AdminReplyState(StatesGroup):
    waiting_for_reply = State()
    user_id_to_reply = State()

class AdminBroadcastState(StatesGroup):
    waiting_for_message = State()

@router.message(CommandStart())
async def choose_language_cmd(message: Message, state: FSMContext):

    if await check_user_exists(message.from_user.id):
        await state.clear() 
        
        user_lang = get_user_language(message.from_user.id) 

        await message.answer(
            get_text('already_registered', user_lang),
            parse_mode="HTML"
        )
        return

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
        data = await get_gtu_grades(user_data.login, decrypted_password, user_id)

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


@router.callback_query(F.data == "change_language")
async def change_language_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_language(user_id)
    
    await callback.answer()
    await callback.message.edit_text(
        text=get_text('choose_language', lang), 
        reply_markup=choose_language_keyboard(), 
        parse_mode="HTML"
    )


@router.callback_query(F.data.in_({"ru", "en", "ka"}))
async def change_language_final(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    new_lang = callback.data
    user_id = callback.from_user.id

    set_user_language(user_id, new_lang)
    await change_user_language(user_id, new_lang)
    await callback.answer()

    if current_state is None:
        await clear_user_data_on_lang_change(user_id)
        clear_user_semester_cache(user_id)
        
        await callback.message.edit_text(
            text=get_text('lang_changed', new_lang),
            parse_mode="HTML"
        )
        
        await asyncio.sleep(3)

        user_data = await get_user_data(user_id)
        if user_data:
            reg_date = user_data.created_at.strftime("%d.%m.%Y") if user_data.created_at else get_text('profile_unknown_date', new_lang)
            text = get_text('profile_text', new_lang).format(
                login=user_data.login,
                reg_date=reg_date
            )

            await callback.message.edit_text(
                text=text,
                parse_mode="HTML",
                reply_markup=get_profile_keyboard(new_lang)
            )
    
    elif current_state == Registration.waiting_language:
        await state.update_data(language=new_lang)
        if await check_user_exists(user_id):
            await state.clear()
            return await callback.message.answer(get_text('already_registered', new_lang))
        
        await callback.message.answer(get_text('welcome', new_lang), reply_markup=get_main_menu(new_lang))
        await state.set_state(Registration.waiting_login)
    

@router.callback_query(F.data == "reset_account")
async def reset_account_cmd(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_lang = get_user_language(user_id)
    await callback.answer()

    reset_text = get_text('reset_ask_login', user_lang)
    await callback.message.answer(reset_text, parse_mode="HTML")
    await delete_user(user_id)
    clear_user_semester_cache(user_id)

    await state.update_data(language=user_lang)
    await state.set_state(Registration.waiting_login)
    return None


@router.message(Command("admin"))
async def admin_panel_cmd(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    total_users = await get_total_users_count()
    lang_stats = await get_language_stats()
    
    ru_count = lang_stats.get('ru', 0)
    en_count = lang_stats.get('en', 0)
    ka_count = lang_stats.get('ka', 0)

    text = (
        "👑 <b>Admin Panel</b>\n"
        "\n"
        f"👥 Всего: <code>{total_users}</code>\n"
        f"🌍 RU: {ru_count} | EN: {en_count} | KA: {ka_count}\n"
        " "
    )

    # Клавиатура подтянется уже без лишней кнопки
    await message.answer(text, reply_markup=get_admin_main_keyboard(), parse_mode="HTML")


@router.message(Command("support"))
async def support_cmd(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_lang = get_user_language(user_id)
    
    prompt_msg = await message.answer(
        get_text('support_prompt', user_lang), 
        reply_markup=get_cancel_support_keyboard(user_lang),
        parse_mode="HTML"
    )
    
    await state.set_state(SupportState.waiting_for_message)
    await state.update_data(prompt_message_id=prompt_msg.message_id)

  
@router.callback_query(F.data == "cancel_support", StateFilter(SupportState.waiting_for_message))
async def cancel_support_callback(callback: CallbackQuery, state: FSMContext):
    user_lang = get_user_language(callback.from_user.id)

    await state.clear()

    await callback.message.edit_text(
        get_text('support_cancelled', user_lang),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(SupportState.waiting_for_message)
async def process_support_message(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    username = message.from_user.username or "Без юзернейма"
    user_lang = get_user_language(user_id)
    
    safe_text = escape(message.text or "Без текста (возможно фото/стикер)")
    
    data = await state.get_data()
    prompt_message_id = data.get("prompt_message_id")
    
    if prompt_message_id:
        try:
            await bot.delete_message(chat_id=user_id, message_id=prompt_message_id)
        except Exception:
            pass

    admin_text = (
        f"📩 <b>Новое обращение!</b>\n"
        f"👤 От: {message.from_user.full_name} (@{username})\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        "────────────────\n"
        f"<i>{safe_text}</i>"
    )
    
    reply_kb = get_admin_reply_keyboard(user_id)
    
    try:
        await bot.send_message(ADMIN_ID, admin_text, reply_markup=reply_kb, parse_mode="HTML")
        await message.answer(get_text('support_sent', user_lang), parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка при отправке обращения: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")
        
    await state.clear()


@router.callback_query(F.data.startswith("reply_"))
async def admin_reply_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("⛔ Нет прав!", show_alert=True)
        
    target_user_id = int(callback.data.split("_")[1])
    
    await state.update_data(user_id_to_reply=target_user_id)
    await state.set_state(AdminReplyState.waiting_for_reply)
    
    await callback.message.answer(
        f"✍️ Напиши ответ для пользователя <code>{target_user_id}</code>.\n\n<i>Текст будет отправлен от имени бота.</i>", 
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminReplyState.waiting_for_reply)
async def send_admin_reply(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    target_user_id = data.get("user_id_to_reply")
    
    safe_reply = escape(message.text or "")
    
    reply_text_for_user = (
        f"👨‍💻 <b>Ответ от разработчика:</b>\n\n"
        f"{safe_reply}"
    )
    
    try:
        await bot.send_message(target_user_id, reply_text_for_user, parse_mode="HTML")
        await message.answer("✅ Ответ успешно доставлен!")
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки: {e}")
        
    await state.clear()


@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("⛔ Нет прав!", show_alert=True)
        
    await state.set_state(AdminBroadcastState.waiting_for_message)
    
    prompt_msg = await callback.message.edit_text(
        "📢 <b>Режим рассылки</b>\n\n"
        "Отправь сообщение, которое нужно разослать всем пользователям бота:\n\n",
        reply_markup=get_cancel_broadcast_keyboard(),
        parse_mode="HTML"
    )

    await state.update_data(prompt_message_id=prompt_msg.message_id)
    await callback.answer()


@router.callback_query(F.data == "cancel_broadcast", StateFilter(AdminBroadcastState.waiting_for_message))
async def cancel_broadcast_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("✅ Рассылка отменена.", parse_mode="HTML")
    await callback.answer()


@router.message(AdminBroadcastState.waiting_for_message)
async def process_broadcast_message(message: Message, state: FSMContext, bot: Bot):
    if message.from_user.id != ADMIN_ID:
        return

    text_to_send = message.html_text or message.text
    if not text_to_send:
        return await message.answer("❌ Рассылка поддерживает только текстовые сообщения.")

    data = await state.get_data()
    prompt_message_id = data.get("prompt_message_id")
    
    if prompt_message_id:
        try:
            await bot.delete_message(chat_id=message.from_user.id, message_id=prompt_message_id)
        except Exception:
            pass

    users = await get_all_user()
    
    await state.clear()
    status_msg = await message.answer(f"⏳ Начинаю рассылку для <code>{len(users)}</code> пользователей...")

    success_count = 0
    fail_count = 0

    for user in users:
        try:
            await bot.send_message(user.tg_id, text_to_send, parse_mode="HTML")
            success_count += 1
        except Exception:
            fail_count += 1
        
        await asyncio.sleep(0.05)

    await status_msg.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"Успешно доставлено: <code>{success_count}</code>\n"
        f"Ошибок (заблокировали бота): <code>{fail_count}</code>",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_feedback")
async def admin_feedback_info(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return

    text = "📥 <b>Обращения</b>\n\nНовые тикеты прилетают напрямую в личку. Общая база тикетов пока не подключена."
    
    await callback.message.edit_text(
        text, 
        reply_markup=get_back_to_admin_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_admin")
async def back_to_admin_handler(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    
    total_users = await get_total_users_count()
    lang_stats = await get_language_stats()
    
    ru_count = lang_stats.get('ru', 0)
    en_count = lang_stats.get('en', 0)
    ka_count = lang_stats.get('ka', 0)

    text = (
        "👑 <b>Admin Panel</b>\n"
        "────────────────\n"
        f"👥 Всего: <code>{total_users}</code>\n"
        f"🌍 RU: {ru_count} | EN: {en_count} | KA: {ka_count}\n"
        "────────────────"
    )

    await callback.message.edit_text(
        text, 
        reply_markup=get_admin_main_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()
