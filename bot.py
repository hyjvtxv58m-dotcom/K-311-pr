import html
import logging
import os
import re
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import pytz
import telebot
from telebot import types
from apscheduler.schedulers.background import BackgroundScheduler

BOT_TOKEN = "8814170419:AAHWiLDlZEJ0KXeQzU_hVmQckRlsB6wRi8w"
USER_CHAT_ID = 780458353

# Сервер для поддержания статуса Live на Render
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_http_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

# Каталог ссылок преподавателей К-311
TEACHER_LINKS = {
    "литвин": ("https://meet.google.com/ait-gnuz-oqo", "Meet"),
    "букатов": ("https://us04web.zoom.us/j/6128385015?pwd=VqXYvANnVG11TCp_xzdzOGtRwnQmzk.1", "Zoom"),
    "захаренков": ("https://us02web.zoom.us/j/6696841684?pwd=eHR3aWV5RTIrWTRFYnFaejlWeXhkUT09", "Zoom"),
    "левченко": ("https://us02web.zoom.us/j/4717138521?pwd=eFI0SEdMN3NxQkNBWGlMNVl3WjB5Zz09", "Zoom"),
    "яровий": ("https://us02web.zoom.us/j/2589993020?pwd=bU9RUk50TVk5TDJxL1lvbXoxNmtrQT09", "Zoom"),
    "бойко": ("https://us02web.zoom.us/j/81133607854?pwd=QwF1BB1kaeZxdI4jVhWa8gOgA9KLVC.1", "Zoom"),
    "гордієнко": ("https://us04web.zoom.us/j/71992214760?pwd=i6KR9LbQYZx97lthUIZN8whASUGdO4.1", "Zoom"),
    "довголуцький": ("https://meet.google.com/bse-espc-vhs", "Meet"),
    "подвиженко": ("https://us02web.zoom.us/j/8110796424?pwd=Z9z6Xa7iRTX0wViW3xawnNEa2K2SaM.1", "Zoom"),
}

DAYS_MAP = {
    0: "Понеділок",
    1: "Вівторок",
    2: "Середа",
    3: "Четвер",
    4: "Пʼятниця",
}

# Идеально точное расписание со скриншота группы К-311 (14 пар)
SCHEDULE_DATA = {
    0: [  # Понеділок (07 вересня)
        {
            "hour": 10, "minute": 40, "time": "10:40 - 11:55",
            "title": "Проектування автономних мереж (пр) — Литвин Д.Т.",
            "link": TEACHER_LINKS["литвин"][0], "service": TEACHER_LINKS["литвин"][1]
        },
        {
            "hour": 12, "minute": 20, "time": "12:20 - 13:35",
            "title": "Комп'ютерна графіка (л) — Букатов Д.В.",
            "link": TEACHER_LINKS["букатов"][0], "service": TEACHER_LINKS["букатов"][1]
        },
        {
            "hour": 13, "minute": 45, "time": "13:45 - 15:00",
            "title": "Інтернет речей та проектування розумного виробництва (л) — Захаренков Д.Ю.",
            "link": TEACHER_LINKS["захаренков"][0], "service": TEACHER_LINKS["захаренков"][1]
        },
    ],
    1: [  # Вівторок (08 вересня)
        {
            "hour": 9, "minute": 15, "time": "09:15 - 10:30",
            "title": "Комп'ютерна графіка (пр) — Литвин Д.Т.",
            "link": TEACHER_LINKS["литвин"][0], "service": TEACHER_LINKS["литвин"][1]
        },
        {
            "hour": 10, "minute": 40, "time": "10:40 - 11:55",
            "title": "Комп'ютерні мережі (л) — Левченко С.В.",
            "link": TEACHER_LINKS["левченко"][0], "service": TEACHER_LINKS["левченко"][1]
        },
    ],
    2: [  # Середа (09 вересня)
        {
            "hour": 9, "minute": 15, "time": "09:15 - 10:30",
            "title": "Об'єктно-орієнтоване програмування (л) — Яровий Р.О.",
            "link": TEACHER_LINKS["яровий"][0], "service": TEACHER_LINKS["яровий"][1]
        },
        {
            "hour": 10, "minute": 40, "time": "10:40 - 11:55",
            "title": "Розробка інтерактивного медіа (л) — Бойко М.М.",
            "link": TEACHER_LINKS["бойко"][0], "service": TEACHER_LINKS["бойко"][1]
        },
        {
            "hour": 12, "minute": 20, "time": "12:20 - 13:35",
            "title": "Комп'ютерні мережі (пр) — Литвин Д.Т.",
            "link": TEACHER_LINKS["литвин"][0], "service": TEACHER_LINKS["литвин"][1]
        },
    ],
    3: [  # Четвер (10 вересня)
        {
            "hour": 9, "minute": 15, "time": "09:15 - 10:30",
            "title": "ІТ та бізнес-аналітика (л) — Букатов Д.В.",
            "link": TEACHER_LINKS["букатов"][0], "service": TEACHER_LINKS["букатов"][1]
        },
        {
            "hour": 10, "minute": 40, "time": "10:40 - 11:55",
            "title": "Організація та адміністрування баз даних (л) — Гордієнко І.М.",
            "link": TEACHER_LINKS["гордієнко"][0], "service": TEACHER_LINKS["гордієнко"][1]
        },
        {
            "hour": 12, "minute": 20, "time": "12:20 - 13:35",
            "title": "Інтернет речей та проектування розумного виробництва (пр) — Захаренков Д.Ю.",
            "link": TEACHER_LINKS["захаренков"][0], "service": TEACHER_LINKS["захаренков"][1]
        },
    ],
    4: [  # Пʼятниця (11 вересня)
        {
            "hour": 9, "minute": 15, "time": "09:15 - 10:30",
            "title": "Організація та адміністрування баз даних (пр) — Довголуцький І.Р.",
            "link": TEACHER_LINKS["довголуцький"][0], "service": TEACHER_LINKS["довголуцький"][1]
        },
        {
            "hour": 10, "minute": 40, "time": "10:40 - 11:55",
            "title": "Проектування автономних мереж (л) — Подвиженко А.В.",
            "link": TEACHER_LINKS["подвиженко"][0], "service": TEACHER_LINKS["подвиженко"][1]
        },
        {
            "hour": 12, "minute": 20, "time": "12:20 - 13:35",
            "title": "Об'єктно-орієнтоване програмування (пр) — Довголуцький І.Р.",
            "link": TEACHER_LINKS["довголуцький"][0], "service": TEACHER_LINKS["довголуцький"][1]
        },
    ]
}

bot = telebot.TeleBot(BOT_TOKEN)
scheduler = BackgroundScheduler(timezone=pytz.timezone("Europe/Kyiv"))

def send_lesson_notification(title: str, link: str, service: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(text=f"🚀 Увійти в {service}", url=link))
    
    text = (
        "🚨 <b>УВАГА! ПАРА РОЗПОЧАЛАСЯ</b> 🚨\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📍 <b>Дисципліна:</b>\n<code>{html.escape(title)}</code>\n\n"
        f"🔗 <b>Платформа:</b> {service}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚡️ <i>Підключайся прямо зараз!</i>"
    )
    bot.send_message(
        chat_id=USER_CHAT_ID,
        text=text,
        parse_mode="HTML",
        reply_markup=kb
    )

def setup_scheduler():
    scheduler.remove_all_jobs()
    days_codes = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri"}
    for day_num, lessons in SCHEDULE_DATA.items():
        day_code = days_codes.get(day_num)
        for item in lessons:
            scheduler.add_job(
                send_lesson_notification,
                "cron",
                day_of_week=day_code,
                hour=item["hour"],
                minute=item["minute"],
                args=[item["title"], item["link"], item["service"]]
            )

@bot.message_handler(commands=["start"])
def cmd_start(message):
    start_text = (
        "🔥 <b>АСИСТЕНТ РОЗКЛАДУ ГРУПИ К-311</b> 🔥\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🚀 <b>Швидкі команди:</b>\n"
        "├ 🔴 /today — пари на сьогодні\n"
        "├ 🟠 /tomorrow — пари на завтра\n"
        "└ 🗓 /week — повний розклад на тиждень\n\n"
        "⏰ Розклад повністю налаштовано під офіційний графік!"
    )
    bot.reply_to(message, start_text, parse_mode="HTML")

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
    lessons = SCHEDULE_DATA.get(day_idx, [])
    if not lessons:
        text = f"🎉 <b>{day_name.upper()}</b> 🎉\n━━━━━━━━━━━━━━━━━━━━\n🌴 <i>Пар немає, відпочивай!</i>"
        bot.reply_to(message, text, parse_mode="HTML")
        return

    text = f"📍 <b>РОЗКЛАД: {day_name.upper()}</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    kb = types.InlineKeyboardMarkup()
    for item in lessons:
        escaped_title = html.escape(item["title"])
        service = item["service"]
        text += (
            f"⏰ <code>{item['time']}</code>\n"
            f"📌 <b>{escaped_title}</b>\n"
            f"🔗 Платформа: <i>{service}</i>\n"
            "──────────────────\n"
        )
        kb.add(types.InlineKeyboardButton(text=f"👉 {item['time']} • Увійти в {service}", url=item["link"]))

    bot.reply_to(message, text, parse_mode="HTML", reply_markup=kb)

@bot.message_handler(commands=["week"])
def cmd_week(message):
    for d_num in range(5):
        d_name = DAYS_MAP[d_num]
        lessons = SCHEDULE_DATA.get(d_num, [])
        
        text = f"🗓 <b>{d_name.upper()}</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        if not lessons:
            text += "🌴 <i>Пар немає</i>\n"
        else:
            for l in lessons:
                service = l["service"]
                escaped_title = html.escape(l["title"])
                text += f"⏰ <code>{l['time']}</code> ➔ <a href=\"{l['link']}\">{escaped_title}</a> [<b>{service}</b>]\n"
        
        bot.send_message(message.chat.id, text.strip(), parse_mode="HTML", disable_web_page_preview=True)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    threading.Thread(target=run_http_server, daemon=True).start()
    setup_scheduler()
    scheduler.start()
    bot.infinity_polling()
