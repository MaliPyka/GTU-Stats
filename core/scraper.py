import asyncio
import re

from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from bot.cache import get_user_language

async def get_gtu_grades(login, password, user_id):
    user_lang = get_user_language(user_id)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto("https://vici.gtu.ge/#/login")

            await page.fill('input[formcontrolname="username"]', login)
            await page.fill('input[formcontrolname="password"]', password)
            await page.keyboard.press("Enter")

            try:
                await page.click('text="დახურვა"', timeout=3000)
            except Exception:
                pass

            await page.wait_for_url("https://vici.gtu.ge/#/dashboard", timeout=10000)

            if user_lang != "ka":
                try:
                    await page.wait_for_selector('button:has(img[src="assets/icons/flags/en.png"])', timeout=5000)
                    await page.click('button:has(img[src="assets/icons/flags/en.png"])')
                    await page.wait_for_timeout(1000)
                except Exception as e:
                    print(f"Предупреждение: не удалось сменить язык на сайте: {e}")

            await page.goto("https://vici.gtu.ge/#/learningCard")
            await page.wait_for_selector('mat-table', timeout=15000)

            content = await page.content()

            return parse_grades(content, user_lang)
            
        except Exception as e:
            print(f"Ошибка парсинга для юзера {user_id}: {e}")
            return None
        finally:
            await browser.close()


def parse_grades(html_content, user_lang='en'):
    soup = BeautifulSoup(html_content, 'html.parser')
    final_data = []

    tables = soup.find_all(role='table')
    if not tables:
        return final_data

    headers = []
    for text_node in soup.find_all(string=re.compile(r"202\d/202\d")):
        clean_text = text_node.strip()
        if clean_text and len(clean_text) < 40 and clean_text not in headers:
            headers.append(clean_text)

    for i, table in enumerate(tables):
        current_semester_data = []

        if i < len(headers):
            semester_name = headers[i]
        else:
            semester_name = f"Unknown Semester {i+1}"

        rows = table.find_all(role='row')
        for row in rows:
            if not hasattr(row, 'select_one'):
                continue

            subject_elem = row.select_one('.book-name-text')
            score_elem = row.select_one('.cdk-column-score')

            if subject_elem and score_elem:
                full_name = subject_elem.get_text(strip=True)
                display_name = full_name

                if user_lang == 'ka':
                    display_name = full_name
                    
                elif user_lang == 'ru':
                    match = re.search(r'[А-Яа-яЁё]', full_name)
                    if match:
                        display_name = full_name[match.start():]
                        while display_name.count(')') > display_name.count('(') and display_name.endswith(')'):
                            display_name = display_name[:-1]
                        display_name = display_name.strip()
                        
                elif user_lang == 'en':
                    match = re.search(r'[А-Яа-яЁё]', full_name)
                    if match:
                        display_name = full_name[:match.start()].strip()
                        
                        if display_name.endswith('('):
                            display_name = display_name[:-1].strip()

                score_value = score_elem.get_text(strip=True)

                current_semester_data.append({
                    "semester": semester_name,
                    "subject": display_name,
                    "score": score_value
                })

        final_data.extend(current_semester_data)

    return final_data


async def get_all_curses(login, password):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto("https://elearning.gtu.ge/login/index.php")

            await page.fill('input[id="username"]', login)
            await page.fill('input[id="password"]', password)
            await page.keyboard.press("Enter")

            try:
                await page.wait_for_selector(".coursename", timeout=10000)
            except:
                print("Селектор .coursename не найден, пробую подождать сеть...")
                await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            content = await page.content()
            await browser.close()
            return curses_parser(content)

        except Exception as e:
            print(f"Ошибка парсинга: {e}")
            return None


def curses_parser(content):
    soup = BeautifulSoup(content, 'html.parser')
    curses_set = set()
    curses_data = []

    rows = soup.select("a.aalink.coursename")

    for row in rows:
        raw_text = row.get_text(separator=" ", strip=True)

        clean_text = raw_text.replace("Course name", "") \
            .replace("Название курса", "") \
            .replace("Course is starred", "") \
            .replace("Курс добавлен в избранное", "")

        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        clean_text = re.sub(r'\d{4}-\d{4}\(.{1,2}\)-\d+\s*', '', clean_text)

        if "ქართული ენა" in clean_text:
            clean_text = "Грузинский язык – 1"

        clean_text = re.sub(r'\(?\d+კრ\)?', '', clean_text).strip()

        if re.search(r'[\u10A0-\u10FF]', clean_text):
            continue

        clean_text = clean_text.strip(" -")

        if clean_text and clean_text not in curses_set:
            curses_set.add(clean_text)
            curses_data.append({"curse": clean_text})

    return curses_data
