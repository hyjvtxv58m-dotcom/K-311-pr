import html
import logging
import os
import re
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import pytz
import requests
import telebot
from telebot import types
from apscheduler.schedulers.background import BackgroundScheduler

BOT_TOKEN = "8814170419:AAHWiLDlZEJ0KXeQzU_hVmQckRlsB6wRi8w"
USER_CHAT_ID = 780458353
OCR_API_KEY = "K86575271388957"

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

# Каталог предметов
SUBJECTS_DB = [
    {
        "title": "Інтернет речей та проектування розумного виробництва",
        "keywords": ["інтернет", "речей", "виробництв", "розумн", "захаренков"],
        "teacher": "Захаренков Д.Ю.",
        "link": "https://us02web.zoom.us/j/6696841684?pwd=eHR3aWV5RTIrWTRFYnFaejlWeXhkUT09",
        "service": "Zoom"
    },
    {
        "title": "Організація та адміністрування баз даних",
        "keywords": ["гордієнко", "горд"],
        "teacher": "Гордієнко І.М.",
        "link": "https://us04web.zoom.us/j/71992214760?pwd=i6KR9LbQYZx97lthUIZN8whASUGdO4.1",
        "service": "Zoom"
    },
    {
        "title": "Організація та адміністрування баз даних",
        "keywords": ["довголуцький", "довгол"],
        "teacher": "Довголуцький І.Р.",
        "link": "https://meet.google.com/bse-espc-vhs",
        "service": "Meet"
    },
    {
        "title": "Проектування автономних мереж",
        "keywords": ["подвиженко", "подв"],
        "teacher": "Подвиженко А.В.",
        "link": "https://us02web.zoom.us/j/8110796424?pwd=Z9z6Xa7iRTX0wViW3xawnNEa2K2SaM.1",
        "service": "Zoom"
    },
    {
        "title": "Проектування автономних мереж",
        "keywords": ["автоном", "литвин"],
        "teacher": "Литвин Д.Т.",
        "link": "https://meet.google.com/ait-gnuz-oqo",
        "service": "Meet"
    },
    {
        "title": "Комп'ютерна графіка",
        "keywords": ["букатов"],
        "teacher": "Букатов Д.В.",
        "link": "https://us04web.zoom.us/j/6128385015?pwd=VqXYvANnVG11TCp_xzdzOGtRwnQmzk.1",
        "service": "Zoom"
    },
    {
        "title": "Комп'ютерна графіка",
        "keywords": ["графік", "литвин"],
        "teacher": "Литвин Д.Т.",
        "link": "https://meet.google.com/ait-gnuz-oqo",
        "service": "Meet"
    },
    {
        "title": "Розробка інтерактивного медіа",
        "keywords": ["інтерактив", "медіа", "бойко"],
        "teacher": "Бойко М.М.",
        "link": "https://us02web.zoom.us/j/81133607854?pwd=QwF1BB1kaeZxdI4jVhWa8gOgA9KLVC.1",
        "service": "Zoom"
    },
    {
        "title": "ІТ та бізнес-аналітика",
        "keywords": ["аналітик", "бізнес", "іт та"],
        "teacher": "Букатов Д.В.",
        "link": "https://us04web.zoom.us/j/6128385015?pwd=VqXYvANnVG11TCp_xzdzOGtRwnQmzk.1",
        "service": "Zoom"
    },
    {
        "title": "Об'єктно-орієнтоване програмування",
        "keywords": ["яровий", "яров"],
        "teacher": "Яровий Р.О.",
        "link": "https://us02web.zoom.us/j/2589993020?pwd=bU9RUk50TVk5TDJxL1lvbXoxNmtrQT09",
        "service": "Zoom"
    },
    {
        "title": "Комп'ютерні мережі",
        "keywords": ["левченко"],
        "teacher": "Левченко С.В.",
        "link": "https://us02web.zoom.us/j/4717138521?pwd=eFI0SEdMN3NxQkNBWGlMNVl3WjB5Zz09",
        "service": "Zoom"
    },
    {
        "title": "Комп'ютерні мережі",
        "keywords": ["мережі", "литвин"],
        "teacher": "Литвин Д.Т.",
        "link": "https://meet.google.com/ait-gnuz-oqo",
        "service": "Meet"
    }
]

DAYS_MAP = {
    0: "Понеділок",
    1: "Вівторок",
    2: "Середа",
    3: "Четвер",
    4: "Пʼятниця",
}

# Шаблоны звонков для каждого дня в твоем расписании:
# Пн: 2, 3, 4 пары (с 10:40)
# Вт: 1, 2 пары (с 09:15)
# Ср: 1, 2, 3 пары
# Чт: 1, 2, 3 пары
# Пт: 1, 2, 3 пары
DAY_SLOTS = {
    0: [
        {"hour": 10, "minute": 40, "time": "10:40 - 11:55"},
        {"hour": 12, "minute": 20, "time": "12:20 - 13:35"},
        {"hour": 13, "minute": 45, "time": "13:45 - 15:00"},
    ],
    1: [
        {"hour": 9,  "minute": 15, "time": "09:15 - 10:30"},
        {"hour": 10, "minute": 40, "time": "10:40 - 11:55"},
    ],
    2: [
        {"hour": 9,  "minute": 15, "time": "09:15 - 10:30"},
        {"hour": 10, "minute": 40, "time": "10:40 - 11:55"},
        {"hour": 12, "minute": 20, "time": "12:20 - 13:35"},
    ],
    3: [
        {"hour": 9,  "minute": 15, "time": "09:15 - 10:30"},
        {"hour": 10, "minute": 40, "time": "10:40 - 11:55"},
        {"hour": 12, "minute": 20, "time": "12:20 - 13:35"},
    ],
    4: [
        {"hour": 9,  "minute": 15, "time": "09:15 - 10:30"},
        {"hour": 10, "minute": 40, "time": "10:40 - 11:55"},
        {"hour": 12, "minute": 20, "time": "12:20 - 13:35"},
    ]
}

SCHEDULE_DATA = {
    0: [
        {"hour": 10, "minute": 40, "time": "10:40 - 11:55", "title": "Проектування автономних мереж (пр) — Литвин Д.Т.", "link": "https://meet.google.com/ait-gnuz-oqo", "service": "Meet"},
        {"hour": 12, "minute": 20, "time": "12:20 - 13:35", "title": "Комп'ютерна графіка (л) — Букатов Д.В.", "link": "https://us04web.zoom.us/j/6128385015?pwd=VqXYvANnVG11TCp_xzdzOGtRwnQmzk.1", "service": "Zoom"},
        {"hour": 13, "minute": 45, "time": "13:45 - 15:00", "title": "Інтернет речей та проектування розумного виробництва (л) — Захаренков Д.Ю.", "link": "https://us02web.zoom.us/j/6696841684?pwd=eHR3aWV5RTIrWTRFYnFaejlWeXhkUT09", "service": "Zoom"},
    ],
    1: [
        {"hour": 9,  "minute": 15, "time": "09:15 - 10:30", "title": "Комп'ютерна графіка (пр) — Литвин Д.Т.", "link": "https://meet.google.com/ait-gnuz-oqo", "service": "Meet"},
        {"hour": 10, "minute": 40, "time": "10:40 - 11:55", "title": "Комп'ютерні мережі (л) — Левченко С.В.", "link": "https://us02web.zoom.us/j/4717138521?pwd=eFI0SEdMN3NxQkNBWGlMNVl3WjB5Zz09", "service": "Zoom"},
    ],
    2: [
        {"hour": 9,  "minute": 15, "time": "09:15 - 10:30", "title": "Об'єктно-орієнтоване програмування (л) — Яровий Р.О.", "link": "https://us02web.zoom.us/j/2589993020?pwd=bU9RUk50TVk5TDJxL1lvbXoxNmtrQT09", "service": "Zoom"},
        {"hour": 10, "minute": 40, "time": "10:40 - 11:55", "title": "Розробка інтерактивного медіа (л) — Бойко М.М.", "link": "https://us02web.zoom.us/j/81133607854?pwd=QwF1BB1kaeZxdI4jVhWa8gOgA9KLVC.1", "service": "Zoom"},
        {"hour": 12, "minute": 20, "time": "12:20 - 13:35", "title": "Комп'ютерні мережі (пр) — Литвин Д.Т.", "link": "https://meet.google.com/ait-gnuz-oqo", "service": "Meet"},
    ],
    3: [
        {"hour": 9,  "minute": 15, "time": "09:15 - 10:30", "title": "ІТ та бізнес-аналітика (л) — Букатов Д.В.", "link": "https://us04web.zoom.us/j/6128385015?pwd=VqXYvANnVG11TCp_xzdzOGtRwnQmzk.1", "service": "Zoom"},
        {"hour": 10, "minute": 40, "time": "10:40 - 11:55", "title": "Організація та адміністрування баз даних (л) — Гордієнко І.М.", "link": "https://us04web.zoom.us/j/71992214760?pwd=i6KR9LbQYZx97lthUIZN8whASUGdO4.1", "service": "Zoom"},
        {"hour": 12, "minute": 20, "time": "12:20 - 13:35", "title": "Інтернет речей та проектування розумного виробництва (л) — Захаренков Д.Ю.", "link": "https://us02web.zoom.us/j/6696841684?pwd=eHR3aWV5RTIrWTRFYnFaejlWeXhkUT09", "service": "Zoom"},
    ],
    4: [
        {"hour": 9,  "minute": 15, "time": "09:15 - 10:30", "title": "Організація та адміністрування баз даних (пр) — Довголуцький І.Р.", "link": "https://meet.google.com/bse-espc-vhs", "service": "Meet"},
        {"hour": 10, "minute": 40, "time": "10:40 - 11:55", "title": "Проектування автономних мереж (л) — Подвиженко А.В.", "link": "https://us02web.zoom.us/j/8110796424?pwd=Z9z6Xa7iRTX0wViW3xawnNEa2K2SaM.1", "service": "Zoom"},
        {"hour": 12, "minute": 20, "time": "12:20 - 13:35", "title": "Об'єктно-орієнтоване програмування (пр) — Довголуцький І.Р.", "link": "https://meet.google.com/bse-espc-vhs", "service": "Meet"},
    ]
}

bot = telebot.TeleBot(BOT_TOKEN)
scheduler = BackgroundScheduler(timezone=pytz.timezone("Europe/Kyiv"))

def match_subject_from_raw(line: str):
    txt = line.lower()
    best_item = None
    max_score = 0
    
    for item in SUBJECTS_DB:
        score = sum(1 for kw in item["keywords"] if kw in txt)
        if score > max_score:
            max_score = score
            best_item = item

    if best_item and max_score > 0:
        l_type = "пр" if ("пр" in txt or "практ" in txt) else "л"
        full_title = f"{best_item['title']} ({l_type}) — {best_item['teacher']}"
        return {
            "title": full_title,
            "link": best_item["link"],
            "service": best_item["service"]
        }
    return None

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

def parse_and_update(message, file_id):
    temp_msg = bot.reply_to(message, "⏳ <b>Оновлюю розклад...</b>", parse_mode="HTML")
    try:
        f_info = bot.get_file(file_id)
        img_bytes = requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{f_info.file_path}").content

        try:
            bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        except Exception:
            pass

        res = requests.post(
            "https://api.ocr.space/parse/image",
            files={"file": ("img.jpg", img_bytes)},
            data={"apikey": OCR_API_KEY, "language": "auto", "isTable": True, "OCREngine": 2},
            timeout=50
        ).json()

        try:
            bot.delete_message(chat_id=message.chat.id, message_id=temp_msg.message_id)
        except Exception:
            pass

        if res.get("IsErroredOnProcessing"):
            bot.send_message(message.chat.id, f"❌ Помилка OCR: {res.get('ErrorMessage')}")
            return

        text = res["ParsedResults"][0]["ParsedText"]
        raw_lines = [l.strip() for l in text.splitlines() if l.strip()]

        # Разрешаем повторы дисциплин (не удаляем одинаковые предметы)
        found_pairs = []
        for line in raw_lines:
            matched = match_subject_from_raw(line)
            if matched:
                found_pairs.append(matched)

        if not found_pairs:
            bot.send_message(message.chat.id, "⚠️ Пари не розпізнано. Спробуй надіслати скріншот як фото без стиснення.")
            return

        # Раскладываем по дням с учётом правильных слотов (Пн с 10:40, Вт 2 пары, остальные по 3)
        idx = 0
        for day_i in range(5):
            SCHEDULE_DATA[day_i] = []
            slots = DAY_SLOTS[day_i]
            for slot in slots:
                if idx < len(found_pairs):
                    pair = found_pairs[idx]
                    SCHEDULE_DATA[day_i].append({
                        "hour": slot["hour"],
                        "minute": slot["minute"],
                        "time": slot["time"],
                        "title": pair["title"],
                        "link": pair["link"],
                        "service": pair["service"]
                    })
                    idx += 1

        setup_scheduler()

        bot.send_message(
            message.chat.id,
            f"✨ <b>РОЗКЛАД ОНОВЛЕНО!</b> ✨\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 <b>Розпізнано пар:</b> <code>{len(found_pairs)}</code> із 14\n"
            f"🔔 Нагадування налаштовано під офіційний розклад.\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Переглянути: /week",
            parse_mode="HTML"
        )

    except Exception as e:
        try:
            bot.delete_message(chat_id=message.chat.id, message_id=temp_msg.message_id)
        except Exception:
            pass
        bot.send_message(message.chat.id, f"❌ Помилка: {e}")

@bot.message_handler(content_types=["photo"])
def on_photo(message):
    if message.chat.id == USER_CHAT_ID:
        parse_and_update(message, message.photo[-1].file_id)

@bot.message_handler(content_types=["document"])
def on_doc(message):
    if message.chat.id == USER_CHAT_ID:
        parse_and_update(message, message.document.file_id)

@bot.message_handler(commands=["start"])
def cmd_start(message):
    start_text = (
        "🔥 <b>АСИСТЕНТ РОЗКЛАДУ ГРУПИ К-311</b> 🔥\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🚀 <b>Команди:</b>\n"
        "├ 🔴 /today — пари на сьогодні\n"
        "├ 🟠 /tomorrow — пари на завтра\n"
        "└ 🗓 /week — весь тиждень з кнопками входу\n\n"
        "📸 <b>Оновлення:</b> надішли сюди скріншот або фото розкладу раз на тиждень!"
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
        text = f"🎉 <b>{day_name.upper()}</b> 🎉\n━━━━━━━━━━━━━━━━━━━━\n🌴 <i>Пар немає, можна відпочивати!</i>"
        bot.reply_to(message, text, parse_mode="HTML")
        return

    text = f"📍 <b>РОЗКЛАД: {day_name.upper()}</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    kb = types.InlineKeyboardMarkup()
    for item in lessons:
        escaped_title = html.escape(item["title"])
        service = item.get("service", "Meet")
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
                service = l.get("service", "Meet")
                escaped_title = html.escape(l["title"])
                text += f"⏰ <code>{l['time']}</code> ➔ <a href=\"{l['link']}\">{escaped_title}</a> [<b>{service}</b>]\n"
        
        bot.send_message(message.chat.id, text.strip(), parse_mode="HTML", disable_web_page_preview=True)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    threading.Thread(target=run_http_server, daemon=True).start()
    setup_scheduler()
    scheduler.start()
    bot.infinity_polling()
