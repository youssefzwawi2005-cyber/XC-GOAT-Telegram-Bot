import telebot
from telebot import types
import random
import sqlite3
import re
import time
import os
from collections import defaultdict

try:
    import yt_dlp
except ImportError:
    os.system("pip install yt-dlp")
    import yt_dlp

# ================== الإعدادات ==================
BOT_TOKEN = '8546373941:AAFRwI3b8xHUsmm5CjoFTdzSZmfDNG9en04'
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
PHOTO_URL = "https://www2.0zz0.com/2025/12/24/22/102880228.jpg"

BAD_WORDS = ["كلب", "حمار", "تفه", "غبي", "يا حمار"]
user_messages = defaultdict(list)
user_warnings = defaultdict(int)

# ================== قاعدة البيانات ==================
def setup_db():
    conn = sqlite3.connect('goat_bot.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS groups
        (chat_id INTEGER PRIMARY KEY, welcome_msg TEXT, rules TEXT, link TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS ranks
        (chat_id INTEGER, user_id INTEGER, rank TEXT,
        PRIMARY KEY(chat_id, user_id))''')

    c.execute('''CREATE TABLE IF NOT EXISTS settings
        (chat_id INTEGER PRIMARY KEY,
        lock_links INTEGER DEFAULT 0,
        lock_forward INTEGER DEFAULT 0,
        lock_media INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        anti_spam INTEGER DEFAULT 1)''')

    conn.commit()
    conn.close()

def set_lock(chat_id, column, value):
    conn = sqlite3.connect('goat_bot.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO settings (chat_id) VALUES (?)", (chat_id,))
    c.execute(f"UPDATE settings SET {column}=? WHERE chat_id=?", (value, chat_id))
    conn.commit()
    conn.close()

def is_locked(chat_id, column):
    conn = sqlite3.connect('goat_bot.db')
    c = conn.cursor()
    c.execute(f"SELECT {column} FROM settings WHERE chat_id=?", (chat_id,))
    r = c.fetchone()
    conn.close()
    return r[0] if r else 0

def get_rank(chat_id, user_id):
    conn = sqlite3.connect('goat_bot.db')
    c = conn.cursor()
    c.execute("SELECT rank FROM ranks WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    r = c.fetchone()
    conn.close()
    return r[0] if r else "عضو"

setup_db()

# ================== الأزرار ==================
def main_markup():
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(
        types.InlineKeyboardButton("👑 المطور الأساسي", url="https://t.me/C_R_B_X"),
        types.InlineKeyboardButton("💰 شراء البوت", url="https://t.me/C_R_B_X"),
        types.InlineKeyboardButton("➕ أضفني للمجموعة", url=f"https://t.me/{bot.get_me().username}?startgroup=true")
    )
    return m

# ================== Start ==================
@bot.message_handler(commands=["start"])
def start_msg(message):
    txt = (
        "🐐 أهلاً بك في بوت XC GOAT!\n"
        "أنا بوت حماية وتسلية متطور، أساعدك في إدارة مجموعتك بكل سهولة وأمان.\n\n"
        "🛡️ مميزات البوت:\n"
        "• حماية قوية ومتكاملة.\n"
        "• أوامر إدارة كاملة.\n"
        "• ألعاب وتسلية.\n"
        "• ميزة البحث الموسيقي (يوت).\n\n"
        "💡 التشغيل:\n"
        "أضفني مشرفاً ثم أرسل (تفعيل) داخل المجموعة.\n\n"
        "📌 يمكنك استخدام كلمة 'الأوامر' لعرض قائمة الأوامر المتاحة."
    )
    bot.send_photo(message.chat.id, PHOTO_URL, caption=txt, reply_markup=main_markup())

# ================== الترحيب ==================
@bot.message_handler(content_types=["new_chat_members", "left_chat_member"])
def welcome(message):
    cid = message.chat.id
    try:
        bot.delete_message(cid, message.message_id)
    except:
        pass

    if message.new_chat_members:
        for u in message.new_chat_members:
            if u.id == bot.get_me().id:
                bot.send_photo(cid, PHOTO_URL, caption="✅ تم تفعيل XC GOAT\nأرسل (تفعيل)")
            else:
                bot.send_photo(cid, PHOTO_URL, caption=f"✨ أهلاً {u.first_name}")

# ================== الحماية والأوامر ==================
@bot.message_handler(func=lambda m: True, content_types=["text", "photo", "video", "document", "forward"])
def protection(message):
    cid = message.chat.id
    uid = message.from_user.id
    name = message.from_user.first_name
    text = message.text or ""

    # تحقق صلاحيات البوت
    try:
        if message.chat.type != "private":
            me = bot.get_chat_member(cid, bot.get_me().id).status
            if me not in ["administrator", "creator"]:
                bot.send_message(cid, "⚠️ لست مشرفاً، سأغادر.")
                bot.leave_chat(cid)
                return
    except:
        return

    status = bot.get_chat_member(cid, uid).status
    is_admin = status in ["administrator", "creator"]

    # فلترة السب
    if text and not is_admin:
        for bad in BAD_WORDS:
            if bad in text:
                try:
                    bot.delete_message(cid, message.message_id)
                except:
                    pass
                bot.send_message(cid, f"🚫 {name} ممنوع السب في المجموعة!")
                return

    # مكافحة السبام
    if not is_admin and is_locked(cid, "anti_spam"):
        now = time.time()
        user_messages[uid] = [t for t in user_messages[uid] if now - t < 3]
        user_messages[uid].append(now)
        if len(user_messages[uid]) > 5:
            bot.restrict_chat_member(cid, uid, until_date=int(now) + 3600)
            bot.send_message(cid, f"⚠️ {name} كتم ساعة بسبب السبام")
            return

    # قفل الصور والفيديو
    if not is_admin and is_locked(cid, "lock_media"):
        if message.content_type in ["photo", "video"]:
            try:
                bot.delete_message(cid, message.message_id)
                bot.send_message(cid, f"🚫 {name} ممنوع إرسال صور/فيديوهات!")
            except:
                pass
            return

    # يوتيوب
    if text.startswith("يوت "):
        q = text.replace("يوت ", "")
        wait = bot.reply_to(message, "🔍 جاري البحث...")
        try:
            opts = {
                "format": "bestaudio/best",
                "outtmpl": "song.%(ext)s",
                "quiet": True,
                "noplaylist": True,
            }
            with yt_dlp.YoutubeDL(opts) as y:
                y.download([f"ytsearch1:{q}"])

            for f in os.listdir("."):
                if f.startswith("song."):
                    bot.send_audio(cid, open(f, "rb"), caption=f"🎵 {q}")
                    os.remove(f)
                    break

            bot.delete_message(cid, wait.message_id)
        except:
            bot.edit_message_text("❌ لم يتم العثور على نتائج.", cid, wait.message_id)
        return

    # أوامر
    if text == "الاوامر":
        bot.reply_to(message, "📜 قائمة الأوامر", reply_markup=main_markup())

    if is_admin:
        if text == "قفل الروابط":
            set_lock(cid, "lock_links", 1)
            bot.reply_to(message, "🚫 تم قفل الروابط")
        elif text == "فتح الروابط":
            set_lock(cid, "lock_links", 0)
            bot.reply_to(message, "🔓 تم فتح الروابط")
        elif text == "قفل الصور":
            set_lock(cid, "lock_media", 1)
            bot.reply_to(message, "🚫 تم قفل الصور والفيديو")
        elif text == "فتح الصور":
            set_lock(cid, "lock_media", 0)
            bot.reply_to(message, "🔓 تم فتح الصور والفيديو")
        elif text == "تفعيل":
            set_lock(cid, "is_active", 1)
            bot.reply_to(message, "✅ تم تفعيل البوت")
        elif text == "تعطيل":
            set_lock(cid, "is_active", 0)
            bot.reply_to(message, "❌ تم تعطيل البوت")

    if text == "ايدي":
        bot.reply_to(message, f"🆔 ايديك: <code>{uid}</code>\n🎖️ رتبتك: {get_rank(cid, uid)}")

# تشغيل البوت
bot.infinity_polling()# ================== إعداد الرتب ==================
def set_rank(chat_id, user_id, rank):
    conn = sqlite3.connect('goat_bot.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO ranks (chat_id, user_id, rank) VALUES (?, ?, ?)", (chat_id, user_id, rank))
    conn.commit()
    conn.close()

def remove_rank(chat_id, user_id):
    conn = sqlite3.connect('goat_bot.db')
    c = conn.cursor()
    c.execute("DELETE FROM ranks WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    conn.commit()
    conn.close()

# ================== إعدادات المجموعة ==================
def set_group_welcome(chat_id, welcome_msg):
    conn = sqlite3.connect('goat_bot.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO groups (chat_id) VALUES (?)", (chat_id,))
    c.execute("UPDATE groups SET welcome_msg=? WHERE chat_id=?", (welcome_msg, chat_id))
    conn.commit()
    conn.close()

def set_group_rules(chat_id, rules):
    conn = sqlite3.connect('goat_bot.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO groups (chat_id) VALUES (?)", (chat_id,))
    c.execute("UPDATE groups SET rules=? WHERE chat_id=?", (rules, chat_id))
    conn.commit()
    conn.close()

def get_group_info(chat_id):
    conn = sqlite3.connect('goat_bot.db')
    c = conn.cursor()
    c.execute("SELECT welcome_msg, rules, link FROM groups WHERE chat_id=?", (chat_id,))
    r = c.fetchone()
    conn.close()
    return r if r else ("", "", "")

# ================== قائمة الأزرار الإضافية ==================
def settings_markup():
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(
        types.InlineKeyboardButton("🔒 قفل/فتح الروابط", callback_data="toggle_links"),
        types.InlineKeyboardButton("🔒 قفل/فتح الوسائط", callback_data="toggle_media"),
        types.InlineKeyboardButton("🚨 نظام التحذيرات", callback_data="warnings_system"),
        types.InlineKeyboardButton("🛡️ حماية", callback_data="protection_settings")
    )
    m.add(
        types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu"),
        types.InlineKeyboardButton("❌ إخفاء", callback_data="hide_cmd")
    )
    return m

# ================== التعامل مع Callbacks ==================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    cid = call.message.chat.id
    mid = call.message.message_id

    if call.data == "toggle_links":
        current = is_locked(cid, "lock_links")
        set_lock(cid, "lock_links", 0 if current else 1)
        bot.answer_callback_query(call.id, f"حالة الروابط: {'مقفلة 🔒' if not current else 'مفتوحة 🔓'}", show_alert=True)

    elif call.data == "toggle_media":
        current = is_locked(cid, "lock_media")
        set_lock(cid, "lock_media", 0 if current else 1)
        bot.answer_callback_query(call.id, f"حالة الوسائط: {'مقفلة 🔒' if not current else 'مفتوحة 🔓'}", show_alert=True)

    elif call.data == "warnings_system":
        bot.answer_callback_query(call.id, "⚠️ نظام التحذيرات يعمل على مراقبة السبام والسب.", show_alert=True)

    elif call.data == "protection_settings":
        bot.answer_callback_query(call.id, "🛡️ يمكنك تعديل حماية المجموعة من الرسائل، الصور، والفيديو.", show_alert=True)

    elif call.data == "main_menu":
        bot.edit_message_text("📜 قائمة الأوامر", cid, mid, reply_markup=main_markup())

    elif call.data == "hide_cmd":
        bot.delete_message(cid, mid)# ================== نظام التحذيرات ==================
def warn_user(chat_id, user_id, reason="مخالفة"):
    user_warnings[user_id] += 1
    count = user_warnings[user_id]
    bot.send_message(chat_id, f"⚠️ تم تحذير العضو <a href='tg://user?id={user_id}'>المستخدم</a>.\nعدد التحذيرات: {count}\nسبب: {reason}", parse_mode="HTML")
    
    # إجراءات حسب عدد التحذيرات
    if count == 3:
        bot.restrict_chat_member(chat_id, user_id, until_date=int(time.time()) + 3600)
        bot.send_message(chat_id, f"⛔ تم كتم العضو <a href='tg://user?id={user_id}'>المستخدم</a> لمدة ساعة بعد تحذيرات متعددة!", parse_mode="HTML")
    elif count >= 5:
        try:
            bot.kick_chat_member(chat_id, user_id)
            bot.send_message(chat_id, f"🚫 تم طرد العضو <a href='tg://user?id={user_id}'>المستخدم</a> بعد تجاوز التحذيرات!", parse_mode="HTML")
            user_warnings[user_id] = 0
        except:
            bot.send_message(chat_id, "❌ لم أستطع طرد العضو. تأكد أن لدي صلاحيات كافية.", parse_mode="HTML")

# ================== فلترة السب الذكي ==================
SMART_BAD_WORDS = ["غباء", "حمار", "كلب", "تفه", "أهبل"]

def smart_filter(text):
    text = text.lower()
    for word in SMART_BAD_WORDS:
        if word in text:
            return True
    return False

# ================== حماية الرسائل ==================
@bot.message_handler(func=lambda m: True, content_types=["text", "photo", "video", "document", "forward"])
def smart_protection(message):
    cid = message.chat.id
    uid = message.from_user.id
    name = message.from_user.first_name
    text = message.text or ""
    
    # تحقق من المشرف
    try:
        status = bot.get_chat_member(cid, uid).status
        is_admin = status in ["administrator", "creator"]
    except:
        is_admin = False
    
    # فلترة سب ذكي
    if not is_admin and text and smart_filter(text):
        warn_user(cid, uid, reason="سب ذكي")
        try:
            bot.delete_message(cid, message.message_id)
        except:
            pass
        return

    # مكافحة السبام المتقدم
    if not is_admin and is_locked(cid, "anti_spam"):
        now = time.time()
        user_messages[uid] = [t for t in user_messages[uid] if now - t < 5]
        user_messages[uid].append(now)
        if len(user_messages[uid]) > 4:
            warn_user(cid, uid, reason="سبام")
            bot.restrict_chat_member(cid, uid, until_date=int(now) + 1800)
            return

    # قفل الصور والفيديو المتقدم
    if not is_admin and is_locked(cid, "lock_media"):
        if message.content_type in ["photo", "video"]:
            try:
                bot.delete_message(cid, message.message_id)
                warn_user(cid, uid, reason="إرسال وسائط ممنوعة")
            except:
                pass
            return

# ================== يوتيوب مع خيارات متقدمة ==================
def download_youtube_audio(query, chat_id):
    opts = {
        "format": "bestaudio/best",
        "outtmpl": "song.%(ext)s",
        "quiet": True,
        "noplaylist": True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as y:
            y.download([f"ytsearch1:{query}"])
        for f in os.listdir("."):
            if f.startswith("song."):
                bot.send_audio(chat_id, open(f, "rb"), caption=f"🎵 {query}")
                os.remove(f)
                break
    except:
        bot.send_message(chat_id, "❌ لم يتم العثور على نتائج.")

@bot.message_handler(func=lambda m: m.text and m.text.startswith("يوت "))
def youtube_handler(message):
    query = message.text.replace("يوت ", "")
    wait = bot.reply_to(message, "🔍 جاري البحث...")
    download_youtube_audio(query, message.chat.id)
    try:
        bot.delete_message(message.chat.id, wait.message_id)
    except:
        pass# ================== إعدادات إضافية للمجموعة ==================
def get_group_settings(chat_id):
    conn = sqlite3.connect('goat_bot.db')
    c = conn.cursor()
    c.execute("SELECT * FROM settings WHERE chat_id=?", (chat_id,))
    result = c.fetchone()
    conn.close()
    return result if result else (chat_id, 0, 0, 0, 1, 1)

# ================== أزرار فرعية ==================
def admin_markup():
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(
        types.InlineKeyboardButton("🚫 قفل الروابط", callback_data="lock_links"),
        types.InlineKeyboardButton("🔓 فتح الروابط", callback_data="unlock_links")
    )
    m.add(
        types.InlineKeyboardButton("🔒 قفل الصور والفيديو", callback_data="lock_media"),
        types.InlineKeyboardButton("🔓 فتح الصور والفيديو", callback_data="unlock_media")
    )
    m.add(
        types.InlineKeyboardButton("✅ تفعيل البوت", callback_data="activate_bot"),
        types.InlineKeyboardButton("❌ تعطيل البوت", callback_data="deactivate_bot")
    )
    return m

# ================== استجابة الأزرار ==================
@bot.callback_query_handler(func=lambda call: True)
def callback_admin(call):
    cid = call.message.chat.id
    mid = call.message.message_id
    user_id = call.from_user.id

    try:
        status = bot.get_chat_member(cid, user_id).status
        is_admin = status in ["administrator", "creator"]
    except:
        is_admin = False

    if not is_admin:
        bot.answer_callback_query(call.id, "❌ فقط المشرفين يمكنهم استخدام هذه الأزرار", show_alert=True)
        return

    if call.data == "lock_links":
        set_lock(cid, "lock_links", 1)
        bot.answer_callback_query(call.id, "🚫 تم قفل الروابط", show_alert=True)
    elif call.data == "unlock_links":
        set_lock(cid, "lock_links", 0)
        bot.answer_callback_query(call.id, "🔓 تم فتح الروابط", show_alert=True)
    elif call.data == "lock_media":
        set_lock(cid, "lock_media", 1)
        bot.answer_callback_query(call.id, "🔒 تم قفل الصور والفيديو", show_alert=True)
    elif call.data == "unlock_media":
        set_lock(cid, "lock_media", 0)
        bot.answer_callback_query(call.id, "🔓 تم فتح الصور والفيديو", show_alert=True)
    elif call.data == "activate_bot":
        set_lock(cid, "is_active", 1)
        bot.answer_callback_query(call.id, "✅ تم تفعيل البوت", show_alert=True)
    elif call.data == "deactivate_bot":
        set_lock(cid, "is_active", 0)
        bot.answer_callback_query(call.id, "❌ تم تعطيل البوت", show_alert=True)

# ================== أوامر إدارية نصية ==================
@bot.message_handler(func=lambda m: True)
def admin_commands(message):
    cid = message.chat.id
    uid = message.from_user.id
    text = message.text or ""
    
    try:
        status = bot.get_chat_member(cid, uid).status
        is_admin = status in ["administrator", "creator"]
    except:
        is_admin = False

    if not is_admin:
        return

    if text == "قفل الروابط":
        set_lock(cid, "lock_links", 1)
        bot.reply_to(message, "🚫 تم قفل الروابط")
    elif text == "فتح الروابط":
        set_lock(cid, "lock_links", 0)
        bot.reply_to(message, "🔓 تم فتح الروابط")
    elif text == "قفل الصور":
        set_lock(cid, "lock_media", 1)
        bot.reply_to(message, "🔒 تم قفل الصور والفيديو")
    elif text == "فتح الصور":
        set_lock(cid, "lock_media", 0)
        bot.reply_to(message, "🔓 تم فتح الصور والفيديو")
    elif text == "تفعيل":
        set_lock(cid, "is_active", 1)
        bot.reply_to(message, "✅ تم تفعيل البوت")
    elif text == "تعطيل":
        set_lock(cid, "is_active", 0)
        bot.reply_to(message, "❌ تم تعطيل البوت")

# ================== عرض حالة البوت ==================
@bot.message_handler(commands=["حالة_البوت"])
def bot_status(message):
    cid = message.chat.id
    settings = get_group_settings(cid)
    status_msg = (
        f"📊 <b>حالة البوت في هذه المجموعة:</b>\n"
        f"🔗 الروابط: {'مقفلة' if settings[1] else 'مفتوحة'}\n"
        f"🖼️ الوسائط: {'مقفلة' if settings[3] else 'مفتوحة'}\n"
        f"🟢 البوت: {'مفعل' if settings[4] else 'معطل'}\n"
        f"⚠️ مكافحة السبام: {'مفعلة' if settings[5] else 'معطلة'}"
    )
    bot.send_message(cid, status_msg, parse_mode="HTML")# ================== نظام التحذيرات ==================
def warn_user(chat_id, user_id, name):
    user_warnings[(chat_id, user_id)] += 1
    warnings = user_warnings[(chat_id, user_id)]

    if warnings == 1:
        bot.send_message(chat_id, f"⚠️ {name} تم تحذيرك أول مرة!")
    elif warnings == 2:
        bot.send_message(chat_id, f"⚠️ {name} تحذير ثاني! احذر من الطرد")
    elif warnings >= 3:
        try:
            bot.kick_chat_member(chat_id, user_id)
            bot.send_message(chat_id, f"❌ {name} تم طرده بعد 3 تحذيرات")
            user_warnings[(chat_id, user_id)] = 0
        except:
            bot.send_message(chat_id, f"⚠️ {name} محاولة الطرد فشلت")
    return warnings

# ================== ذكاء سب متقدم ==================
ADVANCED_BAD_WORDS = [
    "غبي", "حمار", "تفه", "سخيف", "يا حمار", "يا أبله", "أحمق", "مستفز"
]

def advanced_filter(message):
    text = message.text or ""
    cid = message.chat.id
    uid = message.from_user.id
    name = message.from_user.first_name

    try:
        status = bot.get_chat_member(cid, uid).status
        is_admin = status in ["administrator", "creator"]
    except:
        is_admin = False

    if is_admin:
        return False

    for word in ADVANCED_BAD_WORDS:
        if word in text:
            try:
                bot.delete_message(cid, message.message_id)
            except:
                pass
            warn_user(cid, uid, name)
            return True
    return False

# ================== ربط الفلترة المتقدمة ==================
@bot.message_handler(func=lambda m: True, content_types=["text"])
def smart_filter(message):
    advanced_filter(message)

# ================== إعادة ضبط التحذيرات ==================
@bot.message_handler(commands=["reset_warnings"])
def reset_warnings(message):
    cid = message.chat.id
    uid = message.from_user.id
    try:
        status = bot.get_chat_member(cid, uid).status
        is_admin = status in ["administrator", "creator"]
    except:
        is_admin = False

    if not is_admin:
        bot.reply_to(message, "❌ فقط المشرفين يمكنهم استخدام هذا الأمر")
        return

    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        user_warnings[(cid, target_id)] = 0
        bot.send_message(cid, f"✅ تم إعادة ضبط التحذيرات للمستخدم")
    else:
        bot.send_message(cid, "ℹ️ استخدم هذا الأمر كرد على رسالة المستخدم")

# ================== إدارة قائمة الكلمات ==================
@bot.message_handler(commands=["add_bad_word"])
def add_bad_word(message):
    cid = message.chat.id
    uid = message.from_user.id

    try:
        status = bot.get_chat_member(cid, uid).status
        is_admin = status in ["administrator", "creator"]
    except:
        is_admin = False

    if not is_admin:
        bot.reply_to(message, "❌ فقط المشرفين يمكنهم إضافة كلمات")
        return

    word = message.text.split(" ", 1)
    if len(word) < 2:
        bot.reply_to(message, "❌ استخدم: /add_bad_word <الكلمة>")
        return

    BAD_WORDS.append(word[1])
    bot.send_message(cid, f"✅ تم إضافة الكلمة: {word[1]} للقائمة")

@bot.message_handler(commands=["list_bad_words"])
def list_bad_words(message):
    cid = message.chat.id
    bot.send_message(cid, "📜 كلمات ممنوعة حالياً:\n" + "\n".join(BAD_WORDS))# ================== حماية الروابط ==================
@bot.message_handler(func=lambda m: True, content_types=["text"])
def link_protection(message):
    cid = message.chat.id
    uid = message.from_user.id
    text = message.text or ""
    name = message.from_user.first_name

    try:
        status = bot.get_chat_member(cid, uid).status
        is_admin = status in ["administrator", "creator"]
    except:
        is_admin = False

    if not is_admin and is_locked(cid, "lock_links"):
        # اكتشاف أي رابط
        if re.search(r"(https?://\S+|www\.\S+)", text):
            try:
                bot.delete_message(cid, message.message_id)
                bot.send_message(cid, f"🚫 {name} ممنوع إرسال روابط!")
                warn_user(cid, uid, name)
            except:
                pass
            return

# ================== حماية الرسائل المحولة ==================
@bot.message_handler(func=lambda m: True, content_types=["forward"])
def forward_protection(message):
    cid = message.chat.id
    uid = message.from_user.id
    name = message.from_user.first_name

    try:
        status = bot.get_chat_member(cid, uid).status
        is_admin = status in ["administrator", "creator"]
    except:
        is_admin = False

    if not is_admin and is_locked(cid, "lock_forward"):
        try:
            bot.delete_message(cid, message.message_id)
            bot.send_message(cid, f"🚫 {name} ممنوع إعادة توجيه الرسائل!")
            warn_user(cid, uid, name)
        except:
            pass
        return

# ================== أوامر إدارة القفل ==================
@bot.message_handler(commands=["lock_links", "unlock_links", "lock_forward", "unlock_forward"])
def manage_locks(message):
    cid = message.chat.id
    uid = message.from_user.id

    try:
        status = bot.get_chat_member(cid, uid).status
        is_admin = status in ["administrator", "creator"]
    except:
        is_admin = False

    if not is_admin:
        bot.reply_to(message, "❌ فقط المشرفين يمكنهم إدارة الإعدادات")
        return

    cmd = message.text.lower()
    if cmd == "/lock_links":
        set_lock(cid, "lock_links", 1)
        bot.send_message(cid, "🚫 تم قفل الروابط")
    elif cmd == "/unlock_links":
        set_lock(cid, "lock_links", 0)
        bot.send_message(cid, "🔓 تم فتح الروابط")
    elif cmd == "/lock_forward":
        set_lock(cid, "lock_forward", 1)
        bot.send_message(cid, "🚫 تم قفل الرسائل المحولة")
    elif cmd == "/unlock_forward":
        set_lock(cid, "lock_forward", 0)
        bot.send_message(cid, "🔓 تم فتح الرسائل المحولة")

# ================== حماية السبام المتقدم ==================
SPAM_LIMIT = 5
SPAM_INTERVAL = 3  # بالثواني

@bot.message_handler(func=lambda m: True, content_types=["text", "photo", "video", "document"])
def advanced_antispam(message):
    cid = message.chat.id
    uid = message.from_user.id
    name = message.from_user.first_name

    try:
        status = bot.get_chat_member(cid, uid).status
        is_admin = status in ["administrator", "creator"]
    except:
        is_admin = False

    if not is_admin and is_locked(cid, "anti_spam"):
        now = time.time()
        user_messages[uid] = [t for t in user_messages[uid] if now - t < SPAM_INTERVAL]
        user_messages[uid].append(now)
        if len(user_messages[uid]) > SPAM_LIMIT:
            try:
                bot.restrict_chat_member(cid, uid, until_date=int(now) + 3600)
                bot.send_message(cid, f"⚠️ {name} كتم ساعة بسبب السبام المتكرر")
            except:
                bot.send_message(cid, f"⚠️ {name} تم اكتشاف سبام، لكن لم أستطع تقييده")
            return# ================== يوتيوب متقدم ==================
def download_youtube_audio(query, chat_id, message_id):
    wait = bot.send_message(chat_id, "🔍 جاري البحث عن الصوت...")
    try:
        opts = {
            "format": "bestaudio/best",
            "outtmpl": "song.%(ext)s",
            "quiet": True,
            "noplaylist": True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([f"ytsearch1:{query}"])

        for f in os.listdir("."):
            if f.startswith("song."):
                bot.send_audio(chat_id, open(f, "rb"), caption=f"🎵 {query}")
                os.remove(f)
                break
        bot.delete_message(chat_id, wait.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ حدث خطأ أثناء البحث أو التحميل:\n{e}", chat_id, wait.message_id)

# ================== أوامر يوتيوب ==================
@bot.message_handler(func=lambda m: True, content_types=["text"])
def youtube_commands(message):
    cid = message.chat.id
    uid = message.from_user.id
    text = message.text or ""

    try:
        status = bot.get_chat_member(cid, uid).status
        is_admin = status in ["administrator", "creator"]
    except:
        is_admin = False

    if text.startswith("يوت "):
        query = text.replace("يوت ", "")
        download_youtube_audio(query, cid, message.message_id)

# ================== حماية المحتوى المتقدم ==================
@bot.message_handler(func=lambda m: True, content_types=["photo", "video", "document"])
def media_protection(message):
    cid = message.chat.id
    uid = message.from_user.id
    name = message.from_user.first_name

    try:
        status = bot.get_chat_member(cid, uid).status
        is_admin = status in ["administrator", "creator"]
    except:
        is_admin = False

    if not is_admin and is_locked(cid, "lock_media"):
        try:
            bot.delete_message(cid, message.message_id)
            bot.send_message(cid, f"🚫 {name} ممنوع إرسال صور/فيديو/ملفات!")
            warn_user(cid, uid, name)
        except:
            pass

# ================== نظام التحذيرات ==================
def warn_user(chat_id, user_id, name):
    user_warnings[user_id] += 1
    warnings = user_warnings[user_id]
    bot.send_message(chat_id, f"⚠️ {name} لديه {warnings} تحذيرات!")
    if warnings >= 3:
        try:
            bot.kick_chat_member(chat_id, user_id)
            bot.send_message(chat_id, f"🚨 {name} تم طرده بعد 3 تحذيرات!")
            user_warnings[user_id] = 0
        except:
            bot.send_message(chat_id, f"⚠️ {name} وصل إلى 3 تحذيرات لكن لم أستطع طرده")# ================== أوامر الإدارة ==================
@bot.message_handler(func=lambda m: True, content_types=["text"])
def admin_commands(message):
    cid = message.chat.id
    uid = message.from_user.id
    text = message.text or ""

    try:
        status = bot.get_chat_member(cid, uid).status
        is_admin = status in ["administrator", "creator"]
    except:
        is_admin = False

    if not is_admin:
        return

    # ===== إدارة القفل والفتح =====
    if text == "قفل الروابط":
        set_lock(cid, "lock_links", 1)
        bot.send_message(cid, "🚫 تم قفل الروابط")
    elif text == "فتح الروابط":
        set_lock(cid, "lock_links", 0)
        bot.send_message(cid, "🔓 تم فتح الروابط")
    elif text == "قفل الفوروارد":
        set_lock(cid, "lock_forward", 1)
        bot.send_message(cid, "🚫 تم قفل الرسائل المعاد توجيهها")
    elif text == "فتح الفوروارد":
        set_lock(cid, "lock_forward", 0)
        bot.send_message(cid, "🔓 تم فتح الرسائل المعاد توجيهها")

    # ===== تفعيل/تعطيل البوت =====
    elif text == "تفعيل":
        set_lock(cid, "is_active", 1)
        bot.send_message(cid, "✅ تم تفعيل البوت")
    elif text == "تعطيل":
        set_lock(cid, "is_active", 0)
        bot.send_message(cid, "❌ تم تعطيل البوت")

# ================== الحماية ضد الروابط والفوروارد ==================
@bot.message_handler(func=lambda m: True, content_types=["text", "forward_from"])
def link_forward_protection(message):
    cid = message.chat.id
    uid = message.from_user.id
    text = message.text or ""
    name = message.from_user.first_name

    try:
        status = bot.get_chat_member(cid, uid).status
        is_admin = status in ["administrator", "creator"]
    except:
        is_admin = False

    # قفل الروابط
    if not is_admin and is_locked(cid, "lock_links"):
        if re.search(r"(https?://|t.me/)", text):
            try:
                bot.delete_message(cid, message.message_id)
                warn_user(cid, uid, name)
            except:
                pass

    # قفل الفوروارد
    if not is_admin and is_locked(cid, "lock_forward") and message.forward_from:
        try:
            bot.delete_message(cid, message.message_id)
            warn_user(cid, uid, name)
        except:
            pass

# ================== أوامر التسلية ==================
@bot.message_handler(func=lambda m: True, content_types=["text"])
def fun_commands(message):
    cid = message.chat.id
    text = message.text or ""

    if text == "ضحك":
        jokes = ["😂 هاهاها", "🤣 ضحك بدون توقف!", "😹 يا سلام على الضحك!"]
        bot.send_message(cid, random.choice(jokes))
    elif text == "تحية":
        greetings = ["👋 أهلاً!", "🙌 مرحباً بك!", "✨ يا هلا!"]
        bot.send_message(cid, random.choice(greetings))# ================== نظام التحذيرات ==================
def warn_user(chat_id, user_id, name):
    user_warnings[user_id] += 1
    warns = user_warnings[user_id]

    if warns == 1:
        bot.send_message(chat_id, f"⚠️ {name} تلقيت التحذير الأول!")
    elif warns == 2:
        bot.send_message(chat_id, f"⚠️ {name} تلقيت التحذير الثاني!")
    elif warns >= 3:
        bot.restrict_chat_member(chat_id, user_id, until_date=int(time.time()) + 3600)
        bot.send_message(chat_id, f"⛔ {name} تم كتمه لمدة ساعة بسبب تكرار المخالفات!")
        user_warnings[user_id] = 0  # إعادة العد بعد العقوبة

# ================== فلترة متقدمة للكلمات ==================
@bot.message_handler(func=lambda m: True, content_types=["text"])
def advanced_filter(message):
    cid = message.chat.id
    uid = message.from_user.id
    text = message.text or ""
    name = message.from_user.first_name

    try:
        status = bot.get_chat_member(cid, uid).status
        is_admin = status in ["administrator", "creator"]
    except:
        is_admin = False

    if not is_admin:
        for bad in BAD_WORDS:
            if re.search(rf"\b{bad}\b", text):
                try:
                    bot.delete_message(cid, message.message_id)
                    warn_user(cid, uid, name)
                except:
                    pass
                return

# ================== قفل الصور والفيديو الذكي ==================
@bot.message_handler(func=lambda m: True, content_types=["photo", "video"])
def smart_media_lock(message):
    cid = message.chat.id
    uid = message.from_user.id
    name = message.from_user.first_name

    try:
        status = bot.get_chat_member(cid, uid).status
        is_admin = status in ["administrator", "creator"]
    except:
        is_admin = False

    if not is_admin and is_locked(cid, "lock_media"):
        try:
            bot.delete_message(cid, message.message_id)
            warn_user(cid, uid, name)
        except:
            pass# ================== البحث الموسيقي المتقدم ==================
@bot.message_handler(func=lambda m: True, content_types=["text"])
def youtube_search(message):
    cid = message.chat.id
    uid = message.from_user.id
    text = message.text or ""
    name = message.from_user.first_name

    try:
        status = bot.get_chat_member(cid, uid).status
        is_admin = status in ["administrator", "creator"]
    except:
        is_admin = False

    if text.startswith("يوت "):
        query = text.replace("يوت ", "")
        wait_msg = bot.reply_to(message, "🔍 جاري البحث...")
        try:
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": f"temp_song_{uid}.%(ext)s",
                "quiet": True,
                "noplaylist": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"ytsearch1:{query}"])

            for f in os.listdir("."):
                if f.startswith(f"temp_song_{uid}"):
                    bot.send_audio(cid, open(f, "rb"), caption=f"🎵 {query}")
                    os.remove(f)
                    break

            bot.delete_message(cid, wait_msg.message_id)
        except:
            bot.edit_message_text("❌ لم يتم العثور على نتائج.", cid, wait_msg.message_id)# ================== أوامر الإدارة المتقدمة ==================
@bot.message_handler(func=lambda m: True, content_types=["text"])
def admin_commands(message):
    cid = message.chat.id
    uid = message.from_user.id
    text = message.text or ""
    name = message.from_user.first_name

    try:
        status = bot.get_chat_member(cid, uid).status
        is_admin = status in ["administrator", "creator"]
    except:
        is_admin = False

    if not is_admin:
        return

    if text == "قفل الروابط":
        set_lock(cid, "lock_links", 1)
        bot.reply_to(message, "🚫 تم قفل الروابط")
    elif text == "فتح الروابط":
        set_lock(cid, "lock_links", 0)
        bot.reply_to(message, "🔓 تم فتح الروابط")
    elif text == "قفل الصور":
        set_lock(cid, "lock_media", 1)
        bot.reply_to(message, "🚫 تم قفل الصور والفيديو")
    elif text == "فتح الصور":
        set_lock(cid, "lock_media", 0)
        bot.reply_to(message, "🔓 تم فتح الصور والفيديو")
    elif text == "تفعيل":
        set_lock(cid, "is_active", 1)
        bot.reply_to(message, "✅ تم تفعيل البوت")
    elif text == "تعطيل":
        set_lock(cid, "is_active", 0)
        bot.reply_to(message, "❌ تم تعطيل البوت")
    elif text == "ايدي":
        bot.reply_to(message, f"🆔 ايديك: <code>{uid}</code>\n🎖️ رتبتك: {get_rank(cid, uid)}")# ================== نظام التحذيرات ==================
@bot.message_handler(func=lambda m: True, content_types=["text"])
def warning_system(message):
    cid = message.chat.id
    uid = message.from_user.id
    text = message.text or ""
    name = message.from_user.first_name

    try:
        status = bot.get_chat_member(cid, uid).status
        is_admin = status in ["administrator", "creator"]
    except:
        is_admin = False

    if is_admin:
        return

    # ================== فلترة الكلمات السيئة ==================
    for bad in BAD_WORDS:
        if bad in text:
            user_warnings[uid] += 1
            try:
                bot.delete_message(cid, message.message_id)
            except:
                pass

            if user_warnings[uid] == 1:
                bot.send_message(cid, f"⚠️ {name} تم تحذيرك أول مرة!")
            elif user_warnings[uid] == 2:
                bot.send_message(cid, f"⚠️ {name} تحذير ثاني! كن حذراً!")
            elif user_warnings[uid] >= 3:
                bot.restrict_chat_member(cid, uid, until_date=int(time.time()) + 3600)
                bot.send_message(cid, f"❌ {name} تم كتمه لمدة ساعة بسبب المخالفات")
                user_warnings[uid] = 0
            return

    # ================== مكافحة السبام الذكية ==================
    if is_locked(cid, "anti_spam"):
        now = time.time()
        user_messages[uid] = [t for t in user_messages[uid] if now - t < 3]
        user_messages[uid].append(now)
        if len(user_messages[uid]) > 5:
            bot.restrict_chat_member(cid, uid, until_date=int(now) + 3600)
            bot.send_message(cid, f"⚠️ {name} كتم ساعة بسبب السبام")
            return# ================== قفل الصور والفيديو ==================
@bot.message_handler(func=lambda m: True, content_types=["photo", "video"])
def media_lock(message):
    cid = message.chat.id
    uid = message.from_user.id
    name = message.from_user.first_name

    try:
        status = bot.get_chat_member(cid, uid).status
        is_admin = status in ["administrator", "creator"]
    except:
        is_admin = False

    if is_admin:
        return

    if is_locked(cid, "lock_media"):
        try:
            bot.delete_message(cid, message.message_id)
            bot.send_message(cid, f"🚫 {name} ممنوع إرسال صور أو فيديوهات في هذه المجموعة!")
        except:
            pass"):
                bot.send_audio(cid, open(f, "rb"), caption=f"🎵 {query}")
                os.remove(f)
                break

        bot.delete_message(cid, wait.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ لم يتم العثور على نتائج.\n{e}", cid, wait.message_id)# ================== نظام التحذيرات ==================
if not is_admin:
    user_warnings[uid] += 1
    if user_warnings[uid] >= 3:
        try:
            bot.kick_chat_member(cid, uid)
            bot.send_message(cid, f"⚠️ {name} تم طرده بعد 3 تحذيرات")
            user_warnings[uid] = 0
        except:
            pass
    else:
        bot.send_message(cid, f"⚠️ {name} تحذير {user_warnings[uid]}/3")# ================== فلترة الروابط ==================
if not is_admin and is_locked(cid, "lock_links"):
    if text and re.search(r"(https?://|t\.me/)", text):
        try:
            bot.delete_message(cid, message.message_id)
            bot.send_message(cid, f"🚫 {name} ممنوع إرسال روابط!")
        except:
            pass
        return# ================== ردود تلقائية ==================
auto_replies = {
    "سلام": ["وعليكم السلام 🌹", "أهلاً وسهلاً!"],
    "كيف حالك": ["تمام الحمد لله، وأنت؟", "بخير شكراً لسؤالك!"],
    "مرحبا": ["أهلاً بك 😄", "مرحباً! كيفك اليوم؟"]
}

if text.lower() in auto_replies and not is_admin:
    reply = random.choice(auto_replies[text.lower()])
    bot.reply_to(message, reply)
    return# ================== نظام التحذيرات ==================
MAX_WARNINGS = 3  # الحد الأقصى للتحذيرات قبل الإيقاف المؤقت

if not is_admin:
    if any(bad in text for bad in BAD_WORDS):
        user_warnings[uid] += 1
        warnings_left = MAX_WARNINGS - user_warnings[uid]
        if warnings_left > 0:
            bot.reply_to(message, f"⚠️ {name} لقد حصلت على تحذير! المتبقي: {warnings_left}")
        else:
            try:
                bot.restrict_chat_member(cid, uid, until_date=int(time.time()) + 3600)
                bot.send_message(cid, f"❌ {name} تم كتمك لمدة ساعة بسبب تجاوز التحذيرات")
                user_warnings[uid] = 0  # إعادة ضبط التحذيرات بعد العقوبة
            except:
                pass
        return# ================== حماية الروابط ==================
if not is_admin and is_locked(cid, "lock_links"):
    if text and ("t.me/" in text or "telegram.me/" in text or "https://" in text):
        try:
            bot.delete_message(cid, message.message_id)
            bot.send_message(cid, f"🚫 {name} ممنوع إرسال روابط هنا!")
        except:
            pass
        return

# ================== منع التحويل ==================
if not is_admin and is_locked(cid, "lock_forward"):
    if message.forward_from or message.forward_from_chat:
        try:
            bot.delete_message(cid, message.message_id)
            bot.send_message(cid, f"🚫 {name} ممنوع إعادة التوجيه هنا!")
        except:
            pass
        return# ================== نظام التحذيرات ==================
if not is_admin:
    for bad in BAD_WORDS:
        if bad in text:
            user_warnings[uid] += 1
            warn_count = user_warnings[uid]
            try:
                bot.delete_message(cid, message.message_id)
            except:
                pass
            bot.send_message(cid, f"⚠️ {name} حصل على تحذير رقم {warn_count} بسبب استخدام كلمات ممنوعة!")
            # كتم أو طرد عند تجاوز 3 تحذيرات
            if warn_count >= 3:
                bot.restrict_chat_member(cid, uid, until_date=int(time.time()) + 3600)
                bot.send_message(cid, f"🚫 {name} تم كتمه ساعة بسبب تجاوز التحذيرات")
                user_warnings[uid] = 0
            return# ================== الردود التلقائية ==================
AUTO_REPLIES = {
    "السلام عليكم": "وعليكم السلام ورحمة الله وبركاته 🌹",
    "باي": "إلى اللقاء! 👋",
    "مرحبا": "أهلاً وسهلاً بك! 🐐",
    "كيف الحال": "الحمد لله، وأنت؟ 🤗"
}

if text and not is_admin:
    for key, reply in AUTO_REPLIES.items():
        if key in text:
            bot.send_message(cid, f"{reply}")
            break# ================== نظام التحذيرات ==================
MAX_WARNINGS = 3  # الحد الأقصى للتحذيرات قبل الكتم أو الطرد

if not is_admin:
    for bad in BAD_WORDS:
        if bad in text:
            user_warnings[uid] += 1
            warn_count = user_warnings[uid]
            if warn_count >= MAX_WARNINGS:
                try:
                    bot.restrict_chat_member(cid, uid, until_date=int(time.time()) + 3600)
                    bot.send_message(cid, f"⚠️ {name} تم كتمه ساعة بسبب تجاوز التحذيرات ({warn_count}/{MAX_WARNINGS})")
                    user_warnings[uid] = 0
                except:
                    pass
            else:
                bot.send_message(cid, f"⚠️ {name} تحذير {warn_count}/{MAX_WARNINGS} بسبب استخدام كلمات غير لائقة!")
            try:
                bot.delete_message(cid, message.message_id)
            except:
                pass
            return# ================== نظام التحذيرات ==================
if not is_admin:
    # إعطاء تحذير عند مخالفة القوانين (مثل السب أو إرسال روابط/وسائط)
    if text:
        warned = False
        for bad in BAD_WORDS:
            if bad in text:
                user_warnings[uid] += 1
                warned = True
                try:
                    bot.delete_message(cid, message.message_id)
                except:
                    pass
                bot.send_message(cid, f"⚠️ {name} تم تحذيره! مجموع التحذيرات: {user_warnings[uid]}")
                break

        # إجراءات بعد عدد معين من التحذيرات
        if warned and user_warnings[uid] >= 3:
            try:
                bot.kick_chat_member(cid, uid)
                bot.send_message(cid, f"🚨 {name} تم طرده بعد 3 تحذيرات!")
                user_warnings[uid] = 0  # إعادة ضبط التحذيرات بعد الطرد
            except:
                pass# ================== منع الروابط ==================
if not is_admin and is_locked(cid, "lock_links"):
    if text:
        link_pattern = re.compile(r"(https?://\S+|t\.me/\S+)")
        if link_pattern.search(text):
            try:
                bot.delete_message(cid, message.message_id)
                user_warnings[uid] += 1
                bot.send_message(cid, f"🚫 {name} ممنوع نشر الروابط! تحذير {user_warnings[uid]}/3")
            except:
                pass

            # طرد بعد 3 تحذيرات
            if user_warnings[uid] >= 3:
                try:
                    bot.kick_chat_member(cid, uid)
                    bot.send_message(cid, f"🚨 {name} تم طرده بعد 3 تحذيرات!")
                    user_warnings[uid] = 0
                except:
                    pass
            return# ================== إعادة ضبط التحذيرات ==================
@bot.message_handler(commands=["مسح_تحذيرات"])
def reset_warnings(message):
    cid = message.chat.id
    uid = message.from_user.id
    status = bot.get_chat_member(cid, uid).status
    if status in ["administrator", "creator"]:
        user_warnings.clear()
        bot.reply_to(message, "✅ تم مسح جميع التحذيرات لكل الأعضاء.")
    else:
        bot.reply_to(message, "❌ أنت لست مشرفاً لاستخدام هذا الأمر.")

# ================== أوامر إدارية إضافية ==================
@bot.message_handler(commands=["حظر", "طرد"])
def admin_commands(message):
    cid = message.chat.id
    uid = message.from_user.id
    status = bot.get_chat_member(cid, uid).status
    if status not in ["administrator", "creator"]:
        bot.reply_to(message, "❌ لا تملك صلاحيات لاستخدام هذا الأمر.")
        return

    if not message.reply_to_message:
        bot.reply_to(message, "❌ الرجاء الرد على رسالة العضو المراد حظره أو طرده.")
        return

    target_id = message.reply_to_message.from_user.id

    if message.text.startswith("/حظر"):
        try:
            bot.kick_chat_member(cid, target_id)
            bot.reply_to(message, f"🚫 تم حظر العضو بنجاح!")
        except:
            bot.reply_to(message, "❌ حدث خطأ أثناء الحظر.")
    elif message.text.startswith("/طرد"):
        try:
            bot.kick_chat_member(cid, target_id)
            bot.reply_to(message, f"🚨 تم طرد العضو من المجموعة!")
        except:
            bot.reply_to(message, "❌ حدث خطأ أثناء الطرد.")# ================== تقييد الروابط ==================
@bot.message_handler(func=lambda m: True, content_types=["text"])
def link_filter(message):
    cid = message.chat.id
    uid = message.from_user.id
    status = bot.get_chat_member(cid, uid).status
    text = message.text or ""

    if not is_locked(cid, "lock_links"):
        return

    if status in ["administrator", "creator"]:
        return

    # البحث عن روابط
    links = re.findall(r"(https?://[^\s]+)", text)
    if links:
        try:
            bot.delete_message(cid, message.message_id)
            user_warnings[uid] += 1
            bot.send_message(cid, f"⚠️ {message.from_user.first_name} ممنوع إرسال الروابط! التحذير ({user_warnings[uid]}/3)")
            if user_warnings[uid] >= 3:
                bot.restrict_chat_member(cid, uid, until_date=int(time.time()) + 3600)
                bot.send_message(cid, f"🚫 {message.from_user.first_name} تم تقييد العضو لمدة ساعة بسبب تكرار الروابط.")
                user_warnings[uid] = 0
        except:
            pass# ================== مكافحة إعادة التوجيه ==================
@bot.message_handler(func=lambda m: True, content_types=["forward"])
def forward_filter(message):
    cid = message.chat.id
    uid = message.from_user.id
    status = bot.get_chat_member(cid, uid).status

    if not is_locked(cid, "lock_forward"):
        return

    if status in ["administrator", "creator"]:
        return

    try:
        bot.delete_message(cid, message.message_id)
        user_warnings[uid] += 1
        bot.send_message(cid, f"⚠️ {message.from_user.first_name} ممنوع إعادة التوجيه! التحذير ({user_warnings[uid]}/3)")
        if user_warnings[uid] >= 3:
            bot.restrict_chat_member(cid, uid, until_date=int(time.time()) + 3600)
            bot.send_message(cid, f"🚫 {message.from_user.first_name} تم تقييد العضو لمدة ساعة بسبب تكرار إعادة التوجيه.")
            user_warnings[uid] = 0
    except:
        pass# ================== حماية متقدمة ==================
@bot.message_handler(func=lambda m: True, content_types=["text", "photo", "video", "document", "forward"])
def advanced_protection(message):
    cid = message.chat.id
    uid = message.from_user.id
    name = message.from_user.first_name
    text = message.text or ""
    
    status = bot.get_chat_member(cid, uid).status
    is_admin = status in ["administrator", "creator"]

    # ================== قفل الروابط المتقدم ==================
    if not is_admin and is_locked(cid, "lock_links"):
        if re.search(r'http[s]?://', text):
            try:
                bot.delete_message(cid, message.message_id)
                user_warnings[uid] += 1
                bot.send_message(cid, f"🚫 {name} ممنوع إرسال روابط! (تحذير {user_warnings[uid]})")
                if user_warnings[uid] >= 3:
                    bot.kick_chat_member(cid, uid)
                    bot.send_message(cid, f"⚠️ {name} تم طرده بعد 3 تحذيرات!")
                    user_warnings[uid] = 0
            except:
                pass
            return

    # ================== قفل إعادة التوجيه ==================
    if not is_admin and is_locked(cid, "lock_forward"):
        if message.forward_from or message.forward_from_chat:
            try:
                bot.delete_message(cid, message.message_id)
                user_warnings[uid] += 1
                bot.send_message(cid, f"🚫 {name} ممنوع إعادة التوجيه! (تحذير {user_warnings[uid]})")
                if user_warnings[uid] >= 3:
                    bot.kick_chat_member(cid, uid)
                    bot.send_message(cid, f"⚠️ {name} تم طرده بعد 3 تحذيرات!")
                    user_warnings[uid] = 0
            except:
                pass
            return

    # ================== قفل المستندات ==================
    if not is_admin and is_locked(cid, "lock_media"):
        if message.content_type == "document":
            try:
                bot.delete_message(cid, message.message_id)
                user_warnings[uid] += 1
                bot.send_message(cid, f"🚫 {name} ممنوع إرسال مستندات! (تحذير {user_warnings[uid]})")
                if user_warnings[uid] >= 3:
                    bot.kick_chat_member(cid, uid)
                    bot.send_message(cid, f"⚠️ {name} تم طرده بعد 3 تحذيرات!")
                    user_warnings[uid] = 0
            except:
                pass
            return# ================== فلترة سب متقدمة ==================
@bot.message_handler(func=lambda m: True, content_types=["text"])
def smart_filter(message):
    cid = message.chat.id
    uid = message.from_user.id
    name = message.from_user.first_name
    text = message.text or ""
    
    status = bot.get_chat_member(cid, uid).status
    is_admin = status in ["administrator", "creator"]

    # ================== سب ذكي ==================
    if not is_admin:
        lowered = text.lower()
        for bad in BAD_WORDS:
            if bad in lowered:
                user_warnings[uid] += 1
                try:
                    bot.delete_message(cid, message.message_id)
                    bot.send_message(cid, f"🚫 {name} ممنوع السب! (تحذير {user_warnings[uid]})")
                    if user_warnings[uid] >= 3:
                        bot.kick_chat_member(cid, uid)
                        bot.send_message(cid, f"⚠️ {name} تم طرده بعد 3 تحذيرات!")
                        user_warnings[uid] = 0
                except:
                    pass
                return

    # ================== سبام متكرر ==================
    if not is_admin and is_locked(cid, "anti_spam"):
        now = time.time()
        user_messages[uid] = [t for t in user_messages[uid] if now - t < 3]
        user_messages[uid].append(now)
        if len(user_messages[uid]) > 5:
            try:
                bot.restrict_chat_member(cid, uid, until_date=int(now) + 3600)
                bot.send_message(cid, f"⚠️ {name} كتم ساعة بسبب السبام المتكرر")
            except:
                pass# ================== حماية الملفات والفيديوهات الكبيرة ==================
@bot.message_handler(func=lambda m: True, content_types=["photo", "video", "document"])
def media_protection(message):
    cid = message.chat.id
    uid = message.from_user.id
    name = message.from_user.first_name

    status = bot.get_chat_member(cid, uid).status
    is_admin = status in ["administrator", "creator"]

    # قفل الوسائط إذا مفعل
    if not is_admin and is_locked(cid, "lock_media"):
        try:
            bot.delete_message(cid, message.message_id)
            bot.send_message(cid, f"🚫 {name} ممنوع إرسال صور/فيديو/ملفات في الوقت الحالي!")
        except:
            pass
        return

    # حماية ضد الملفات الكبيرة
    if not is_admin:
        if message.content_type == "document" and message.document.file_size > 5 * 1024 * 1024:  # 5 ميجا
            try:
                bot.delete_message(cid, message.message_id)
                bot.send_message(cid, f"🚫 {name} الملف كبير جداً (>5MB)، ممنوع إرساله!")
            except:
                pass
            return

    # حماية ضد الصور المكررة (يمكن توسيعها لاحقاً بالتعرف على الصور)
    if not is_admin and message.content_type == "photo":
        # تخزين معرف الصورة لتجنب التكرار (هنا مثال بسيط باستخدام file_id)
        if not hasattr(bot, "sent_photos"):
            bot.sent_photos = defaultdict(set)
        photo_id = message.photo[-1].file_id
        if photo_id in bot.sent_photos[cid]:
            try:
                bot.delete_message(cid, message.message_id)
                bot.send_message(cid, f"🚫 {name} لا يمكن إعادة إرسال نفس الصورة!")
            except:
                pass
        else:
            bot.sent_photos[cid].add(photo_id)# ================== حماية الروابط والفوروورد المكرر ==================
@bot.message_handler(func=lambda m: True, content_types=["text", "forward"])
def link_forward_protection(message):
    cid = message.chat.id
    uid = message.from_user.id
    name = message.from_user.first_name

    status = bot.get_chat_member(cid, uid).status
    is_admin = status in ["administrator", "creator"]

    text = message.text or ""

    # قفل الروابط إذا مفعل
    if not is_admin and is_locked(cid, "lock_links"):
        if re.search(r"(https?://|t.me/)", text):
            try:
                bot.delete_message(cid, message.message_id)
                bot.send_message(cid, f"🚫 {name} ممنوع نشر الروابط!")
            except:
                pass
            return

    # مكافحة الفوروورد المكرر
    if not is_admin:
        if is_locked(cid, "lock_forward") and getattr(message, "forward_from", None):
            try:
                bot.delete_message(cid, message.message_id)
                bot.send_message(cid, f"🚫 {name} ممنوع إعادة توجيه الرسائل!")
            except:
                pass
            return# ================== حماية متقدمة ==================
@bot.message_handler(func=lambda m: True, content_types=["text", "photo", "video", "document", "forward"])
def advanced_protection(message):
    cid = message.chat.id
    uid = message.from_user.id
    name = message.from_user.first_name
    text = message.text or ""

    status = bot.get_chat_member(cid, uid).status
    is_admin = status in ["administrator", "creator"]

    if is_admin:
        return

    warned = False

    # ================== فلترة السب ==================
    for bad in BAD_WORDS:
        if bad in text:
            warned = True
            user_warnings[uid] += 1
            break

    # ================== قفل الروابط ==================
    if is_locked(cid, "lock_links") and re.search(r"(https?://|t.me/)", text):
        warned = True
        user_warnings[uid] += 1
        try:
            bot.delete_message(cid, message.message_id)
        except:
            pass

    # ================== قفل الفوروورد ==================
    if is_locked(cid, "lock_forward") and getattr(message, "forward_from", None):
        warned = True
        user_warnings[uid] += 1
        try:
            bot.delete_message(cid, message.message_id)
        except:
            pass

    # ================== قفل الوسائط ==================
    if is_locked(cid, "lock_media") and message.content_type in ["photo", "video"]:
        warned = True
        user_warnings[uid] += 1
        try:
            bot.delete_message(cid, message.message_id)
        except:
            pass

    # ================== نظام التحذيرات ==================
    MAX_WARNINGS = 3
    if warned:
        remaining = MAX_WARNINGS - user_warnings[uid]
        if remaining > 0:
            bot.send_message(cid, f"⚠️ {name} تم تحذيرك! تبقى {remaining} تحذيرات.")
        else:
            now = time.time()
            bot.restrict_chat_member(cid, uid, until_date=int(now) + 3600)
            bot.send_message(cid, f"🚫 {name} تم كتمه ساعة بسبب تجاوز التحذيرات!")
            user_warnings[uid] = 0# ================== حماية ضد الرسائل المكررة ==================
@bot.message_handler(func=lambda m: True, content_types=["text", "photo", "video", "document", "forward"])
def anti_flood_protection(message):
    cid = message.chat.id
    uid = message.from_user.id
    name = message.from_user.first_name

    status = bot.get_chat_member(cid, uid).status
    is_admin = status in ["administrator", "creator"]

    if is_admin:
        return

    now = time.time()
    # تنظيف الرسائل القديمة من القائمة
    user_messages[uid] = [t for t in user_messages[uid] if now - t < 5]
    user_messages[uid].append(now)

    if len(user_messages[uid]) > 5:
        try:
            bot.restrict_chat_member(cid, uid, until_date=int(now) + 3600)
            bot.send_message(cid, f"🚫 {name} تم كتمه ساعة بسبب الرسائل المكررة!")
        except:
            pass
        return

    # ================== نظام تحذيرات تلقائي ==================
    warned = False

    # فلترة السب
    for bad in BAD_WORDS:
        if getattr(message, "text", "") and bad in message.text:
            warned = True
            user_warnings[uid] += 1
            break

    # قفل الروابط
    if is_locked(cid, "lock_links") and getattr(message, "text", "") and re.search(r"(https?://|t.me/)", message.text):
        warned = True
        user_warnings[uid] += 1
        try:
            bot.delete_message(cid, message.message_id)
        except:
            pass

    # قفل الوسائط
    if is_locked(cid, "lock_media") and message.content_type in ["photo", "video"]:
        warned = True
        user_warnings[uid] += 1
        try:
            bot.delete_message(cid, message.message_id)
        except:
            pass

    # التعامل مع التحذيرات
    MAX_WARNINGS = 3
    if warned:
        remaining = MAX_WARNINGS - user_warnings[uid]
        if remaining > 0:
            bot.send_message(cid, f"⚠️ {name} تم تحذيرك! تبقى {remaining} تحذيرات.")
        else:
            try:
                bot.restrict_chat_member(cid, uid, until_date=int(now) + 3600)
                bot.send_message(cid, f"🚫 {name} تم كتمه ساعة بسبب تجاوز التحذيرات!")
            except:
                pass
            user_warnings[uid] = 0# ================== منع إعادة التوجيه ==================
@bot.message_handler(func=lambda m: True, content_types=["forward"])
def forward_lock(message):
    cid = message.chat.id
    uid = message.from_user.id
    name = message.from_user.first_name

    status = bot.get_chat_member(cid, uid).status
    is_admin = status in ["administrator", "creator"]

    if is_admin:
        return

    if is_locked(cid, "lock_forward"):
        try:
            bot.delete_message(cid, message.message_id)
            bot.send_message(cid, f"🚫 {name} ممنوع إعادة توجيه الرسائل!")
        except:
            pass

# ================== مراقبة الروابط ==================
@bot.message_handler(func=lambda m: True, content_types=["text"])
def link_monitor(message):
    cid = message.chat.id
    uid = message.from_user.id
    name = message.from_user.first_name
    text = message.text or ""

    status = bot.get_chat_member(cid, uid).status
    is_admin = status in ["administrator", "creator"]

    if is_admin:
        return

    if is_locked(cid, "lock_links") and re.search(r"(https?://|t.me/)", text):
        try:
            bot.delete_message(cid, message.message_id)
            user_warnings[uid] += 1
            bot.send_message(cid, f"⚠️ {name} تم تحذيرك لإرسال روابط غير مسموحة!")
        except:
            pass

        # إذا تجاوز التحذيرات
        if user_warnings[uid] >= 3:
            try:
                bot.restrict_chat_member(cid, uid, until_date=int(time.time()) + 3600)
                bot.send_message(cid, f"🚫 {name} تم كتمه ساعة بسبب تجاوز التحذيرات!")
            except:
                pass
            user_warnings[uid] = 0

# ================== مراقبة أسماء المستخدمين ==================
@bot.message_handler(func=lambda m: True, content_types=["new_chat_members"])
def username_monitor(message):
    cid = message.chat.id
    for u in message.new_chat_members:
        try:
            if re.search(r"(كلب|حمار|تفه|غبي)", u.username or "", re.IGNORECASE):
                bot.kick_chat_member(cid, u.id)
                bot.send_message(cid, f"🚫 تم طرد {u.first_name} بسبب اسم مستخدم مسيء!")
        except:
            pass# ================== فلترة سب متقدمة ==================
@bot.message_handler(func=lambda m: True, content_types=["text"])
def advanced_badwords_filter(message):
    cid = message.chat.id
    uid = message.from_user.id
    name = message.from_user.first_name
    text = message.text or ""

    status = bot.get_chat_member(cid, uid).status
    is_admin = status in ["administrator", "creator"]

    if is_admin:
        return

    # قائمة موسعة للكلمات المسيئة (بمتغيرات)
    extended_badwords = [w for w in BAD_WORDS] + ["ابن حرام", "غباء", "تخلف"]
    pattern = "|".join([re.escape(w) for w in extended_badwords])

    if re.search(pattern, text, re.IGNORECASE):
        try:
            bot.delete_message(cid, message.message_id)
            user_warnings[uid] += 1
            bot.send_message(cid, f"🚫 {name} تم تحذيرك بسبب استخدام كلمات مسيئة!")
        except:
            pass

        if user_warnings[uid] >= 3:
            try:
                bot.restrict_chat_member(cid, uid, until_date=int(time.time()) + 3600)
                bot.send_message(cid, f"⚠️ {name} تم كتمه ساعة بسبب تكرار الإساءة!")
            except:
                pass
            user_warnings[uid] = 0

# ================== منع السبام البصري ==================
@bot.message_handler(func=lambda m: True, content_types=["text"])
def emoji_spam_monitor(message):
    cid = message.chat.id
    uid = message.from_user.id
    text = message.text or ""

    status = bot.get_chat_member(cid, uid).status
    is_admin = status in ["administrator", "creator"]

    if is_admin:
        return

    # عد الإيموجي في الرسالة
    emoji_count = len(re.findall(r"[^\w\s,]", text))
    if emoji_count > 10:  # أكثر من 10 رموز/إيموجي
        try:
            bot.delete_message(cid, message.message_id)
            bot.send_message(cid, f"🚫 {message.from_user.first_name} ممنوع إرسال رسائل مليئة بالإيموجي!")
        except:
            pass

# ================== منع الملصقات المزعجة ==================
@bot.message_handler(func=lambda m: True, content_types=["sticker"])
def sticker_lock(message):
    cid = message.chat.id
    uid = message.from_user.id

    status = bot.get_chat_member(cid, uid).status
    is_admin = status in ["administrator", "creator"]

    if is_admin:
        return

    # إذا تم تفعيل قفل الملصقات
    if is_locked(cid, "lock_media"):
        try:
            bot.delete_message(cid, message.message_id)
            bot.send_message(cid, f"🚫 {message.from_user.first_name} ممنوع إرسال الملصقات!")
        except:
            pass# ================== أوامر الإدارة ==================
@bot.message_handler(func=lambda m: True, content_types=["text"])
def admin_commands(message):
    cid = message.chat.id
    uid = message.from_user.id
    text = message.text or ""

    status = bot.get_chat_member(cid, uid).status
    is_admin = status in ["administrator", "creator"]
    is_owner = uid == 1234567890  # ضع هنا ID صاحب المجموعة الأساسي
    is_dev = uid == 9876543210    # ضع هنا ID المطور الأساسي

    # ================== أوامر المشرفين ==================
    if is_admin or is_owner or is_dev:
        if text == "تحذير":
            bot.reply_to(message, "⚠️ استخدم هذا الأمر لتحذير الأعضاء المخالفين.")
        elif text.startswith("كتم "):
            try:
                target_id = int(text.split(" ")[1])
                bot.restrict_chat_member(cid, target_id, until_date=int(time.time()) + 3600)
                bot.send_message(cid, f"🔇 تم كتم العضو {target_id} لمدة ساعة.")
            except:
                bot.reply_to(message, "❌ خطأ في الأمر، استخدم: كتم <ايدي>")
        elif text.startswith("حظر "):
            try:
                target_id = int(text.split(" ")[1])
                bot.kick_chat_member(cid, target_id)
                bot.send_message(cid, f"🚫 تم حظر العضو {target_id} من المجموعة.")
            except:
                bot.reply_to(message, "❌ خطأ في الأمر، استخدم: حظر <ايدي>")

    # ================== أوامر المطور الأساسي ==================
    if is_dev:
        if text == "تفعيل كل الأنظمة":
            set_lock(cid, "lock_links", 1)
            set_lock(cid, "lock_forward", 1)
            set_lock(cid, "lock_media", 1)
            set_lock(cid, "anti_spam", 1)
            bot.send_message(cid, "✅ تم تفعيل كل أنظمة الحماية القصوى!")
        elif text == "تعطيل كل الأنظمة":
            set_lock(cid, "lock_links", 0)
            set_lock(cid, "lock_forward", 0)
            set_lock(cid, "lock_media", 0)
            set_lock(cid, "anti_spam", 0)
            bot.send_message(cid, "❌ تم تعطيل كل أنظمة الحماية!")

    # ================== أوامر المراقبين ==================
    if status == "member":
        if text == "تقرير":
            bot.reply_to(message, "📝 استخدم هذا الأمر لإرسال تقرير إلى الإدارة.")

# ================== مراقبة الروابط الدعائية ==================
@bot.message_handler(func=lambda m: True, content_types=["text"])
def link_filter(message):
    cid = message.chat.id
    uid = message.from_user.id
    text = message.text or ""

    status = bot.get_chat_member(cid, uid).status
    is_admin = status in ["administrator", "creator"]

    if is_locked(cid, "lock_links") and not is_admin:
        if re.search(r"(https?://\S+)", text):
            try:
                bot.delete_message(cid, message.message_id)
                bot.send_message(cid, f"🚫 {message.from_user.first_name} ممنوع إرسال روابط!")
            except:
                pass# ================== مراقبة الملفات والميديا ==================
@bot.message_handler(func=lambda m: True, content_types=["document", "photo", "video", "audio"])
def media_filter(message):
    cid = message.chat.id
    uid = message.from_user.id
    status = bot.get_chat_member(cid, uid).status
    is_admin = status in ["administrator", "creator"]

    # حماية من الملفات الكبيرة والميديا
    if not is_admin:
        # ================== قفل الملفات الثقيلة ==================
        if message.content_type == "document" and message.document.file_size > 10*1024*1024:  # أكبر من 10MB
            try:
                bot.delete_message(cid, message.message_id)
                bot.send_message(cid, f"🚫 {message.from_user.first_name} ممنوع إرسال ملفات أكبر من 10MB!")
            except:
                pass

        # ================== قفل الفيديوهات الطويلة ==================
        if message.content_type == "video" and message.video.duration > 300:  # أطول من 5 دقائق
            try:
                bot.delete_message(cid, message.message_id)
                bot.send_message(cid, f"🚫 {message.from_user.first_name} ممنوع إرسال فيديو أطول من 5 دقائق!")
            except:
                pass

        # ================== قفل الصور والفيديوهات إذا مفعل ==================
        if is_locked(cid, "lock_media"):
            if message.content_type in ["photo", "video"]:
                try:
                    bot.delete_message(cid, message.message_id)
                    bot.send_message(cid, f"🚫 {message.from_user.first_name} ممنوع إرسال صور/فيديوهات!")
                except:
                    pass

# ================== ذكاء سب متقدم ==================
@bot.message_handler(func=lambda m: True, content_types=["text"])
def smart_filter(message):
    cid = message.chat.id
    uid = message.from_user.id
    text = message.text or ""
    status = bot.get_chat_member(cid, uid).status
    is_admin = status in ["administrator", "creator"]

    # ================== فلترة متقدمة ==================
    if not is_admin:
        lower_text = text.lower()
        for bad in BAD_WORDS:
            if bad in lower_text:
                user_warnings[uid] += 1
                try:
                    bot.delete_message(cid, message.message_id)
                    if user_warnings[uid] == 1:
                        bot.send_message(cid, f"⚠️ {message.from_user.first_name} تم تحذيره للمرة الأولى بسبب السب!")
                    elif user_warnings[uid] == 2:
                        bot.send_message(cid, f"⚠️ {message.from_user.first_name} تم تحذيره للمرة الثانية، الحذر!")
                    elif user_warnings[uid] >= 3:
                        bot.kick_chat_member(cid, uid)
                        bot.send_message(cid, f"🚫 {message.from_user.first_name} تم طرده بسبب تكرار السب!")
                        user_warnings[uid] = 0
                except:
                    pass# ================== قفل الروابط المتقدم ==================
@bot.message_handler(func=lambda m: True, content_types=["text"])
def link_filter(message):
    cid = message.chat.id
    uid = message.from_user.id
    text = message.text or ""
    status = bot.get_chat_member(cid, uid).status
    is_admin = status in ["administrator", "creator"]

    if not is_admin and is_locked(cid, "lock_links"):
        # البحث عن روابط داخل الرسالة
        if re.search(r"(https?://|t\.me/)", text):
            try:
                bot.delete_message(cid, message.message_id)
                bot.send_message(cid, f"🚫 {message.from_user.first_name} ممنوع نشر الروابط!")
            except:
                pass

# ================== مراقبة الرسائل المعاد توجيهها ==================
@bot.message_handler(func=lambda m: True, content_types=["forward"])
def forward_filter(message):
    cid = message.chat.id
    uid = message.from_user.id
    status = bot.get_chat_member(cid, uid).status
    is_admin = status in ["administrator", "creator"]

    if not is_admin and is_locked(cid, "lock_forward"):
        try:
            bot.delete_message(cid, message.message_id)
            bot.send_message(cid, f"🚫 {message.from_user.first_name} ممنوع إعادة توجيه الرسائل!")
        except:
            pass

# ================== أوامر خاصة بالمشرفين والمدراء ==================
@bot.message_handler(func=lambda m: True, content_types=["text"])
def admin_commands(message):
    cid = message.chat.id
    uid = message.from_user.id
    text = message.text or ""
    status = bot.get_chat_member(cid, uid).status
    ranks = ["administrator", "creator"]

    if status in ranks:
        # كتم عضو
        if text.startswith("كتم "):
            try:
                target_id = int(re.findall(r"\d+", text)[0])
                bot.restrict_chat_member(cid, target_id, until_date=int(time.time()) + 3600)
                bot.send_message(cid, f"🔇 العضو {target_id} تم كتمه لمدة ساعة")
            except:
                bot.send_message(cid, "❌ فشل تنفيذ الأمر، تأكد من الصياغة")

        # رفع عضو إلى رتبة معينة
        if text.startswith("رفع "):
            try:
                parts = text.split()
                target_id = int(parts[1])
                rank_name = parts[2]
                conn = sqlite3.connect('goat_bot.db')
                c = conn.cursor()
                c.execute("INSERT OR REPLACE INTO ranks (chat_id, user_id, rank) VALUES (?, ?, ?)", (cid, target_id, rank_name))
                conn.commit()
                conn.close()
                bot.send_message(cid, f"🎖️ العضو {target_id} تمت ترقيته إلى رتبة {rank_name}")
            except:
                bot.send_message(cid, "❌ فشل تنفيذ الأمر، تأكد من الصياغة")# ================== أوامر المطور الأساسي ==================
DEVELOPER_ID = 123456789  # ضع هنا آيدي المطور الأساسي

@bot.message_handler(func=lambda m: True, content_types=["text"])
def developer_commands(message):
    cid = message.chat.id
    uid = message.from_user.id
    text = message.text or ""

    if uid != DEVELOPER_ID:
        return  # فقط المطور الأساسي يستطيع استخدام هذه الأوامر

    # إعادة تشغيل البوت
    if text == "اعادة تشغيل":
        bot.send_message(cid, "🔄 جاري إعادة تشغيل البوت...")
        os.execl(sys.executable, sys.executable, *sys.argv)

    # إرسال رسالة لجميع المجموعات
    if text.startswith("رسالة عام "):
        try:
            broadcast = text.replace("رسالة عام ", "")
            conn = sqlite3.connect('goat_bot.db')
            c = conn.cursor()
            c.execute("SELECT chat_id FROM groups")
            groups = c.fetchall()
            conn.close()
            for g in groups:
                try:
                    bot.send_message(g[0], f"📢 رسالة من المطور:\n{broadcast}")
                except:
                    pass
            bot.send_message(cid, "✅ تم إرسال الرسالة لجميع المجموعات")
        except:
            bot.send_message(cid, "❌ فشل إرسال الرسالة")

    # حظر أي عضو من كل المجموعات
    if text.startswith("حظر عام "):
        try:
            target_id = int(text.split()[2])
            conn = sqlite3.connect('goat_bot.db')
            c = conn.cursor()
            c.execute("SELECT chat_id FROM groups")
            groups = c.fetchall()
            conn.close()
            for g in groups:
                try:
                    bot.kick_chat_member(g[0], target_id)
                except:
                    pass
            bot.send_message(cid, f"🚫 تم حظر العضو {target_id} من جميع المجموعات")
        except:
            bot.send_message(cid, "❌ فشل تنفيذ الأمر، تأكد من الرقم")# ================== أوامر المالك / الأساسي للقروب ==================
@bot.message_handler(func=lambda m: True, content_types=["text"])
def owner_commands(message):
    cid = message.chat.id
    uid = message.from_user.id
    text = message.text or ""

    # جلب معلومات العضو
    if text.startswith("معلومات "):
        if get_rank(cid, uid) != "مالك":
            return  # فقط المالك يستطيع استخدام الأمر
        try:
            target_id = int(text.split()[1])
            member = bot.get_chat_member(cid, target_id)
            bot.send_message(cid, f"🧾 معلومات العضو:\n"
                                  f"الاسم: {member.user.first_name}\n"
                                  f"ايدي: {member.user.id}\n"
                                  f"الحالة: {member.status}")
        except:
            bot.send_message(cid, "❌ لم أتمكن من جلب المعلومات")

    # طرد عضو من القروب
    if text.startswith("طرد "):
        if get_rank(cid, uid) != "مالك":
            return
        try:
            target_id = int(text.split()[1])
            bot.kick_chat_member(cid, target_id)
            bot.send_message(cid, f"🚫 تم طرد العضو {target_id}")
        except:
            bot.send_message(cid, "❌ فشل تنفيذ الأمر، تأكد من الرقم")

    # تعيين رتبة عضو
    if text.startswith("رتبة "):
        if get_rank(cid, uid) != "مالك":
            return
        try:
            parts = text.split()
            target_id = int(parts[1])
            rank_name = parts[2]
            conn = sqlite3.connect('goat_bot.db')
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO ranks (chat_id, user_id, rank) VALUES (?, ?, ?)",
                      (cid, target_id, rank_name))
            conn.commit()
            conn.close()
            bot.send_message(cid, f"🎖️ تم تعيين رتبة {rank_name} للعضو {target_id}")
        except:
            bot.send_message(cid, "❌ فشل تعيين الرتبة، تأكد من الصياغة")

    # حظر روابط داخل القروب
    if text == "قفل الروابط":
        if get_rank(cid, uid) != "مالك":
            return
        set_lock(cid, "lock_links", 1)
        bot.send_message(cid, "🚫 تم قفل الروابط داخل القروب")# ================== تفعيل جميع الأوامر المبرمجة ==================
@bot.message_handler(func=lambda m: True, content_types=["text"])
def all_commands(message):
    cid = message.chat.id
    uid = message.from_user.id
    text = message.text or ""
    user_rank = get_rank(cid, uid)

    # أوامر عامة لجميع الأعضاء
    if text == "ايدي":
        bot.reply_to(message, f"🆔 ايديك: <code>{uid}</code>\n🎖️ رتبتك: {user_rank}")

    if text == "الاوامر":
        bot.reply_to(message, "📜 قائمة الأوامر", reply_markup=main_markup())

    # أوامر المشرفين والإداريين
    if user_rank in ["مشرف", "إداري", "مدير", "مراقب شات"]:
        if text == "قفل الروابط":
            set_lock(cid, "lock_links", 1)
            bot.reply_to(message, "🚫 تم قفل الروابط")
        elif text == "فتح الروابط":
            set_lock(cid, "lock_links", 0)
            bot.reply_to(message, "🔓 تم فتح الروابط")
        elif text == "قفل الصور":
            set_lock(cid, "lock_media", 1)
            bot.reply_to(message, "🚫 تم قفل الصور والفيديو")
        elif text == "فتح الصور":
            set_lock(cid, "lock_media", 0)
            bot.reply_to(message, "🔓 تم فتح الصور والفيديو")
        elif text == "تفعيل":
            set_lock(cid, "is_active", 1)
            bot.reply_to(message, "✅ تم تفعيل البوت")
        elif text == "تعطيل":
            set_lock(cid, "is_active", 0)
            bot.reply_to(message, "❌ تم تعطيل البوت")

    # أوامر المالك / الأساسي
    if user_rank == "مالك":
        if text.startswith("طرد "):
            try:
                target_id = int(text.split()[1])
                bot.kick_chat_member(cid, target_id)
                bot.send_message(cid, f"🚫 تم طرد العضو {target_id}")
            except:
                bot.send_message(cid, "❌ فشل تنفيذ الأمر، تأكد من الرقم")

        if text.startswith("معلومات "):
            try:
                target_id = int(text.split()[1])
                member = bot.get_chat_member(cid, target_id)
                bot.send_message(cid, f"🧾 معلومات العضو:\n"
                                      f"الاسم: {member.user.first_name}\n"
                                      f"ايدي: {member.user.id}\n"
                                      f"الحالة: {member.status}")
            except:
                bot.send_message(cid, "❌ لم أتمكن من جلب المعلومات")

        if text.startswith("رتبة "):
            try:
                parts = text.split()
                target_id = int(parts[1])
                rank_name = parts[2]
                conn = sqlite3.connect('goat_bot.db')
                c = conn.cursor()
                c.execute("INSERT OR REPLACE INTO ranks (chat_id, user_id, rank) VALUES (?, ?, ?)",
                          (cid, target_id, rank_name))
                conn.commit()
                conn.close()
                bot.send_message(cid, f"🎖️ تم تعيين رتبة {rank_name} للعضو {target_id}")
            except:
                bot.send_message(cid, "❌ فشل تعيين الرتبة، تأكد من الصياغة")# ================== الحماية القصوى ==================
@bot.message_handler(func=lambda m: True, content_types=["text", "photo", "video", "document", "sticker", "forward"])
def ultimate_protection(message):
    cid = message.chat.id
    uid = message.from_user.id
    user_rank = get_rank(cid, uid)
    text = message.text or ""

    # حماية الروابط داخل المجموعة
    if is_locked(cid, "lock_links") and not user_rank in ["إداري", "مدير", "مالك", "المطور الأساسي"]:
        if re.search(r"(https?://\S+)", text):
            try:
                bot.delete_message(cid, message.message_id)
                bot.send_message(cid, f"🚫 {message.from_user.first_name} ممنوع إرسال روابط!")
            except:
                pass

    # منع التكرار والميديا الثقيلة
    if is_locked(cid, "lock_media") and not user_rank in ["إداري", "مدير", "مالك", "المطور الأساسي"]:
        if message.content_type in ["photo", "video", "document", "sticker"]:
            try:
                bot.delete_message(cid, message.message_id)
                bot.send_message(cid, f"🚫 {message.from_user.first_name} ممنوع إرسال صور/فيديو/ملفات!")
            except:
                pass

    # مكافحة السبام الذكي
    if is_locked(cid, "anti_spam") and not user_rank in ["إداري", "مدير", "مالك", "المطور الأساسي"]:
        now = time.time()
        user_messages[uid] = [t for t in user_messages[uid] if now - t < 5]
        user_messages[uid].append(now)
        if len(user_messages[uid]) > 4:
            try:
                bot.restrict_chat_member(cid, uid, until_date=int(now) + 3600)
                bot.send_message(cid, f"⚠️ {message.from_user.first_name} تم كتمه ساعة بسبب السبام")
            except:
                pass

    # فلترة كلمات السب الذكي
    for bad in BAD_WORDS:
        if bad in text and not user_rank in ["إداري", "مدير", "مالك", "المطور الأساسي"]:
            try:
                bot.delete_message(cid, message.message_id)
                bot.send_message(cid, f"🚫 {message.from_user.first_name} ممنوع السب في المجموعة!")
            except:
                pass# ================== أوامر المطور الأساسي ==================
@bot.message_handler(func=lambda m: True, content_types=["text"])
def dev_commands(message):
    cid = message.chat.id
    uid = message.from_user.id
    user_rank = get_rank(cid, uid)
    text = message.text or ""

    # هذه الأوامر مخصصة للمطور الأساسي فقط
    if user_rank == "المطور الأساسي":
        if text == "🔄 إعادة تشغيل البوت":
            bot.send_message(cid, "♻️ جاري إعادة تشغيل البوت...")
            os.execl(sys.executable, sys.executable, *sys.argv)

        elif text == "📊 إحصائيات المجموعة":
            members = bot.get_chat_members_count(cid)
            admins = [m.user.first_name for m in bot.get_chat_administrators(cid)]
            bot.send_message(cid, f"👥 عدد الأعضاء: {members}\n🛡️ المشرفين: {', '.join(admins)}")

        elif text == "🧹 مسح الرسائل":
            try:
                for msg_id in range(message.message_id - 100, message.message_id):
                    bot.delete_message(cid, msg_id)
                bot.send_message(cid, "🧹 تم مسح آخر 100 رسالة")
            except:
                pass

        elif text == "🔒 قفل الكل":
            set_lock(cid, "lock_links", 1)
            set_lock(cid, "lock_media", 1)
            set_lock(cid, "anti_spam", 1)
            bot.send_message(cid, "🔒 تم تفعيل جميع أنظمة الحماية القصوى")

        elif text == "🔓 فتح الكل":
            set_lock(cid, "lock_links", 0)
            set_lock(cid, "lock_media", 0)
            set_lock(cid, "anti_spam", 0)
            bot.send_message(cid, "🔓 تم تعطيل جميع أنظمة الحماية القصوى")# ================== أوامر المالكين والمدراء ==================
@bot.message_handler(func=lambda m: True, content_types=["text"])
def owner_admin_commands(message):
    cid = message.chat.id
    uid = message.from_user.id
    user_rank = get_rank(cid, uid)
    text = message.text or ""

    # أوامر المالك فقط
    if user_rank in ["المالك الأساسي", "المطور الأساسي"]:
        if text == "➕ إضافة مشرف":
            bot.send_message(cid, "👤 أرسل ايدي المستخدم لإضافته مشرفاً:")
        elif text.startswith("أضف مشرف "):
            try:
                target_id = int(text.split()[2])
                bot.promote_chat_member(cid, target_id, can_change_info=True, can_delete_messages=True,
                                        can_invite_users=True, can_restrict_members=True, can_pin_messages=True,
                                        can_promote_members=False)
                bot.send_message(cid, f"✅ تم إضافة المستخدم {target_id} كمشرف")
            except:
                bot.send_message(cid, "❌ حدث خطأ أثناء إضافة المشرف")

        if text == "📋 قائمة المحظورين":
            banned = bot.get_chat_administrators(cid)
            bot.send_message(cid, f"🛡️ قائمة الأعضاء الممنوعين: {', '.join([b.user.first_name for b in banned])}")

    # أوامر المدراء
    if user_rank in ["مدير", "المالك الأساسي", "المطور الأساسي"]:
        if text == "🛑 حظر مستخدم":
            bot.send_message(cid, "👤 أرسل ايدي المستخدم لحظره:")

        if text.startswith("حظر "):
            try:
                target_id = int(text.split()[1])
                bot.kick_chat_member(cid, target_id)
                bot.send_message(cid, f"✅ تم حظر المستخدم {target_id}")
            except:
                bot.send_message(cid, "❌ حدث خطأ أثناء الحظر")

        if text == "🔓 فك الحظر":
            bot.send_message(cid, "👤 أرسل ايدي المستخدم لفك الحظر:")

        if text.startswith("فك الحظر "):
            try:
                target_id = int(text.split()[2])
                bot.unban_chat_member(cid, target_id)
                bot.send_message(cid, f"✅ تم فك الحظر عن المستخدم {target_id}")
            except:
                bot.send_message(cid, "❌ حدث خطأ أثناء فك الحظر")

    # أوامر المراقب
    if user_rank in ["مراقب", "مدير", "المالك الأساسي", "المطور الأساسي"]:
        if text == "👀 مشاهدة الرسائل":
            bot.send_message(cid, "📌 المراقب يمكنه الآن مشاهدة الرسائل دون التدخل")# ================== أوامر المطور الأساسي ==================
@bot.message_handler(func=lambda m: True, content_types=["text"])
def developer_commands(message):
    cid = message.chat.id
    uid = message.from_user.id
    user_rank = get_rank(cid, uid)
    text = message.text or ""

    # مطور أساسي فقط
    if user_rank == "المطور الأساسي":
        if text == "🚀 إعادة تشغيل البوت":
            bot.send_message(cid, "♻️ جاري إعادة تشغيل البوت...")
            os.execv(sys.executable, ['python'] + sys.argv)

        elif text == "📝 تحديث قاعدة البيانات":
            try:
                setup_db()
                bot.send_message(cid, "✅ تم تحديث قاعدة البيانات بنجاح")
            except:
                bot.send_message(cid, "❌ حدث خطأ أثناء التحديث")

        elif text == "⚙️ ضبط إعدادات عامة":
            bot.send_message(cid, "🔧 أرسل الإعدادات الجديدة على شكل: 'الخاصية القيمة'")

        elif text.startswith("تحديث "):
            try:
                parts = text.split()
                column = parts[1]
                value = int(parts[2])
                set_lock(cid, column, value)
                bot.send_message(cid, f"✅ تم تحديث {column} إلى {value}")
            except:
                bot.send_message(cid, "❌ خطأ في تحديث الإعدادات")

# ================== حماية قصوى إضافية ==================
@bot.message_handler(func=lambda m: True, content_types=["text", "photo", "video", "document"])
def ultimate_protection(message):
    cid = message.chat.id
    uid = message.from_user.id
    status = bot.get_chat_member(cid, uid).status
    is_admin = status in ["administrator", "creator"]

    text = message.text or ""

    # حذف الروابط والوسائط المشبوهة
    if not is_admin and is_locked(cid, "lock_links"):
        if re.search(r"(https?://|t.me/|telegram.me/)", text):
            try:
                bot.delete_message(cid, message.message_id)
                bot.send_message(cid, f"🚫 {message.from_user.first_name} ممنوع نشر روابط!")
            except:
                pass

    # فلترة متقدمة للسب
    if not is_admin:
        for bad in BAD_WORDS:
            if bad in text:
                user_warnings[uid] += 1
                bot.delete_message(cid, message.message_id)
                if user_warnings[uid] >= 3:
                    bot.kick_chat_member(cid, uid)
                    bot.send_message(cid, f"⚠️ {message.from_user.first_name} تم طرده بعد 3 تحذيرات")
                    user_warnings[uid] = 0
                else:
                    bot.send_message(cid, f"🚨 {message.from_user.first_name} تم تحذيره! ({user_warnings[uid]}/3)")
                return

# ================== تشغيل البوت ==================
bot.infinity_polling()# ================== أوامر الإدارة الكاملة ==================
@bot.message_handler(func=lambda m: True, content_types=["text"])
def full_commands(message):
    cid = message.chat.id
    uid = message.from_user.id
    user_rank = get_rank(cid, uid)
    text = message.text or ""

    # أوامر المشرفين والمدراء والمراقبين
    if user_rank in ["مشرف", "مدير", "مراقب"]:
        if text == "حظر":
            bot.reply_to(message, "أرسل معرف المستخدم أو قم برد على الرسالة لحظر العضو.")
        elif text == "طرد":
            bot.reply_to(message, "أرسل معرف المستخدم أو قم برد على الرسالة لطرد العضو.")
        elif text == "كتم":
            bot.reply_to(message, "أرسل معرف المستخدم أو قم برد على الرسالة لكتم العضو.")
        elif text == "الغاء الكتم":
            bot.reply_to(message, "أرسل معرف المستخدم أو قم برد على الرسالة لإلغاء الكتم.")

    # أوامر المالك والقائمين على القروب
    if user_rank in ["مالك", "المالك الأساسي"]:
        if text == "رفع مشرف":
            bot.reply_to(message, "أرسل معرف المستخدم لرفع رتبة مشرف.")
        elif text == "خفض مشرف":
            bot.reply_to(message, "أرسل معرف المستخدم لخفض رتبة المشرف.")
        elif text == "رفع مدير":
            bot.reply_to(message, "أرسل معرف المستخدم لرفع رتبة مدير.")
        elif text == "خفض مدير":
            bot.reply_to(message, "أرسل معرف المستخدم لخفض رتبة مدير.")

    # أوامر المطور الأساسي فقط
    if user_rank == "المطور الأساسي":
        if text == "تحديث كامل":
            bot.reply_to(message, "✅ جاري تحديث جميع الأنظمة والأوامر...")
            setup_db()  # تحديث قاعدة البيانات
        elif text == "تفعيل الحماية القصوى":
            set_lock(cid, "lock_links", 1)
            set_lock(cid, "lock_media", 1)
            set_lock(cid, "anti_spam", 1)
            bot.reply_to(message, "🔒 تم تفعيل جميع أنظمة الحماية القصوى.")

# ================== حماية إضافية ==================
@bot.message_handler(func=lambda m: True, content_types=["text", "photo", "video", "document"])
def enhanced_protection(message):
    cid = message.chat.id
    uid = message.from_user.id
    text = message.text or ""
    status = bot.get_chat_member(cid, uid).status
    is_admin = status in ["administrator", "creator"]

    # حظر الصور والفيديوهات بشكل تلقائي عند تفعيل القفل
    if not is_admin and is_locked(cid, "lock_media"):
        if message.content_type in ["photo", "video"]:
            try:
                bot.delete_message(cid, message.message_id)
                bot.send_message(cid, f"🚫 {message.from_user.first_name} ممنوع إرسال وسائط!")
            except:
                pass

    # مكافحة السبام والتكرار
    if not is_admin and is_locked(cid, "anti_spam"):
        now = time.time()
        user_messages[uid] = [t for t in user_messages[uid] if now - t < 3]
        user_messages[uid].append(now)
        if len(user_messages[uid]) > 5:
            bot.restrict_chat_member(cid, uid, until_date=int(now) + 3600)
            bot.send_message(cid, f"⚠️ {message.from_user.first_name} كتم ساعة بسبب السبام")
            return

# تشغيل البوت
bot.infinity_polling()# ================== التفعيل التلقائي ==================
@bot.message_handler(func=lambda m: m.text in ["تفعيل", "تفعيل البوت"], content_types=["text"])
def auto_activate(message):
    cid = message.chat.id
    uid = message.from_user.id
    status = bot.get_chat_member(cid, bot.get_me().id).status

    # تحقق من أن البوت مشرف
    if status not in ["administrator", "creator"]:
        bot.reply_to(message, "⚠️ يجب أن أكون مشرفاً لتفعيل البوت.")
        return

    set_lock(cid, "is_active", 1)

    # رسالة فخمة عند التفعيل
    txt = (
        f"✅ تم تفعيل XC GOAT في هذه المجموعة!\n\n"
        "🛡️ حماية متكاملة: السبام، السب، الصور والفيديوهات.\n"
        "🎮 تسلية وألعاب.\n"
        "🎵 بحث وتحميل موسيقي من يوتيوب.\n\n"
        "💡 ملاحظة: جميع الأوامر جاهزة للاستخدام.\n"
        "📌 اكتب 'الاوامر' لعرض القائمة الكاملة."
    )
    bot.send_photo(cid, PHOTO_URL, caption=txt, reply_markup=main_markup())

# ================== الردود التلقائية عند التفعيل ==================
@bot.message_handler(content_types=["new_chat_members"])
def welcome_activation(message):
    cid = message.chat.id
    for u in message.new_chat_members:
        if u.id == bot.get_me().id:
            # رسالة تفعيل تلقائي
            bot.send_photo(
                cid,
                PHOTO_URL,
                caption=(
                    "🌟 مرحباً! XC GOAT جاهز الآن لحماية وإدارة مجموعتك بشكل احترافي.\n"
                    "🛡️ جميع أنظمة الحماية مفعلة تلقائياً.\n"
                    "📌 استخدم 'الاوامر' لعرض كافة الأوامر."
                ),
                reply_markup=main_markup()
            )# ================== أوامر المطور الأساسي ==================
@bot.message_handler(func=lambda m: m.from_user.id == 123456789, content_types=["text"])  # ضع هنا ايدي المطور الأساسي
def dev_commands(message):
    text = message.text
    cid = message.chat.id

    if text == "🔒 قفل المجموعة":
        set_lock(cid, "is_active", 0)
        bot.reply_to(message, "🚫 تم قفل المجموعة مؤقتاً من قبل المطور الأساسي!")
    elif text == "🔓 فتح المجموعة":
        set_lock(cid, "is_active", 1)
        bot.reply_to(message, "✅ تم فتح المجموعة بنجاح من قبل المطور الأساسي!")
    elif text == "📢 رسالة جماعية":
        bot.reply_to(message, "💡 ارسل الرسالة التالية ليتم نشرها في كل المجموعات.")
        bot.register_next_step_handler(message, broadcast_message)
    elif text == "📌 تحديث الرابط":
        bot.reply_to(message, "💡 أرسل الرابط الجديد للمجموعة ليتم تحديثه.")
        bot.register_next_step_handler(message, update_group_link)

# ================== وظائف المطور ==================
def broadcast_message(message):
    text = message.text
    conn = sqlite3.connect('goat_bot.db')
    c = conn.cursor()
    c.execute("SELECT chat_id FROM groups")
    all_chats = c.fetchall()
    conn.close()
    for chat in all_chats:
        try:
            bot.send_message(chat[0], f"📢 رسالة من المطور:\n\n{text}")
        except:
            pass
    bot.reply_to(message, "✅ تم نشر الرسالة في جميع المجموعات.")

def update_group_link(message):
    link = message.text
    cid = message.chat.id
    conn = sqlite3.connect('goat_bot.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO groups (chat_id, link) VALUES (?, ?)", (cid, link))
    c.execute("UPDATE groups SET link=? WHERE chat_id=?", (link, cid))
    conn.commit()
    conn.close()
    bot.reply_to(message, f"✅ تم تحديث الرابط: {link}")

# ================== حماية متقدمة ==================
@bot.message_handler(func=lambda m: True, content_types=["text", "photo", "video", "document", "forward"])
def advanced_protection(message):
    cid = message.chat.id
    uid = message.from_user.id
    text = message.text or ""
    status = bot.get_chat_member(cid, uid).status
    is_admin = status in ["administrator", "creator"]

    # ================== حظر المتكرر ==================
    if not is_admin:
        user_warnings[uid] += 1
        if user_warnings[uid] >= 3:
            try:
                bot.kick_chat_member(cid, uid)
                bot.send_message(cid, f"🚨 {message.from_user.first_name} تم حظره بسبب تكرار المخالفات!")
                user_warnings[uid] = 0
            except:
                pass# ================== حماية نهائية ==================
@bot.message_handler(func=lambda m: True, content_types=["text", "photo", "video", "document", "forward"])
def ultimate_protection(message):
    cid = message.chat.id
    uid = message.from_user.id
    status = bot.get_chat_member(cid, uid).status
    is_admin = status in ["administrator", "creator"]

    # منع الروابط والملفات غير المرغوبة
    if not is_admin and is_locked(cid, "lock_links") and message.entities:
        for e in message.entities:
            if e.type in ["url", "text_link"]:
                try:
                    bot.delete_message(cid, message.message_id)
                    bot.send_message(cid, f"🚫 {message.from_user.first_name} ممنوع ارسال روابط!")
                except:
                    pass
                return

    # منع إعادة التوجيه
    if not is_admin and is_locked(cid, "lock_forward") and message.forward_from:
        try:
            bot.delete_message(cid, message.message_id)
            bot.send_message(cid, f"🚫 {message.from_user.first_name} ممنوع إعادة توجيه الرسائل!")
        except:
            pass
        return

# ================== تفعيل تلقائي ورد فخم ==================
@bot.message_handler(func=lambda m: m.text == "تفعيل")
def auto_activation(message):
    cid = message.chat.id
    set_lock(cid, "is_active", 1)
    txt = (
        f"✅ مرحباً {message.from_user.first_name}!\n"
        "📌 تم تفعيل البوت تلقائياً\n"
        "🛡️ الحماية متوفرة الآن مع جميع أنظمة القفل والتحذيرات\n"
        "💡 استخدم 'الاوامر' لعرض جميع الوظائف المتاحة"
    )
    bot.send_message(cid, txt)

# ================== تشغيل البوت ==================
bot.infinity_polling()