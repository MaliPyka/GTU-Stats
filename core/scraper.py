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