import os
import re
import sys
import time
import json
import shutil
import zipfile
import logging
import subprocess
from datetime import datetime
from threading import Thread

# Logging configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")

def install_system_package(package_name, import_target=None):
    """Auto-installs required packages if missing to prevent boot crashes."""
    target = import_target or package_name
    try:
        __import__(target)
    except ImportError:
        logging.warning(f"Package '{package_name}' not found. Installing now...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
            logging.info(f"Package '{package_name}' installed successfully.")
        except Exception as err:
            logging.critical(f"Failed to install package '{package_name}': {err}")

# Verify essential system packages
install_system_package("Flask", "flask")
install_system_package("pyTelegramBotAPI", "telebot")
install_system_package("requests", "requests")

from flask import Flask
import telebot
from telebot import types

# === Default Bot Credentials (with Safe Fallbacks) ===
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8965571841:AAEoQpR1Uyfww0YSJB0ev6RMH9qIfLftC3Q").strip()
raw_admin = os.environ.get("ADMIN_ID", "8122951733").strip().lstrip("@")
ADMIN_ID = int(raw_admin) if raw_admin.isdigit() else 8122951733

BASE_DIR = os.getcwd()
PROJECTS_DIR = os.path.join(BASE_DIR, "hosted_projects")
METADATA_FILE = os.path.join(BASE_DIR, "projects_db.json")
BACKUPS_TEMP_DIR = os.path.join(BASE_DIR, "temp_backups")

os.makedirs(PROJECTS_DIR, exist_ok=True)
os.makedirs(BACKUPS_TEMP_DIR, exist_ok=True)

# Lightweight Flask server for 24/7 keep-alive checks
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
    logging.info(f"Flask server listening on port {port}...")
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
    """Persists project configuration data to disk."""
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
        logging.error(f"Failed to save metadata database: {e}")

def load_metadata():
    """Loads previously saved projects from disk on startup."""
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
            logging.info(f"Loaded {len(DEPLOYED_BOTS)} projects from metadata database.")
        except Exception as e:
            logging.error(f"Error loading metadata database: {e}")

def admin_only(func):
    """Admin-only access gatekeeper."""
    def wrapper(message_or_call, *args, **kwargs):
        user_id = message_or_call.from_user.id
        if ADMIN_ID != 0 and user_id != ADMIN_ID:
            if isinstance(message_or_call, types.CallbackQuery):
                bot.answer_callback_query(message_or_call.id, "Access Denied: You are not authorized.", show_alert=True)
            else:
                bot.reply_to(message_or_call, "<b>Access Denied:</b> This bot is restricted to the administrator.")
            return
        return func(message_or_call, *args, **kwargs)
    return wrapper

def scan_python_imports(file_path):
    """Scans python code to automatically extract external dependencies."""
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
        logging.warning(f"Import scanning warning: {e}")
    return packages

def detect_entry_point(folder_path):
    """Detects the main execution entry file of the project."""
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
    """Auto-generates requirements.txt and installs packages."""
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
                logging.error(f"Pip installation error: {e}")

def launch_project(name):
    """Launches a project background process with log redirection."""
    info = DEPLOYED_BOTS.get(name)
    if not info:
        return False, "Project not found."

    project_dir = info["dir"]
    entry_file = info.get("entry")
    runtime = info.get("runtime", "python")

    if not entry_file:
        return False, "Main execution entry file is missing."

    log_path = os.path.join(project_dir, "output.log")
    log_file = open(log_path, "a", encoding="utf-8")
    cmd = [sys.executable, entry_file] if runtime == "python" else ["node", entry_file]

    try:
        proc = subprocess.Popen(cmd, cwd=project_dir, stdout=log_file, stderr=subprocess.STDOUT)
        info["process"] = proc
        info["status"] = "running"
        info["log_file"] = log_path
        save_metadata()
        return True, "Project is now online and active."
    except Exception as e:
        return False, f"Execution failed: {str(e)}"

def stop_project(name, mark_stopped=True):
    """Stops an active project process."""
    info = DEPLOYED_BOTS.get(name)
    if not info:
        return False, "Project not found."

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
    return True, "Project has been stopped."

# ==================== Automated Watchdog & 24H Refresh Engine ====================
def background_watchdog():
    """
    Background daemon running every 15 seconds:
    1. Checks if any active bot crashed and immediately auto-restarts it.
    2. Runs a 24-hour maintenance cycle to prevent memory leaks and zombie processes.
    """
    logging.info("Automated protection watchdog thread initialized.")
    last_24h_cycle = time.time()

    while True:
        try:
            time.sleep(15)
            current_time = time.time()

            # 1. Crash recovery check
            for name, info in list(DEPLOYED_BOTS.items()):
                if info.get("status") == "running" and info.get("auto_restart", True):
                    proc = info.get("process")
                    if proc is None or proc.poll() is not None:
                        logging.warning(f"Bot '{name}' is offline. Watchdog is restarting it...")
                        launch_project(name)

            # 2. 24-Hour scheduled maintenance cycle (86400 seconds)
            if current_time - last_24h_cycle >= 86400:
                logging.info("24-Hour cycle reached: Running maintenance refresh and cleanup...")
                for name, info in list(DEPLOYED_BOTS.items()):
                    if info.get("status") == "running":
                        logging.info(f"24h refresh: Restarting '{name}'")
                        stop_project(name, mark_stopped=False)
                        time.sleep(1)
                        launch_project(name)

                # Clear old temporary zip backups
                shutil.rmtree(BACKUPS_TEMP_DIR, ignore_errors=True)
                os.makedirs(BACKUPS_TEMP_DIR, exist_ok=True)
                last_24h_cycle = current_time
                logging.info("24-Hour scheduled maintenance completed successfully.")

        except Exception as err:
            logging.error(f"Watchdog exception encountered: {err}")
            time.sleep(10)

def create_project_backup(name):
    """Creates a zip backup for an individual project."""
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
    """Creates a full archive backup of all projects and the database."""
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
    b1 = types.InlineKeyboardButton("📋 My Projects", callback_data="btn_list")
    b2 = types.InlineKeyboardButton("📊 Server Monitor", callback_data="btn_status")
    b3 = types.InlineKeyboardButton("💾 Full System Backup", callback_data="btn_full_backup")
    b4 = types.InlineKeyboardButton("🔄 Restart All", callback_data="btn_restart_all")
    b5 = types.InlineKeyboardButton("ℹ️ Help & Guide", callback_data="btn_help")
    markup.add(b1, b2)
    markup.add(b3, b4)
    markup.add(b5)
    return markup

def get_project_keyboard(name):
    markup = types.InlineKeyboardMarkup(row_width=2)
    info = DEPLOYED_BOTS.get(name, {})
    is_running = info.get("status") == "running"

    toggle_btn = types.InlineKeyboardButton("⏹ Stop", callback_data=f"stop_{name}") if is_running else types.InlineKeyboardButton("▶️ Start", callback_data=f"start_{name}")
    restart_btn = types.InlineKeyboardButton("🔄 Restart", callback_data=f"restart_{name}")
    logs_btn = types.InlineKeyboardButton("📜 Live Logs", callback_data=f"logs_{name}")
    backup_btn = types.InlineKeyboardButton("📦 Backup ZIP", callback_data=f"backup_{name}")
    delete_btn = types.InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_{name}")
    back_btn = types.InlineKeyboardButton("⬅️ Projects List", callback_data="btn_list")

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
        "👑 <b>Enterprise Telegram Bot Host Manager (24/7 Online)</b>\n\n"
        "⚡ <b>System Status:</b>\n"
        "• <b>Auto-Restart Watchdog:</b> Active (15s polling health check)\n"
        "• <b>24H Auto-Refresh:</b> Enabled (prevents memory leaks & freezes)\n"
        "• <b>Deployment:</b> Send any <code>.py</code> or <code>.zip</code> file to deploy\n\n"
        "👇 Use the dashboard below to control your bots:"
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
        bot.reply_to(message, "⚠️ <b>Invalid File:</b> Please send only <code>.py</code> or <code>.zip</code> archives.")
        return

    clean_name = re.sub(r'[^a-zA-Z0-9_]', '', file_name.rsplit('.', 1)[0]).lower()
    if not clean_name:
        clean_name = f"bot_{int(time.time())}"

    project_dir = os.path.join(PROJECTS_DIR, clean_name)
    if clean_name in DEPLOYED_BOTS:
        stop_project(clean_name)

    status_msg = bot.reply_to(message, "⏳ <b>Downloading file, please wait...</b>")

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
                bot.edit_message_text("❌ <b>Error:</b> No executable script (bot.py, main.py, etc.) found inside zip.",
                                      chat_id=message.chat.id, message_id=status_msg.message_id)
                return

        bot.edit_message_text("📦 <b>Scanning dependencies and configuring environment...</b>",
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
                f"✅ <b>Project Successfully Deployed & Online!</b>\n\n"
                f"🏷 <b>Name:</b> <code>{clean_name}</code>\n"
                f"⚙️ <b>Entry:</b> <code>{entry_file}</code>\n"
                f"🛡️ <b>Auto-Restart:</b> Enabled (24/7 Watchdog)\n"
                f"🟢 <b>Status:</b> Live and running"
            )
            bot.edit_message_text(resp_text, chat_id=message.chat.id, message_id=status_msg.message_id,
                                  reply_markup=get_project_keyboard(clean_name))
        else:
            bot.edit_message_text(f"❌ <b>Startup Failed:</b>\n<code>{msg}</code>",
                                  chat_id=message.chat.id, message_id=status_msg.message_id)

    except Exception as e:
        logging.error(f"Upload processing error: {e}")
        bot.edit_message_text(f"❌ Error: {str(e)}", chat_id=message.chat.id, message_id=status_msg.message_id)

@bot.callback_query_handler(func=lambda call: True)
@admin_only
def handle_callbacks(call):
    data = call.data

    if data == "btn_list":
        bot.answer_callback_query(call.id)
        if not DEPLOYED_BOTS:
            bot.edit_message_text("📭 No deployed projects found.",
                                  chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  reply_markup=get_main_keyboard())
            return

        markup = types.InlineKeyboardMarkup(row_width=1)
        for name, info in DEPLOYED_BOTS.items():
            icon = "🟢" if info.get("status") == "running" else "🔴"
            markup.add(types.InlineKeyboardButton(f"{icon} {name}", callback_data=f"manage_{name}"))
        markup.add(types.InlineKeyboardButton("⬅️ Back to Menu", callback_data="btn_home"))

        bot.edit_message_text("📋 <b>Deployed Projects List:</b>",
                              chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

    elif data == "btn_home":
        bot.answer_callback_query(call.id)
        bot.edit_message_text("👑 <b>Admin Dashboard:</b>", chat_id=call.message.chat.id,
                              message_id=call.message.message_id, reply_markup=get_main_keyboard())

    elif data == "btn_status":
        bot.answer_callback_query(call.id)
        running = sum(1 for b in DEPLOYED_BOTS.values() if b.get("status") == "running")
        text = (
            "📊 <b>Server Monitor & Health Status:</b>\n\n"
            f"📁 <b>Total Projects:</b> {len(DEPLOYED_BOTS)}\n"
            f"🟢 <b>Online Bots:</b> {running}\n"
            f"🔴 <b>Offline Bots:</b> {len(DEPLOYED_BOTS) - running}\n"
            f"🛡️ <b>Watchdog Engine:</b> Active (Auto-Heal Enabled)\n"
            f"⏳ <b>24-Hour Refresh:</b> Active (Prevents Freezes)\n"
            f"🌐 <b>Keep-Alive Server:</b> 24/7 Online"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ Back to Menu", callback_data="btn_home"))
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

    elif data == "btn_help":
        bot.answer_callback_query(call.id)
        msg = (
            "ℹ️ <b>Host Manager Features & Guide:</b>\n\n"
            "1. <b>Upload:</b> Send any <code>.py</code> or <code>.zip</code> file to auto-deploy.\n"
            "2. <b>Self-Healing:</b> If a bot crashes, the watchdog revives it within 15 seconds.\n"
            "3. <b>24H Refresh:</b> System runs maintenance daily to clean cached memory and ensure zero freezes.\n"
            "4. <b>Backups:</b> Download individual or full system backups at any time directly in Telegram."
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ Back to Menu", callback_data="btn_home"))
        bot.edit_message_text(msg, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

    elif data == "btn_full_backup":
        bot.answer_callback_query(call.id, "Generating full system backup...")
        zip_path = create_full_system_backup()
        if zip_path and os.path.exists(zip_path):
            with open(zip_path, "rb") as zf:
                bot.send_document(call.message.chat.id, zf, caption="💾 <b>Full System Backup (All Projects & DB)</b>")
            os.remove(zip_path)
        else:
            bot.send_message(call.message.chat.id, "❌ Failed to create system backup archive.")

    elif data == "btn_restart_all":
        bot.answer_callback_query(call.id, "Restarting all projects...")
        for name in list(DEPLOYED_BOTS.keys()):
            stop_project(name, mark_stopped=False)
            time.sleep(0.5)
            launch_project(name)
        bot.answer_callback_query(call.id, "All bots restarted successfully!", show_alert=True)
        cmd_start(call.message)

    elif data.startswith("manage_"):
        name = data.split("_", 1)[1]
        info = DEPLOYED_BOTS.get(name)
        if not info:
            bot.answer_callback_query(call.id, "Project not found!", show_alert=True)
            return
        status_txt = "🟢 Online (Watchdog Active)" if info.get("status") == "running" else "🔴 Stopped"
        txt = (
            f"⚙️ <b>Project:</b> <code>{name}</code>\n"
            f"📊 <b>Status:</b> {status_txt}\n"
            f"🎯 <b>Entry File:</b> <code>{info.get('entry')}</code>\n"
            f"🛡️ <b>Crash Protection:</b> 24/7 Auto-Restart"
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
        bot.answer_callback_query(call.id, f"{name} restarted successfully!", show_alert=True)
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_project_keyboard(name))

    elif data.startswith("logs_"):
        name = data.split("_", 1)[1]
        info = DEPLOYED_BOTS.get(name)
        log_file = os.path.join(info["dir"], "output.log") if info else None
        if log_file and os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8", errors="ignore") as lf:
                lines = lf.readlines()
                last_logs = "".join(lines[-25:]) if lines else "Log file is currently empty."
            bot.send_message(call.message.chat.id, f"📜 <b>Logs for {name}:</b>\n\n<pre>{last_logs}</pre>")
        else:
            bot.answer_callback_query(call.id, "No logs available yet!", show_alert=True)

    elif data.startswith("backup_"):
        name = data.split("_", 1)[1]
        bot.answer_callback_query(call.id, f"Creating backup for {name}...")
        zip_path = create_project_backup(name)
        if zip_path and os.path.exists(zip_path):
            with open(zip_path, "rb") as zf:
                bot.send_document(call.message.chat.id, zf, caption=f"📦 <b>Project Backup:</b> <code>{name}</code>")
            os.remove(zip_path)

    elif data.startswith("delete_"):
        name = data.split("_", 1)[1]
        stop_project(name, mark_stopped=True)
        info = DEPLOYED_BOTS.pop(name, None)
        if info and os.path.exists(info["dir"]):
            shutil.rmtree(info["dir"], ignore_errors=True)
        save_metadata()
        bot.answer_callback_query(call.id, f"{name} deleted successfully!", show_alert=True)
        cmd_start(call.message)

if __name__ == "__main__":
    load_metadata()

    # 1. Flask Keep-Alive Web Server
    web_thread = Thread(target=launch_flask_server, daemon=True)
    web_thread.start()

    # 2. Automated Watchdog and 24-Hour Auto-Restart Engine
    watchdog_worker = Thread(target=background_watchdog, daemon=True)
    watchdog_worker.start()

    # Restore previously active projects
    for p_name, p_info in DEPLOYED_BOTS.items():
        if p_info.get("status") == "running":
            launch_project(p_name)

    logging.info("Host Manager and Watchdog service running 24/7.")

    # Crash-proof reconnection loop for long polling
    while True:
        try:
            bot.infinity_polling(timeout=25, long_polling_timeout=20)
        except Exception as poll_err:
            logging.error(f"Network interrupt / connection drop: {poll_err}")
            logging.info("Reconnecting to Telegram API in 5 seconds...")
            time.sleep(5)
