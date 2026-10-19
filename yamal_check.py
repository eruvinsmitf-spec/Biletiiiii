import os
import requests
from playwright.sync_api import sync_playwright

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
MANUAL = os.environ.get("MANUAL_RUN", "") == "true"  # запуск кнопкой вручную

URL = "https://yamalaero.ru/booking/#/results/81176590368"
SHOT = "status.png"

NO_FLIGHTS = [
    "перелетов не найдено",
    "рейсов не найдено",
    "мест нет",
    "нет доступных",
]


def tg(text, photo=None):
    if not TOKEN or not CHAT_ID:
        print("Не заданы секреты TELEGRAM_TOKEN / CHAT_ID")
        return
    try:
        if photo:
            with open(photo, "rb") as f:
                requests.post(
                    f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
                    data={"chat_id": CHAT_ID, "caption": text[:1000]},
                    files={"photo": f},
                    timeout=30,
                )
        else:
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                data={"chat_id": CHAT_ID, "text": text},
                timeout=30,
            )
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            ctx = browser.new_context(
                viewport={"width": 1366, "height": 900},
                locale="ru-RU",
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            )
            page = ctx.new_page()
            page.goto(URL, timeout=60000)
            page.wait_for_timeout(12000)

            # Повторный поиск, чтобы сессия не протухала
            for label in ["Найти", "Повторить поиск", "Обновить"]:
                btn = page.get_by_text(label, exact=True)
                if btn.count() > 0 and btn.first.is_visible():
                    btn.first.click()
                    page.wait_for_timeout(12000)
                    break

            final_url = page.url
            page.screenshot(path=SHOT)
            text = page.inner_text("body").lower()
        except Exception as e:
            print(f"Ошибка: {e}")
            if MANUAL:
                tg(f"⚠️ Ручная проверка не удалась: {e}")
            return
        finally:
            browser.close()

    has_no_flights = any(s in text for s in NO_FLIGHTS)
    has_buy = ("выбрать" in text or "купить" in text) and (
        "₽" in text or "руб" in text
    )
    found = has_buy and not has_no_flights

    if found:
        tg(
            f"🚨 ПОХОЖЕ, ПОЯВИЛИСЬ БИЛЕТЫ! Салехард — Омск, 31 декабря.\n{final_url}",
            SHOT,
        )
    elif MANUAL:
        tg(
            "Ручная проверка: билетов пока не видно.\n"
            "Посмотри скриншот: так ли видит страницу бот.",
            SHOT,
        )
    print("Найдено" if found else "Билетов нет")


if __name__ == "__main__":
    main()
