from db.requests import get_all_user, update_lessons_and_grades, sync_old_scores_in_db
from core.security import decrypt_password
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
                continue  # Если сайт лежит или вернул пустоту, просто идем к следующему юзеру

            for item in data:
                sem_name = item['semester']
                subject_name = item['subject']
                score_float = float(item['score'])

                # 1. Проверяем семестр в кэше (идентично хендлеру)
                if sem_name not in semester_cache:
                    await sync_semesters(sem_name)
                    await update_cache()

                semester_id = semester_cache.get(sem_name)

                # Защита от зависаний
                if not semester_id:
                    continue

                # 2. Передаем semester_id в основную функцию обновления
                res = await update_lessons_and_grades(user.tg_id, subject_name, score_float, semester_id)

                if res and isinstance(res, list):
                    for db_item in res:
                        if db_item.lesson_name == subject_name and db_item.score != db_item.old_score:
                            # Сохраняем в список словарей, чтобы не потерять semester_id для следующего шага
                            updated_items.append({
                                "obj": db_item,
                                "sem_id": semester_id
                            })

            if updated_items:
                msg = "🔔 <b>Обновление баллов!</b>\n\n"

                for item_dict in updated_items:
                    obj = item_dict["obj"]

                    # Причесываем название предмета для уведомления (ты же делал эту крутую очистку)
                    name = obj.lesson_name.strip()
                    if name.endswith(')') and name.count(')') > name.count('('):
                        name = name[:-1].strip()

                    msg += f"📚 {name}: {obj.old_score} ➡️ <b>{obj.score}</b>\n"

                await bot.send_message(user.tg_id, msg, parse_mode="HTML")

                # 3. Синхронизируем old_score
                for item_dict in updated_items:
                    obj = item_dict["obj"]
                    sem_id = item_dict["sem_id"]

                    # ВАЖНО: Тебе нужно будет зайти в db/requests.py и добавить semester_id
                    # в аргументы функции sync_old_scores_in_db, чтобы она обновляла правильную строку!
                    await sync_old_scores_in_db(user.tg_id, obj.lesson_name, obj.score, sem_id)

                updated_items.clear()

        except Exception as e:
            print(f"Ошибка юзера {user.tg_id}: {e}")
    