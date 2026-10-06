import os
import re
import sys
import time
import json
import shutil
import zipfile
import logging
import tempfile
import subprocess
from datetime import datetime
from threading import Thread

# لاگنگ کنفیگریشن
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")

def install_system_package(package_name, import_target=None):
    """اگر کوئی بنیادی لائبریری مسنگ ہو تو اسکرپٹ خودکار طور پر ڈاؤن لوڈ کر لے گا تاکہ کریش نہ ہو"""
    target = import_target or package_name
    try:
        __import__(target)
    except ImportError:
        logging.warning(f"لائبریری '{package_name}' نہیں ملی۔ فوری انسٹالیشن شروع کی جا رہی ہے...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
            logging.info(f"لائبریری '{package_name}' کامیابی سے انسٹال ہو گئی۔")
        except Exception as err:
            logging.critical(f"لائبریری انسٹالیشن میں رکاوٹ: {err}")

# بنیادی پیکیجز کی تصدیق
install_system_package("Flask", "flask")
install_system_package("pyTelegramBotAPI", "telebot")
install_system_package("requests", "requests")

from flask import Flask
import telebot
from telebot import types

# === آپ کے فراہم کردہ کریڈینشلز (Safe Fallback کے ساتھ) ===
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8965571841:AAEoQpR1Uyfww0YSJB0ev6RMH9qIfLftC3Q").strip()
raw_admin = os.environ.get("ADMIN_ID", "8122951733").strip().lstrip("@")
ADMIN_ID = int(raw_admin) if raw_admin.isdigit() else 8122951733

BASE_DIR = os.getcwd()
PROJECTS_DIR = os.path.join(BASE_DIR, "hosted_projects")
METADATA_FILE = os.path.join(BASE_DIR, "projects_db.json")
BACKUPS_TEMP_DIR = os.path.join(BASE_DIR, "temp_backups")

os.makedirs(PROJECTS_DIR, exist_ok=True)
os.makedirs(BACKUPS_TEMP_DIR, exist_ok=True)

# فلاسکی ویب سرور برائے 24/7 لائیو اسٹیٹس
flask_app = Flask(__name__)
DEPLOYED_BOTS = {}

@flask_app.route("/")
def home_index():
    return "Enterprise Telegram Host Manager with Auto-Restart is 24/7 Online!", 200

@flask_app.route("/health")
def health_check():
    running_count = sum(1 for b in DEPLOYED_BOTS.values() if b.get("status") == "running")
    return {
        "status": "healthy",
        "running_bots": running_count,
        "total_projects": len(DEPLOYED_BOTS),
        "admin_configured": bool(ADMIN_ID)
    }, 200

def launch_flask_server():
    port = int(os.environ.get("PORT", 8080))
    logging.info(f"فلاسکی پورٹ {port} پر فعال ہو رہا ہے...")
    flask_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

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

def save_metadata():
    """پروجیکٹس کی لسٹ کو محفوظ رکھنا"""
    data_to_save = {}
    for name, info in DEPLOYED_BOTS.items():
        data_to_save[name] = {
            "dir": info.get("dir"),
            "entry": info.get("entry"),
            "runtime": info.get("runtime", "python"),
            "status": info.get("status", "stopped"),
            "auto_restart": info.get("auto_restart", True)
        }
    try:
        with open(METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=2)
    except Exception as e:
        logging.error(f"ڈیٹا بیس محفوظ کرنے میں خرابی: {e}")

def load_metadata():
    """پروجیکٹس لوڈ کرنا اور خودکار بحالی"""
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
                            "auto_restart": info.get("auto_restart", True),
                            "process": None
                        }
            logging.info(f"{len(DEPLOYED_BOTS)} پروجیکٹس کامیابی سے لوڈ ہو گئے۔")
        except Exception as e:
            logging.error(f"ڈیٹا بیس لوڈنگ خرابی: {e}")

def admin_only(func):
    """ایڈمن سیکیورٹی فلٹر"""
    def wrapper(message_or_call, *args, **kwargs):
        user_id = message_or_call.from_user.id
        if ADMIN_ID != 0 and user_id != ADMIN_ID:
            if isinstance(message_or_call, types.CallbackQuery):
                bot.answer_callback_query(message_or_call.id, "❌ رسائی مسترد: آپ ایڈمن نہیں ہیں۔", show_alert=True)
            else:
                bot.reply_to(message_or_call, "❌ <b>رسائی مسترد:</b> یہ بوٹ صرف ایڈمن کے لیے وقف ہے۔")
            return
        return func(message_or_call, *args, **kwargs)
    return wrapper

def scan_python_imports(file_path):
    """کوڈ سے ضروری لائبریریوں کا تعین"""
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
        logging.warning(f"لائبریری اسکین وارننگ: {e}")
    return packages

def detect_entry_point(folder_path):
    """پروجیکٹ کی مین ایگزیکیوشن فائل ڈھونڈنا"""
    preferred = ["bot.py", "main.py", "app.py", "run.py", "index.py", "index.js", "bot.js"]
    for pref in preferred:
        target = os.path.join(folder_path, pref)
        if os.path.exists(target):
            runtime = "node" if pref.endswith(".js") else "python"
            return pref, runtime

    for root, _, files in os.walk(folder_path):
        for f in files:
            if f.endswith(".py"):
                return os.path.relpath(os.path.join(root, f), folder_path), "python"
            elif f.endswith(".js"):
                return os.path.relpath(os.path.join(root, f), folder_path), "node"

    return None, None

def install_dependencies(project_dir, runtime):
    """لائبریریاں انسٹال کرنا"""
    req_file = os.path.join(project_dir, "requirements.txt")
    if runtime == "python":
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

        if os.path.exists(req_file) and os.path.getsize(req_file) > 0:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_file])
            except Exception as e:
                logging.error(f"پپ انسٹالیشن ایرر: {e}")

def launch_project(name):
    """بوٹ کو پس منظر میں شروع کرنا"""
    info = DEPLOYED_BOTS.get(name)
    if not info:
        return False, "پروجیکٹ نہیں ملا۔"

    project_dir = info["dir"]
    entry_file = info.get("entry")
    runtime = info.get("runtime", "python")

    if not entry_file:
        return False, "مین ایگزیکیوشن فائل موجود نہیں ہے۔"

    log_path = os.path.join(project_dir, "output.log")
    log_file = open(log_path, "a", encoding="utf-8")
    cmd = [sys.executable, entry_file] if runtime == "python" else ["node", entry_file]

    try:
        proc = subprocess.Popen(cmd, cwd=project_dir, stdout=log_file, stderr=subprocess.STDOUT)
        info["process"] = proc
        info["status"] = "running"
        info["log_file"] = log_path
        save_metadata()
        return True, "پروجیکٹ کامیابی سے لائیو ہو چکا ہے۔"
    except Exception as e:
        return False, f"ایگزیکیوشن فیل: {str(e)}"

def stop_project(name, mark_stopped=True):
    """بوٹ کو روکنا"""
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

    if mark_stopped:
        info["status"] = "stopped"
    info["process"] = None
    save_metadata()
    return True, "پروجیکٹ بند کر دیا گیا۔"

# ==================== خودکار واچ ڈاگ اور 24 گھنٹے آٹو ریسٹارٹ انجن ====================
def background_watchdog():
    """
    یہ تھریڈ بیک گراؤنڈ میں ہر 15 سیکنڈ بعد چیک کرتا ہے کہ:
    1. اگر کوئی بوٹ خود بخود یا ایرر کی وجہ سے بند ہوا ہے تو اسے فوراً ری اسٹارٹ کر دے۔
    2. ہر 24 گھنٹے بعد سسٹم کو خودکار کلین ریفریش دے تاکہ میموری لیکس نہ ہوں۔
    """
    logging.info("خودکار پروٹیکشن اور واچ ڈاگ انجن فعال ہو چکا ہے۔")
    last_24h_cycle = time.time()

    while True:
        try:
            time.sleep(15)
            current_time = time.time()

            # 1. کریش پروٹیکشن: چیک کریں کہ جو بوٹس 'running' تھے وہ زندہ ہیں یا نہیں
            for name, info in list(DEPLOYED_BOTS.items()):
                if info.get("status") == "running" and info.get("auto_restart", True):
                    proc = info.get("process")
                    if proc is None or proc.poll() is not None:
                        logging.warning(f"بوٹ '{name}' آف لائن ملا۔ واچ ڈاگ اسے فوری ری اسٹارٹ کر رہا ہے...")
                        launch_project(name)

            # 2. 24 گھنٹے بعد خودکار ریفریش اور ہیلتھ چیک (86400 سیکنڈ)
            if current_time - last_24h_cycle >= 86400:
                logging.info("24 گھنٹے مکمل: خودکار سسٹم ریفریش اور کلین اپ شروع ہو رہا ہے...")
                for name, info in list(DEPLOYED_BOTS.items()):
                    if info.get("status") == "running":
                        logging.info(f"24h ریفریش: ری اسٹارٹ برائے '{name}'")
                        stop_project(name, mark_stopped=False)
                        time.sleep(1)
                        launch_project(name)

                # کیشے کلین اپ
                shutil.rmtree(BACKUPS_TEMP_DIR, ignore_errors=True)
                os.makedirs(BACKUPS_TEMP_DIR, exist_ok=True)
                last_24h_cycle = current_time
                logging.info("24 گھنٹے کا شیڈیولڈ ریفریش کامیابی سے مکمل ہو گیا۔")

        except Exception as err:
            logging.error(f"واچ ڈاگ میں رکاوٹ: {err}")
            time.sleep(10)

def create_project_backup(name):
    """انفرادی پروجیکٹ کا زپ بیک اپ"""
    info = DEPLOYED_BOTS.get(name)
    if not info or not os.path.exists(info["dir"]):
        return None

    project_dir = info["dir"]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filepath = os.path.join(BACKUPS_TEMP_DIR, f"{name}_backup_{timestamp}.zip")

    with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(project_dir):
            dirs[:] = [d for d in dirs if d not in ["__pycache__", ".git", "node_modules"]]
            for file in files:
                full_path = os.path.join(root, file)
                zipf.write(full_path, arcname=os.path.relpath(full_path, project_dir))

    return zip_filepath

def create_full_system_backup():
    """مکمل سسٹم زپ بیک اپ"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filepath = os.path.join(BACKUPS_TEMP_DIR, f"FULL_SYSTEM_BACKUP_{timestamp}.zip")

    with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(PROJECTS_DIR):
            dirs[:] = [d for d in dirs if d not in ["__pycache__", ".git", "node_modules"]]
            for file in files:
                full_path = os.path.join(root, file)
                zipf.write(full_path, arcname=os.path.relpath(full_path, BASE_DIR))
        if os.path.exists(METADATA_FILE):
            zipf.write(METADATA_FILE, arcname="projects_db.json")

    return zip_filepath

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
    backup_btn = types.InlineKeyboardButton("📦 بیک اپ زپ", callback_data=f"backup_{name}")
    delete_btn = types.InlineKeyboardButton("🗑️ ڈیلیٹ کریں", callback_data=f"delete_{name}")
    back_btn = types.InlineKeyboardButton("⬅️ پروجیکٹس لسٹ", callback_data="btn_list")

    markup.add(toggle_btn, restart_btn)
    markup.add(logs_btn, backup_btn)
    markup.add(delete_btn)
    markup.add(back_btn)
    return markup

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

@bot.message_handler(commands=["start", "menu"])
@admin_only
def cmd_start(message):
    text = (
        "👑 <b>انڈسٹری گریڈ ٹیلیگرام بوٹ ہوسٹنگ مینیجر (24/7 آن لائن)</b>\n\n"
        "⚡ <b>سسٹم اسٹیٹس:</b>\n"
        "• <b>آٹو ری اسٹارٹ واچ ڈاگ:</b> فعال (ہر 15 سیکنڈ مانیٹرنگ)\n"
        "• <b>24 گھنٹے آٹو ریفریش:</b> فعال (میموری اور کریش فری انجن)\n"
        "• <b>پروجیکٹ ہوسٹنگ:</b> <code>.py</code> یا <code>.zip</code> فائل بھیجیں\n\n"
        "👇 نیچے دیے گئے مینیو سے تمام بوٹس مینیج کریں:"
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
        bot.reply_to(message, "⚠️ <b>ناقابل قبول فارمیٹ:</b> صرف <code>.py</code> یا <code>.zip</code> فائل بھیجیں۔")
        return

    clean_name = re.sub(r'[^a-zA-Z0-9_]', '', file_name.rsplit('.', 1)[0]).lower()
    if not clean_name:
        clean_name = f"bot_{int(time.time())}"

    project_dir = os.path.join(PROJECTS_DIR, clean_name)
    if clean_name in DEPLOYED_BOTS:
        stop_project(clean_name)

    status_msg = bot.reply_to(message, "⏳ <b>فائل ڈاؤن لوڈ ہو رہی ہے، برائے مہربانی انتظار کریں...</b>")

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
            temp_zip = os.path.join(BACKUPS_TEMP_DIR, f"temp_{clean_name}.zip")
            with open(temp_zip, "wb") as f:
                f.write(downloaded)
            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                zip_ref.extractall(project_dir)
            if os.path.exists(temp_zip):
                os.remove(temp_zip)

            entry_file, runtime = detect_entry_point(project_dir)
            if not entry_file:
                bot.edit_message_text("❌ <b>ایرر:</b> زپ فائل میں کوئی مین ایگزیکیوشن فائل نہیں ملی۔",
                                      chat_id=message.chat.id, message_id=status_msg.message_id)
                return

        bot.edit_message_text("📦 <b>لائبریریوں کی تنصیب اور کنفیگریشن جاری ہے...</b>",
                              chat_id=message.chat.id, message_id=status_msg.message_id)

        install_dependencies(project_dir, runtime)

        DEPLOYED_BOTS[clean_name] = {
            "dir": project_dir,
            "entry": entry_file,
            "runtime": runtime,
            "status": "running",
            "auto_restart": True,
            "process": None
        }
        save_metadata()

        success, msg = launch_project(clean_name)
        if success:
            resp_text = (
                f"✅ <b>پروجیکٹ کامیابی کے ساتھ لائیو ہو گیا!</b>\n\n"
                f"🏷 <b>نام:</b> <code>{clean_name}</code>\n"
                f"⚙️ <b>مین فائل:</b> <code>{entry_file}</code>\n"
                f"🛡️ <b>آٹو ری اسٹارٹ:</b> فعال (24/7 واچ ڈاگ)\n"
                f"🟢 <b>اسٹیٹس:</b> لائیو اور فعال"
            )
            bot.edit_message_text(resp_text, chat_id=message.chat.id, message_id=status_msg.message_id,
                                  reply_markup=get_project_keyboard(clean_name))
        else:
            bot.edit_message_text(f"❌ <b>اسٹارٹ ایرر:</b>\n<code>{msg}</code>",
                                  chat_id=message.chat.id, message_id=status_msg.message_id)

    except Exception as e:
        logging.error(f"اپلوڈ پروسیسنگ خرابی: {e}")
        bot.edit_message_text(f"❌ ایرر: {str(e)}", chat_id=message.chat.id, message_id=status_msg.message_id)

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
            markup.add(types.InlineKeyboardButton(f"{icon} {name}", callback_data=f"manage_{name}"))
        markup.add(types.InlineKeyboardButton("⬅️ واپس مینیو", callback_data="btn_home"))

        bot.edit_message_text("📋 <b>آپ کے تمام ڈپلائے شدہ پروجیکٹس:</b>",
                              chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

    elif data == "btn_home":
        bot.answer_callback_query(call.id)
        bot.edit_message_text("👑 <b>ایڈمن ڈیش بورڈ:</b>", chat_id=call.message.chat.id,
                              message_id=call.message.message_id, reply_markup=get_main_keyboard())

    elif data == "btn_status":
        bot.answer_callback_query(call.id)
        running = sum(1 for b in DEPLOYED_BOTS.values() if b.get("status") == "running")
        text = (
            "📊 <b>سرور مانیٹر اور ہیلتھ اسٹیٹس:</b>\n\n"
            f"📁 <b>کُل پروجیکٹس:</b> {len(DEPLOYED_BOTS)}\n"
            f"🟢 <b>آن لائن بوٹس:</b> {running}\n"
            f"🔴 <b>آف لائن بوٹس:</b> {len(DEPLOYED_BOTS) - running}\n"
            f"🛡️ <b>خودکار واچ ڈاگ:</b> فعال (Auto-Heal Active)\n"
            f"⏳ <b>24 گھنٹے آٹو ریفریش:</b> فعال (Prevent Freeze)\n"
            f"🌐 <b>Keep-Alive ویب سرور:</b> فعال (24/7)"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ واپس مینیو", callback_data="btn_home"))
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

    elif data == "btn_help":
        bot.answer_callback_query(call.id)
        msg = (
            "ℹ️ <b>سسٹم رہنمائی اور آٹو ری اسٹارٹ فیچرز:</b>\n\n"
            "1. <b>فائل اپلوڈ:</b> <code>.py</code> یا <code>.zip</code> بھیجیں، بوٹ خود بخود رن ہو جائے گا۔\n"
            "2. <b>سیلف ہیلنگ:</b> اگر آپ کا کوئی بھی بوٹ انٹرنیٹ یا ایرر کی وجہ سے بند ہوگا، تو واچ ڈاگ اسے 15 سیکنڈ کے اندر خود چلا دے گا۔\n"
            "3. <b>24 گھنٹے آٹو ریفریش:</b> سسٹم 24 گھنٹے بعد خود کو ریفریش رکھے گا تاکہ کبھی بوٹ ہینگ نہ ہو۔\n"
            "4. <b>بیک اپ:</b> کسی بھی وقت مکمل زپ ڈاؤن لوڈ کر سکتے ہیں۔"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ واپس مینیو", callback_data="btn_home"))
        bot.edit_message_text(msg, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

    elif data == "btn_full_backup":
        bot.answer_callback_query(call.id, "مکمل بیک اپ تیار ہو رہا ہے...")
        zip_path = create_full_system_backup()
        if zip_path and os.path.exists(zip_path):
            with open(zip_path, "rb") as zf:
                bot.send_document(call.message.chat.id, zf, caption="💾 <b>مکمل سسٹم بیک اپ (کوڈ اور ڈیٹا)</b>")
            os.remove(zip_path)
        else:
            bot.send_message(call.message.chat.id, "❌ بیک اپ فائل بنانے میں خرابی ہوئی۔")

    elif data == "btn_restart_all":
        bot.answer_callback_query(call.id, "تمام بوٹس ری اسٹارٹ ہو رہے ہیں...")
        for name in list(DEPLOYED_BOTS.keys()):
            stop_project(name, mark_stopped=False)
            time.sleep(0.5)
            launch_project(name)
        bot.answer_callback_query(call.id, "تمام بوٹس ری اسٹارٹ ہو گئے!", show_alert=True)
        cmd_start(call.message)

    elif data.startswith("manage_"):
        name = data.split("_", 1)[1]
        info = DEPLOYED_BOTS.get(name)
        if not info:
            bot.answer_callback_query(call.id, "پروجیکٹ نہیں ملا!", show_alert=True)
            return
        status_txt = "🟢 آن لائن (واچ ڈاگ فعال)" if info.get("status") == "running" else "🔴 بند"
        txt = (
            f"⚙️ <b>پروجیکٹ:</b> <code>{name}</code>\n"
            f"📊 <b>اسٹیٹس:</b> {status_txt}\n"
            f"🎯 <b>مین فائل:</b> <code>{info.get('entry')}</code>\n"
            f"🛡️ <b>کریش پروٹیکشن:</b> 24/7 آٹو ری اسٹارٹ"
        )
        bot.edit_message_text(txt, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_project_keyboard(name))

    elif data.startswith("start_"):
        name = data.split("_", 1)[1]
        succ, msg = launch_project(name)
        bot.answer_callback_query(call.id, msg, show_alert=True)
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_project_keyboard(name))

    elif data.startswith("stop_"):
        name = data.split("_", 1)[1]
        succ, msg = stop_project(name, mark_stopped=True)
        bot.answer_callback_query(call.id, msg, show_alert=True)
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_project_keyboard(name))

    elif data.startswith("restart_"):
        name = data.split("_", 1)[1]
        stop_project(name, mark_stopped=False)
        time.sleep(1)
        launch_project(name)
        bot.answer_callback_query(call.id, f"{name} ری اسٹارٹ ہو گیا!", show_alert=True)
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_project_keyboard(name))

    elif data.startswith("logs_"):
        name = data.split("_", 1)[1]
        info = DEPLOYED_BOTS.get(name)
        log_file = os.path.join(info["dir"], "output.log") if info else None
        if log_file and os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8", errors="ignore") as lf:
                lines = lf.readlines()
                last_logs = "".join(lines[-25:]) if lines else "لاگ فائل فی الحال خالی ہے۔"
            bot.send_message(call.message.chat.id, f"📜 <b>لاگز برائے {name}:</b>\n\n<pre>{last_logs}</pre>")
        else:
            bot.answer_callback_query(call.id, "ابھی کوئی لاگز موجود نہیں ہیں!", show_alert=True)

    elif data.startswith("backup_"):
        name = data.split("_", 1)[1]
        bot.answer_callback_query(call.id, f"{name} کا زپ بیک اپ تیار ہو رہا ہے...")
        zip_path = create_project_backup(name)
        if zip_path and os.path.exists(zip_path):
            with open(zip_path, "rb") as zf:
                bot.send_document(call.message.chat.id, zf, caption=f"📦 <b>بیک اپ برائے:</b> <code>{name}</code>")
            os.remove(zip_path)

    elif data.startswith("delete_"):
        name = data.split("_", 1)[1]
        stop_project(name, mark_stopped=True)
        info = DEPLOYED_BOTS.pop(name, None)
        if info and os.path.exists(info["dir"]):
            shutil.rmtree(info["dir"], ignore_errors=True)
        save_metadata()
        bot.answer_callback_query(call.id, f"{name} ڈیلیٹ ہو گیا!", show_alert=True)
        cmd_start(call.message)

if __name__ == "__main__":
    load_metadata()

    # 1. فلاسکی ویب سرور (Keep-Alive)
    web_thread = Thread(target=launch_flask_server, daemon=True)
    web_thread.start()

    # 2. خودکار واچ ڈاگ اور 24 گھنٹے آٹو ری اسٹارٹ تھریڈ
    watchdog_worker = Thread(target=background_watchdog, daemon=True)
    watchdog_worker.start()

    # پہلے سے موجود آن لائن بوٹس کی بحالی
    for p_name, p_info in DEPLOYED_BOTS.items():
        if p_info.get("status") == "running":
            launch_project(p_name)

    logging.info("ہوسٹنگ مینیجر اور واچ ڈاگ انجن مکمل طور پر فعال ہو چکے ہیں۔")

    # کریش پروف انفینیٹ پولنگ لوپ (مین بوٹ کے لیے خودکار ری کنکشن)
    while True:
        try:
            bot.infinity_polling(timeout=25, long_polling_timeout=20)
        except Exception as poll_err:
            logging.error(f"نیٹ ورک رکاوٹ یا کنکشن ڈراپ: {poll_err}")
            logging.info("5 سیکنڈ میں ٹیلیگرام سے خودکار ری کنیکٹ کیا جا رہا ہے...")
            time.sleep(5)
