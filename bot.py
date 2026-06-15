import logging
import sqlite3
from datetime import datetime, date, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler

TOKEN = "8353396026:AAEOwcLU8IU6WlF8q9yYbg4-iSOyXVH3g7I"

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.WARNING)

# Conversation states
WAITING_TASK = 1
WAITING_STOP_COMMENT = 2
WAITING_RETRO_TIME = 3
WAITING_RETRO_END = 4
WAITING_HABIT_NAME = 5
WAITING_LANG = 6

# User data in memory
user_states = {}
user_langs = {}

# Translations
TEXTS = {
    "uz": {
        "welcome": "👋 Salom! Men sizning shaxsiy vaqt menejeringizman!\n\nQuyidagi menyudan tanlang:",
        "main_menu": "🏠 Asosiy menyu",
        "today": "📝 Bugungi kun",
        "report": "📊 Hisobotlar",
        "habits": "🔥 Odatlar",
        "settings": "⚙️ Sozlamalar",
        "start_task": "✏️ Ish boshlash",
        "retro": "⏮ O'tgan vaqtni kiritish",
        "back": "🔙 Orqaga",
        "stop": "⏹ Tugatish",
        "task_started": "⏱ Qayd etildi!\n📌 {task}\n🕐 Boshlangan: {time}\n\nTugatganda ⏹ Tugatish bosing.",
        "write_task": "📝 Qilayotgan ishingizni yozing:",
        "write_comment": "💬 Izoh yozing (ixtiyoriy):\n\nMasalan: 5 sahifa kitob o'qidim",
        "task_stopped": "✅ Bajarildi!\n📌 {task}\n⏱ Vaqt: {duration}\n💬 Izoh: {comment}",
        "no_task": "❌ Faol vazifa yo'q. Avval ish boshlang.",
        "today_report": "📊 Bugungi hisobot",
        "yesterday_report": "📅 Kechagi hisobot",
        "weekly_report": "📈 Haftalik hisobot",
        "specific_task": "🔍 Aniq ish tahlili",
        "no_tasks_today": "📭 Bugun hali hech narsa qayd etilmagan.",
        "add_habit": "➕ Odat qo'shish",
        "my_habits": "📋 Mening odatlarim",
        "write_habit": "✏️ Yangi odat nomini yozing:\n\nMasalan: Kitob o'qish, Sport, Namoz",
        "habit_added": "✅ Odat qo'shildi: {habit}",
        "no_habits": "📭 Hali odat qo'shilmagan.\n➕ Odat qo'shish tugmasini bosing.",
        "lang_changed": "✅ Til o'zgartirildi!",
        "choose_lang": "🌐 Tilni tanlang:",
        "retro_write": "⏮ O'tgan vaqtni kiritish\n\nIsh nomini va boshlanish vaqtini yozing:\nMasalan: 09:00 Kitob o'qidim",
        "retro_end": "Tugash vaqtini yozing:\nMasalan: 10:30",
        "retro_saved": "✅ Qayd etildi!\n📌 {task}\n🕐 {start} → {end}\n⏱ {duration}",
        "skip": "⏭ O'tkazish",
        "intensity_high": "🔥 Juda intensiv kun!",
        "intensity_mid": "👍 Yaxshi kun!",
        "intensity_low": "💡 Ertaga ko'proq harakat qil!",
        "top_task": "🏆 Eng ko'p vaqt: {task} ({duration})",
        "total_time": "⏳ Jami: {hours} soat {minutes} daqiqa",
        "done_today": "✅ Belgilandi!",
        "streak": "🔥 {days} kunlik streak!",
    },
    "ru": {
        "welcome": "👋 Привет! Я ваш личный менеджер времени!\n\nВыберите из меню:",
        "main_menu": "🏠 Главное меню",
        "today": "📝 Сегодня",
        "report": "📊 Отчёты",
        "habits": "🔥 Привычки",
        "settings": "⚙️ Настройки",
        "start_task": "✏️ Начать задачу",
        "retro": "⏮ Ввести прошедшее время",
        "back": "🔙 Назад",
        "stop": "⏹ Завершить",
        "task_started": "⏱ Зафиксировано!\n📌 {task}\n🕐 Начато: {time}\n\nНажмите ⏹ Завершить когда закончите.",
        "write_task": "📝 Напишите чем занимаетесь:",
        "write_comment": "💬 Напишите комментарий (необязательно):\n\nНапример: Прочитал 5 страниц книги",
        "task_stopped": "✅ Выполнено!\n📌 {task}\n⏱ Время: {duration}\n💬 Комментарий: {comment}",
        "no_task": "❌ Нет активной задачи. Сначала начните задачу.",
        "today_report": "📊 Отчёт за сегодня",
        "yesterday_report": "📅 Отчёт за вчера",
        "weekly_report": "📈 Недельный отчёт",
        "specific_task": "🔍 Анализ конкретной задачи",
        "no_tasks_today": "📭 Сегодня ещё ничего не зафиксировано.",
        "add_habit": "➕ Добавить привычку",
        "my_habits": "📋 Мои привычки",
        "write_habit": "✏️ Напишите название новой привычки:\n\nНапример: Чтение, Спорт, Медитация",
        "habit_added": "✅ Привычка добавлена: {habit}",
        "no_habits": "📭 Привычки ещё не добавлены.\nНажмите ➕ Добавить привычку.",
        "lang_changed": "✅ Язык изменён!",
        "choose_lang": "🌐 Выберите язык:",
        "retro_write": "⏮ Ввод прошедшего времени\n\nНапишите название задачи и время начала:\nНапример: 09:00 Читал книгу",
        "retro_end": "Напишите время окончания:\nНапример: 10:30",
        "retro_saved": "✅ Сохранено!\n📌 {task}\n🕐 {start} → {end}\n⏱ {duration}",
        "skip": "⏭ Пропустить",
        "intensity_high": "🔥 Очень интенсивный день!",
        "intensity_mid": "👍 Хороший день!",
        "intensity_low": "💡 Завтра постарайся больше!",
        "top_task": "🏆 Больше всего времени: {task} ({duration})",
        "total_time": "⏳ Итого: {hours} ч {minutes} мин",
        "done_today": "✅ Отмечено!",
        "streak": "🔥 Серия {days} дней!",
    },
    "en": {
        "welcome": "👋 Hello! I'm your personal time manager!\n\nChoose from the menu:",
        "main_menu": "🏠 Main menu",
        "today": "📝 Today",
        "report": "📊 Reports",
        "habits": "🔥 Habits",
        "settings": "⚙️ Settings",
        "start_task": "✏️ Start task",
        "retro": "⏮ Log past time",
        "back": "🔙 Back",
        "stop": "⏹ Stop",
        "task_started": "⏱ Logged!\n📌 {task}\n🕐 Started: {time}\n\nPress ⏹ Stop when done.",
        "write_task": "📝 Write what you're doing:",
        "write_comment": "💬 Write a comment (optional):\n\nExample: Read 5 pages of a book",
        "task_stopped": "✅ Done!\n📌 {task}\n⏱ Time: {duration}\n💬 Comment: {comment}",
        "no_task": "❌ No active task. Start a task first.",
        "today_report": "📊 Today's report",
        "yesterday_report": "📅 Yesterday's report",
        "weekly_report": "📈 Weekly report",
        "specific_task": "🔍 Specific task analysis",
        "no_tasks_today": "📭 Nothing logged today yet.",
        "add_habit": "➕ Add habit",
        "my_habits": "📋 My habits",
        "write_habit": "✏️ Write new habit name:\n\nExample: Reading, Exercise, Meditation",
        "habit_added": "✅ Habit added: {habit}",
        "no_habits": "📭 No habits added yet.\nPress ➕ Add habit.",
        "lang_changed": "✅ Language changed!",
        "choose_lang": "🌐 Choose language:",
        "retro_write": "⏮ Log past time\n\nWrite task name and start time:\nExample: 09:00 Read a book",
        "retro_end": "Write end time:\nExample: 10:30",
        "retro_saved": "✅ Saved!\n📌 {task}\n🕐 {start} → {end}\n⏱ {duration}",
        "skip": "⏭ Skip",
        "intensity_high": "🔥 Very intensive day!",
        "intensity_mid": "👍 Good day!",
        "intensity_low": "💡 Try harder tomorrow!",
        "top_task": "🏆 Most time: {task} ({duration})",
        "total_time": "⏳ Total: {hours}h {minutes}m",
        "done_today": "✅ Marked!",
        "streak": "🔥 {days} day streak!",
    }
}

def t(user_id, key, **kwargs):
    lang = user_langs.get(user_id, "uz")
    text = TEXTS[lang].get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text

# Database
def init_db():
    conn = sqlite3.connect('timebot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        task_name TEXT,
        start_time TEXT,
        end_time TEXT,
        duration_minutes INTEGER,
        comment TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS habits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        habit_name TEXT,
        created_date TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS habit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        habit_id INTEGER,
        log_date TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_settings (
        user_id INTEGER PRIMARY KEY,
        language TEXT DEFAULT 'uz'
    )''')
    conn.commit()
    conn.close()

def save_task(user_id, task_name, start_time, end_time, duration, comment=""):
    conn = sqlite3.connect('timebot.db')
    c = conn.cursor()
    c.execute("INSERT INTO tasks (user_id, task_name, start_time, end_time, duration_minutes, comment) VALUES (?, ?, ?, ?, ?, ?)",
              (user_id, task_name, start_time, end_time, duration, comment))
    conn.commit()
    conn.close()

def get_tasks_by_date(user_id, target_date):
    conn = sqlite3.connect('timebot.db')
    c = conn.cursor()
    date_str = target_date.strftime("%Y-%m-%d")
    c.execute("SELECT task_name, start_time, end_time, duration_minutes, comment FROM tasks WHERE user_id=? AND start_time LIKE ?",
              (user_id, date_str + "%"))
    tasks = c.fetchall()
    conn.close()
    return tasks

def get_weekly_tasks(user_id):
    conn = sqlite3.connect('timebot.db')
    c = conn.cursor()
    week_ago = (date.today() - timedelta(days=7)).strftime("%Y-%m-%d")
    c.execute("SELECT task_name, start_time, end_time, duration_minutes FROM tasks WHERE user_id=? AND start_time >= ?",
              (user_id, week_ago))
    tasks = c.fetchall()
    conn.close()
    return tasks

def get_habits(user_id):
    conn = sqlite3.connect('timebot.db')
    c = conn.cursor()
    c.execute("SELECT id, habit_name FROM habits WHERE user_id=?", (user_id,))
    habits = c.fetchall()
    conn.close()
    return habits

def add_habit(user_id, habit_name):
    conn = sqlite3.connect('timebot.db')
    c = conn.cursor()
    c.execute("INSERT INTO habits (user_id, habit_name, created_date) VALUES (?, ?, ?)",
              (user_id, habit_name, date.today().strftime("%Y-%m-%d")))
    conn.commit()
    conn.close()

def log_habit(user_id, habit_id):
    conn = sqlite3.connect('timebot.db')
    c = conn.cursor()
    today = date.today().strftime("%Y-%m-%d")
    c.execute("SELECT id FROM habit_logs WHERE user_id=? AND habit_id=? AND log_date=?", (user_id, habit_id, today))
    existing = c.fetchone()
    if not existing:
        c.execute("INSERT INTO habit_logs (user_id, habit_id, log_date) VALUES (?, ?, ?)", (user_id, habit_id, today))
        conn.commit()
    conn.close()
    return not existing

def get_habit_streak(user_id, habit_id):
    conn = sqlite3.connect('timebot.db')
    c = conn.cursor()
    c.execute("SELECT log_date FROM habit_logs WHERE user_id=? AND habit_id=? ORDER BY log_date DESC", (user_id, habit_id))
    logs = [row[0] for row in c.fetchall()]
    conn.close()
    if not logs:
        return 0
    streak = 0
    check_date = date.today()
    for log in logs:
        log_date = datetime.strptime(log, "%Y-%m-%d").date()
        if log_date == check_date:
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break
    return streak

def format_duration(minutes):
    if minutes < 60:
        return f"{minutes} daqiqa"
    hours = minutes // 60
    mins = minutes % 60
    if mins == 0:
        return f"{hours} soat"
    return f"{hours} soat {mins} daqiqa"

def build_report(tasks, title):
    if not tasks:
        return None
    total = 0
    summary = {}
    text = f"{title}\n{'─'*25}\n\n"
    for task in tasks:
        name, start, end, duration, *rest = task
        comment = rest[0] if rest else ""
        duration = duration or 0
        text += f"📌 *{name}*\n"
        text += f"   🕐 {start} → {end or '...'}\n"
        text += f"   ⏱ {format_duration(duration)}\n"
        if comment:
            text += f"   💬 {comment}\n"
        text += "\n"
        total += duration
        summary[name] = summary.get(name, 0) + duration
    text += "─" * 25 + "\n"
    if summary:
        top = max(summary, key=summary.get)
        text += f"🏆 *Eng ko'p:* {top} ({format_duration(summary[top])})\n"
    hours = total // 60
    mins = total % 60
    text += f"⏳ *Jami:* {hours} soat {mins} daqiqa\n\n"
    if total >= 360:
        text += "🔥 Juda intensiv kun!"
    elif total >= 180:
        text += "👍 Yaxshi kun!"
    else:
        text += "💡 Ertaga ko'proq harakat qil!"
    return text

# Keyboards
def main_keyboard(user_id):
    keyboard = [
        [InlineKeyboardButton(t(user_id, "today"), callback_data="today"),
         InlineKeyboardButton(t(user_id, "report"), callback_data="report")],
        [InlineKeyboardButton(t(user_id, "habits"), callback_data="habits"),
         InlineKeyboardButton(t(user_id, "settings"), callback_data="settings")],
    ]
    return InlineKeyboardMarkup(keyboard)

def today_keyboard(user_id):
    uid = user_id
    buttons = [
        [InlineKeyboardButton(t(uid, "start_task"), callback_data="start_task"),
         InlineKeyboardButton(t(uid, "retro"), callback_data="retro")],
    ]
    if uid in user_states and user_states[uid]:
        buttons.insert(0, [InlineKeyboardButton(t(uid, "stop"), callback_data="stop_task")])
    buttons.append([InlineKeyboardButton(t(uid, "back"), callback_data="main")])
    return InlineKeyboardMarkup(buttons)

def report_keyboard(user_id):
    uid = user_id
    keyboard = [
        [InlineKeyboardButton(t(uid, "today_report"), callback_data="rep_today"),
         InlineKeyboardButton(t(uid, "yesterday_report"), callback_data="rep_yesterday")],
        [InlineKeyboardButton(t(uid, "weekly_report"), callback_data="rep_weekly")],
        [InlineKeyboardButton(t(uid, "back"), callback_data="main")],
    ]
    return InlineKeyboardMarkup(keyboard)

def habits_keyboard(user_id):
    uid = user_id
    keyboard = [
        [InlineKeyboardButton(t(uid, "add_habit"), callback_data="add_habit"),
         InlineKeyboardButton(t(uid, "my_habits"), callback_data="my_habits")],
        [InlineKeyboardButton(t(uid, "back"), callback_data="main")],
    ]
    return InlineKeyboardMarkup(keyboard)

def settings_keyboard(user_id):
    keyboard = [
        [InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz"),
         InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
         InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton(t(user_id, "back"), callback_data="main")],
    ]
    return InlineKeyboardMarkup(keyboard)

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_langs:
        user_langs[user_id] = "uz"
    await update.message.reply_text(
        t(user_id, "welcome"),
        reply_markup=main_keyboard(user_id),
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "main":
        await query.edit_message_text(t(user_id, "main_menu"), reply_markup=main_keyboard(user_id))

    elif data == "today":
        active = user_states.get(user_id)
        text = t(user_id, "today")
        if active:
            text += f"\n\n⏱ *Faol:* {active['name']}\n🕐 Boshlangan: {active['start_time'].strftime('%H:%M')}"
        await query.edit_message_text(text, reply_markup=today_keyboard(user_id), parse_mode='Markdown')

    elif data == "report":
        await query.edit_message_text(t(user_id, "report"), reply_markup=report_keyboard(user_id))

    elif data == "habits":
        await query.edit_message_text(t(user_id, "habits"), reply_markup=habits_keyboard(user_id))

    elif data == "settings":
        await query.edit_message_text(t(user_id, "choose_lang"), reply_markup=settings_keyboard(user_id))

    elif data.startswith("lang_"):
        lang = data.split("_")[1]
        user_langs[user_id] = lang
        await query.edit_message_text(t(user_id, "lang_changed"), reply_markup=main_keyboard(user_id))

    elif data == "start_task":
        context.user_data['waiting'] = 'task'
        await query.edit_message_text(t(user_id, "write_task"))

    elif data == "stop_task":
        if user_id not in user_states or not user_states[user_id]:
            await query.edit_message_text(t(user_id, "no_task"), reply_markup=today_keyboard(user_id))
            return
        context.user_data['waiting'] = 'comment'
        skip_btn = InlineKeyboardMarkup([[InlineKeyboardButton(t(user_id, "skip"), callback_data="skip_comment")]])
        await query.edit_message_text(t(user_id, "write_comment"), reply_markup=skip_btn)

    elif data == "skip_comment":
        await finish_task(update, context, user_id, "")

    elif data == "retro":
        context.user_data['waiting'] = 'retro'
        await query.edit_message_text(t(user_id, "retro_write"))

    elif data == "add_habit":
        context.user_data['waiting'] = 'habit'
        await query.edit_message_text(t(user_id, "write_habit"))

    elif data == "my_habits":
        await show_habits(query, user_id)

    elif data.startswith("habit_done_"):
        habit_id = int(data.split("_")[2])
        success = log_habit(user_id, habit_id)
        streak = get_habit_streak(user_id, habit_id)
        if success:
            text = t(user_id, "done_today") + "\n" + t(user_id, "streak", days=streak)
        else:
            text = "⚠️ Bugun allaqachon belgilangan!\n" + t(user_id, "streak", days=streak)
        await query.answer(text, show_alert=True)
        await show_habits(query, user_id)

    elif data == "rep_today":
        tasks = get_tasks_by_date(user_id, date.today())
        report = build_report(tasks, "📊 *Bugungi hisobot*")
        if not report:
            report = t(user_id, "no_tasks_today")
        await query.edit_message_text(report, reply_markup=report_keyboard(user_id), parse_mode='Markdown')

    elif data == "rep_yesterday":
        yesterday = date.today() - timedelta(days=1)
        tasks = get_tasks_by_date(user_id, yesterday)
        report = build_report(tasks, f"📅 *{yesterday.strftime('%d.%m.%Y')} hisoboti*")
        if not report:
            report = "📭 Kecha hech narsa qayd etilmagan."
        await query.edit_message_text(report, reply_markup=report_keyboard(user_id), parse_mode='Markdown')

    elif data == "rep_weekly":
        tasks = get_weekly_tasks(user_id)
        report = build_report(tasks, "📈 *Haftalik hisobot*")
        if not report:
            report = "📭 Bu hafta hech narsa qayd etilmagan."
        await query.edit_message_text(report, reply_markup=report_keyboard(user_id), parse_mode='Markdown')

async def show_habits(query, user_id):
    habits = get_habits(user_id)
    if not habits:
        await query.edit_message_text(
            TEXTS[user_langs.get(user_id, "uz")]["no_habits"],
            reply_markup=habits_keyboard(user_id)
        )
        return
    today = date.today().strftime("%Y-%m-%d")
    conn = sqlite3.connect('timebot.db')
    c = conn.cursor()
    buttons = []
    text = "🔥 *Odatlarim*\n\n"
    for habit_id, habit_name in habits:
        c.execute("SELECT id FROM habit_logs WHERE user_id=? AND habit_id=? AND log_date=?", (user_id, habit_id, today))
        done = c.fetchone()
        streak = get_habit_streak(user_id, habit_id)
        status = "✅" if done else "⬜"
        text += f"{status} {habit_name} — 🔥{streak} kun\n"
        if not done:
            buttons.append([InlineKeyboardButton(f"✅ {habit_name}", callback_data=f"habit_done_{habit_id}")])
    conn.close()
    buttons.append([InlineKeyboardButton("🔙 Orqaga", callback_data="habits")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='Markdown')

async def finish_task(update, context, user_id, comment):
    task = user_states.get(user_id)
    if not task:
        return
    end_time = datetime.now()
    duration = int((end_time - task['start_time']).total_seconds() / 60)
    save_task(user_id, task['name'], task['start_time'].strftime("%Y-%m-%d %H:%M"),
              end_time.strftime("%Y-%m-%d %H:%M"), duration, comment)
    user_states[user_id] = None
    text = t(user_id, "task_stopped",
             task=task['name'],
             duration=format_duration(duration),
             comment=comment if comment else "—")
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=today_keyboard(user_id), parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=main_keyboard(user_id), parse_mode='Markdown')

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    waiting = context.user_data.get('waiting')

    if waiting == 'task':
        context.user_data['waiting'] = None
        if user_id in user_states and user_states[user_id]:
            old = user_states[user_id]
            end_time = datetime.now()
            duration = int((end_time - old['start_time']).total_seconds() / 60)
            save_task(user_id, old['name'], old['start_time'].strftime("%Y-%m-%d %H:%M"),
                      end_time.strftime("%Y-%m-%d %H:%M"), duration, "")
        now = datetime.now()
        user_states[user_id] = {'name': text, 'start_time': now}
        msg = t(user_id, "task_started", task=text, time=now.strftime('%H:%M'))
        await update.message.reply_text(msg, reply_markup=today_keyboard(user_id), parse_mode='Markdown')

    elif waiting == 'comment':
        context.user_data['waiting'] = None
        await finish_task(update, context, user_id, text)

    elif waiting == 'habit':
        context.user_data['waiting'] = None
        add_habit(user_id, text)
        await update.message.reply_text(
            t(user_id, "habit_added", habit=text),
            reply_markup=habits_keyboard(user_id)
        )

    elif waiting == 'retro':
        context.user_data['waiting'] = 'retro_end'
        parts = text.split(' ', 1)
        if len(parts) >= 2:
            context.user_data['retro_start_time'] = parts[0]
            context.user_data['retro_task'] = parts[1]
            await update.message.reply_text(t(user_id, "retro_end"))
        else:
            await update.message.reply_text("❌ Noto'g'ri format. Qayta yozing:\nMasalan: 09:00 Kitob o'qidim")

    elif waiting == 'retro_end':
        context.user_data['waiting'] = None
        start_str = context.user_data.get('retro_start_time')
        task_name = context.user_data.get('retro_task')
        end_str = text.strip()
        try:
            today_str = date.today().strftime("%Y-%m-%d")
            start_dt = datetime.strptime(f"{today_str} {start_str}", "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(f"{today_str} {end_str}", "%Y-%m-%d %H:%M")
            duration = int((end_dt - start_dt).total_seconds() / 60)
            if duration <= 0:
                await update.message.reply_text("❌ Tugash vaqti boshlanish vaqtidan keyin bo'lishi kerak!")
                return
            save_task(user_id, task_name, start_dt.strftime("%Y-%m-%d %H:%M"),
                      end_dt.strftime("%Y-%m-%d %H:%M"), duration, "")
            msg = t(user_id, "retro_saved", task=task_name,
                    start=start_str, end=end_str, duration=format_duration(duration))
            await update.message.reply_text(msg, reply_markup=main_keyboard(user_id), parse_mode='Markdown')
        except ValueError:
            await update.message.reply_text("❌ Vaqt formati noto'g'ri. Masalan: 10:30")

    else:
        await update.message.reply_text(
            t(user_id, "main_menu"),
            reply_markup=main_keyboard(user_id)
        )

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("✅ Bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
