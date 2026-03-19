from db.requests import get_all_semesters, get_all_semesters_db, get_all_language

semester_cache = {}

language_cache = {}

async def load_all_cache():
    global semester_cache
    raw_data = await get_all_semesters_db()

    new_data = {(sem.tg_id, sem.semester_name): sem.id for sem in raw_data}
    semester_cache.clear()
    semester_cache.update(new_data)

    print(f"✅ Кэш загружен при старте. Записей: {len(semester_cache)}")


async def update_cache(tg_id):
    global semester_cache
    raw_data = await get_all_semesters(tg_id)

    for sem in raw_data:
        semester_cache[(sem.tg_id, sem.semester_name)] = sem.id

def clear_user_semester_cache(tg_id: int):
    global semester_cache
    keys_to_remove = [key for key in semester_cache.keys() if key[0] == tg_id]
    for key in keys_to_remove:
        del semester_cache[key]


async def load_all_users_language():
    global language_cache
    users_data = await get_all_language()

    language_cache = {tg_id: lang for tg_id, lang in users_data}

    print(f"DEBUG: Загружено из БД для кэша: {users_data}")
    print(f"✅ Кэш языков обновлен: {len(language_cache)} юзеров")


def get_user_language(tg_id: int) -> str:
    return language_cache.get(int(tg_id), 'en')

def set_user_language(tg_id: int, lang: str):
    language_cache[int(tg_id)] = lang
