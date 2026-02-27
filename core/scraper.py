import asyncio
import re

from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def get_gtu_grades(login, password):
    async with async_playwright() as p:
        # запуск браузера
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        try:
            # заходим на страницу регистрации
            await page.goto("https://vici.gtu.ge/#/login")

            # ввод данных
            await page.fill('input[formcontrolname="username"]', login)
            await page.fill('input[formcontrolname="password"]', password)

            # нажатие кнопки входа
            await page.keyboard.press("Enter")
            await page.click('text="დახურვა"')
            await page.wait_for_url("https://vici.gtu.ge/#/dashboard")

            # жмем на перевод страницы
            await page.click('button:has(img[src="assets/icons/flags/en.png"])')
            # заходим на страницу с баллами
            await page.goto("https://vici.gtu.ge/#/learningCard")
            await page.wait_for_selector('mat-table', timeout=5000)

            # собираем HTML код страницы
            content = await page.content()
            return parse_grades(content)
        except Exception as e:
                print(f"Ошибка парсинга: {e}")
                return None
        finally:
            await browser.close() 


def parse_grades(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    grades_data = []

    rows = soup.find_all(['mat-row', 'div'], class_='mat-mdc-row')

    for row in rows:
        subject_elem = row.select_one('.book-name-text')
        score_elem = row.select_one('.cdk-column-score')
        
        if subject_elem and score_elem:
            full_name = subject_elem.get_text(strip=True)
            
            match = re.search(r'[А-Яа-яЁё]', full_name)
            
            if match:
                display_name = full_name[match.start():]
                while display_name.count(')') > display_name.count('(') and display_name.endswith(')'):
                    display_name = display_name[:-1]
                    
                display_name = display_name.strip()
            else:
                display_name = full_name

            score_value = score_elem.get_text(strip=True)
            
            grades_data.append({
                "subject": display_name,
                "score": score_value
            })

    return grades_data


async def get_all_curses(login, password):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
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
