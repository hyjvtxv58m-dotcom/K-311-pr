import asyncio
import csv
import io
import logging
from datetime import datetime
import pytz
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from apscheduler.schedulers.asyncio import AsyncIOScheduler

BOT_TOKEN = 8814170419:AAHWiLDlZEJ0KXeQzU_hVmQckRlsB6wRi8w
USER_CHAT_ID = 780458353

SHEET_ID = "1KPQpwM98V8lW-sCGZiWLX5M7NimVKGNbQJENZVZyNHw"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=240436523"

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

weekly_schedule = {}

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone=pytz.timezone("Europe/Kyiv"))

def get_link_for_lesson(lesson_text: str) -> str:
    text = str(lesson_text).lower()
    for keyword, link in TEACHER_LINKS.items():
        if keyword in text:
            return link
    return DEFAULT_MEET

async def send_lesson_notification(title: str, link: str):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Войти в пару (Zoom / Meet)", url=link)]
    ])
    await bot.send_message(
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
            return

        header = rows[0]
        target_col_idx = None
        for idx, col_name in enumerate(header):
            if "3к" in col_name.lower() and "фбк" in col_name.lower():
                target_col_idx = idx
                break
        
        if target_col_idx is None:
            logging.error("Колонка '3к фбк' не найдена")
            return

        lessons = []
        for r in rows[1:]:
            if len(r) > target_col_idx:
                val = r[target_col_idx].strip()
                if val:
                    lessons.append(val)

        scheduler.remove_all_jobs()
        scheduler.add_job(sync_schedule, "cron", day_of_week="sun", hour=21, minute=0)

        weekly_schedule.clear()
        lesson_idx = 0
        days_names = ["mon", "tue", "wed", "thu", "fri"]

        for day_num, day_code in enumerate(days_names):
            weekly_schedule[day_num] = []
            for t in CALL_TIMES:
                if lesson_idx < len(lessons):
                    title = lessons[lesson_idx]
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
                    lesson_idx += 1

        logging.info("Синхронизация завершена успешно!")
    except Exception as e:
        logging.error(f"Ошибка парсинга: {e}")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Бот расписания запущен!\n\n"
        "• /today — пары на сегодня\n"
        "• /sync — обновить расписание из таблицы"
    )

@dp.message(Command("sync"))
async def cmd_sync(message: types.Message):
    await message.answer("🔄 Загружаю расписание из Google Таблицы...")
    sync_schedule()
    await message.answer("✅ Расписание обновлено! Будильники расставлены.")

@dp.message(Command("today"))
async def cmd_today(message: types.Message):
    kyiv_tz = pytz.timezone("Europe/Kyiv")
    today_idx = datetime.now(kyiv_tz).weekday()
    
    if today_idx not in weekly_schedule or not weekly_schedule[today_idx]:
        await message.answer("🎉 Сегодня пар нет или расписание ещё не загружено!")
        return

    text = "📋 <b>Пары на сегодня:</b>\n\n"
    buttons = []
    for item in weekly_schedule[today_idx]:
        text += f"⏰ <b>{item['time']}</b> — {item['title']}\n"
        buttons.append([InlineKeyboardButton(text=f"👉 {item['time']} Войти", url=item['link'])])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

async def main():
    logging.basicConfig(level=logging.INFO)
    scheduler.start()
    sync_schedule()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
