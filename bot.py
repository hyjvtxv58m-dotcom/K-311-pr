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

SHEET_ID = "1KPQpwM98V8lW-sCGZiWLX5M7NimVKGNbQJENZVZyNHw"
SHEET_URL = "https://docs.google.com/spreadsheets/d/1-GXO6fGHpQynrfuTj9UnJaX4NkaOvKKoqR9Cii1UuZo/edit?usp=drivesdk"

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
    4: "Пʼятниця",
    5: "Субота",
    6: "Неділя"
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
    kb.add(types.InlineKeyboardButton(text="🚀 Войти в пару", url=link))
    bot.send_message(
        chat_id=USER_CHAT_ID,
        text=f"🔔 <b>Пара началась!</b>\n\n📚 {title}",
        reply_markup=kb,
        parse_mode="HTML"
    )

def sync_schedule():
    global weekly_schedule
    try:
        res = requests.get(SHEET_URL, timeout=10)
        res.encoding = 'utf-8'
        reader = csv.reader(io.StringIO(res.text))
        rows = list(reader)
        
        if not rows:
            return "Таблиця порожня"

        header = rows[0]
        target_col_idx = None
        for idx, col_name in enumerate(header):
            col_clean = col_name.lower().replace(" ", "")
            if "3к" in col_clean and "фбк" in col_clean:
                target_col_idx = idx
                break
        
        if target_col_idx is None:
            # пробуем взять 2-ю колонку, если заголовок объединённый
            target_col_idx = 1

        lessons = []
        for r in rows[1:]:
            if len(r) > target_col_idx:
                val = r[target_col_idx].strip()
                lessons.append(val)

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

        logging.info("Синхронизация завершена успешно!")
        total = sum(len(v) for v in weekly_schedule.values())
        return f"Успішно! Знайдено пар на тиждень: {total}"
    except Exception as e:
        logging.error(f"Помилка: {e}")
        return f"Помилка синхронізації: {e}"

@bot.message_handler(commands=["start"])
def cmd_start(message):
    bot.reply_to(
        message,
        "👋 Бот розкладу К-311 запущений!\n\n"
        "• /today — пари на сьогодні\n"
        "• /tomorrow — пари на завтра\n"
        "• /week — розклад на весь тиждень\n"
        "• /sync — оновити з Google Таблиці"
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
    if day_idx not in weekly_schedule or not weekly_schedule[day_idx]:
        bot.reply_to(message, f"🎉 <b>{day_name}</b>: пар немає!", parse_mode="HTML")
        return

    text = f"📋 <b>Пари на {day_name}:</b>\n\n"
    kb = types.InlineKeyboardMarkup()
    for item in weekly_schedule[day_idx]:
        text += f"⏰ <b>{item['time']}</b> — {item['title']}\n"
        kb.add(types.InlineKeyboardButton(text=f"👉 {item['time']} {item['title'][:20]}...", url=item['link']))

    bot.reply_to(message, text, reply_markup=kb, parse_mode="HTML")

@bot.message_handler(commands=["week"])
def cmd_week(message):
    total = sum(len(v) for v in weekly_schedule.values())
    if total == 0:
        bot.reply_to(message, "Поки що розклад порожній. Спробуй /sync.")
        return

    text = "🗓 <b>Розклад на тиждень:</b>\n\n"
    for d_num in range(5):
        d_name = DAYS_MAP[d_num]
        text += f"<b>{d_name}:</b>\n"
        day_lessons = weekly_schedule.get(d_num, [])
        if not day_lessons:
            text += "  <i>Пар немає</i>\n"
        else:
            for l in day_lessons:
                text += f"  • {l['time']} — {l['title']}\n"
        text += "\n"

    bot.reply_to(message, text, parse_mode="HTML")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scheduler.start()
    sync_schedule()
    bot.infinity_polling()
