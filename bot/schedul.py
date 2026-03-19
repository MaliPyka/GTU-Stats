from db.requests import get_all_user, sync_semesters, update_lessons_and_grades, sync_old_scores_in_db
from core.security import decrypt_password
from bot.cache import semester_cache, update_cache, get_user_language 
from bot.texts import get_text
from core.scraper import get_gtu_grades
from html import escape
from aiogram import Bot

async def check_grades_job(bot: Bot):
    users = await get_all_user()
    for user in users:
        updated_items = []
        try:
            p_word = decrypt_password(user.encrypted_password)

            data = await get_gtu_grades(user.login, p_word, user.tg_id)

            if not data:
                continue

            unique_sems = list(set(item['semester'] for item in data))
            for sem in unique_sems:
                if (user.tg_id, sem) not in semester_cache:
                    await sync_semesters(sem, user.tg_id)
            
            await update_cache(user.tg_id)

            for item in data:
                sem_name = item['semester']
                subject_name = item['subject']
                score_float = float(item['score'])

                cache_key = (user.tg_id, sem_name)
                semester_id = semester_cache.get(cache_key)

                if not semester_id:
                    continue 

                res = await update_lessons_and_grades(user.tg_id, subject_name, score_float, semester_id)

                if res:
                    if res.lesson_name == subject_name and res.score != res.old_score:
                        print(f"✅ НАШЛИ ОБНОВЛЕНИЕ! {subject_name}: {res.old_score} -> {res.score}")
                        updated_items.append({
                            "obj": res,
                            "sem_id": semester_id
                        })

            if updated_items:
                user_lang = get_user_language(user.tg_id)
                msg = get_text('notification_header', user_lang)

                for item_dict in updated_items:
                    obj = item_dict["obj"]
                    name = obj.lesson_name.strip()
                    
                    if name.endswith(')') and name.count(')') > name.count('('):
                        name = name[:-1].strip()

                    safe_name = escape(name)

                    msg += f"📚 {safe_name}: <code>{obj.old_score}</code> → <code>{obj.score}</code>\n"

                try:
                    await bot.send_message(user.tg_id, msg, parse_mode="HTML")
                    print(f"✅ Уведомление успешно отправлено в ТГ!")
                except Exception as tg_e:
                    print(f"❌ ОШИБКА ОТПРАВКИ В ТГ: {tg_e}")
                    print(f"❌ СЛОМАННЫЙ ТЕКСТ:\n{msg}")

                for item_dict in updated_items:
                    obj = item_dict["obj"]
                    sem_id = item_dict["sem_id"]
                    await sync_old_scores_in_db(user.tg_id, obj.lesson_name, obj.score, sem_id)

            updated_items.clear()

        except Exception as e:
            print(f"Ошибка юзера {user.tg_id}: {e}")