import csv
import io
import logging
from datetime import datetime
import pytz
import requests
import telebot
from telebot import types
from apscheduler.schedulers.background import BackgroundScheduler

BOT_TOKEN = "8814170419:AAHWiLDlZEJ0KXeQzU_hVmQckRlsB6wRi8w"
USER_CHAT_ID = 780458353

SHEET_ID = "1GVh_6jnAoTsp-U8c0xvV85zEdgP8sgIJwEMHWdaSVno"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv"

TEACHER_LINKS = {
    "литвин": "https://meet.google.com/ait-gnuz-oqo",
    "букатов": "https://us04web.zoom.us/j/6128385015?pwd=VqXYvANnVG11TCp_xzdzOGtRwnQmzk.1",
    "захаренков": "https://us02web.zoom.us/j/6696841684?pwd=eHR3aWV5RTIrWTRFYnFaejlWeXhkUT09",
    "левченко": "https://us02web.zoom.us/j/4717138521?pwd=eFI0SEdMN3NxQkNBWGlMNVl3WjB5Zz09",
    "яровий": "https://us02web.zoom.us/j/2589993020?pwd=bU9RUk50TVk5TDJxL1lvbXoxNmtrQT09",
    "бойко": "https://us02web.zoom.us/j/81133607854?pwd=QwF1BB1kaeZxdI4jVhWa8gOgA9KLVC.1",
    "гордієнко": "https://us04web.zoom.us/j/71992214760?pwd=i6KR9LbQYZx97lthUIZN8whASUGdO4.1",
    "довголуцький": "https://meet.google.com/bse-espc-vhs",
    "подвиженко": "https://us02web.zoom.us/j/8110796424?pwd=Z9z6Xa7iRTX0wViW3xawnNEa2K2SaM.1",
}

DEFAULT_MEET = "https://meet.google.com/"

CALL_TIMES = [
    {"hour": 9, "minute": 15},
    {"hour": 10, "minute": 40},
    {"hour": 12, "minute": 20},
    {"hour": 13, "minute": 45},
]

DAYS_MAP = {
    0: "Понеділок",
    1: "Вівторок",
    2: "Середа",
    3: "Четвер",
    4: "Пʼятниця"
}

weekly_schedule = {}

bot = telebot.TeleBot(BOT_TOKEN)
scheduler = BackgroundScheduler(timezone=pytz.timezone("Europe/Kyiv"))

def get_link_for_lesson(lesson_text: str) -> str:
    text = str(lesson_text).lower()
    for keyword, link in TEACHER_LINKS.items():
        if keyword in text:
            return link
    return DEFAULT_MEET

def send_lesson_notification(title: str, link: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(text="🚀 Увійти в пару", url=link))
    bot.send_message(
        chat_id=USER_CHAT_ID,
        text=f"🔔 Пара розпочалася!\n\n📚 {title}",
        reply_markup=kb
    )

def sync_schedule():
    global weekly_schedule
    try:
        res = requests.get(SHEET_URL, timeout=15)
        res.encoding = "utf-8"
        raw_text = res.text

        if "<!doctype html" in raw_text.lower() or "google.com/accounts" in raw_text:
            return "⚠️ Таблиця все ще закрита в налаштуваннях Google. Відкрий доступ усім за посиланням."

        reader = csv.reader(io.StringIO(raw_text))
        rows = [r for r in reader if any(cell.strip() for cell in r)]
        
        if not rows:
            return "Таблиця порожня."

        # Пошук колонки К-311
        target_col_idx = None
        for r in rows[:4]:
            for idx, cell in enumerate(r):
                c = cell.lower().replace(" ", "")
                if ("3к" in c and "фбк" in c) or "к-311" in c or "k-311" in c:
                    target_col_idx = idx
                    break
            if target_col_idx is not None:
                break

        if target_col_idx is None:
            target_col_idx = 1

        lessons = []
        for r in rows[1:]:
            if len(r) > target_col_idx:
                val = r[target_col_idx].strip()
                if val and not any(js in val for js in ["function", "window.", "var ", "return ", ".concat", "{", "}"]):
                    lessons.append(val)
                else:
                    lessons.append("")

        scheduler.remove_all_jobs()
        scheduler.add_job(sync_schedule, "cron", day_of_week="sun", hour=21, minute=0)

        weekly_schedule.clear()
        lesson_idx = 0
        days_codes = ["mon", "tue", "wed", "thu", "fri"]

        for day_num, day_code in enumerate(days_codes):
            weekly_schedule[day_num] = []
            for t in CALL_TIMES:
                title = lessons[lesson_idx] if lesson_idx < len(lessons) else ""
                lesson_idx += 1
                if title and title != "-":
                    link = get_link_for_lesson(title)
                    weekly_schedule[day_num].append({
                        "time": f"{t['hour']:02d}:{t['minute']:02d}",
                        "title": title,
                        "link": link
                    })
                    scheduler.add_job(
                        send_lesson_notification,
                        "cron",
                        day_of_week=day_code,
                        hour=t["hour"],
                        minute=t["minute"],
                        args=[title, link]
                    )

        total = sum(len(v) for v in weekly_schedule.values())
        return f"Успішно! Знайдено пар: {total}"
    except Exception as e:
        return f"Помилка: {e}"

@bot.message_handler(commands=["start"])
def cmd_start(message):
    bot.reply_to(
        message,
        "👋 Бот розкладу К-311 запущений!\n\n"
        "• /today — пари на сьогодні\n"
        "• /tomorrow — пари на завтра\n"
        "• /week — розклад на весь тиждень\n"
        "• /sync — оновити розклад з Google Таблиці"
    )

@bot.message_handler(commands=["sync"])
def cmd_sync(message):
    res_text = sync_schedule()
    bot.reply_to(message, f"🔄 {res_text}")

@bot.message_handler(commands=["today"])
def cmd_today(message):
    kyiv_tz = pytz.timezone("Europe/Kyiv")
    today_idx = datetime.now(kyiv_tz).weekday()
    send_day_schedule(message, today_idx, DAYS_MAP.get(today_idx, "Сьогодні"))

@bot.message_handler(commands=["tomorrow"])
def cmd_tomorrow(message):
    kyiv_tz = pytz.timezone("Europe/Kyiv")
    t_idx = (datetime.now(kyiv_tz).weekday() + 1) % 7
    send_day_schedule(message, t_idx, DAYS_MAP.get(t_idx, "Завтра"))

def send_day_schedule(message, day_idx, day_name):
    lessons = weekly_schedule.get(day_idx, [])
    if not lessons:
        bot.reply_to(message, f"🎉 {day_name}: пар немає!")
        return

    text = f"📋 Пари на {day_name}:\n\n"
    kb = types.InlineKeyboardMarkup()
    for item in lessons:
        text += f"⏰ {item['time']} — {item['title']}\n"
        kb.add(types.InlineKeyboardButton(text=f"👉 {item['time']} Увійти", url=item['link']))

    bot.reply_to(message, text, reply_markup=kb)

@bot.message_handler(commands=["week"])
def cmd_week(message):
    total = sum(len(v) for v in weekly_schedule.values())
    if total == 0:
        bot.reply_to(message, "Поки що розклад порожній. Надішли /sync.")
        return

    for d_num in range(5):
        d_name = DAYS_MAP[d_num]
        lessons = weekly_schedule.get(d_num, [])
        text = f"🗓 {d_name}:\n"
        if not lessons:
            text += "  (пар немає)\n"
        else:
            for l in lessons:
                text += f"  • {l['time']} — {l['title']}\n"
        bot.send_message(message.chat.id, text)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scheduler.start()
    sync_schedule()
    bot.infinity_polling()
