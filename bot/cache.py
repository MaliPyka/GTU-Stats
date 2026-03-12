from db.requests import get_all_semesters

semester_cache = {}


async def update_cache(tg_id):
    global semester_cache


    raw_data = await get_all_semesters(tg_id)


    new_data = {(sem.tg_id, sem.semester_name): sem.id for sem in raw_data}

    semester_cache.clear()
    semester_cache.update(new_data)

    print(f"✅ Кэш обновлен для всех юзеров. Записей: {len(semester_cache)}")