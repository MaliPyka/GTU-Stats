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

            for item in data:
                res = await update_lessons_and_grades(user.tg_id, item['subject'], float(item['score']))
                
                if res and isinstance(res, list):
                    for db_item in res:
                        if db_item.lesson_name == item['subject'] and db_item.score != db_item.old_score:
                            updated_items.append(db_item)

            if updated_items:
                msg = "🔔 <b>Обновление баллов!</b>\n\n"
                for obj in updated_items:
                    msg += f"📚 {obj.lesson_name}: {obj.old_score} ➡️ <b>{obj.score}</b>\n"
                
                await bot.send_message(user.tg_id, msg, parse_mode="HTML")

                for obj in updated_items:
                    await sync_old_scores_in_db(user.tg_id, obj.lesson_name, obj.score)

                updated_items.clear()

        except Exception as e:
            print(f"Ошибка юзера {user.tg_id}: {e}")
    