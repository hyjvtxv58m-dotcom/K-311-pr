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

TEACHER_CATALOG = {
    "литвин": {
        "subject": "Комп'ютерні мережі",
        "name": "Литвин Д.Т.",
        "link": "https://meet.google.com/ait-gnuz-oqo"
    },
    "букатов": {
        "subject": "Комп'ютерна графіка / IT-аналітика",
        "name": "Букатов Д.В.",
        "link": "https://us04web.zoom.us/j/6128385015?pwd=VqXYvANnVG11TCp_xzdzOGtRwnQmzk.1"
    },
    "захаренков": {
        "subject": "Інтернет речей та розумне виробництво",
        "name": "Захаренков Д.Ю.",
        "link": "https://us02web.zoom.us/j/6696841684?pwd=eHR3aWV5RTIrWTRFYnFaejlWeXhkUT09"
    },
    "левченко": {
        "subject": "Комп'ютерні мережі",
        "name": "Левченко С.В.",
        "link": "https://us02web.zoom.us/j/4717138521?pwd=eFI0SEdMN3NxQkNBWGlMNVl3WjB5Zz09"
    },
    "яровий": {
        "subject": "Об'єктно-орієнтоване програмування",
        "name": "Яровий Р.О.",
        "link": "https://us02web.zoom.us/j/2589993020?pwd=bU9RUk50TVk5TDJxL1lvbXoxNmtrQT09"
    },
    "бойко": {
        "subject": "Розробка інтерактивного медіа",
        "name": "Бойко М.М.",
        "link": "https://us02web.zoom.us/j/81133607854?pwd=QwF1BB1kaeZxdI4jVhWa8gOgA9KLVC.1"
    },
    "гордієнко": {
        "subject": "Організація та адміністрування БД",
        "name": "Гордієнко І.М.",
        "link": "https://us04web.zoom.us/j/71992214760?pwd=i6KR9LbQYZx97lthUIZN8whASUGdO4.1"
    },
    "довголуцький": {
        "subject": "ООП / Адміністрування БД",
        "name": "Довголуцький І.Р.",
        "link": "https://meet.google.com/bse-espc-vhs"
    },
    "подвиженко": {
        "subject": "Проектування автономних мереж",
        "name": "Подвиженко А.В.",
        "link": "https://us02web.zoom.us/j/8110796424?pwd=Z9z6Xa7iRTX0wViW3xawnNEa2K2SaM.1"
    }
}

DEFAULT_MEET = "https://meet.google.com/"

DAYS_MAP = {
    0: "Понеділок",
    1: "Вівторок",
    2: "Середа",
    3: "Четвер",
    4: "Пʼятниця",
}

CALL_TIMES = [
    {"hour": 9, "minute": 15, "time": "09:15 - 10:30"},
    {"hour": 10, "minute": 40, "time": "10:40 - 11:55"},
    {"hour": 12, "minute": 20, "time": "12:20 - 13:35"},
    {"hour": 13, "minute": 45, "time": "13:45 - 15:00"},
]

SCHEDULE_DATA = {
    0: [
        {"hour": 10, "minute": 40, "time": "10:40 - 11:55", "title": "Проектування автономних мереж (пр) — Литвин Д.Т."},
        {"hour": 12, "minute": 20, "time": "12:20 - 13:35", "title": "Комп'ютерна графіка (л) — Букатов Д.В."},
        {"hour": 13, "minute": 45, "time": "13:45 - 15:00", "title": "Інтернет речей та розумне виробництво (л) — Захаренков Д.Ю."},
    ],
    1: [
        {"hour": 9,  "minute": 15, "time": "09:15 - 10:30", "title": "Комп'ютерна графіка (пр) — Литвин Д.Т."},
        {"hour": 10, "minute": 40, "time": "10:40 - 11:55", "title": "Комп'ютерні мережі (л) — Левченко С.В."},
    ],
    2: [
        {"hour": 9,  "minute": 15, "time": "09:15 - 10:30", "title": "Об'єктно-орієнтоване програмування (л) — Яровий Р.О."},
        {"hour": 10, "minute": 40, "time": "10:40 - 11:55", "title": "Розробка інтерактивного медіа (л) — Бойко М.М."},
        {"hour": 12, "minute": 20, "time": "12:20 - 13:35", "title": "Комп'ютерні мережі (пр) — Литвин Д.Т."},
    ],
    3: [
        {"hour": 9,  "minute": 15, "time": "09:15 - 10:30", "title": "ІТ та бізнес-аналітика (л) — Букатов Д.В."},
        {"hour": 10, "minute": 40, "time": "10:40 - 11:55", "title": "Організація та адміністрування БД (л) — Гордієнко І.М."},
        {"hour": 12, "minute": 20, "time": "12:20 - 13:35", "title": "Інтернет речей та розумне виробництво (л) — Захаренков Д.Ю."},
    ],
    4: [
        {"hour": 9,  "minute": 15, "time": "09:15 - 10:30", "title": "Організація та адміністрування БД (пр) — Довголуцький І.Р."},
        {"hour": 10, "minute": 40, "time": "10:40 - 11:55", "title": "Проектування автономних мереж (л) — Подвиженко А.В."},
        {"hour": 12, "minute": 20, "time": "12:20 - 13:35", "title": "Об'єктно-орієнтоване програмування (пр) — Довголуцький І.Р."},
    ]
}

bot = telebot.TeleBot(BOT_TOKEN)
scheduler = BackgroundScheduler(timezone=pytz.timezone("Europe/Kyiv"))

def build_clean_lesson_title(raw_text: str) -> str:
    text_lower = raw_text.lower()
    
    matched_key = None
    for key in TEACHER_CATALOG.keys():
        if key in text_lower:
            matched_key = key
            break
            
    if not matched_key:
        if "мереж" in text_lower or "автоном" in text_lower:
            matched_key = "подвиженко" if "подв" in text_lower else "литвин"
        elif "граф" in text_lower:
            matched_key = "букатов"
        elif "речей" in text_lower or "виробн" in text_lower:
            matched_key = "захаренков"
        elif "медіа" in text_lower or "інтеракт" in text_lower:
            matched_key = "бойко"
        elif "ооп" in text_lower or "програм" in text_lower:
            matched_key = "яровий" if "яров" in text_lower else "довголуцький"
        elif "баз" in text_lower or "бд" in text_lower:
            matched_key = "гордієнко" if "горд" in text_lower else "довголуцький"

    if not matched_key:
        cleaned = re.sub(r"^\s*\d{1,2}[:.]\d{2}\s*[-–]\s*\d{1,2}[:.]\d{2}\s*", "", raw_text)
        return cleaned.strip()

    info = TEACHER_CATALOG[matched_key]
    lesson_type = "пр" if ("пр" in text_lower or "практ" in text_lower) else "л"
    
    subject = info["subject"]
    if matched_key == "литвин":
        if "граф" in text_lower:
            subject = "Комп'ютерна графіка"
        elif "мереж" in text_lower or "автоном" in text_lower:
            subject = "Проектування автономних мереж"
    elif matched_key == "довголуцький":
        if "бд" in text_lower or "баз" in text_lower:
            subject = "Організація та адміністрування БД"
        else:
            subject = "Об'єктно-орієнтоване програмування"

    return f"{subject} ({lesson_type}) — {info['name']}"

def get_link_for_lesson(lesson_text: str) -> str:
    text_lower = str(lesson_text).lower()
    for key, data in TEACHER_CATALOG.items():
        if key in text_lower:
            return data["link"]
    return DEFAULT_MEET

def send_lesson_notification(title: str, link: str):
    clean = build_clean_lesson_title(title)
    service = "Google Meet" if "meet.google" in link else "Zoom"
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(text=f"🚀 Увійти в {service}", url=link))
    
    text = (
        "🚨 <b>УВАГА! ПАРА РОЗПОЧАЛАСЯ</b> 🚨\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📍 <b>Дисципліна:</b>\n<code>{html.escape(clean)}</code>\n\n"
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
            link = get_link_for_lesson(item["title"])
            scheduler.add_job(
                send_lesson_notification,
                "cron",
                day_of_week=day_code,
                hour=item["hour"],
                minute=item["minute"],
                args=[item["title"], link]
            )

def process_schedule_image(message, file_id):
    temp_msg = bot.reply_to(message, "⏳ <b>Сканую високу точність розкладу...</b>", parse_mode="HTML")

    try:
        file_info = bot.get_file(file_id)
        tg_file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        img_data = requests.get(tg_file_url).content

        try:
            bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        except Exception:
            pass

        ocr_res = requests.post(
            "https://api.ocr.space/parse/image",
            files={"file": ("schedule.jpg", img_data)},
            data={
                "apikey": OCR_API_KEY,
                "language": "auto",
                "isTable": True,
                "scale": True,
                "detectOrientation": True,
                "OCREngine": 1
            },
            timeout=50
        ).json()

        try:
            bot.delete_message(chat_id=message.chat.id, message_id=temp_msg.message_id)
        except Exception:
            pass

        if ocr_res.get("IsErroredOnProcessing"):
            bot.send_message(message.chat.id, f"❌ <b>Помилка OCR:</b> <code>{ocr_res.get('ErrorMessage')}</code>", parse_mode="HTML")
            return

        parsed_text = ocr_res["ParsedResults"][0]["ParsedText"]
        lines = [line.strip() for line in parsed_text.splitlines() if line.strip()]

        found_pairs = []
        keywords = list(TEACHER_CATALOG.keys()) + ["мереж", "графік", "речей", "медіа", "програм", "баз дан", "аналіт"]
        
        for line in lines:
            line_lower = line.lower()
            if any(k in line_lower for k in keywords):
                if not any(d in line_lower for d in ["понеділок", "вівторок", "середа", "четвер", "п'ятниця", "спеціальність"]):
                    cleaned_line = build_clean_lesson_title(line)
                    if cleaned_line and cleaned_line not in found_pairs:
                        found_pairs.append(cleaned_line)

        if not found_pairs:
            bot.send_message(message.chat.id, "⚠️ <b>Пари не знайдено!</b>\nСпробуй надіслати скріншот як <b>файл (без стиснення)</b>.", parse_mode="HTML")
            return

        pair_idx = 0
        for day_idx in range(5):
            SCHEDULE_DATA[day_idx] = []
            slot_count = 3 if day_idx in [0, 2, 3, 4] else 2
            for slot in CALL_TIMES[:slot_count]:
                if pair_idx < len(found_pairs):
                    SCHEDULE_DATA[day_idx].append({
                        "hour": slot["hour"],
                        "minute": slot["minute"],
                        "time": slot["time"],
                        "title": found_pairs[pair_idx]
                    })
                    pair_idx += 1

        setup_scheduler()
        
        success_text = (
            "✨ <b>РОЗКЛАД УСПІШНО ОНОВЛЕНО!</b> ✨\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 <b>Знайдено пар:</b> <code>{len(found_pairs)}</code>\n"
            "🔔 <b>Автонагадування:</b> Активовано ✅\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📌 Натисни /week або /today, щоб переглянути."
        )
        bot.send_message(message.chat.id, success_text, parse_mode="HTML")

    except Exception as e:
        try:
            bot.delete_message(chat_id=message.chat.id, message_id=temp_msg.message_id)
        except Exception:
            pass
        bot.send_message(message.chat.id, f"❌ <b>Помилка:</b> <code>{e}</code>", parse_mode="HTML")

@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    if message.chat.id == USER_CHAT_ID:
        process_schedule_image(message, message.photo[-1].file_id)

@bot.message_handler(content_types=["document"])
def handle_document(message):
    if message.chat.id == USER_CHAT_ID:
        if message.document.mime_type and message.document.mime_type.startswith("image/"):
            process_schedule_image(message, message.document.file_id)
        else:
            bot.reply_to(message, "⚠️ Надішли зображення (jpg/png) як файл без стиснення.")

@bot.message_handler(commands=["start"])
def cmd_start(message):
    start_text = (
        "🔥 <b>АСИСТЕНТ РОЗКЛАДУ ГРУПИ К-311</b> 🔥\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🚀 <b>Швидкі команди:</b>\n"
        "├ 🔴 /today — пари на сьогодні\n"
        "├ 🟠 /tomorrow — пари на завтра\n"
        "└ 🗓 /week — повний тиждень з посиланнями\n\n"
        "📸 <b>Оновлення розкладу:</b>\n"
        "Надішли скріншот або <b>файл без стиснення</b> сюди в чат!\n"
        "━━━━━━━━━━━━━━━━━━━━"
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
        clean_title = item["title"]
        link = get_link_for_lesson(clean_title)
        service = "Meet" if "meet.google" in link else "Zoom"
        
        text += (
            f"⏰ <code>{item['time']}</code>\n"
            f"📌 <b>{clean_title}</b>\n"
            f"🔗 Платформа: <i>{service}</i>\n"
            "──────────────────\n"
        )
        kb.add(types.InlineKeyboardButton(text=f"👉 {item['time']} • Увійти в {service}", url=link))

    bot.reply_to(message, text, reply_markup=kb)

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
                clean_title = l["title"]
                link = get_link_for_lesson(clean_title)
                service = "Meet" if "meet.google" in link else "Zoom"
                escaped_title = html.escape(clean_title)
                text += f"⏰ <code>{l['time']}</code> ➔ <a href=\"{link}\">{escaped_title}</a> [<b>{service}</b>]\n"
        
        bot.send_message(message.chat.id, text.strip(), parse_mode="HTML", disable_web_page_preview=True)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    threading.Thread(target=run_http_server, daemon=True).start()
    setup_scheduler()
    scheduler.start()
    bot.infinity_polling()
