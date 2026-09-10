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

# Каталог преподавателей и ссылок
TEACHERS = {
    "литвин": {
        "name": "Литвин Д.Т.",
        "link": "https://meet.google.com/ait-gnuz-oqo",
        "service": "Meet",
        "default_subject": "Комп'ютерна графіка"
    },
    "букатов": {
        "name": "Букатов Д.В.",
        "link": "https://us04web.zoom.us/j/6128385015?pwd=VqXYvANnVG11TCp_xzdzOGtRwnQmzk.1",
        "service": "Zoom",
        "default_subject": "Комп'ютерна графіка"
    },
    "захаренков": {
        "name": "Захаренков Д.Ю.",
        "link": "https://us02web.zoom.us/j/6696841684?pwd=eHR3aWV5RTIrWTRFYnFaejlWeXhkUT09",
        "service": "Zoom",
        "default_subject": "Інтернет речей та проектування розумного виробництва"
    },
    "левченко": {
        "name": "Левченко С.В.",
        "link": "https://us02web.zoom.us/j/4717138521?pwd=eFI0SEdMN3NxQkNBWGlMNVl3WjB5Zz09",
        "service": "Zoom",
        "default_subject": "Комп'ютерні мережі"
    },
    "яровий": {
        "name": "Яровий Р.О.",
        "link": "https://us02web.zoom.us/j/2589993020?pwd=bU9RUk50TVk5TDJxL1lvbXoxNmtrQT09",
        "service": "Zoom",
        "default_subject": "Об'єктно-орієнтоване програмування"
    },
    "бойко": {
        "name": "Бойко М.М.",
        "link": "https://us02web.zoom.us/j/81133607854?pwd=QwF1BB1kaeZxdI4jVhWa8gOgA9KLVC.1",
        "service": "Zoom",
        "default_subject": "Розробка інтерактивного медіа"
    },
    "гордієнко": {
        "name": "Гордієнко І.М.",
        "link": "https://us04web.zoom.us/j/71992214760?pwd=i6KR9LbQYZx97lthUIZN8whASUGdO4.1",
        "service": "Zoom",
        "default_subject": "Організація та адміністрування баз даних"
    },
    "довголуцький": {
        "name": "Довголуцький І.Р.",
        "link": "https://meet.google.com/bse-espc-vhs",
        "service": "Meet",
        "default_subject": "Об'єктно-орієнтоване програмування"
    },
    "подвиженко": {
        "name": "Подвиженко А.В.",
        "link": "https://us02web.zoom.us/j/8110796424?pwd=Z9z6Xa7iRTX0wViW3xawnNEa2K2SaM.1",
        "service": "Zoom",
        "default_subject": "Проектування автономних мереж"
    }
}

DAYS_MAP = {
    0: "Понеділок",
    1: "Вівторок",
    2: "Середа",
    3: "Четвер",
    4: "Пʼятниця",
}

# Сетка звонков по дням для группы К-311
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

# Текущее расписание по умолчанию
SCHEDULE_DATA = {
    0: [
        {"hour": 10, "minute": 40, "time": "10:40 - 11:55", "title": "Проектування автономних мереж (пр) — Литвин Д.Т.", "link": TEACHERS["литвин"]["link"], "service": TEACHERS["литвин"]["service"]},
        {"hour": 12, "minute": 20, "time": "12:20 - 13:35", "title": "Комп'ютерна графіка (л) — Букатов Д.В.", "link": TEACHERS["букатов"]["link"], "service": TEACHERS["букатов"]["service"]},
        {"hour": 13, "minute": 45, "time": "13:45 - 15:00", "title": "Інтернет речей та проектування розумного виробництва (л) — Захаренков Д.Ю.", "link": TEACHERS["захаренков"]["link"], "service": TEACHERS["захаренков"]["service"]},
    ],
    1: [
        {"hour": 9,  "minute": 15, "time": "09:15 - 10:30", "title": "Комп'ютерна графіка (пр) — Литвин Д.Т.", "link": TEACHERS["литвин"]["link"], "service": TEACHERS["литвин"]["service"]},
        {"hour": 10, "minute": 40, "time": "10:40 - 11:55", "title": "Комп'ютерні мережі (л) — Левченко С.В.", "link": TEACHERS["левченко"]["link"], "service": TEACHERS["левченко"]["service"]},
    ],
    2: [
        {"hour": 9,  "minute": 15, "time": "09:15 - 10:30", "title": "Об'єктно-орієнтоване програмування (л) — Яровий Р.О.", "link": TEACHERS["яровий"]["link"], "service": TEACHERS["яровий"]["service"]},
        {"hour": 10, "minute": 40, "time": "10:40 - 11:55", "title": "Розробка інтерактивного медіа (л) — Бойко М.М.", "link": TEACHERS["бойко"]["link"], "service": TEACHERS["бойко"]["service"]},
        {"hour": 12, "minute": 20, "time": "12:20 - 13:35", "title": "Комп'ютерні мережі (пр) — Литвин Д.Т.", "link": TEACHERS["литвин"]["link"], "service": TEACHERS["литвин"]["service"]},
    ],
    3: [
        {"hour": 9,  "minute": 15, "time": "09:15 - 10:30", "title": "ІТ та бізнес-аналітика (л) — Букатов Д.В.", "link": TEACHERS["букатов"]["link"], "service": TEACHERS["букатов"]["service"]},
        {"hour": 10, "minute": 40, "time": "10:40 - 11:55", "title": "Організація та адміністрування баз даних (л) — Гордієнко І.М.", "link": TEACHERS["гордієнко"]["link"], "service": TEACHERS["гордієнко"]["service"]},
        {"hour": 12, "minute": 20, "time": "12:20 - 13:35", "title": "Інтернет речей та проектування розумного виробництва (пр) — Захаренков Д.Ю.", "link": TEACHERS["захаренков"]["link"], "service": TEACHERS["захаренков"]["service"]},
    ],
    4: [
        {"hour": 9,  "minute": 15, "time": "09:15 - 10:30", "title": "Організація та адміністрування баз даних (пр) — Довголуцький І.Р.", "link": TEACHERS["довголуцький"]["link"], "service": TEACHERS["довголуцький"]["service"]},
        {"hour": 10, "minute": 40, "time": "10:40 - 11:55", "title": "Проектування автономних мереж (л) — Подвиженко А.В.", "link": TEACHERS["подвиженко"]["link"], "service": TEACHERS["подвиженко"]["service"]},
        {"hour": 12, "minute": 20, "time": "12:20 - 13:35", "title": "Об'єктно-орієнтоване програмування (пр) — Довголуцький І.Р.", "link": TEACHERS["довголуцький"]["link"], "service": TEACHERS["довголуцький"]["service"]},
    ]
}

bot = telebot.TeleBot(BOT_TOKEN)
scheduler = BackgroundScheduler(timezone=pytz.timezone("Europe/Kyiv"))

def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_now = types.KeyboardButton("🔴 Зараз йде")
    btn_today = types.KeyboardButton("🟡 Сьогодні")
    btn_tomorrow = types.KeyboardButton("🟠 Завтра")
    btn_week = types.KeyboardButton("🗓 Весь тиждень")
    btn_upload = types.KeyboardButton("📸 Оновити розклад (фото)")
    markup.add(btn_now)
    markup.add(btn_today, btn_tomorrow)
    markup.add(btn_week)
    markup.add(btn_upload)
    return markup

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

def identify_lesson_details(block_text: str, teacher_key: str):
    txt = block_text.lower()
    t_info = TEACHERS[teacher_key]
    
    # Определяем предмет с учетом специфики преподавателей
    subject = t_info["default_subject"]
    if teacher_key == "литвин":
        if "автоном" in txt:
            subject = "Проектування автономних мереж"
        elif "мереж" in txt:
            subject = "Комп'ютерні мережі"
        elif "граф" in txt:
            subject = "Комп'ютерна графіка"
    elif teacher_key == "букатов":
        if "аналіт" in txt or "бізнес" in txt:
            subject = "ІТ та бізнес-аналітика"
        else:
            subject = "Комп'ютерна графіка"
    elif teacher_key == "довголуцький":
        if "баз" in txt or "бд" in txt:
            subject = "Організація та адміністрування баз даних"
        else:
            subject = "Об'єктно-орієнтоване програмування"

    l_type = "пр" if ("пр" in txt or "практ" in txt) else "л"
    title = f"{subject} ({l_type}) — {t_info['name']}"
    return {
        "title": title,
        "link": t_info["link"],
        "service": t_info["service"]
    }

def parse_and_update(message, file_id):
    temp_msg = bot.reply_to(message, "⏳ <b>Аналізую розклад зі скріншота...</b>", parse_mode="HTML")
    try:
        f_info = bot.get_file(file_id)
        img_bytes = requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{f_info.file_path}").content

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
            bot.send_message(message.chat.id, f"❌ Помилка OCR: {res.get('ErrorMessage')}", reply_markup=get_main_keyboard())
            return

        text = res["ParsedResults"][0]["ParsedText"]
        lines = [l.strip() for l in text.splitlines() if l.strip()]

        # Находим каждую пару строго по фамилии преподавателя в строках
        found_lessons = []
        for i, line in enumerate(lines):
            line_lower = line.lower()
            for t_key in TEACHERS.keys():
                if t_key in line_lower:
                    # Берем контекст: саму строку и строку выше (где обычно название предмета)
                    context = (lines[i-1] + " " + line) if i > 0 else line
                    lesson_obj = identify_lesson_details(context, t_key)
                    found_lessons.append(lesson_obj)
                    break

        if not found_lessons:
            bot.send_message(message.chat.id, "⚠️ Пари не вдалося розпізнати. Переконайся, що скріншот чіткий.", reply_markup=get_main_keyboard())
            return

        # Раскладываем пары по дням недели
        idx = 0
        total_assigned = 0
        for day_i in range(5):
            SCHEDULE_DATA[day_i] = []
            slots = DAY_SLOTS[day_i]
            for slot in slots:
                if idx < len(found_lessons):
                    l_data = found_lessons[idx]
                    SCHEDULE_DATA[day_i].append({
                        "hour": slot["hour"],
                        "minute": slot["minute"],
                        "time": slot["time"],
                        "title": l_data["title"],
                        "link": l_data["link"],
                        "service": l_data["service"]
                    })
                    idx += 1
                    total_assigned += 1

        setup_scheduler()

        bot.send_message(
            message.chat.id,
            f"✨ <b>РОЗКЛАД ОНОВЛЕНО З ФОТО!</b> ✨\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 <b>Знайдено пар:</b> <code>{total_assigned}</code>\n"
            f"🔔 Нагадування переналаштовано.\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Натисни <b>🗓 Весь тиждень</b> або <b>🔴 Зараз йде</b>!",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )

    except Exception as e:
        try:
            bot.delete_message(chat_id=message.chat.id, message_id=temp_msg.message_id)
        except Exception:
            pass
        bot.send_message(message.chat.id, f"❌ Помилка обробки: {e}", reply_markup=get_main_keyboard())

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
        "🚀 <b>Керування кнопками знизу:</b>\n"
        "├ 🔴 <b>Зараз йде</b> — поточна пара або скільки до наступної\n"
        "├ 🟡 <b>Сьогодні</b> — розклад на поточний день\n"
        "├ 🟠 <b>Завтра</b> — пари на завтрашній день\n"
        "├ 🗓 <b>Весь тиждень</b> — повний розклад\n"
        "└ 📸 <b>Оновити розклад (фото)</b> — надіслати скріншот\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    bot.reply_to(message, start_text, parse_mode="HTML", reply_markup=get_main_keyboard())

@bot.message_handler(commands=["now", "current"])
def cmd_now(message):
    kyiv_tz = pytz.timezone("Europe/Kyiv")
    now = datetime.now(kyiv_tz)
    weekday = now.weekday()

    if weekday not in SCHEDULE_DATA or not SCHEDULE_DATA[weekday]:
        bot.reply_to(message, "🎉 <b>Сьогодні вихідний або пар немає!</b>", parse_mode="HTML", reply_markup=get_main_keyboard())
        return

    today_lessons = SCHEDULE_DATA[weekday]
    current_time_minutes = now.hour * 60 + now.minute

    current_lesson = None
    next_lesson = None

    for item in today_lessons:
        time_parts = item["time"].split(" - ")
        start_h, start_m = map(int, time_parts[0].split(":"))
        end_h, end_m = map(int, time_parts[1].split(":"))

        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m

        if start_minutes <= current_time_minutes <= end_minutes:
            current_lesson = (item, end_minutes - current_time_minutes)
            break
        elif current_time_minutes < start_minutes and next_lesson is None:
            next_lesson = (item, start_minutes - current_time_minutes)

    if current_lesson:
        lesson, mins_left = current_lesson
        escaped_title = html.escape(lesson["title"])
        service = lesson["service"]
        
        text = (
            "🔴 <b>ЗАРАЗ ІДЕ ПАРА</b> 🔴\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ <code>{lesson['time']}</code> (залишилось {mins_left} хв)\n"
            f"📌 <b>{escaped_title}</b>\n"
            f"🔗 Платформа: <i>{service}</i>\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(text=f"🚀 Увійти в {service}", url=lesson["link"]))
        bot.reply_to(message, text, parse_mode="HTML", reply_markup=kb)

    elif next_lesson:
        lesson, mins_before = next_lesson
        escaped_title = html.escape(lesson["title"])
        service = lesson["service"]
        
        text = (
            "⏳ <b>ЗАРАЗ ПЕРЕРВА</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🔜 <b>Наступна пара через {mins_before} хв:</b>\n"
            f"⏰ <code>{lesson['time']}</code>\n"
            f"📌 <b>{escaped_title}</b>\n"
            f"🔗 Платформа: <i>{service}</i>\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(text=f"👉 Підготуватися • {service}", url=lesson["link"]))
        bot.reply_to(message, text, parse_mode="HTML", reply_markup=kb)

    else:
        bot.reply_to(
            message,
            "✅ <b>Всі пари на сьогодні закінчилися!</b>\nВідпочивай або переглянь розклад на завтра.",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )

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
        bot.reply_to(message, text, parse_mode="HTML", reply_markup=get_main_keyboard())
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

@bot.message_handler(func=lambda msg: msg.text in ["🔴 Зараз йде", "🟡 Сьогодні", "🟠 Завтра", "🗓 Весь тиждень", "📸 Оновити розклад (фото)"])
def handle_menu_buttons(message):
    if message.text == "🔴 Зараз йде":
        cmd_now(message)
    elif message.text == "🟡 Сьогодні":
        cmd_today(message)
    elif message.text == "🟠 Завтра":
        cmd_tomorrow(message)
    elif message.text == "🗓 Весь тиждень":
        cmd_week(message)
    elif message.text == "📸 Оновити розклад (фото)":
        instruction = (
            "📸 <b>НАДІШЛИ СКРІНШОТ РОЗКЛАДУ:</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "1. Натисни на <b>скріпку 📎</b> біля поля вводу.\n"
            "2. Оберіть скріншот розкладу як фото або файл.\n"
            "3. Бот самостійно розпізнає всі пари і оновить базу!"
        )
        bot.reply_to(message, instruction, parse_mode="HTML", reply_markup=get_main_keyboard())

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    threading.Thread(target=run_http_server, daemon=True).start()
    setup_scheduler()
    scheduler.start()
    bot.infinity_polling()
