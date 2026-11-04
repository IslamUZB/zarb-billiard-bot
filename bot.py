import os
import sqlite3
import time
from datetime import datetime, date
from zoneinfo import ZoneInfo

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes
)

TOKEN = os.getenv("BOT_TOKEN")
TZ = ZoneInfo("Asia/Tashkent")
RATE_PER_HOUR = 50000
TABLE_COUNT = 10
DB_PATH = os.getenv("DB_PATH", "zarb.sqlite3")

def now():
    return datetime.now(TZ)

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, role TEXT NOT NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS sessions (
            table_no INTEGER PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'free',
            started_at REAL,
            segment_started REAL,
            elapsed_seconds REAL NOT NULL DEFAULT 0,
            total_seconds REAL NOT NULL DEFAULT 0,
            last_amount INTEGER NOT NULL DEFAULT 0
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_no INTEGER, started TEXT, ended TEXT,
            seconds INTEGER, amount INTEGER, cashier_id INTEGER
        )""")
        for n in range(1, TABLE_COUNT + 1):
            con.execute("INSERT OR IGNORE INTO sessions(table_no) VALUES (?)", (n,))

def is_admin(user_id):
    with db() as con:
        row = con.execute("SELECT role FROM users WHERE user_id=?", (user_id,)).fetchone()
    return bool(row and row["role"] == "admin")

def is_staff(user_id):
    with db() as con:
        row = con.execute("SELECT role FROM users WHERE user_id=?", (user_id,)).fetchone()
    return bool(row)

def money(seconds):
    # Charge by each started minute, calculated from elapsed whole seconds.
    minutes = (max(0, int(seconds)) + 59) // 60
    return round(minutes * RATE_PER_HOUR / 60)

def duration(seconds):
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def current_seconds(row):
    elapsed = float(row["elapsed_seconds"] or 0)
    if row["status"] == "running" and row["segment_started"]:
        elapsed += time.time() - float(row["segment_started"])
    return max(0, elapsed)

def keyboard():
    rows = []
    for start in range(1, TABLE_COUNT + 1, 2):
        rows.append([
            InlineKeyboardButton(f"🎱 Stol {start}", callback_data=f"table:{start}"),
            InlineKeyboardButton(f"🎱 Stol {start+1}", callback_data=f"table:{start+1}")
        ])
    rows.append([InlineKeyboardButton("📊 Bugungi kassa", callback_data="report")])
    return InlineKeyboardMarkup(rows)

def table_text(row):
    n = row["table_no"]
    status = row["status"]
    if status == "free":
        return f"🎱 Stol {n}\nHolati: 🟢 Bo‘sh"
    secs = current_seconds(row)
    state = "▶️ Ishlayapti" if status == "running" else "⏸ Pauzada"
    return (f"🎱 Stol {n}\nHolati: {state}\n"
            f"Vaqt: {duration(secs)}\n"
            f"Joriy summa: {money(secs):,} so‘m".replace(",", " "))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid):
        await update.message.reply_text(
            "Assalomu alaykum! ZARB BILLIARD boshqaruv botiga xush kelibsiz.\n\n"
            "Birinchi bo‘lib botni sozlayotgan egasi /setup buyrug‘ini yuborsin.\n"
            "Agar egasi allaqachon sozlagan bo‘lsa, undan sizni kassir sifatida qo‘shishini so‘rang."
        )
        return
    await update.message.reply_text(
        "🎱 ZARB BILLIARD\nTarif: 50 000 so‘m / soat\nHisob: har daqiqada.\n\n"
        "Stolni tanlang:", reply_markup=keyboard()
    )

async def setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    with db() as con:
        count = con.execute("SELECT COUNT(*) AS n FROM users WHERE role='admin'").fetchone()["n"]
        if count == 0:
            con.execute("INSERT OR REPLACE INTO users(user_id, role) VALUES (?, 'admin')", (uid,))
            await update.message.reply_text(
                "✅ Siz ZARB botining egasi/adminisiz.\n"
                "Endi /start yuboring. Boshqa odamlarni kassir qilish uchun /addcashier USER_ID buyrug‘idan foydalaning."
            )
        elif is_admin(uid):
            await update.message.reply_text("Siz allaqachon adminsiz. /start ni bosing.")
        else:
            await update.message.reply_text("Bot egasi allaqachon ro‘yxatdan o‘tgan. /setup faqat birinchi admin uchun.")

async def addcashier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Bu buyruq faqat admin uchun.")
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Foydalanish: /addcashier USER_ID")
        return
    uid = int(context.args[0])
    with db() as con:
        con.execute("INSERT OR REPLACE INTO users(user_id, role) VALUES (?, 'cashier')", (uid,))
    await update.message.reply_text(f"✅ {uid} kassir sifatida qo‘shildi.")

async def remove_cashier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Bu buyruq faqat admin uchun.")
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Foydalanish: /delcashier USER_ID")
        return
    uid = int(context.args[0])
    with db() as con:
        con.execute("DELETE FROM users WHERE user_id=? AND role='cashier'", (uid,))
    await update.message.reply_text("Kassir ro‘yxati yangilandi.")

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Telegram ID: {update.effective_user.id}")

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=False):
    if not is_staff(update.effective_user.id):
        if update.callback_query:
            await update.callback_query.answer("Ruxsat yo‘q", show_alert=True)
        return
    today = now().date().isoformat()
    with db() as con:
        row = con.execute(
            "SELECT COUNT(*) AS games, COALESCE(SUM(amount),0) AS total "
            "FROM sales WHERE substr(ended,1,10)=?", (today,)
        ).fetchone()
    msg = (f"📊 BUGUNGI KASSA\n📅 {today}\n"
           f"Yakunlangan o‘yinlar: {row['games']}\n"
           f"Jami tushum: {row['total']:,} so‘m".replace(",", " "))
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(msg)
    else:
        await update.message.reply_text(msg)

async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    if not is_staff(uid):
        await q.answer("Sizga ruxsat berilmagan.", show_alert=True)
        return
    await q.answer()
    if q.data == "report":
        await report(update, context, edit=True)
        return
    if not q.data.startswith("table:"):
        return
    n = int(q.data.split(":")[1])
    with db() as con:
        row = con.execute("SELECT * FROM sessions WHERE table_no=?", (n,)).fetchone()
    if not row:
        return
    buttons = []
    if row["status"] == "free":
        buttons.append([InlineKeyboardButton("▶️ Boshlash", callback_data=f"start:{n}")])
    elif row["status"] == "running":
        buttons.extend([
            [InlineKeyboardButton("⏸ Pauza", callback_data=f"pause:{n}")],
            [InlineKeyboardButton("⏹ Tugatish va hisoblash", callback_data=f"stop:{n}")]
        ])
    elif row["status"] == "paused":
        buttons.extend([
            [InlineKeyboardButton("▶️ Davom ettirish", callback_data=f"resume:{n}")],
            [InlineKeyboardButton("⏹ Tugatish va hisoblash", callback_data=f"stop:{n}")]
        ])
    buttons.append([InlineKeyboardButton("⬅️ Stollar", callback_data="back")])
    await q.message.reply_text(table_text(row), reply_markup=InlineKeyboardMarkup(buttons))

    # Handle action callbacks separately below
async def action_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    if not is_staff(uid):
        await q.answer("Ruxsat yo‘q", show_alert=True)
        return
    await q.answer()
    action, n_str = q.data.split(":")
    n = int(n_str)
    with db() as con:
        row = con.execute("SELECT * FROM sessions WHERE table_no=?", (n,)).fetchone()
        if action == "start" and row["status"] == "free":
            con.execute("""UPDATE sessions SET status='running', started_at=?, segment_started=?,
                elapsed_seconds=0 WHERE table_no=?""", (time.time(), time.time(), n))
            msg = f"✅ Stol {n} boshlandi."
        elif action == "pause" and row["status"] == "running":
            elapsed = current_seconds(row)
            con.execute("UPDATE sessions SET status='paused', segment_started=NULL, elapsed_seconds=? WHERE table_no=?",
                        (elapsed, n))
            msg = f"⏸ Stol {n} pauza qilindi. Vaqt: {duration(elapsed)}"
        elif action == "resume" and row["status"] == "paused":
            con.execute("UPDATE sessions SET status='running', segment_started=? WHERE table_no=?",
                        (time.time(), n))
            msg = f"▶️ Stol {n} davom ettirildi."
        elif action == "stop" and row["status"] in ("running", "paused"):
            elapsed = current_seconds(row)
            amount = money(elapsed)
            started = datetime.fromtimestamp(float(row["started_at"]), TZ).isoformat()
            ended = now().isoformat()
            con.execute("""INSERT INTO sales(table_no,started,ended,seconds,amount,cashier_id)
                VALUES (?,?,?,?,?,?)""", (n, started, ended, int(elapsed), amount, uid))
            con.execute("""UPDATE sessions SET status='free', started_at=NULL, segment_started=NULL,
                elapsed_seconds=0, total_seconds=total_seconds+?, last_amount=? WHERE table_no=?""",
                (elapsed, amount, n))
            msg = (f"✅ Stol {n} yakunlandi.\nVaqt: {duration(elapsed)}\n"
                   f"To‘lov: {amount:,} so‘m".replace(",", " "))
        else:
            msg = "Bu amal hozir bajarilmaydi."
    await q.message.reply_text(msg, reply_markup=keyboard())

async def back_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_staff(q.from_user.id):
        await q.answer("Ruxsat yo‘q", show_alert=True)
        return
    await q.answer()
    await q.message.reply_text("🎱 Stolni tanlang:", reply_markup=keyboard())

def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN muhit o‘zgaruvchisi kiritilmagan.")
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setup", setup))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("addcashier", addcashier))
    app.add_handler(CommandHandler("delcashier", remove_cashier))
    app.add_handler(CallbackQueryHandler(back_button, pattern="^back$"))
    app.add_handler(CallbackQueryHandler(action_button, pattern="^(start|pause|resume|stop):"))
    app.add_handler(CallbackQueryHandler(on_button, pattern="^(table:|report$)"))
    print("ZARB bot ishga tushdi.")
    app.run_polling()

if __name__ == "__main__":
    main()
