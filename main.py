import os
import re
import sys
import time
import json
import zipfile
import shutil
import logging
import tempfile
import subprocess
from datetime import datetime
from threading import Thread
from flask import Flask
import telebot
from telebot import types

# لاگنگ کنفیگریشن
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# === بنیادی کنفیگریشن ===
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8965571841:AAEoQpR1Uyfww0YSJB0ev6RMH9qIfLftC3Q")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8122951733"))  # اپنا ٹیلیگرام عددی یوزر آئی ڈی درج کریں

BASE_DIR = os.getcwd()
PROJECTS_DIR = os.path.join(BASE_DIR, "hosted_projects")
METADATA_FILE = os.path.join(BASE_DIR, "projects_db.json")
BACKUPS_TEMP_DIR = os.path.join(BASE_DIR, "temp_backups")

os.makedirs(PROJECTS_DIR, exist_ok=True)
os.makedirs(BACKUPS_TEMP_DIR, exist_ok=True)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# فعال پروسیسز اور پروجیکٹس ڈیٹا
# Format: { "project_name": { "status": "running|stopped", "dir": str, "entry": str, "runtime": "python|node", "process": Popen } }
DEPLOYED_BOTS = {}

# 24/7 لائیو رکھنے کے لیے فلاسکی ویب سرور
flask_app = Flask(__name__)

@flask_app.route("/")
def index():
    return "Enterprise Bot Host Manager is Active 24/7!", 200

@flask_app.route("/health")
def health():
    active_count = len([b for b in DEPLOYED_BOTS.values() if b.get("status") == "running"])
    return {"status": "healthy", "active_bots": active_count, "total_projects": len(DEPLOYED_BOTS)}, 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)

def start_keep_alive():
    web_thread = Thread(target=run_flask, daemon=True)
    web_thread.start()
    logging.info("Flask Keep-Alive سرور پس منظر میں فعال ہو چکا ہے۔")

# پائیتھن پیکیج میپنگ برائے امپورٹ ٹو پپ
PACKAGE_MAPPINGS = {
    "telebot": "pyTelegramBotAPI",
    "telegram": "python-telegram-bot",
    "telethon": "telethon",
    "pyrogram": "pyrogram",
    "discord": "discord.py",
    "bs4": "beautifulsoup4",
    "PIL": "Pillow",
    "cv2": "opencv-python",
    "dotenv": "python-dotenv",
    "yaml": "PyYAML",
    "sklearn": "scikit-learn",
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "aiohttp": "aiohttp",
    "requests": "requests",
    "pymongo": "pymongo",
    "motor": "motor",
    "sqlalchemy": "SQLAlchemy"
}

STANDARD_LIBS = set(sys.builtin_module_names) | {
    "os", "sys", "time", "json", "math", "re", "subprocess", "threading", "random",
    "logging", "datetime", "shutil", "urllib", "pathlib", "collections", "itertools",
    "hashlib", "socket", "sqlite3", "csv", "tempfile", "traceback", "copy", "asyncio",
    "typing", "base64", "glob", "platform", "signal", "inspect", "io", "string", "zipfile"
}

# --- ڈیٹا بیس اور پرزسٹینس فنکشنز ---
def save_metadata():
    """پروجیکٹس کی لسٹ کو ڈسک پر محفوظ کرتا ہے تاکہ سرور ری بوٹ پر ڈیٹا ضائع نہ ہو"""
    data_to_save = {}
    for name, info in DEPLOYED_BOTS.items():
        data_to_save[name] = {
            "dir": info.get("dir"),
            "entry": info.get("entry"),
            "runtime": info.get("runtime", "python"),
            "status": "stopped"  # سرور ری اسٹارٹ پر پروسیسز فریش شروع ہوں گے
        }
    try:
        with open(METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=2)
    except Exception as e:
        logging.error(f"ڈیٹا محفوظ کرنے میں خرابی: {e}")

def load_metadata():
    """ڈسک سے پروجیکٹس کی لسٹ لوڈ کرتا ہے"""
    global DEPLOYED_BOTS
    if os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                for name, info in saved.items():
                    if os.path.exists(info.get("dir", "")):
                        DEPLOYED_BOTS[name] = {
                            "dir": info.get("dir"),
                            "entry": info.get("entry"),
                            "runtime": info.get("runtime", "python"),
                            "status": "stopped",
                            "process": None
                        }
            logging.info(f"{len(DEPLOYED_BOTS)} پروجیکٹس کامیابی سے ڈیٹا بیس سے بحال ہو گئے۔")
        except Exception as e:
            logging.error(f"ڈیٹا لوڈ کرنے میں خرابی: {e}")

def admin_only(func):
    """سیکیورٹی پروٹیکشن برائے ایڈمن"""
    def wrapper(message_or_call, *args, **kwargs):
        user_id = message_or_call.from_user.id
        if user_id != ADMIN_ID:
            if isinstance(message_or_call, types.CallbackQuery):
                bot.answer_callback_query(message_or_call.id, "❌ رسائی مسترد: آپ ایڈمن نہیں ہیں۔", show_alert=True)
            else:
                bot.reply_to(message_or_call, "❌ <b>رسائی مسترد:</b> یہ بوٹ صرف ایڈمن کے لیے وقف ہے۔")
            return
        return func(message_or_call, *args, **kwargs)
    return wrapper

# --- آٹو ڈیپینڈینسی اینڈ اینٹری پوائنٹ اینالائزر ---
def scan_python_imports(file_path):
    """پائیتھن فائل کو پڑھ کر بغیر سنٹیکس ایرر کے لائبریریوں کا تعین کرنا"""
    packages = set()
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#"):
                    continue
                match = re.match(r"^(?:from|import)\s+([a-zA-Z0-9_]+)", line)
                if match:
                    pkg = match.group(1)
                    if pkg and pkg not in STANDARD_LIBS:
                        packages.add(PACKAGE_MAPPINGS.get(pkg, pkg))
    except Exception as e:
        logging.warning(f"لائبریری اسکیننگ وارننگ: {e}")
    return packages

def detect_entry_point(folder_path):
    """پروجیکٹ فولڈر میں سے مین ایگزیکیوشن فائل تلاش کرنا"""
    # ترجیحی فائلیں
    preferred = ["bot.py", "main.py", "app.py", "run.py", "index.py", "index.js", "bot.js"]
    for pref in preferred:
        target = os.path.join(folder_path, pref)
        if os.path.exists(target):
            runtime = "node" if pref.endswith(".js") else "python"
            return pref, runtime

    # اگر مخصوص فائل نہ ملے تو کوئی بھی .py یا .js فائل تلاش کریں
    for root, _, files in os.walk(folder_path):
        for f in files:
            if f.endswith(".py"):
                rel_path = os.path.relpath(os.path.join(root, f), folder_path)
                return rel_path, "python"
            elif f.endswith(".js"):
                rel_path = os.path.relpath(os.path.join(root, f), folder_path)
                return rel_path, "node"

    return None, None

def install_dependencies(project_dir, runtime):
    """ضروری پیکیجز خودکار انسٹال کرنا"""
    installed_summary = []
    req_file = os.path.join(project_dir, "requirements.txt")

    if runtime == "python":
        # اگر requirements.txt پہلے سے موجود نہ ہو تو تمام .py فائلوں کو اسکین کر کے بنائیں
        if not os.path.exists(req_file):
            all_pkgs = set()
            for root, _, files in os.walk(project_dir):
                for f in files:
                    if f.endswith(".py"):
                        all_pkgs.update(scan_python_imports(os.path.join(root, f)))
            if all_pkgs:
                with open(req_file, "w", encoding="utf-8") as rf:
                    for p in sorted(all_pkgs):
                        rf.write(f"{p}\n")

        # پپ سے انسٹال کریں
        if os.path.exists(req_file) and os.path.getsize(req_file) > 0:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_file])
                installed_summary.append("Python Requirements Installed")
            except Exception as e:
                logging.error(f"Pip Error: {e}")
                installed_summary.append("Pip Warning/Error")

    elif runtime == "node":
        pkg_json = os.path.join(project_dir, "package.json")
        if os.path.exists(pkg_json):
            try:
                subprocess.check_call(["npm", "install"], cwd=project_dir)
                installed_summary.append("NPM Packages Installed")
            except Exception as e:
                logging.error(f"NPM Error: {e}")
                installed_summary.append("NPM Error")

    return installed_summary

# --- پروسیس مینجمنٹ انجن ---
def launch_project(name):
    """کسی پروجیکٹ کو بیک گراؤنڈ میں چلانا اور لاگ فائل بائنڈ کرنا"""
    info = DEPLOYED_BOTS.get(name)
    if not info:
        return False, "پروجیکٹ نہیں ملا۔"

    project_dir = info["dir"]
    entry_file = info.get("entry")
    runtime = info.get("runtime", "python")

    if not entry_file:
        return False, "کوئی چلانے کے قابل فائل موجود نہیں ہے۔"

    log_path = os.path.join(project_dir, "output.log")
    log_file = open(log_path, "a", encoding="utf-8")

    cmd = [sys.executable, entry_file] if runtime == "python" else ["node", entry_file]

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=project_dir,
            stdout=log_file,
            stderr=subprocess.STDOUT
        )
        info["process"] = proc
        info["status"] = "running"
        info["log_file"] = log_path
        save_metadata()
        return True, "پروجیکٹ کامیابی کے ساتھ آن لائن ہو چکا ہے۔"
    except Exception as e:
        return False, f"ایگزیکیوشن ایرر: {str(e)}"

def stop_project(name):
    """چلتے ہوئے بوٹ کے پروسیس کو بند کرنا"""
    info = DEPLOYED_BOTS.get(name)
    if not info:
        return False, "پروجیکٹ نہیں ملا۔"

    proc = info.get("process")
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()

    info["status"] = "stopped"
    info["process"] = None
    save_metadata()
    return True, "پروجیکٹ بند کر دیا گیا۔"

# --- بیک اپ انجن (Zip Compression) ---
def create_project_backup(name):
    """سنگل پروجیکٹ کی مکمل زپ فائل بناتا ہے"""
    info = DEPLOYED_BOTS.get(name)
    if not info or not os.path.exists(info["dir"]):
        return None

    project_dir = info["dir"]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"{name}_backup_{timestamp}.zip"
    zip_filepath = os.path.join(BACKUPS_TEMP_DIR, zip_filename)

    with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(project_dir):
            # غیر ضروری فولڈرز نکال دیں تاکہ سائز چھوٹا رہے
            dirs[:] = [d for d in dirs if d not in ["__pycache__", ".git", "node_modules"]]
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, project_dir)
                zipf.write(full_path, arcname=rel_path)

    return zip_filepath

def create_full_system_backup():
    """تمام پروجیکٹس اور ڈیٹا بیس کا مکمل سسٹم زپ بناتا ہے"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"FULL_SYSTEM_BACKUP_{timestamp}.zip"
    zip_filepath = os.path.join(BACKUPS_TEMP_DIR, zip_filename)

    with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # پروجیکٹس ڈائریکٹری محفوظ کریں
        for root, dirs, files in os.walk(PROJECTS_DIR):
            dirs[:] = [d for d in dirs if d not in ["__pycache__", ".git", "node_modules"]]
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, BASE_DIR)
                zipf.write(full_path, arcname=rel_path)
        # ڈیٹا بیس فائل شامل کریں
        if os.path.exists(METADATA_FILE):
            zipf.write(METADATA_FILE, arcname="projects_db.json")

    return zip_filepath

# --- کی بورڈز اور UI ---
def get_main_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    b1 = types.InlineKeyboardButton("📋 مائی پروجیکٹس", callback_data="btn_list")
    b2 = types.InlineKeyboardButton("📊 سرور مانیٹر", callback_data="btn_status")
    b3 = types.InlineKeyboardButton("💾 مکمل سسٹم بیک اپ", callback_data="btn_full_backup")
    b4 = types.InlineKeyboardButton("🔄 ری اسٹارٹ آل", callback_data="btn_restart_all")
    b5 = types.InlineKeyboardButton("ℹ️ رہنمائی / طریقہ کار", callback_data="btn_help")
    markup.add(b1, b2)
    markup.add(b3, b4)
    markup.add(b5)
    return markup

def get_project_keyboard(name):
    markup = types.InlineKeyboardMarkup(row_width=2)
    info = DEPLOYED_BOTS.get(name, {})
    is_running = info.get("status") == "running"

    toggle_btn = types.InlineKeyboardButton("⏹ اسٹاپ کریں", callback_data=f"stop_{name}") if is_running else types.InlineKeyboardButton("▶️ اسٹارٹ کریں", callback_data=f"start_{name}")
    restart_btn = types.InlineKeyboardButton("🔄 ری اسٹارٹ", callback_data=f"restart_{name}")
    logs_btn = types.InlineKeyboardButton("📜 لائیو لاگز", callback_data=f"logs_{name}")
    backup_btn = types.InlineKeyboardButton("📦 بیک اپ زپ حاصل کریں", callback_data=f"backup_{name}")
    delete_btn = types.InlineKeyboardButton("🗑️ ڈیلیٹ کریں", callback_data=f"delete_{name}")
    back_btn = types.InlineKeyboardButton("⬅️ پروجیکٹس لسٹ", callback_data="btn_list")

    markup.add(toggle_btn, restart_btn)
    markup.add(logs_btn, backup_btn)
    markup.add(delete_btn)
    markup.add(back_btn)
    return markup

# --- ٹیلیگرام میسج ہینڈلرز ---
@bot.message_handler(commands=["start", "menu"])
@admin_only
def cmd_start(message):
    text = (
        "👑 <b>انڈسٹری گریڈ ٹیلیگرام بوٹ ہوسٹنگ مینیجر</b>\n\n"
        "⚡ <b>سپورٹڈ فائلز:</b>\n"
        "• <b>سنگل پائیتھن فائل:</b> <code>.py</code> (لائبریریاں خودکار اسکین ہوں گی)\n"
        "• <b>مکمل پروجیکٹ آرکائیو:</b> <code>.zip</code> (خود بخود ان زپ اور کنفیگر ہوگا)\n\n"
        "💾 <b>بیک اپ سسٹم:</b> ہر پروجیکٹ کا علیحدہ یا پورے سرور کا ایک ساتھ زپ بیک اپ ٹیلیگرام پر دستیاب ہے۔\n\n"
        "👇 نیچے دیے گئے مینیو سے کنٹرول کریں یا کوئی بھی فائل بھیجیں:"
    )
    bot.reply_to(message, text, reply_markup=get_main_keyboard())

@bot.message_handler(content_types=["document"])
@admin_only
def handle_file_upload(message):
    doc = message.document
    file_name = doc.file_name or "unknown_file"

    is_py = file_name.endswith(".py")
    is_zip = file_name.endswith(".zip")

    if not (is_py or is_zip):
        bot.reply_to(message, "⚠️ <b>ناقابل قبول فارمیٹ:</b> برائے مہربانی صرف <code>.py</code> یا <code>.zip</code> فائل بھیجیں۔")
        return

    clean_name = re.sub(r'[^a-zA-Z0-9_]', '', file_name.rsplit('.', 1)[0]).lower()
    if not clean_name:
        clean_name = f"bot_{int(time.time())}"

    project_dir = os.path.join(PROJECTS_DIR, clean_name)

    # اگر پہلے سے چل رہا ہو تو بند کریں
    if clean_name in DEPLOYED_BOTS:
        stop_project(clean_name)

    status_msg = bot.reply_to(message, "⏳ <b>فائل ڈاؤن لوڈ ہو رہی ہے، برائے مہربانی انتظار فرمائیں...</b>")

    try:
        file_info = bot.get_file(doc.file_id)
        downloaded = bot.download_file(file_info.file_path)

        os.makedirs(project_dir, exist_ok=True)

        if is_py:
            target_file = os.path.join(project_dir, "bot.py")
            with open(target_file, "wb") as f:
                f.write(downloaded)
            entry_file = "bot.py"
            runtime = "python"
        elif is_zip:
            # زپ فائل کو محفوظ کر کے ایکسٹریکٹ کریں
            temp_zip = os.path.join(BACKUPS_TEMP_DIR, f"temp_{clean_name}.zip")
            with open(temp_zip, "wb") as f:
                f.write(downloaded)
            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                zip_ref.extractall(project_dir)
            if os.path.exists(temp_zip):
                os.remove(temp_zip)

            entry_file, runtime = detect_entry_point(project_dir)
            if not entry_file:
                bot.edit_message_text("❌ <b>ایرر:</b> زپ فائل میں کوئی قابل عمل فائل (main.py, bot.py، وغیرہ) نہیں ملی۔",
                                      chat_id=message.chat.id, message_id=status_msg.message_id)
                return

        bot.edit_message_text("📦 <b>لائبریریوں کی تنصیب اور انوائرنمنٹ سیٹ اپ ہو رہا ہے...</b>",
                              chat_id=message.chat.id, message_id=status_msg.message_id)

        # پیکیجز انسٹال کریں
        install_dependencies(project_dir, runtime)

        # پروجیکٹ رجسٹر کریں
        DEPLOYED_BOTS[clean_name] = {
            "dir": project_dir,
            "entry": entry_file,
            "runtime": runtime,
            "status": "stopped",
            "process": None
        }
        save_metadata()

        bot.edit_message_text("🚀 <b>پروجیکٹ بوٹ لانچ کیا جا رہا ہے...</b>",
                              chat_id=message.chat.id, message_id=status_msg.message_id)

        success, msg = launch_project(clean_name)
        if success:
            resp_text = (
                f"✅ <b>پروجیکٹ کامیابی کے ساتھ لائیو ہو گیا!</b>\n\n"
                f"🏷 <b>نام:</b> <code>{clean_name}</code>\n"
                f"⚙️ <b>مین فائل:</b> <code>{entry_file}</code>\n"
                f"🌐 <b>رن ٹائم:</b> <code>{runtime}</code>\n"
                f"🟢 <b>اسٹیٹس:</b> 24/7 آن لائن"
            )
            bot.edit_message_text(resp_text, chat_id=message.chat.id, message_id=status_msg.message_id,
                                  reply_markup=get_project_keyboard(clean_name))
        else:
            bot.edit_message_text(f"❌ <b>اسٹارٹ کرنے میں رکاوٹ:</b>\n<code>{msg}</code>",
                                  chat_id=message.chat.id, message_id=status_msg.message_id)

    except Exception as e:
        logging.error(f"اپلوڈ پروسیسنگ خرابی: {e}")
        bot.edit_message_text(f"❌ پروسیسنگ میں نقص آیا: {str(e)}", chat_id=message.chat.id, message_id=status_msg.message_id)

# --- کال بیکس ہینڈلر ---
@bot.callback_query_handler(func=lambda call: True)
@admin_only
def handle_callbacks(call):
    data = call.data

    if data == "btn_list":
        bot.answer_callback_query(call.id)
        if not DEPLOYED_BOTS:
            bot.edit_message_text("📭 فی الوقت کوئی ڈپلائے شدہ پروجیکٹ موجود نہیں ہے۔",
                                  chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  reply_markup=get_main_keyboard())
            return

        markup = types.InlineKeyboardMarkup(row_width=1)
        for name, info in DEPLOYED_BOTS.items():
            icon = "🟢" if info.get("status") == "running" else "🔴"
            lang = "🐍" if info.get("runtime") == "python" else "⚡"
            markup.add(types.InlineKeyboardButton(f"{icon} {lang} {name}", callback_data=f"manage_{name}"))
        markup.add(types.InlineKeyboardButton("⬅️ واپس مینیو", callback_data="btn_home"))

        bot.edit_message_text("📋 <b>آپ کے تمام ڈپلائے شدہ پروجیکٹس:</b>\nتفصیل اور کنٹرول کے لیے پروجیکٹ منتخب کریں:",
                              chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

    elif data == "btn_home":
        bot.answer_callback_query(call.id)
        bot.edit_message_text("👑 <b>ایڈمن ڈیش بورڈ:</b>", chat_id=call.message.chat.id,
                              message_id=call.message.message_id, reply_markup=get_main_keyboard())

    elif data == "btn_status":
        bot.answer_callback_query(call.id)
        running = len([b for b in DEPLOYED_BOTS.values() if b.get("status") == "running"])
        total = len(DEPLOYED_BOTS)
        text = (
            "📊 <b>سرور مانیٹر اسٹیٹس:</b>\n\n"
            f"📁 <b>کُل پروجیکٹس:</b> {total}\n"
            f"🟢 <b>آن لائن بوٹس:</b> {running}\n"
            f"🔴 <b>آف لائن بوٹس:</b> {total - running}\n"
            f"🌐 <b>Keep-Alive ویب سرور:</b> ایکٹیو (24/7)"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ واپس مینیو", callback_data="btn_home"))
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

    elif data == "btn_help":
        bot.answer_callback_query(call.id)
        msg = (
            "ℹ️ <b>بوٹ ڈپلائمنٹ رہنمائی:</b>\n\n"
            "1. <b>سنگل فائل:</b> براہ راست <code>.py</code> فائل بھیجیں، بوٹ خود بخود امپورٹس تلاش کر کے پیکجز انسٹال کرے گا۔\n"
            "2. <b>پورا پروجیکٹ:</b> اپنے پروجیکٹ فولڈر کی <code>.zip</code> فائل بنا کر بھیجیں۔ یہ خود بخود main.py یا bot.py کو ڈھونڈ کر چلا دے گا۔\n"
            "3. <b>بیک اپ:</b> ہر پروجیکٹ کے اندر سے یا مین مینیو سے ایک کلک پر زپ بیک اپ اپنے فون میں ڈاؤن لوڈ کریں۔"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ واپس مینیو", callback_data="btn_home"))
        bot.edit_message_text(msg, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

    elif data == "btn_full_backup":
        bot.answer_callback_query(call.id, "مکمل بیک اپ تیار کیا جا رہا ہے...")
        zip_path = create_full_system_backup()
        if zip_path and os.path.exists(zip_path):
            with open(zip_path, "rb") as zf:
                bot.send_document(
                    call.message.chat.id,
                    zf,
                    caption=f"💾 <b>مکمل سسٹم بیک اپ</b>\nتاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nاس میں تمام بوٹس کا ڈیٹا بیس اور کوڈ شامل ہے۔"
                )
            os.remove(zip_path)
        else:
            bot.send_message(call.message.chat.id, "❌ بیک اپ فائل تیار کرنے میں دشواری پیش آئی۔")

    elif data == "btn_restart_all":
        bot.answer_callback_query(call.id, "تمام پروجیکٹس ری اسٹارٹ کیے جا رہے ہیں...")
        for name in list(DEPLOYED_BOTS.keys()):
            stop_project(name)
            time.sleep(0.5)
            launch_project(name)
        bot.answer_callback_query(call.id, "تمام فعال بوٹس ری اسٹارٹ ہو چکے ہیں!", show_alert=True)
        cmd_start(call.message)

    # انفرادی پروجیکٹ کے بٹن
    elif data.startswith("manage_"):
        name = data.split("_", 1)[1]
        info = DEPLOYED_BOTS.get(name)
        if not info:
            bot.answer_callback_query(call.id, "پروجیکٹ نہیں ملا!", show_alert=True)
            return
        status_txt = "🟢 آن لائن" if info.get("status") == "running" else "🔴 بند"
        txt = (
            f"⚙️ <b>پروجیکٹ مینیجر:</b> <code>{name}</code>\n\n"
            f"📊 <b>اسٹیٹس:</b> {status_txt}\n"
            f"🎯 <b>اینٹری پوائنٹ:</b> <code>{info.get('entry')}</code>\n"
            f"🌐 <b>رن ٹائم:</b> <code>{info.get('runtime')}</code>"
        )
        bot.edit_message_text(txt, chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=get_project_keyboard(name))

    elif data.startswith("start_"):
        name = data.split("_", 1)[1]
        succ, msg = launch_project(name)
        bot.answer_callback_query(call.id, msg, show_alert=True)
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      reply_markup=get_project_keyboard(name))

    elif data.startswith("stop_"):
        name = data.split("_", 1)[1]
        succ, msg = stop_project(name)
        bot.answer_callback_query(call.id, msg, show_alert=True)
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      reply_markup=get_project_keyboard(name))

    elif data.startswith("restart_"):
        name = data.split("_", 1)[1]
        stop_project(name)
        time.sleep(1)
        launch_project(name)
        bot.answer_callback_query(call.id, f"{name} کامیابی سے ری اسٹارٹ ہو گیا!", show_alert=True)
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      reply_markup=get_project_keyboard(name))

    elif data.startswith("logs_"):
        name = data.split("_", 1)[1]
        info = DEPLOYED_BOTS.get(name)
        log_file = os.path.join(info["dir"], "output.log") if info else None
        if log_file and os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8", errors="ignore") as lf:
                lines = lf.readlines()
                last_logs = "".join(lines[-30:]) if lines else "لاگ فائل فی الحال خالی ہے۔"
            bot.send_message(call.message.chat.id, f"📜 <b>لاگز برائے {name}:</b>\n\n<pre>{last_logs}</pre>")
        else:
            bot.answer_callback_query(call.id, "ابھی کوئی لاگز موجود نہیں ہیں!", show_alert=True)

    elif data.startswith("backup_"):
        name = data.split("_", 1)[1]
        bot.answer_callback_query(call.id, f"{name} کا زپ بیک اپ تیار ہو رہا ہے...")
        zip_path = create_project_backup(name)
        if zip_path and os.path.exists(zip_path):
            with open(zip_path, "rb") as zf:
                bot.send_document(
                    call.message.chat.id,
                    zf,
                    caption=f"📦 <b>پروجیکٹ بیک اپ:</b> <code>{name}</code>\nتاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
            os.remove(zip_path)
        else:
            bot.send_message(call.message.chat.id, f"❌ پروجیکٹ {name} کا بیک اپ بنانے میں دشواری آئی۔")

    elif data.startswith("delete_"):
        name = data.split("_", 1)[1]
        stop_project(name)
        info = DEPLOYED_BOTS.pop(name, None)
        if info and os.path.exists(info["dir"]):
            shutil.rmtree(info["dir"], ignore_errors=True)
        save_metadata()
        bot.answer_callback_query(call.id, f"پروجیکٹ {name} کامیابی سے ڈیلیٹ ہو گیا!", show_alert=True)
        cmd_start(call.message)

if __name__ == "__main__":
    # ڈسک سے سابقہ پروجیکٹس لوڈ کریں
    load_metadata()

    # فلاسکی ویب پورٹ شروع کریں تاکہ ہوسٹنگ پر 24/7 لائیو رہے
    start_keep_alive()

    logging.info("انڈسٹری گریڈ ہوسٹنگ مینیجر سروس شروع ہو چکی ہے۔")
    while True:
        try:
            bot.infinity_polling(timeout=25, long_polling_timeout=20)
        except Exception as err:
            logging.error(f"ٹیلیگرام کنکشن ایرر: {err}")
            time.sleep(5)