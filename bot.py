import html
import logging
import re
from datetime import datetime
import pytz
import requests
import telebot
from telebot import types
from apscheduler.schedulers.background import BackgroundScheduler

BOT_TOKEN = "8814170419:AAHWiLDlZEJ0KXeQzU_hVmQckRlsB6wRi8w"
USER_CHAT_ID = 780458353
OCR_API_KEY = "K86575271388957"

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
        {"hour": 13, "minute": 45, "time": "13:45 - 15:00", "title": "Інтернет речей та проектування розумного виробництва (л) — Захаренков Д.Ю."},
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
        {"hour": 10, "minute": 40, "time": "10:40 - 11:55", "title": "Організація та адміністрування баз даних (л) — Гордієнко І.М."},
        {"hour": 12, "minute": 20, "time": "12:20 - 13:35", "title": "Інтернет речей та проектування розумного виробництва (л) — Захаренков Д.Ю."},
    ],
    4: [
        {"hour": 9,  "minute": 15, "time": "09:15 - 10:30", "title": "Організація та адміністрування баз даних (пр) — Довголуцький І.Р."},
        {"hour": 10, "minute": 40, "time": "10:40 - 11:55", "title": "Проектування автономних мереж (л) — Подвиженко А.В."},
        {"hour": 12, "minute": 20, "time": "12:20 - 13:35", "title": "Об'єктно-орієнтоване програмування (пр) — Довголуцький І.Р."},
    ]
}

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

@bot.message_handler(content_types=["photo"])
def handle_schedule_photo(message):
    if message.chat.id != USER_CHAT_ID:
        return

    temp_msg = bot.reply_to(message, "⏳ Зчитую скріншот і розпізнаю пари...")

    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        tg_file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        img_data = requests.get(tg_file_url).content

        ocr_res = requests.post(
            "https://api.ocr.space/parse/image",
            files={"file": ("schedule.jpg", img_data)},
            data={
                "apikey": OCR_API_KEY,
                "language": "auto",
                "isTable": True,
                "OCREngine": 2
            },
            timeout=40
        ).json()

        try:
            bot.delete_message(chat_id=message.chat.id, message_id=temp_msg.message_id)
        except Exception:
            pass

        if ocr_res.get("IsErroredOnProcessing"):
            bot.reply_to(message, f"❌ Помилка OCR: {ocr_res.get('ErrorMessage')}")
            return

        parsed_text = ocr_res["ParsedResults"][0]["ParsedText"]
        lines = [line.strip() for line in parsed_text.splitlines() if line.strip()]

        found_pairs = []
        for line in lines:
            line_lower = line.lower()
            if any(teacher in line_lower for teacher in TEACHER_LINKS.keys()):
                found_pairs.append(line)

        if not found_pairs:
            bot.reply_to(message, "⚠️ Пари не знайдено. Переконайся, що на зображенні чітко видно прізвища викладачів.")
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
        bot.reply_to(message, f"✅ Розклад оновлено! Знайдено пар: {len(found_pairs)}.\n\nПеревір оновлення: /week")

    except Exception as e:
        try:
            bot.delete_message(chat_id=message.chat.id, message_id=temp_msg.message_id)
        except Exception:
            pass
        bot.reply_to(message, f"❌ Помилка: {e}")

@bot.message_handler(commands=["start"])
def cmd_start(message):
    bot.reply_to(
        message,
        "👋 Бот розкладу К-311!\n\n"
        "• /today — пари на сьогодні\n"
        "• /tomorrow — пари на завтра\n"
        "• /week — розклад на весь тиждень з посиланнями\n\n"
        "📷 <b>Надішли скріншот розкладу</b> — бот автоматично оновить пари на тиждень!",
        parse_mode="HTML"
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
        bot.reply_to(message, f"🎉 {day_name}: пар немає!")
        return

    text = f"📋 Пари на {day_name}:\n\n"
    kb = types.InlineKeyboardMarkup()
    for item in lessons:
        link = get_link_for_lesson(item["title"])
        service = "Meet" if "meet.google" in link else "Zoom"
        text += f"⏰ {item['time']} — {item['title']}\n"
        kb.add(types.InlineKeyboardButton(text=f"👉 {item['time']} Увійти ({service})", url=link))

    bot.reply_to(message, text, reply_markup=kb)

@bot.message_handler(commands=["week"])
def cmd_week(message):
    for d_num in range(5):
        d_name = DAYS_MAP[d_num]
        lessons = SCHEDULE_DATA.get(d_num, [])
        text = f"🗓 <b>{d_name}</b>:\n"
        if not lessons:
            text += "  <i>(пар немає)</i>"
        else:
            for l in lessons:
                link = get_link_for_lesson(l["title"])
                service = "Meet" if "meet.google" in link else "Zoom"
                escaped_title = html.escape(l["title"])
                text += f"  • <b>{l['time']}</b> — <a href=\"{link}\">{escaped_title}</a> [<b>{service}</b>]\n"
        bot.send_message(message.chat.id, text.strip(), parse_mode="HTML", disable_web_page_preview=True)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    setup_scheduler()
    scheduler.start()
    bot.infinity_polling()
