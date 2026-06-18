import logging
import sqlite3
from datetime import datetime, date
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8353396026:AAEOwcLU8IU6WlF8q9yYbg4-iSOyXVH3g7I"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

user_states = {}

def init_db():
    conn = sqlite3.connect('timebot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        task_name TEXT,
        start_time TEXT,
        end_time TEXT,
        duration_minutes INTEGER
    )''')
    conn.commit()
    conn.close()

def save_task(user_id, task_name, start_time, end_time, duration):
    conn = sqlite3.connect('timebot.db')
    c = conn.cursor()
    c.execute("INSERT INTO tasks (user_id, task_name, start_time, end_time, duration_minutes) VALUES (?, ?, ?, ?, ?)",
              (user_id, task_name, start_time, end_time, duration))
    conn.commit()
    conn.close()

def get_today_tasks(user_id):
    conn = sqlite3.connect('timebot.db')
    c = conn.cursor()
    today = date.today().strftime("%Y-%m-%d")
    c.execute("SELECT task_name, start_time, end_time, duration_minutes FROM tasks WHERE user_id=? AND start_time LIKE ?",
              (user_id, today + "%"))
    tasks = c.fetchall()
    conn.close()
    return tasks

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = ReplyKeyboardMarkup([["/stop", "/report"]], resize_keyboard=True)
    await update.message.reply_text(
        "👋 Salom! Men sizning vaqt menejeringizman!\n\n"
        "📝 Qilayotgan ishingizni yozing, men vaqtini belgilab qo'yaman.\n"
        "⏹ /stop — ishni tugatish\n"
        "📊 /report — kunlik hisobot",
        reply_markup=reply_markup
    )

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_states or user_states[user_id] is None:
        await update.message.reply_text("❌ Hozir faol vazifa yo'q. Avval biror ish yozing.")
        return

    task = user_states[user_id]
    end_time = datetime.now()
    start_time = task['start_time']
    duration = int((end_time - start_time).total_seconds() / 60)

    save_task(
        user_id,
        task['name'],
        start_time.strftime("%Y-%m-%d %H:%M"),
        end_time.strftime("%Y-%m-%d %H:%M"),
        duration
    )

    user_states[user_id] = None
    await update.message.reply_text(
        f"✅ Vazifa tugatildi!\n"
        f"📌 {task['name']}\n"
        f"⏱ Sarflangan vaqt: {duration} daqiqa\n\n"
        f"Keyingi ishingizni yozing yoki /report ko'ring."
    )

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    tasks = get_today_tasks(user_id)

    if not tasks:
        await update.message.reply_text("📭 Bugun hali hech qanday vazifa qayd etilmagan.")
        return

    total_minutes = 0
    task_summary = {}
    report_text = "📊 *Kunlik hisobot*\n\n"

    for task in tasks:
        name, start, end, duration = task
        if duration is None:
            duration = 0
        report_text += f"• *{name}*\n  🕐 {start} → {end}\n  ⏱ {duration} daqiqa\n\n"
        total_minutes += duration
        task_summary[name] = task_summary.get(name, 0) + duration

    if task_summary:
        top_task = max(task_summary, key=task_summary.get)
        report_text += f"🏆 *Eng ko'p vaqt:* {top_task} ({task_summary[top_task]} daqiqa)\n"

    hours = total_minutes // 60
    minutes = total_minutes % 60
    report_text += f"⏳ *Jami faol vaqt:* {hours} soat {minutes} daqiqa\n\n"

    if total_minutes >= 360:
        report_text += "🔥 Ajoyib kun! Juda intensiv ishlading!"
    elif total_minutes >= 180:
        report_text += "👍 Yaxshi kun! O'rtacha intensivlik."
    else:
        report_text += "💡 Bugun kam ishlading. Ertaga ko'proq harakat qil!"

    await update.message.reply_text(report_text, parse_mode='Markdown')

async def track_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if user_id in user_states and user_states[user_id] is not None:
        old_task = user_states[user_id]
        end_time = datetime.now()
        duration = int((end_time - old_task['start_time']).total_seconds() / 60)
        save_task(
            user_id,
            old_task['name'],
            old_task['start_time'].strftime("%Y-%m-%d %H:%M"),
            end_time.strftime("%Y-%m-%d %H:%M"),
            duration
        )
        await update.message.reply_text(
            f"⏹ Oldingi vazifa avtomatik tugatildi: *{old_task['name']}* ({duration} daqiqa)",
            parse_mode='Markdown'
        )

    now = datetime.now()
    user_states[user_id] = {
        'name': text,
        'start_time': now
    }

    await update.message.reply_text(
        f"⏱ *Qayd etildi!*\n"
        f"📌 {text}\n"
        f"🕐 Boshlangan vaqt: {now.strftime('%H:%M')}\n\n"
        f"Tugatganda /stop bosing yoki yangi ish yozing.",
        parse_mode='Markdown'
    )

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, track_task))
    print("✅ Bot ishga tushdi!")
    app.run_polling()

if __name__ == '__main__':
    main()
