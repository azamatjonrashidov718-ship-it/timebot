import logging
import sqlite3
import os
import re
import io
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from fpdf import FPDF
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN", "8353396026:AAEOwcLU8IU6WlF8q9yYbg4-iSOyXVH3g7I")
TZ = ZoneInfo("Asia/Tashkent")

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.WARNING)


def now_tz():
    return datetime.now(TZ)


def init_db():
    conn = sqlite3.connect('timebot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        task_name TEXT,
        duration_minutes INTEGER,
        log_date TEXT,
        log_time TEXT
    )''')
    conn.commit()
    conn.close()


def save_task(user_id, task_name, duration):
    now = now_tz()
    conn = sqlite3.connect('timebot.db')
    c = conn.cursor()
    c.execute(
        "INSERT INTO tasks (user_id, task_name, duration_minutes, log_date, log_time) VALUES (?, ?, ?, ?, ?)",
        (user_id, task_name, duration, now.strftime("%Y-%m-%d"), now.strftime("%H:%M"))
    )
    conn.commit()
    conn.close()


def get_tasks_by_date(user_id, target_date):
    conn = sqlite3.connect('timebot.db')
    c = conn.cursor()
    c.execute(
        "SELECT task_name, duration_minutes, log_time FROM tasks WHERE user_id=? AND log_date=? ORDER BY log_time",
        (user_id, target_date.strftime("%Y-%m-%d"))
    )
    tasks = c.fetchall()
    conn.close()
    return tasks


def get_weekly_tasks(user_id):
    conn = sqlite3.connect('timebot.db')
    c = conn.cursor()
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    c.execute(
        "SELECT task_name, duration_minutes, log_date FROM tasks WHERE user_id=? AND log_date>=? ORDER BY log_date",
        (user_id, week_start.strftime("%Y-%m-%d"))
    )
    tasks = c.fetchall()
    conn.close()
    return tasks


def format_duration(minutes):
    if minutes < 60:
        return f"{minutes} daqiqa"
    hours = minutes // 60
    mins = minutes % 60
    if mins == 0:
        return f"{hours} soat"
    return f"{hours} soat {mins} daqiqa"


def parse_task_message(text):
    """
    Parses messages like:
    'Kitob o'qidim 30 daqiqa'
    'Yugurdim 1 soat'
    'Dars qildim 1.5 soat'
    Returns (task_name, duration_in_minutes) or None
    """
    text = text.strip()
    pattern = r'^(.+?)\s+(\d+(?:[.,]\d+)?)\s*(daqiqa|min|soat|sek|soniya)\s*$'
    match = re.match(pattern, text, re.IGNORECASE)
    if not match:
        return None
    task_name = match.group(1).strip()
    number = float(match.group(2).replace(',', '.'))
    unit = match.group(3).lower()
    if unit in ['soat']:
        minutes = int(round(number * 60))
    elif unit in ['daqiqa', 'min']:
        minutes = int(round(number))
    else:
        minutes = max(1, int(round(number / 60)))
    if minutes <= 0:
        return None
    return task_name, minutes


def generate_pdf_report(tasks, title, is_weekly=False):
    if not tasks:
        return None

    summary = {}
    daily_totals = {}

    for task in tasks:
        if is_weekly:
            name, duration, log_date = task
            daily_totals[log_date] = daily_totals.get(log_date, 0) + duration
        else:
            name, duration, log_time = task
        summary[name] = summary.get(name, 0) + duration

    total = sum(summary.values())

    # ---- Build chart image ----
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    names = list(summary.keys())
    values = list(summary.values())
    colors = ['#e94560', '#0f3460', '#533483', '#f5a623', '#7ed321',
              '#3498db', '#9b59b6', '#e67e22', '#1abc9c', '#e74c3c']
    chart_colors = (colors * 3)[:len(names)]

    axes[0].pie(values, labels=[n[:12] for n in names], colors=chart_colors,
                autopct='%1.0f%%', startangle=90, textprops={'fontsize': 8})
    axes[0].set_title("Vaqt taqsimoti", fontsize=11, fontweight='bold')

    short_names = [n[:12] + '..' if len(n) > 12 else n for n in names]
    axes[1].barh(short_names, values, color=chart_colors)
    axes[1].set_xlabel("Daqiqa")
    axes[1].set_title("Daqiqalar bo'yicha", fontsize=11, fontweight='bold')
    axes[1].tick_params(labelsize=8)

    plt.tight_layout()
    chart_path = "/tmp/chart.png"
    plt.savefig(chart_path, dpi=130, bbox_inches='tight')
    plt.close()

    # ---- Build PDF ----
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 12, title, ln=True, align="C")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Jami vaqt: {format_duration(total)}", ln=True, align="C")
    pdf.ln(4)

    pdf.image(chart_path, x=10, w=190)
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Batafsil jadval:", ln=True)
    pdf.set_font("Helvetica", "", 10)

    pdf.set_fill_color(230, 230, 250)
    pdf.cell(110, 8, "Ish nomi", border=1, fill=True)
    pdf.cell(40, 8, "Vaqt", border=1, fill=True)
    pdf.cell(40, 8, "Foiz", border=1, fill=True, ln=True)

    for name, dur in sorted(summary.items(), key=lambda x: -x[1]):
        pct = (dur / total * 100) if total else 0
        display_name = name if len(name) <= 45 else name[:42] + "..."
        pdf.cell(110, 7, display_name, border=1)
        pdf.cell(40, 7, format_duration(dur), border=1)
        pdf.cell(40, 7, f"{pct:.1f}%", border=1, ln=True)

    if is_weekly and daily_totals:
        pdf.ln(6)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Kunlar bo'yicha:", ln=True)
        pdf.set_font("Helvetica", "", 10)
        for d in sorted(daily_totals.keys()):
            pdf.cell(0, 7, f"{d}: {format_duration(daily_totals[d])}", ln=True)

    pdf_path = "/tmp/report.pdf"
    pdf.output(pdf_path)
    os.remove(chart_path)
    return pdf_path


def report_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Kunlik hisobot", callback_data="rep_daily"),
         InlineKeyboardButton("📈 Haftalik hisobot", callback_data="rep_weekly")],
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Salom! Men sizning shaxsiy vaqt menejeringizman!\n\n"
        "📝 Bajargan ishingizni va vaqtini yozing:\n"
        "Masalan:\n"
        "<i>Kitob o'qidim 30 daqiqa</i>\n"
        "<i>Yugurdim 1 soat</i>\n\n"
        "Pastdagi tugmalar orqali hisobot olishingiz mumkin 👇",
        parse_mode='HTML',
        reply_markup=report_keyboard()
    )


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    result = parse_task_message(text)
    if not result:
        await update.message.reply_text(
            "❌ Tushunmadim. Quyidagicha yozing:\n\n"
            "<i>Kitob o'qidim 30 daqiqa</i>\n"
            "<i>Yugurdim 1 soat</i>\n"
            "<i>Dars qildim 1.5 soat</i>",
            parse_mode='HTML'
        )
        return

    task_name, duration = result
    save_task(user_id, task_name, duration)

    await update.message.reply_text(
        f"✅ Well done! Vazifa qabul qilindi!\n📌 {task_name}\n⏱ {format_duration(duration)}",
        reply_markup=report_keyboard()
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "rep_daily":
        await query.message.reply_text("⏳ PDF tayyorlanmoqda...")
        tasks = get_tasks_by_date(user_id, date.today())
        if not tasks:
            await query.message.reply_text("📭 Bugun hali hech narsa qayd etilmagan.")
            return
        pdf_path = generate_pdf_report(tasks, f"Kunlik hisobot - {date.today().strftime('%d.%m.%Y')}")
        if pdf_path:
            with open(pdf_path, 'rb') as f:
                await query.message.reply_document(document=f, filename="kunlik_hisobot.pdf")
            os.remove(pdf_path)

    elif data == "rep_weekly":
        await query.message.reply_text("⏳ PDF tayyorlanmoqda...")
        tasks = get_weekly_tasks(user_id)
        if not tasks:
            await query.message.reply_text("📭 Bu hafta hech narsa qayd etilmagan.")
            return
        pdf_path = generate_pdf_report(tasks, "Haftalik hisobot", is_weekly=True)
        if pdf_path:
            with open(pdf_path, 'rb') as f:
                await query.message.reply_document(document=f, filename="haftalik_hisobot.pdf")
            os.remove(pdf_path)


def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("Bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()