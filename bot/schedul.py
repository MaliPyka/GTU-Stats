from db.requests import get_all_user, sync_semesters, update_lessons_and_grades, sync_old_scores_in_db
from core.security import decrypt_password
from bot.cache import semester_cache, update_cache
from core.scraper import get_gtu_grades
from aiogram import Bot


async def check_grades_job(bot: Bot):
    users = await get_all_user()
    for user in users:
        updated_items = []
        try:
            p_word = decrypt_password(user.encrypted_password)
            data = await get_gtu_grades(user.login, p_word)

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


                if res and isinstance(res, list):
                    for db_item in res:
                        if db_item.lesson_name == subject_name and db_item.score != db_item.old_score:
                            updated_items.append({
                                "obj": db_item,
                                "sem_id": semester_id
                            })


            if updated_items:
                msg = "🔔 <b>Обновление баллов!</b>\n\n"

                for item_dict in updated_items:
                    obj = item_dict["obj"]
                    name = obj.lesson_name.strip()
                    

                    if name.endswith(')') and name.count(')') > name.count('('):
                        name = name[:-1].strip()

                    msg += f"📚 {name}: <code>{obj.old_score}</code> → <code>{obj.score}<code>\n"

                await bot.send_message(user.tg_id, msg, parse_mode="HTML")

                for item_dict in updated_items:
                    obj = item_dict["obj"]
                    await sync_old_scores_in_db(user.tg_id, obj.lesson_name, obj.score)

            updated_items.clear()

        except Exception as e:
            print(f"Ошибка юзера {user.tg_id}: {e}")
    