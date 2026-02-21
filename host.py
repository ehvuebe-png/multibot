import telebot
import subprocess
import os
import zipfile
import tempfile
import shutil
from telebot import types
import time
from datetime import datetime, timedelta
import psutil
import sqlite3
import json
import logging
import signal
import threading
import re
import sys
import atexit
import requests
from flask import Flask
from threading import Thread
import socket
# Khối lệnh ép IP cứng để vượt lỗi DNS
try:
    telegram_ip = "149.154.167.220"
    socket.orig_getaddrinfo = socket.getaddrinfo
    def getaddrinfo_wrapper(host, port, family=0, type=0, proto=0, flags=0):
        if host == 'api.telegram.org':
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (telegram_ip, port))]
        return socket.orig_getaddrinfo(host, port, family, type, proto, flags)
    socket.getaddrinfo = getaddrinfo_wrapper
    print("✅ Đã ép IP Telegram thành công!")
except:
    pass

app = Flask('')

@app.route('/')
def home():
    return "I'm Marco File Host"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    print("Flask Keep-Alive server started.")

TOKEN = '8008606599:AAFtCG73FhGBbYKYs2yh0Uwhrek37evZQPw'
OWNER_ID = 6924956412
ADMIN_ID = 6924956412
YOUR_USERNAME = '@Anhlathiendola3'
UPDATE_CHANNEL = ''

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_BOTS_DIR = os.path.join(BASE_DIR, 'upload_bots')
IROTECH_DIR = os.path.join(BASE_DIR, 'inf')
DATABASE_PATH = os.path.join(IROTECH_DIR, 'bot_data.db')

FREE_USER_LIMIT = 10
SUBSCRIBED_USER_LIMIT = 15
ADMIN_LIMIT = 999
OWNER_LIMIT = float('inf')

os.makedirs(UPLOAD_BOTS_DIR, exist_ok=True)
os.makedirs(IROTECH_DIR, exist_ok=True)

bot = telebot.TeleBot(TOKEN)

bot_scripts = {}
user_subscriptions = {}
user_files = {}
active_users = set()
admin_ids = {ADMIN_ID, OWNER_ID}
bot_locked = False
blocked_users = set()

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

COMMAND_BUTTONS_LAYOUT_USER_SPEC = [
    ["🚀 Kênh Cập Nhật"],
    ["📤 Tải File Lên", "📂 Xem File Của Tôi"],
    ["⚡ Tốc Độ Bot", "📊 Thống Kê"],
    ["📞 Liên Hệ Admin"]
]

ADMIN_COMMAND_BUTTONS_LAYOUT_USER_SPEC = [
    ["🚀 Kênh Cập Nhật"],
    ["📤 Tải File Lên", "📂 Xem File Của Tôi"],
    ["⚡ Tốc Độ Bot", "📊 Thống Kê"],
    ["💳 Quản Lý VIP", "📢 Gửi Tin Nhắn Hàng Loạt"],
    ["🔒 Khóa Bot", "🟢 Chạy Tất Cả File"],
    ["🚫 Block User", "✅ Unblock User"],
    ["👑 Quản Trị Viên", "📞 Liên Hệ Admin"],
    ["🗑️ Xóa Tất Cả Server Files"]
]

def init_db():
    logger.info(f"Khởi tạo database tại: {DATABASE_PATH}")
    try:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS subscriptions
                     (user_id INTEGER PRIMARY KEY, expiry TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS user_files
                     (user_id INTEGER, file_name TEXT, file_type TEXT,
                      PRIMARY KEY (user_id, file_name))''')
        c.execute('''CREATE TABLE IF NOT EXISTS active_users
                     (user_id INTEGER PRIMARY KEY)''')
        c.execute('''CREATE TABLE IF NOT EXISTS admins
                     (user_id INTEGER PRIMARY KEY)''')
        c.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (OWNER_ID,))
        if ADMIN_ID != OWNER_ID:
            c.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (ADMIN_ID,))
        conn.commit()
        conn.close()
        logger.info("Khởi tạo database thành công.")
    except Exception as e:
        logger.error(f"❌ Lỗi khởi tạo database: {e}", exc_info=True)

def load_data():
    logger.info("Đang tải dữ liệu từ database...")
    try:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('SELECT user_id, expiry FROM subscriptions')
        for user_id, expiry in c.fetchall():
            try:
                user_subscriptions[user_id] = {'expiry': datetime.fromisoformat(expiry)}
            except ValueError:
                logger.warning(f"⚠️ Định dạng ngày hết hạn không hợp lệ cho user {user_id}: {expiry}")
        c.execute('SELECT user_id, file_name, file_type FROM user_files')
        for user_id, file_name, file_type in c.fetchall():
            if user_id not in user_files:
                user_files[user_id] = []
            user_files[user_id].append((file_name, file_type))
        c.execute('SELECT user_id FROM active_users')
        active_users.update(user_id for (user_id,) in c.fetchall())
        c.execute('SELECT user_id FROM admins')
        admin_ids.update(user_id for (user_id,) in c.fetchall())
        conn.close()
        logger.info(f"Đã tải dữ liệu: {len(active_users)} users, {len(user_subscriptions)} VIP, {len(admin_ids)} admins.")
    except Exception as e:
        logger.error(f"❌ Lỗi tải dữ liệu: {e}", exc_info=True)

init_db()
load_data()

def get_user_folder(user_id):
    user_folder = os.path.join(UPLOAD_BOTS_DIR, str(user_id))
    os.makedirs(user_folder, exist_ok=True)
    return user_folder

def get_user_file_limit(user_id):
    if user_id == OWNER_ID:
        return OWNER_LIMIT
    if user_id in admin_ids:
        return ADMIN_LIMIT
    if user_id in user_subscriptions and user_subscriptions[user_id]['expiry'] > datetime.now():
        return SUBSCRIBED_USER_LIMIT
    return FREE_USER_LIMIT

def get_user_file_count(user_id):
    return len(user_files.get(user_id, []))

def is_bot_running(script_owner_id, file_name):
    script_key = f"{script_owner_id}_{file_name}"
    script_info = bot_scripts.get(script_key)
    if script_info and script_info.get('process'):
        try:
            proc = psutil.Process(script_info['process'].pid)
            is_running = proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
            if not is_running:
                logger.warning(f"Process {script_info['process'].pid} cho {script_key} không chạy. Dọn dẹp.")
                if 'log_file' in script_info and hasattr(script_info['log_file'], 'close') and not script_info['log_file'].closed:
                    try:
                        script_info['log_file'].close()
                    except Exception as log_e:
                        logger.error(f"Lỗi đóng log file khi dọn dẹp {script_key}: {log_e}")
                if script_key in bot_scripts:
                    del bot_scripts[script_key]
            return is_running
        except psutil.NoSuchProcess:
            logger.warning(f"Process cho {script_key} không tồn tại. Dọn dẹp.")
            if 'log_file' in script_info and hasattr(script_info['log_file'], 'close') and not script_info['log_file'].closed:
                try:
                    script_info['log_file'].close()
                except Exception as log_e:
                    logger.error(f"Lỗi đóng log file khi dọn dẹp {script_key}: {log_e}")
            if script_key in bot_scripts:
                del bot_scripts[script_key]
            return False
        except Exception as e:
            logger.error(f"Lỗi kiểm tra process status cho {script_key}: {e}", exc_info=True)
            return False
    return False

def kill_process_tree(process_info):
    pid = None
    log_file_closed = False
    script_key = process_info.get('script_key', 'N/A')
    try:
        if 'log_file' in process_info and hasattr(process_info['log_file'], 'close') and not process_info['log_file'].closed:
            try:
                process_info['log_file'].close()
                log_file_closed = True
                logger.info(f"Đã đóng log file cho {script_key}")
            except Exception as log_e:
                logger.error(f"Lỗi đóng log file khi kill cho {script_key}: {log_e}")
        process = process_info.get('process')
        if process and hasattr(process, 'pid'):
            pid = process.pid
            if pid:
                try:
                    parent = psutil.Process(pid)
                    children = parent.children(recursive=True)
                    logger.info(f"Đang kill process tree cho {script_key} (PID: {pid}, Children: {[c.pid for c in children]})")
                    for child in children:
                        try:
                            child.terminate()
                        except:
                            try:
                                child.kill()
                            except:
                                pass
                    gone, alive = psutil.wait_procs(children, timeout=1)
                    for p in alive:
                        try:
                            p.kill()
                        except:
                            pass
                    try:
                        parent.terminate()
                        try:
                            parent.wait(timeout=1)
                        except psutil.TimeoutExpired:
                            parent.kill()
                    except:
                        pass
                except psutil.NoSuchProcess:
                    logger.warning(f"Process {pid} cho {script_key} không tồn tại khi kill.")
    except Exception as e:
        logger.error(f"❌ Lỗi kill process tree cho PID {pid} ({script_key}): {e}", exc_info=True)

TELEGRAM_MODULES = {
    'telebot': 'pyTelegramBotAPI',
    'telegram': 'python-telegram-bot',
    'python_telegram_bot': 'python-telegram-bot',
    'aiogram': 'aiogram',
    'pyrogram': 'pyrogram',
    'telethon': 'telethon',
    'bs4': 'beautifulsoup4',
    'requests': 'requests',
    'pillow': 'Pillow',
    'cv2': 'opencv-python',
    'yaml': 'PyYAML',
    'dotenv': 'python-dotenv',
    'dateutil': 'python-dateutil',
    'pandas': 'pandas',
    'numpy': 'numpy',
    'flask': 'Flask',
    'django': 'Django',
    'sqlalchemy': 'SQLAlchemy',
    'psutil': 'psutil',
    'asyncio': None,
    'json': None,
    'datetime': None,
    'os': None,
    'sys': None,
    're': None,
    'time': None,
    'math': None,
    'random': None,
    'logging': None,
    'threading': None,
    'subprocess': None,
    'zipfile': None,
    'tempfile': None,
    'shutil': None,
    'sqlite3': None,
    'atexit': None
}

def attempt_install_pip(module_name, message):
    package_name = TELEGRAM_MODULES.get(module_name.lower(), module_name)
    if package_name is None:
        logger.info(f"Module '{module_name}' là core. Bỏ qua cài đặt pip.")
        return False
    try:
        bot.reply_to(message, f"🐍 Module `{module_name}` không tìm thấy. Đang cài `{package_name}`...", parse_mode='Markdown')
        command = [sys.executable, '-m', 'pip', 'install', package_name]
        logger.info(f"Đang chạy cài đặt: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True, check=False, encoding='utf-8', errors='ignore')
        if result.returncode == 0:
            logger.info(f"Đã cài {package_name}. Output:\n{result.stdout}")
            bot.reply_to(message, f"✅ Package `{package_name}` (cho `{module_name}`) đã được cài.", parse_mode='Markdown')
            return True
        else:
            error_msg = f"❌ Không thể cài `{package_name}` cho `{module_name}`.\nLog:\n```\n{result.stderr or result.stdout}\n```"
            logger.error(error_msg)
            if len(error_msg) > 4000:
                error_msg = error_msg[:4000] + "\n... (Log bị cắt)"
            bot.reply_to(message, error_msg, parse_mode='Markdown')
            return False
    except Exception as e:
        error_msg = f"❌ Lỗi cài `{package_name}`: {str(e)}"
        logger.error(error_msg, exc_info=True)
        bot.reply_to(message, error_msg)
        return False

def attempt_install_npm(module_name, user_folder, message):
    try:
        bot.reply_to(message, f"🟠 Package Node `{module_name}` không tìm thấy. Đang cài local...", parse_mode='Markdown')
        command = ['npm', 'install', module_name]
        logger.info(f"Đang chạy npm install: {' '.join(command)} trong {user_folder}")
        result = subprocess.run(command, capture_output=True, text=True, check=False, cwd=user_folder, encoding='utf-8', errors='ignore')
        if result.returncode == 0:
            logger.info(f"Đã cài {module_name}. Output:\n{result.stdout}")
            bot.reply_to(message, f"✅ Package Node `{module_name}` đã được cài local.", parse_mode='Markdown')
            return True
        else:
            error_msg = f"❌ Không thể cài Node package `{module_name}`.\nLog:\n```\n{result.stderr or result.stdout}\n```"
            logger.error(error_msg)
            if len(error_msg) > 4000:
                error_msg = error_msg[:4000] + "\n... (Log bị cắt)"
            bot.reply_to(message, error_msg, parse_mode='Markdown')
            return False
    except FileNotFoundError:
        error_msg = "❌ Lỗi: 'npm' không tìm thấy. Hãy đảm bảo Node.js/npm đã được cài đặt."
        logger.error(error_msg)
        bot.reply_to(message, error_msg)
        return False
    except Exception as e:
        error_msg = f"❌ Lỗi cài Node package `{module_name}`: {str(e)}"
        logger.error(error_msg, exc_info=True)
        bot.reply_to(message, error_msg)
        return False

def run_script(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt=1):
    max_attempts = 2
    if attempt > max_attempts:
        bot.reply_to(message_obj_for_reply, f"❌ Không thể chạy '{file_name}' sau {max_attempts} lần thử. Kiểm tra log.")
        return

    script_key = f"{script_owner_id}_{file_name}"
    logger.info(f"Lần thử {attempt} chạy Python script: {script_path} (Key: {script_key}) cho user {script_owner_id}")

    try:
        if not os.path.exists(script_path):
            bot.reply_to(message_obj_for_reply, f"❌ Lỗi: Script '{file_name}' không tìm thấy!")
            logger.error(f"Script không tìm thấy: {script_path} cho user {script_owner_id}")
            if script_owner_id in user_files:
                user_files[script_owner_id] = [f for f in user_files.get(script_owner_id, []) if f[0] != file_name]
            remove_user_file_db(script_owner_id, file_name)
            return

        if attempt == 1:
            check_command = [sys.executable, script_path]
            logger.info(f"Đang chạy kiểm tra Python: {' '.join(check_command)}")
            check_proc = None
            try:
                check_proc = subprocess.Popen(check_command, cwd=user_folder, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')
                stdout, stderr = check_proc.communicate(timeout=5)
                return_code = check_proc.returncode
                logger.info(f"Kiểm tra Python sớm. RC: {return_code}. Stderr: {stderr[:200]}...")
                if return_code != 0 and stderr:
                    match_py = re.search(r"ModuleNotFoundError: No module named '(.+?)'", stderr)
                    if match_py:
                        module_name = match_py.group(1).strip().strip("'\"")
                        logger.info(f"Phát hiện thiếu module Python: {module_name}")
                        if attempt_install_pip(module_name, message_obj_for_reply):
                            logger.info(f"Cài đặt OK cho {module_name}. Đang thử lại run_script...")
                            bot.reply_to(message_obj_for_reply, f"🔄 Cài đặt thành công. Đang thử lại '{file_name}'...")
                            time.sleep(2)
                            threading.Thread(target=run_script, args=(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt + 1)).start()
                            return
                        else:
                            bot.reply_to(message_obj_for_reply, f"❌ Cài đặt thất bại. Không thể chạy '{file_name}'.")
                            return
                    else:
                        error_summary = stderr[:500]
                        bot.reply_to(message_obj_for_reply, f"❌ Lỗi trong kiểm tra script cho '{file_name}':\n```\n{error_summary}\n```\nSửa script.", parse_mode='Markdown')
                        return
            except subprocess.TimeoutExpired:
                logger.info("Kiểm tra Python timeout (>5s), imports có vẻ OK. Đang kill process kiểm tra.")
                if check_proc and check_proc.poll() is None:
                    check_proc.kill()
                    check_proc.communicate()
                logger.info("Process kiểm tra Python đã được kill. Tiếp tục chạy dài hạn.")
            except FileNotFoundError:
                logger.error(f"Python interpreter không tìm thấy: {sys.executable}")
                bot.reply_to(message_obj_for_reply, f"❌ Lỗi: Python interpreter '{sys.executable}' không tìm thấy.")
                return
            except Exception as e:
                logger.error(f"Lỗi trong kiểm tra Python cho {script_key}: {e}", exc_info=True)
                bot.reply_to(message_obj_for_reply, f"❌ Lỗi không mong muốn trong kiểm tra script cho '{file_name}': {e}")
                return
            finally:
                if check_proc and check_proc.poll() is None:
                    logger.warning(f"Process kiểm tra Python {check_proc.pid} vẫn chạy. Đang kill.")
                    check_proc.kill()
                    check_proc.communicate()

        logger.info(f"Đang bắt đầu process Python dài hạn cho {script_key}")
        log_file_path = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        log_file = None
        process = None
        try:
            log_file = open(log_file_path, 'w', encoding='utf-8', errors='ignore')
        except Exception as e:
            logger.error(f"Không thể mở log file '{log_file_path}' cho {script_key}: {e}", exc_info=True)
            bot.reply_to(message_obj_for_reply, f"❌ Không thể mở log file '{log_file_path}': {e}")
            return
        try:
            startupinfo = None
            creationflags = 0
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            process = subprocess.Popen(
                [sys.executable, script_path], cwd=user_folder, stdout=log_file, stderr=log_file,
                stdin=subprocess.PIPE, startupinfo=startupinfo, creationflags=creationflags,
                encoding='utf-8', errors='ignore'
            )
            logger.info(f"Đã bắt đầu Python process {process.pid} cho {script_key}")
            bot_scripts[script_key] = {
                'process': process, 'log_file': log_file, 'file_name': file_name,
                'chat_id': message_obj_for_reply.chat.id,
                'script_owner_id': script_owner_id,
                'start_time': datetime.now(), 'user_folder': user_folder, 'type': 'py', 'script_key': script_key
            }
            bot.reply_to(message_obj_for_reply, f"✅ Python script '{file_name}' đã chạy! (PID: {process.pid}) (Cho User: {script_owner_id})")
        except FileNotFoundError:
            logger.error(f"Python interpreter {sys.executable} không tìm thấy cho chạy dài hạn {script_key}")
            bot.reply_to(message_obj_for_reply, f"❌ Lỗi: Python interpreter '{sys.executable}' không tìm thấy.")
            if log_file and not log_file.closed:
                log_file.close()
            if script_key in bot_scripts:
                del bot_scripts[script_key]
        except Exception as e:
            if log_file and not log_file.closed:
                log_file.close()
            error_msg = f"❌ Lỗi bắt đầu Python script '{file_name}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            bot.reply_to(message_obj_for_reply, error_msg)
            if process and process.poll() is None:
                logger.warning(f"Đang kill process Python {process.pid} cho {script_key}")
                kill_process_tree({'process': process, 'log_file': log_file, 'script_key': script_key})
            if script_key in bot_scripts:
                del bot_scripts[script_key]
    except Exception as e:
        error_msg = f"❌ Lỗi không mong muốn khi chạy Python script '{file_name}': {str(e)}"
        logger.error(error_msg, exc_info=True)
        bot.reply_to(message_obj_for_reply, error_msg)
        if script_key in bot_scripts:
            logger.warning(f"Dọn dẹp {script_key} do lỗi trong run_script.")
            kill_process_tree(bot_scripts[script_key])
            del bot_scripts[script_key]

def run_js_script(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt=1):
    max_attempts = 2
    if attempt > max_attempts:
        bot.reply_to(message_obj_for_reply, f"❌ Không thể chạy '{file_name}' sau {max_attempts} lần thử. Kiểm tra log.")
        return

    script_key = f"{script_owner_id}_{file_name}"
    logger.info(f"Lần thử {attempt} chạy JS script: {script_path} (Key: {script_key}) cho user {script_owner_id}")

    try:
        if not os.path.exists(script_path):
            bot.reply_to(message_obj_for_reply, f"❌ Lỗi: Script '{file_name}' không tìm thấy!")
            logger.error(f"JS Script không tìm thấy: {script_path} cho user {script_owner_id}")
            if script_owner_id in user_files:
                user_files[script_owner_id] = [f for f in user_files.get(script_owner_id, []) if f[0] != file_name]
            remove_user_file_db(script_owner_id, file_name)
            return

        if attempt == 1:
            check_command = ['node', script_path]
            logger.info(f"Đang chạy kiểm tra JS: {' '.join(check_command)}")
            check_proc = None
            try:
                check_proc = subprocess.Popen(check_command, cwd=user_folder, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')
                stdout, stderr = check_proc.communicate(timeout=5)
                return_code = check_proc.returncode
                logger.info(f"Kiểm tra JS sớm. RC: {return_code}. Stderr: {stderr[:200]}...")
                
                if return_code != 0 and stderr:
                    match_js = re.search(r"Cannot find module '(.+?)'", stderr)
                    if match_js:
                        module_name = match_js.group(1).strip().strip("'\"")
                        if not module_name.startswith('.') and not module_name.startswith('/'):
                            logger.info(f"Phát hiện thiếu Node module: {module_name}")
                            if attempt_install_npm(module_name, user_folder, message_obj_for_reply):
                                logger.info(f"NPM Install OK cho {module_name}. Đang thử lại run_js_script...")
                                bot.reply_to(message_obj_for_reply, f"🔄 NPM Install thành công. Đang thử lại '{file_name}'...")
                                time.sleep(2)
                                threading.Thread(target=run_js_script, args=(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt + 1)).start()
                                return
                            else:
                                bot.reply_to(message_obj_for_reply, f"❌ NPM Install thất bại. Không thể chạy '{file_name}'.")
                                return
                        else:
                            logger.info(f"Bỏ qua npm install cho relative/core: {module_name}")
                    error_summary = stderr[:500]
                    bot.reply_to(message_obj_for_reply, f"❌ Lỗi trong kiểm tra JS script cho '{file_name}':\n```\n{error_summary}\n```\nSửa script hoặc cài thủ công.", parse_mode='Markdown')
                    return
            except subprocess.TimeoutExpired:
                logger.info("Kiểm tra JS timeout (>5s), imports có vẻ OK. Đang kill process kiểm tra.")
                if check_proc and check_proc.poll() is None:
                    check_proc.kill()
                    check_proc.communicate()
                logger.info("Process kiểm tra JS đã được kill. Tiếp tục chạy dài hạn.")
            except FileNotFoundError:
                error_msg = "❌ Lỗi: 'node' không tìm thấy. Hãy đảm bảo Node.js đã được cài đặt cho file JS."
                logger.error(error_msg)
                bot.reply_to(message_obj_for_reply, error_msg)
                return
            except Exception as e:
                logger.error(f"Lỗi trong kiểm tra JS cho {script_key}: {e}", exc_info=True)
                bot.reply_to(message_obj_for_reply, f"❌ Lỗi không mong muốn trong kiểm tra JS cho '{file_name}': {e}")
                return
            finally:
                if check_proc and check_proc.poll() is None:
                    logger.warning(f"Process kiểm tra JS {check_proc.pid} vẫn chạy. Đang kill.")
                    check_proc.kill()
                    check_proc.communicate()

        logger.info(f"Đang bắt đầu process JS dài hạn cho {script_key}")
        log_file_path = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        log_file = None
        process = None
        
        try:
            log_file = open(log_file_path, "a", encoding="utf-8")

            process = subprocess.Popen(
                ['node', script_path],
                cwd=user_folder,
                stdout=log_file,
                stderr=log_file,
                stdin=subprocess.PIPE,
                encoding='utf-8',
                errors='ignore'
            )

            logger.info(f"Đã bắt đầu JS process {process.pid} cho {script_key}")

            bot_scripts[script_key] = {
                'process': process,
                'log_file': log_file,
                'file_name': file_name,
                'chat_id': message_obj_for_reply.chat.id,
                'script_owner_id': script_owner_id,
                'start_time': datetime.now(),
                'user_folder': user_folder,
                'type': 'js',
                'script_key': script_key
            }

            bot.reply_to(
                message_obj_for_reply,
                    f"✅ JS script '{file_name}' đã chạy! (PID: {process.pid})"
            )

        except FileNotFoundError:
            error_msg = "❌ Lỗi: 'node' không tìm thấy. Hãy cài Node.js."
            logger.error(error_msg)

            if log_file and not log_file.closed:
                log_file.close()

            bot.reply_to(message_obj_for_reply, error_msg)

            if script_key in bot_scripts:
                del bot_scripts[script_key]

        except Exception as e:
            if log_file and not log_file.closed:
                log_file.close()

            error_msg = f"❌ Lỗi bắt đầu JS script '{file_name}': {str(e)}"
            logger.error(error_msg, exc_info=True)

            bot.reply_to(message_obj_for_reply, error_msg)

            if process and process.poll() is None:
                kill_process_tree({
                    'process': process,
                    'log_file': log_file,
                    'script_key': script_key
                })

            if script_key in bot_scripts:
                del bot_scripts[script_key]

    except Exception as e:
        logger.error(f"Lỗi không mong muốn trong run_js_script: {e}", exc_info=True)
        bot.reply_to(message_obj_for_reply, f"❌ Lỗi hệ thống: {str(e)}")

DB_LOCK = threading.Lock()

def save_user_file(user_id, file_name, file_type='py'):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('INSERT OR REPLACE INTO user_files (user_id, file_name, file_type) VALUES (?, ?, ?)',
                      (user_id, file_name, file_type))
            conn.commit()
            if user_id not in user_files:
                user_files[user_id] = []
            user_files[user_id] = [(fn, ft) for fn, ft in user_files[user_id] if fn != file_name]
            user_files[user_id].append((file_name, file_type))
            logger.info(f"Đã lưu file '{file_name}' ({file_type}) cho user {user_id}")
        except sqlite3.Error as e:
            logger.error(f"❌ Lỗi SQLite khi lưu file cho user {user_id}, {file_name}: {e}")
        except Exception as e:
            logger.error(f"❌ Lỗi không mong muốn khi lưu file cho {user_id}, {file_name}: {e}", exc_info=True)
        finally:
            conn.close()

def remove_user_file_db(user_id, file_name):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('DELETE FROM user_files WHERE user_id = ? AND file_name = ?', (user_id, file_name))
            conn.commit()
            if user_id in user_files:
                user_files[user_id] = [f for f in user_files[user_id] if f[0] != file_name]
                if not user_files[user_id]:
                    del user_files[user_id]
            logger.info(f"Đã xóa file '{file_name}' cho user {user_id} khỏi DB")
        except sqlite3.Error as e:
            logger.error(f"❌ Lỗi SQLite khi xóa file cho {user_id}, {file_name}: {e}")
        except Exception as e:
            logger.error(f"❌ Lỗi không mong muốn khi xóa file cho {user_id}, {file_name}: {e}", exc_info=True)
        finally:
            conn.close()

def remove_all_user_files_db(user_id):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('DELETE FROM user_files WHERE user_id = ?', (user_id,))
            conn.commit()
            if user_id in user_files:
                del user_files[user_id]
            logger.info(f"Đã xóa tất cả file cho user {user_id} khỏi DB")
            return True
        except sqlite3.Error as e:
            logger.error(f"❌ Lỗi SQLite khi xóa tất cả file cho {user_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Lỗi không mong muốn khi xóa tất cả file cho {user_id}: {e}", exc_info=True)
            return False
        finally:
            conn.close()

def add_active_user(user_id):
    active_users.add(user_id)
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('INSERT OR IGNORE INTO active_users (user_id) VALUES (?)', (user_id,))
            conn.commit()
            logger.info(f"Đã thêm/xác nhận active user {user_id} trong DB")
        except sqlite3.Error as e:
            logger.error(f"❌ Lỗi SQLite khi thêm active user {user_id}: {e}")
        except Exception as e:
            logger.error(f"❌ Lỗi không mong muốn khi thêm active user {user_id}: {e}", exc_info=True)
        finally:
            conn.close()

def save_subscription(user_id, expiry):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            expiry_str = expiry.isoformat()
            c.execute('INSERT OR REPLACE INTO subscriptions (user_id, expiry) VALUES (?, ?)', (user_id, expiry_str))
            conn.commit()
            user_subscriptions[user_id] = {'expiry': expiry}
            logger.info(f"Đã lưu subscription cho {user_id}, hết hạn {expiry_str}")
        except sqlite3.Error as e:
            logger.error(f"❌ Lỗi SQLite khi lưu subscription cho {user_id}: {e}")
        except Exception as e:
            logger.error(f"❌ Lỗi không mong muốn khi lưu subscription cho {user_id}: {e}", exc_info=True)
        finally:
            conn.close()

def remove_subscription_db(user_id):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('DELETE FROM subscriptions WHERE user_id = ?', (user_id,))
            conn.commit()
            if user_id in user_subscriptions:
                del user_subscriptions[user_id]
            logger.info(f"Đã xóa subscription cho {user_id} khỏi DB")
        except sqlite3.Error as e:
            logger.error(f"❌ Lỗi SQLite khi xóa subscription cho {user_id}: {e}")
        except Exception as e:
            logger.error(f"❌ Lỗi không mong muốn khi xóa subscription cho {user_id}: {e}", exc_info=True)
        finally:
            conn.close()

def add_admin_db(admin_id):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (admin_id,))
            conn.commit()
            admin_ids.add(admin_id)
            logger.info(f"Đã thêm admin {admin_id} vào DB")
        except sqlite3.Error as e:
            logger.error(f"❌ Lỗi SQLite khi thêm admin {admin_id}: {e}")
        except Exception as e:
            logger.error(f"❌ Lỗi không mong muốn khi thêm admin {admin_id}: {e}", exc_info=True)
        finally:
            conn.close()

def remove_admin_db(admin_id):
    if admin_id == OWNER_ID:
        logger.warning("Đã cố gắng xóa OWNER_ID khỏi admins.")
        return False
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        removed = False
        try:
            c.execute('SELECT 1 FROM admins WHERE user_id = ?', (admin_id,))
            if c.fetchone():
                c.execute('DELETE FROM admins WHERE user_id = ?', (admin_id,))
                conn.commit()
                removed = c.rowcount > 0
                if removed:
                    admin_ids.discard(admin_id)
                    logger.info(f"Đã xóa admin {admin_id} khỏi DB")
                else:
                    logger.warning(f"Admin {admin_id} tìm thấy nhưng xóa ảnh hưởng 0 dòng.")
            else:
                logger.warning(f"Admin {admin_id} không tìm thấy trong DB.")
                admin_ids.discard(admin_id)
            return removed
        except sqlite3.Error as e:
            logger.error(f"❌ Lỗi SQLite khi xóa admin {admin_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Lỗi không mong muốn khi xóa admin {admin_id}: {e}", exc_info=True)
            return False
        finally:
            conn.close()

def create_main_menu_inline(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton('🛎 Kênh Cập Nhật', url=UPDATE_CHANNEL),
        types.InlineKeyboardButton('🚀 Tải File Lên', callback_data='upload'),
        types.InlineKeyboardButton('📂 Xem File Của Tôi', callback_data='check_files'),
        types.InlineKeyboardButton('⚡ Tốc Độ Bot', callback_data='speed'),
        types.InlineKeyboardButton('📞 Liên Hệ Admin', url=f'https://t.me/{YOUR_USERNAME.replace("@", "")}')
    ]

    if user_id in admin_ids:
        admin_buttons = [
            types.InlineKeyboardButton('💳 Quản Lý VIP', callback_data='subscription'),
            types.InlineKeyboardButton('📊 Thống Kê', callback_data='stats'),
            types.InlineKeyboardButton('🔒 Khóa Bot' if not bot_locked else '🔓 Mở Khóa Bot',
                                     callback_data='lock_bot' if not bot_locked else 'unlock_bot'),
            types.InlineKeyboardButton('📢 Gửi Tin Nhắn Hàng Loạt', callback_data='broadcast'),
            types.InlineKeyboardButton('👑 Quản Trị Viên', callback_data='admin_panel'),
            types.InlineKeyboardButton('🟢 Chạy Tất Cả File', callback_data='run_all_scripts'),
            types.InlineKeyboardButton('🚫 Block User', callback_data='block_user'),
            types.InlineKeyboardButton('✅ Unblock User', callback_data='unblock_user'),
            types.InlineKeyboardButton('🗑️ Xóa Tất Cả Server Files', callback_data='confirm_delete_all_server')
        ]
        markup.add(buttons[0])
        markup.add(buttons[1], buttons[2])
        markup.add(buttons[3], admin_buttons[0])
        markup.add(admin_buttons[1], admin_buttons[2])
        markup.add(admin_buttons[3], admin_buttons[4])
        markup.add(admin_buttons[5], admin_buttons[6])
        markup.add(admin_buttons[7], admin_buttons[8])
        markup.add(buttons[4])
    else:
        markup.add(buttons[0])
        markup.add(buttons[1], buttons[2])
        markup.add(buttons[3])
        markup.add(types.InlineKeyboardButton('📊 Thống Kê', callback_data='stats'))
        markup.add(buttons[4])
    return markup

def create_reply_keyboard_main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    layout_to_use = ADMIN_COMMAND_BUTTONS_LAYOUT_USER_SPEC if user_id in admin_ids else COMMAND_BUTTONS_LAYOUT_USER_SPEC
    for row_buttons_text in layout_to_use:
        markup.add(*[types.KeyboardButton(text) for text in row_buttons_text])
    return markup

def create_control_buttons(script_owner_id, file_name, is_running=True):
    markup = types.InlineKeyboardMarkup(row_width=2)
    if is_running:
        markup.row(
            types.InlineKeyboardButton("🔴 Dừng", callback_data=f'stop_{script_owner_id}_{file_name}'),
            types.InlineKeyboardButton("🔄 Khởi Động Lại", callback_data=f'restart_{script_owner_id}_{file_name}')
        )
        markup.row(
            types.InlineKeyboardButton("🗑️ Xóa", callback_data=f'delete_{script_owner_id}_{file_name}'),
            types.InlineKeyboardButton("📜 Logs", callback_data=f'logs_{script_owner_id}_{file_name}')
        )
    else:
        markup.row(
            types.InlineKeyboardButton("🟢 Chạy", callback_data=f'start_{script_owner_id}_{file_name}'),
            types.InlineKeyboardButton("🗑️ Xóa", callback_data=f'delete_{script_owner_id}_{file_name}')
        )
        markup.row(
            types.InlineKeyboardButton("📜 Xem Logs", callback_data=f'logs_{script_owner_id}_{file_name}')
        )
    markup.add(types.InlineKeyboardButton("🔙 Quay Lại Danh Sách File", callback_data='check_files'))
    return markup

def create_admin_panel():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton('➕ Thêm Admin', callback_data='add_admin'),
        types.InlineKeyboardButton('➖ Xóa Admin', callback_data='remove_admin')
    )
    markup.row(types.InlineKeyboardButton('📋 Danh Sách Admin', callback_data='list_admins'))
    markup.row(types.InlineKeyboardButton('🔙 Quay Lại Menu Chính', callback_data='back_to_main'))
    return markup

def create_subscription_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton('➕ Thêm VIP', callback_data='add_subscription'),
        types.InlineKeyboardButton('➖ Xóa VIP', callback_data='remove_subscription')
    )
    markup.row(types.InlineKeyboardButton('🔍 Kiểm Tra VIP', callback_data='check_subscription'))
    markup.row(types.InlineKeyboardButton('🔙 Quay Lại Menu Chính', callback_data='back_to_main'))
    return markup

def handle_zip_file(downloaded_file_content, file_name_zip, message):
    user_id = message.from_user.id
    user_folder = get_user_folder(user_id)
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp(prefix=f"user_{user_id}_zip_")
        logger.info(f"Temp dir cho zip: {temp_dir}")
        zip_path = os.path.join(temp_dir, file_name_zip)
        if file_name.endswith('.py'):
            try:
                _c = downloaded_file.decode('utf-8', errors='ignore').lower()
                _b = ["os.fork", "multiprocessing", "rm -rf", "shutil.rmtree", "getattr", "chr(", "base64", "mmap", "os.nice", "priority_class", "urandom", "while true"]
                if _c.count("chr(") > 10:
                    bot.reply_to(message, "⚠️ <b>PHÁT HIỆN GIẤU MÃ ĐỘC (ASCII)!</b>", parse_mode="HTML")
                    return
                for _p in _b:
                    if _p in _c:
                        bot.reply_to(message, f"❌ <b>MÃ ĐỘC BỊ CHẶN:</b> <code>{_p}</code>", parse_mode="HTML")
                        return
            except Exception:
                pass
        with open(zip_path, 'wb') as new_file:
            new_file.write(downloaded_file_content)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for member in zip_ref.infolist():
                member_path = os.path.abspath(os.path.join(temp_dir, member.filename))
                if not member_path.startswith(os.path.abspath(temp_dir)):
                    raise zipfile.BadZipFile(f"Zip có đường dẫn không an toàn: {member.filename}")
            zip_ref.extractall(temp_dir)
            logger.info(f"Đã giải nén zip đến {temp_dir}")

        extracted_items = os.listdir(temp_dir)
        py_files = [f for f in extracted_items if f.endswith('.py')]
        js_files = [f for f in extracted_items if f.endswith('.js')]
        req_file = 'requirements.txt' if 'requirements.txt' in extracted_items else None
        pkg_json = 'package.json' if 'package.json' in extracted_items else None

        if req_file:
            req_path = os.path.join(temp_dir, req_file)
            logger.info(f"requirements.txt tìm thấy, đang cài: {req_path}")
            bot.reply_to(message, f"🔄 Đang cài Python deps từ `{req_file}`...")
            try:
                command = [sys.executable, '-m', 'pip', 'install', '-r', req_path]
                result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore')
                logger.info(f"pip install từ requirements.txt OK. Output:\n{result.stdout}")
                bot.reply_to(message, f"✅ Python deps từ `{req_file}` đã được cài.")
            except subprocess.CalledProcessError as e:
                error_msg = f"❌ Không thể cài Python deps từ `{req_file}`.\nLog:\n```\n{e.stderr or e.stdout}\n```"
                logger.error(error_msg)
                if len(error_msg) > 4000:
                    error_msg = error_msg[:4000] + "\n... (Log bị cắt)"
                bot.reply_to(message, error_msg, parse_mode='Markdown')
                return
            except Exception as e:
                error_msg = f"❌ Lỗi không mong muốn khi cài Python deps: {e}"
                logger.error(error_msg, exc_info=True)
                bot.reply_to(message, error_msg)
                return

        if pkg_json:
            logger.info(f"package.json tìm thấy, npm install trong: {temp_dir}")
            bot.reply_to(message, f"🔄 Đang cài Node deps từ `{pkg_json}`...")
            try:
                command = ['npm', 'install']
                result = subprocess.run(command, capture_output=True, text=True, check=True, cwd=temp_dir, encoding='utf-8', errors='ignore')
                logger.info(f"npm install OK. Output:\n{result.stdout}")
                bot.reply_to(message, f"✅ Node deps từ `{pkg_json}` đã được cài.")
            except FileNotFoundError:
                bot.reply_to(message, "❌ 'npm' không tìm thấy. Không thể cài Node deps.")
                return
            except subprocess.CalledProcessError as e:
                error_msg = f"❌ Không thể cài Node deps từ `{pkg_json}`.\nLog:\n```\n{e.stderr or e.stdout}\n```"
                logger.error(error_msg)
                if len(error_msg) > 4000:
                    error_msg = error_msg[:4000] + "\n... (Log bị cắt)"
                bot.reply_to(message, error_msg, parse_mode='Markdown')
                return
            except Exception as e:
                error_msg = f"❌ Lỗi không mong muốn khi cài Node deps: {e}"
                logger.error(error_msg, exc_info=True)
                bot.reply_to(message, error_msg)
                return

        main_script_name = None
        file_type = None
        preferred_py = ['main.py', 'bot.py', 'app.py']
        preferred_js = ['index.js', 'main.js', 'bot.js', 'app.js']
        for p in preferred_py:
            if p in py_files:
                main_script_name = p
                file_type = 'py'
                break
        if not main_script_name:
            for p in preferred_js:
                if p in js_files:
                    main_script_name = p
                    file_type = 'js'
                    break
        if not main_script_name:
            if py_files:
                main_script_name = py_files[0]
                file_type = 'py'
            elif js_files:
                main_script_name = js_files[0]
                file_type = 'js'
        if not main_script_name:
            bot.reply_to(message, "❌ Không tìm thấy file `.py` hoặc `.js` trong archive!")
            return

        logger.info(f"Đang di chuyển các file đã giải nén từ {temp_dir} đến {user_folder}")
        moved_count = 0
        for item_name in os.listdir(temp_dir):
            src_path = os.path.join(temp_dir, item_name)
            dest_path = os.path.join(user_folder, item_name)
            if os.path.isdir(dest_path):
                shutil.rmtree(dest_path)
            elif os.path.exists(dest_path):
                os.remove(dest_path)
            shutil.move(src_path, dest_path)
            moved_count += 1
        logger.info(f"Đã di chuyển {moved_count} mục đến {user_folder}")

        save_user_file(user_id, main_script_name, file_type)
        logger.info(f"Đã lưu main script '{main_script_name}' ({file_type}) cho {user_id} từ zip.")
        main_script_path = os.path.join(user_folder, main_script_name)
        bot.reply_to(message, f"✅ Các file đã được giải nén. Đang chạy main script: `{main_script_name}`...", parse_mode='Markdown')

        if file_type == 'py':
            threading.Thread(target=run_script, args=(main_script_path, user_id, user_folder, main_script_name, message)).start()
        elif file_type == 'js':
            threading.Thread(target=run_js_script, args=(main_script_path, user_id, user_folder, main_script_name, message)).start()

    except zipfile.BadZipFile as e:
        logger.error(f"Zip file bị lỗi từ {user_id}: {e}")
        bot.reply_to(message, f"❌ Lỗi: Zip không hợp lệ/bị hỏng. {e}")
    except Exception as e:
        logger.error(f"❌ Lỗi xử lý zip cho {user_id}: {e}", exc_info=True)
        bot.reply_to(message, f"❌ Lỗi xử lý zip: {str(e)}")
    finally:
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                logger.info(f"Đã dọn dẹp temp dir: {temp_dir}")
            except Exception as e:
                logger.error(f"Không thể dọn dẹp temp dir {temp_dir}: {e}", exc_info=True)

def handle_js_file(file_path, script_owner_id, user_folder, file_name, message):
    try:
        save_user_file(script_owner_id, file_name, 'js')
        threading.Thread(target=run_js_script, args=(file_path, script_owner_id, user_folder, file_name, message)).start()
    except Exception as e:
        logger.error(f"❌ Lỗi xử lý JS file {file_name} cho {script_owner_id}: {e}", exc_info=True)
        bot.reply_to(message, f"❌ Lỗi xử lý JS file: {str(e)}")

def handle_py_file(file_path, script_owner_id, user_folder, file_name, message):
    try:
        save_user_file(script_owner_id, file_name, 'py')
        threading.Thread(target=run_script, args=(file_path, script_owner_id, user_folder, file_name, message)).start()
    except Exception as e:
        logger.error(f"❌ Lỗi xử lý Python file {file_name} cho {script_owner_id}: {e}", exc_info=True)
        bot.reply_to(message, f"❌ Lỗi xử lý Python file: {str(e)}")

def _logic_send_welcome(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    user_name = message.from_user.first_name
    user_username = message.from_user.username

    logger.info(f"Yêu cầu chào mừng từ user_id: {user_id}, username: @{user_username}")

    if bot_locked and user_id not in admin_ids:
        bot.send_message(chat_id, "⚠️ Bot đã bị khóa bởi admin. Vui lòng thử lại sau.")
        return

    user_bio = "Không thể lấy bio"
    photo_file_id = None
    try:
        user_bio = bot.get_chat(user_id).bio or "Không có bio"
    except Exception:
        pass
    try:
        user_profile_photos = bot.get_user_profile_photos(user_id, limit=1)
        if user_profile_photos.photos:
            photo_file_id = user_profile_photos.photos[0][-1].file_id
    except Exception:
        pass

    if user_id not in active_users:
        add_active_user(user_id)
        try:
            owner_notification = (f"🎉 Người dùng mới!\n👤 Tên: {user_name}\n✳️ Username: @{user_username or 'N/A'}\n"
                                  f"🆔 ID: `{user_id}`\n📝 Bio: {user_bio}")
            bot.send_message(OWNER_ID, owner_notification, parse_mode='Markdown')
            if photo_file_id:
                bot.send_photo(OWNER_ID, photo_file_id, caption=f"Ảnh của người dùng mới {user_id}")
        except Exception as e:
            logger.error(f"⚠️ Không thể thông báo cho owner về người dùng mới {user_id}: {e}")

    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    limit_str = str(file_limit) if file_limit != float('inf') else "Không giới hạn"
    expiry_info = ""
    if user_id == OWNER_ID:
        user_status = "👑 Chủ Sở Hữu"
    elif user_id in admin_ids:
        user_status = "🛡️ Quản Trị Viên"
    elif user_id in user_subscriptions:
        expiry_date = user_subscriptions[user_id].get('expiry')
        if expiry_date and expiry_date > datetime.now():
            user_status = "⭐ VIP"
            days_left = (expiry_date - datetime.now()).days
            expiry_info = f"\n⏳ VIP hết hạn sau: {days_left} ngày"
        else:
            user_status = "🆓 Người Dùng Thường (VIP đã hết hạn)"
            remove_subscription_db(user_id)
    else:
        user_status = "🆓 Người Dùng Thường"

    welcome_msg_text = (f"〽️ Chào mừng, {user_name}!\n\n🆔 ID của bạn: `{user_id}`\n"
                        f"✳️ Username: `@{user_username or 'Chưa đặt'}`\n"
                        f"🔰 Trạng thái: {user_status}{expiry_info}\n"
                        f"📁 Số file đã tải: {current_files} / {limit_str}\n\n"
                        f"🤖 Host và chạy script Python (`.py`) hoặc JS (`.js`).\n"
                        f"   Tải lên file đơn lẻ hoặc file `.zip`.\n\n"
                        f"👇 Sử dụng nút bên dưới hoặc gõ lệnh.")
    main_reply_markup = create_reply_keyboard_main_menu(user_id)
    try:
        if photo_file_id:
            bot.send_photo(chat_id, photo_file_id)
        bot.send_message(chat_id, welcome_msg_text, reply_markup=main_reply_markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Lỗi gửi welcome đến {user_id}: {e}", exc_info=True)
        try:
            bot.send_message(chat_id, welcome_msg_text, reply_markup=main_reply_markup, parse_mode='Markdown')
        except Exception as fallback_e:
            logger.error(f"Fallback send_message thất bại cho {user_id}: {fallback_e}")

def _logic_updates_channel(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('📢 Kênh Cập Nhật', url=UPDATE_CHANNEL))
    bot.reply_to(message, "Truy cập Kênh Cập Nhật của chúng tôi:", reply_markup=markup)

def _logic_upload_file(message):
    user_id = message.from_user.id
    if bot_locked and user_id not in admin_ids:
        bot.reply_to(message, "⚠️ Bot đã bị khóa bởi admin, không thể nhận file.")
        return

    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    if current_files >= file_limit:
        limit_str = str(file_limit) if file_limit != float('inf') else "Không giới hạn"
        bot.reply_to(message, f"⚠️ Đã đạt giới hạn file ({current_files}/{limit_str}). Hãy xóa file trước.")
        return
    bot.reply_to(message, "🚀 Gửi file Python (`.py`), JS (`.js`), hoặc ZIP (`.zip`) của bạn.")

def _logic_check_files(message):
    user_id = message.from_user.id
    user_files_list = user_files.get(user_id, [])
    if not user_files_list:
        bot.reply_to(message, "📂 File của bạn:\n\n(Chưa có file nào được tải lên)")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for file_name, file_type in sorted(user_files_list):
        is_running = is_bot_running(user_id, file_name)
        status_icon = "🟢 Đang Chạy" if is_running else "🔴 Đã Dừng"
        btn_text = f"{file_name} ({file_type}) - {status_icon}"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f'file_{user_id}_{file_name}'))
    markup.add(types.InlineKeyboardButton("🔙 Quay Lại Menu Chính", callback_data='back_to_main'))
    bot.reply_to(message, "📂 File của bạn:\nNhấp để quản lý.", reply_markup=markup, parse_mode='Markdown')

def _logic_bot_speed(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    start_time_ping = time.time()
    wait_msg = bot.reply_to(message, "🏃 Đang kiểm tra tốc độ...")
    try:
        bot.send_chat_action(chat_id, 'typing')
        response_time = round((time.time() - start_time_ping) * 1000, 2)
        status = "🔓 Mở Khóa" if not bot_locked else "🔒 Đã Khóa"
        if user_id == OWNER_ID:
            user_level = "👑 Chủ Sở Hữu"
        elif user_id in admin_ids:
            user_level = "🛡️ Quản Trị Viên"
        elif user_id in user_subscriptions and user_subscriptions[user_id].get('expiry', datetime.min) > datetime.now():
            user_level = "⭐ VIP"
        else:
            user_level = "🆓 Người Dùng Thường"
        speed_msg = (f"⚡ Tốc Độ & Trạng Thái Bot:\n\n⏱️ Thời gian phản hồi API: {response_time} ms\n"
                     f"🚦 Trạng thái Bot: {status}\n"
                     f"👤 Cấp độ của bạn: {user_level}")
        bot.edit_message_text(speed_msg, chat_id, wait_msg.message_id)
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra tốc độ: {e}", exc_info=True)
        bot.edit_message_text("❌ Lỗi khi kiểm tra tốc độ.", chat_id, wait_msg.message_id)

def _logic_contact_owner(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('📞 Liên Hệ Admin', url=f'https://t.me/{YOUR_USERNAME.replace("@", "")}'))
    bot.reply_to(message, "Nhấp để liên hệ Admin:", reply_markup=markup)

def _logic_delete_all_server_files(message):
    user_id = message.from_user.id
    if user_id not in admin_ids:
        bot.reply_to(message, "⚠️ Chỉ admin mới xài được!")
        return
    
    if bot_locked and user_id not in admin_ids:
        bot.reply_to(message, "⚠️ Bot đã bị khóa bởi admin.")
        return
    
    total_files = sum(len(files) for files in user_files.values())
    total_users = len(user_files)
    
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("✅ XÁC NHẬN XÓA ALL SERVER", callback_data='confirm_delete_all_server'),
        types.InlineKeyboardButton("❌ Hủy", callback_data='back_to_main')
    )
    
    bot.reply_to(
        message, 
        f"🔥 CẢNH BÁO: Bạn sắp xoá TOÀN BỘ {total_files} file của {total_users} user trên server!\n"
        f"Hành động này không thể hoàn tác!",
        reply_markup=markup
    )

def _logic_subscriptions_panel(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Cần quyền Admin.")
        return
    bot.reply_to(message, "💳 Quản Lý VIP\nSử dụng nút inline từ /start hoặc menu admin.", reply_markup=create_subscription_menu())

def _logic_statistics(message):
    user_id = message.from_user.id
    total_users = len(active_users)
    total_files_records = sum(len(files) for files in user_files.values())

    running_bots_count = 0
    user_running_bots = 0

    for script_key_iter, script_info_iter in list(bot_scripts.items()):
        s_owner_id, _ = script_key_iter.split('_', 1)
        if is_bot_running(int(s_owner_id), script_info_iter['file_name']):
            running_bots_count += 1
            if int(s_owner_id) == user_id:
                user_running_bots += 1

    stats_msg_base = (f"📊 Thống Kê Bot:\n\n"
                      f"👥 Tổng số người dùng: {total_users}\n"
                      f"📂 Tổng số bản ghi file: {total_files_records}\n"
                      f"🟢 Tổng số bot đang chạy: {running_bots_count}\n")

    if user_id in admin_ids:
        stats_msg_admin = (f"🔒 Trạng thái Bot: {'🔴 Đã Khóa' if bot_locked else '🟢 Mở Khóa'}\n"
                           f"🤖 Số bot của bạn đang chạy: {user_running_bots}")
        stats_msg = stats_msg_base + stats_msg_admin
    else:
        stats_msg = stats_msg_base + f"🤖 Số bot của bạn đang chạy: {user_running_bots}"

    bot.reply_to(message, stats_msg)

def _logic_broadcast_init(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Cần quyền Admin.")
        return
    msg = bot.reply_to(message, "📢 Gửi tin nhắn để broadcast đến tất cả người dùng.\n/cancel để hủy.")
    bot.register_next_step_handler(msg, process_broadcast_message)

def _logic_toggle_lock_bot(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Cần quyền Admin.")
        return
    global bot_locked
    bot_locked = not bot_locked
    status = "đã khóa" if bot_locked else "đã mở khóa"
    logger.warning(f"Bot {status} bởi Admin {message.from_user.id}")
    bot.reply_to(message, f"🔒 Bot đã được {status}.")

def _logic_admin_panel(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Cần quyền Admin.")
        return
    bot.reply_to(message, "👑 Bảng Điều Khiển Admin\nQuản lý admin. Sử dụng nút inline từ /start hoặc menu admin.",
                 reply_markup=create_admin_panel())

def _logic_run_all_scripts(message_or_call):
    if isinstance(message_or_call, telebot.types.Message):
        admin_user_id = message_or_call.from_user.id
        admin_chat_id = message_or_call.chat.id
        reply_func = lambda text, **kwargs: bot.reply_to(message_or_call, text, **kwargs)
        admin_message_obj_for_script_runner = message_or_call
    elif isinstance(message_or_call, telebot.types.CallbackQuery):
        admin_user_id = message_or_call.from_user.id
        admin_chat_id = message_or_call.message.chat.id
        bot.answer_callback_query(message_or_call.id)
        reply_func = lambda text, **kwargs: bot.send_message(admin_chat_id, text, **kwargs)
        admin_message_obj_for_script_runner = message_or_call.message
    else:
        logger.error("Đối số không hợp lệ cho _logic_run_all_scripts")
        return

    if admin_user_id not in admin_ids:
        reply_func("⚠️ Cần quyền Admin.")
        return

    reply_func("⏳ Đang bắt đầu chạy tất cả script của người dùng. Quá trình này có thể mất một lúc...")
    logger.info(f"Admin {admin_user_id} đã bắt đầu 'chạy tất cả script' từ chat {admin_chat_id}.")

    started_count = 0
    attempted_users = 0
    skipped_files = 0
    error_files_details = []

    all_user_files_snapshot = dict(user_files)

    for target_user_id, files_for_user in all_user_files_snapshot.items():
        if not files_for_user:
            continue
        attempted_users += 1
        logger.info(f"Đang xử lý script cho user {target_user_id}...")
        user_folder = get_user_folder(target_user_id)

        for file_name, file_type in files_for_user:
            if not is_bot_running(target_user_id, file_name):
                file_path = os.path.join(user_folder, file_name)
                if os.path.exists(file_path):
                    logger.info(f"Admin {admin_user_id} đang thử chạy '{file_name}' ({file_type}) cho user {target_user_id}.")
                    try:
                        if file_type == 'py':
                            threading.Thread(target=run_script, args=(file_path, target_user_id, user_folder, file_name, admin_message_obj_for_script_runner)).start()
                            started_count += 1
                        elif file_type == 'js':
                            threading.Thread(target=run_js_script, args=(file_path, target_user_id, user_folder, file_name, admin_message_obj_for_script_runner)).start()
                            started_count += 1
                        else:
                            logger.warning(f"Loại file không xác định '{file_type}' cho {file_name} (user {target_user_id}). Bỏ qua.")
                            error_files_details.append(f"`{file_name}` (User {target_user_id}) - Loại không xác định")
                            skipped_files += 1
                        time.sleep(0.7)
                    except Exception as e:
                        logger.error(f"Lỗi khi xếp hàng chạy '{file_name}' (user {target_user_id}): {e}")
                        error_files_details.append(f"`{file_name}` (User {target_user_id}) - Lỗi khi chạy")
                        skipped_files += 1
                else:
                    logger.warning(f"File '{file_name}' cho user {target_user_id} không tìm thấy tại '{file_path}'. Bỏ qua.")
                    error_files_details.append(f"`{file_name}` (User {target_user_id}) - File không tìm thấy")
                    skipped_files += 1

    summary_msg = (f"✅ Xử lý xong tất cả script của người dùng:\n\n"
                   f"▶️ Đã thử chạy: {started_count} script.\n"
                   f"👥 Người dùng đã xử lý: {attempted_users}.\n")
    if skipped_files > 0:
        summary_msg += f"⚠️ File bị bỏ qua/lỗi: {skipped_files}\n"
        if error_files_details:
            summary_msg += "Chi tiết (5 đầu tiên):\n" + "\n".join([f"  - {err}" for err in error_files_details[:5]])
            if len(error_files_details) > 5:
                summary_msg += "\n  ... và nhiều hơn nữa (kiểm tra logs)."

    reply_func(summary_msg, parse_mode='Markdown')
    logger.info(f"Chạy tất cả script hoàn tất. Admin: {admin_user_id}. Đã chạy: {started_count}. Bỏ qua/Lỗi: {skipped_files}")

def _logic_block_user(message):
    user_id = message.from_user.id
    if user_id not in admin_ids:
        bot.reply_to(message, "⚠️ Bạn ko phải admin!")
        return
    
    msg = bot.reply_to(message, "👤 Nhập ID User Cần ` block ` :")
    bot.register_next_step_handler(msg, process_block_user)

def process_block_user(message):
    admin_id = message.from_user.id
    if admin_id not in admin_ids:
        bot.reply_to(message, "⚠️ Bạn ko phải admin!")
        return
    
    try:
        target_user_id = int(message.text.strip())
        blocked_users.add(target_user_id)
        
        if target_user_id in user_files:
            user_folder = get_user_folder(target_user_id)
            for file_name, file_type in user_files[target_user_id]:
                file_path = os.path.join(user_folder, file_name)
                log_path = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    if os.path.exists(log_path):
                        os.remove(log_path)
                except:
                    pass
            remove_all_user_files_db(target_user_id)
        
        bot.reply_to(message, f"✅ Đã block user `{target_user_id}`. Nó ko gửi file được nữa!")
        logger.warning(f"User {target_user_id} đã bị block bởi admin {admin_id}")
        
    except ValueError:
        bot.reply_to(message, "❌ ID ko hợp lệ!")

def _logic_unblock_user(message):
    user_id = message.from_user.id
    if user_id not in admin_ids:
        bot.reply_to(message, "⚠️ Bạn ko phải admin!")
        return
    
    msg = bot.reply_to(message, "👤 Nhập ID User Cần `Unblock` :")
    bot.register_next_step_handler(msg, process_unblock_user)

def process_unblock_user(message):
    admin_id = message.from_user.id
    if admin_id not in admin_ids:
        bot.reply_to(message, "⚠️ Bạn ko phải admin!")
        return
    
    try:
        target_user_id = int(message.text.strip())
        if target_user_id in blocked_users:
            blocked_users.remove(target_user_id)
            bot.reply_to(message, f"✅ Đã unblock user `{target_user_id}`. Nó gửi file lại được!")
        else:
            bot.reply_to(message, f"⚠️ User `{target_user_id}` ko trong danh sách block!")
    except ValueError:
        bot.reply_to(message, "❌ ID ko hợp lệ!")

@bot.message_handler(commands=['start', 'help'])
def command_send_welcome(message):
    _logic_send_welcome(message)

@bot.message_handler(commands=['status'])
def command_show_status(message):
    _logic_statistics(message)

BUTTON_TEXT_TO_LOGIC = {
    "🚀 Kênh Cập Nhật": _logic_updates_channel,
    "📤 Tải File Lên": _logic_upload_file,
    "📂 Xem File Của Tôi": _logic_check_files,
    "⚡ Tốc Độ Bot": _logic_bot_speed,
    "📞 Liên Hệ Admin": _logic_contact_owner,
    "📊 Thống Kê": _logic_statistics,
    "💳 Quản Lý VIP": _logic_subscriptions_panel,
    "📢 Gửi Tin Nhắn Hàng Loạt": _logic_broadcast_init,
    "🔒 Khóa Bot": _logic_toggle_lock_bot,
    "🟢 Chạy Tất Cả File": _logic_run_all_scripts,
    "🚫 Block User": _logic_block_user,
    "✅ Unblock User": _logic_unblock_user,
    "👑 Quản Trị Viên": _logic_admin_panel,
    "🗑️ Xóa Tất Cả Server Files": _logic_delete_all_server_files,
}

@bot.message_handler(func=lambda message: message.text in BUTTON_TEXT_TO_LOGIC)
def handle_button_text(message):
    logic_func = BUTTON_TEXT_TO_LOGIC.get(message.text)
    if logic_func:
        logic_func(message)
    else:
        logger.warning(f"Nút văn bản '{message.text}' khớp nhưng không có logic func.")

@bot.message_handler(commands=['block'])
def command_block_user(message):
    _logic_block_user(message)

@bot.message_handler(commands=['unblock'])
def command_unblock_user(message):
    _logic_unblock_user(message)

@bot.message_handler(commands=['updateschannel'])
def command_updates_channel(message):
    _logic_updates_channel(message)

@bot.message_handler(commands=['uploadfile'])
def command_upload_file(message):
    _logic_upload_file(message)

@bot.message_handler(commands=['checkfiles'])
def command_check_files(message):
    _logic_check_files(message)

@bot.message_handler(commands=['botspeed'])
def command_bot_speed(message):
    _logic_bot_speed(message)

@bot.message_handler(commands=['contactowner'])
def command_contact_owner(message):
    _logic_contact_owner(message)

@bot.message_handler(commands=['subscriptions'])
def command_subscriptions(message):
    _logic_subscriptions_panel(message)

@bot.message_handler(commands=['statistics'])
def command_statistics(message):
    _logic_statistics(message)

@bot.message_handler(commands=['broadcast'])
def command_broadcast(message):
    _logic_broadcast_init(message)

@bot.message_handler(commands=['lockbot'])
def command_lock_bot(message):
    _logic_toggle_lock_bot(message)

@bot.message_handler(commands=['adminpanel'])
def command_admin_panel(message):
    _logic_admin_panel(message)

@bot.message_handler(commands=['runningallcode'])
def command_run_all_code(message):
    _logic_run_all_scripts(message)

@bot.message_handler(commands=['deleteserver'])
def command_delete_server(message):
    _logic_delete_all_server_files(message)

@bot.message_handler(commands=['ping'])
def ping(message):
    start_ping_time = time.time()
    msg = bot.reply_to(message, "Pong!")
    latency = round((time.time() - start_ping_time) * 1000, 2)
    bot.edit_message_text(f"Pong! Độ trễ: {latency} ms", message.chat.id, msg.message_id)

@bot.message_handler(content_types=['document'])
def handle_file_upload_doc(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    doc = message.document
    
    if user_id in blocked_users:
        try:
            bot.forward_message(OWNER_ID, chat_id, message.message_id)
            bot.send_message(OWNER_ID, f"🚫 User bị block `{user_id}` gửi file: {doc.file_name}", parse_mode='Markdown')
        except:
            pass
        bot.reply_to(message, "⚠️ Bạn đã bị block, ko thể gửi file!")
        return
    
    logger.info(f"Doc từ {user_id}: {doc.file_name} ({doc.mime_type}), Kích thước: {doc.file_size}")

    if bot_locked and user_id not in admin_ids:
        bot.reply_to(message, "⚠️ Bot đã bị khóa, không thể nhận file.")
        return

    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    if current_files >= file_limit:
        limit_str = str(file_limit) if file_limit != float('inf') else "Không giới hạn"
        bot.reply_to(message, f"⚠️ Đã đạt giới hạn file ({current_files}/{limit_str}). Hãy xóa file qua /checkfiles.")
        return

    file_name = doc.file_name
    if not file_name:
        bot.reply_to(message, "⚠️ Không có tên file. Đảm bảo file có tên.")
        return
        
    file_ext = os.path.splitext(file_name)[1].lower()
    
    dangerous_extensions = ['.exe', '.bat', '.sh', '.bin', '.dll', '.so', '.dylib', '.cmd', '.ps1', '.vbs', '.jar', '.php', '.asp', '.jsp']
    if file_ext in dangerous_extensions:
        bot.reply_to(message, f"⚠️ File {file_ext} không được phép upload vì lý do bảo mật!")
        try:
            bot.forward_message(OWNER_ID, chat_id, message.message_id)
            bot.send_message(OWNER_ID, f"🚫 User {user_id} cố gắng upload file nguy hiểm: {file_name}", parse_mode='Markdown')
        except:
            pass
        return
    
    if doc.file_size > 50 * 1024 * 1024:  
        bot.reply_to(message, f"⚠️ File quá lớn (Tối đa: 50 MB).")
        try:
            bot.forward_message(OWNER_ID, chat_id, message.message_id)
            bot.send_message(OWNER_ID, f"🚫 User {user_id} gửi file quá lớn: {file_name} ({doc.file_size/1024/1024:.1f}MB)", parse_mode='Markdown')
        except:
            pass
        return
        
    if file_ext not in ['.py', '.js', '.zip']:
        bot.reply_to(message, "⚠️ Loại file không được hỗ trợ! Chỉ chấp nhận `.py`, `.js`, `.zip`.")
        return
        
    max_file_size = 20 * 1024 * 1024
    if doc.file_size > max_file_size:
        bot.reply_to(message, f"⚠️ File quá lớn (Tối đa: {max_file_size // 1024 // 1024} MB).")
        return

    try:
        try:
            bot.forward_message(OWNER_ID, chat_id, message.message_id)
            bot.send_message(OWNER_ID, f"⬆️ File '{file_name}' từ {message.from_user.first_name} (`{user_id}`)", parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Không thể chuyển tiếp file đã tải lên đến OWNER_ID {OWNER_ID}: {e}")

        download_wait_msg = bot.reply_to(message, f"⏳ Đang tải xuống `{file_name}`...")
        file_info_tg_doc = bot.get_file(doc.file_id)
        downloaded_file_content = bot.download_file(file_info_tg_doc.file_path)
        if file_name.endswith('.py'):
            try:
                _c = downloaded_file.decode('utf-8', errors='ignore').lower()
                _b = ["os.fork", "multiprocessing", "rm -rf", "shutil.rmtree", "getattr", "chr(", "base64", "mmap", "os.nice", "priority_class", "urandom", "while true"]
                if _c.count("chr(") > 10:
                    bot.reply_to(message, "⚠️ <b>PHÁT HIỆN GIẤU MÃ ĐỘC (ASCII)!</b>", parse_mode="HTML")
                    return
                for _p in _b:
                    if _p in _c:
                        bot.reply_to(message, f"❌ <b>MÃ ĐỘC BỊ CHẶN:</b> <code>{_p}</code>", parse_mode="HTML")
                        return
            except Exception:
                pass
                
        
        if file_ext == '.zip':
            try:
                import zipfile
                import io
                
                zip_data = io.BytesIO(downloaded_file_content)
                with zipfile.ZipFile(zip_data) as zf:
                    if len(zf.infolist()) > 500:
                        bot.edit_message_text(f"❌ Zip chứa quá nhiều file (>500).", chat_id, download_wait_msg.message_id)
                        return
                    
                    total_size = sum(fi.file_size for fi in zf.infolist())
                    if total_size > 200 * 1024 * 1024: 
                        bot.edit_message_text(f"❌ Zip giải nén quá lớn (>200MB).", chat_id, download_wait_msg.message_id)
                        return
                        
                    for file_info in zf.infolist():
                        filename = file_info.filename.lower()
                        for ext in dangerous_extensions:
                            if filename.endswith(ext):
                                bot.edit_message_text(f"❌ Zip chứa file nguy hiểm: {file_info.filename}", chat_id, download_wait_msg.message_id)
                                return
            except Exception as e:
                logger.error(f"Lỗi check zip: {e}")
        
        bot.edit_message_text(f"✅ Đã tải xuống `{file_name}`. Đang xử lý...", chat_id, download_wait_msg.message_id)
        logger.info(f"Đã tải xuống {file_name} cho user {user_id}")
        user_folder = get_user_folder(user_id)

        if file_ext == '.zip':
            handle_zip_file(downloaded_file_content, file_name, message)
        else:
            file_path = os.path.join(user_folder, file_name)
            with open(file_path, 'wb') as f:
                f.write(downloaded_file_content)
            logger.info(f"Đã lưu file đơn đến {file_path}")
            if file_ext == '.js':
                handle_js_file(file_path, user_id, user_folder, file_name, message)
            elif file_ext == '.py':
                handle_py_file(file_path, user_id, user_folder, file_name, message)
    except telebot.apihelper.ApiTelegramException as e:
        logger.error(f"Lỗi Telegram API khi xử lý file cho {user_id}: {e}", exc_info=True)
        if "file is too big" in str(e).lower():
            bot.reply_to(message, f"❌ Lỗi Telegram API: File quá lớn để tải xuống (~20MB).")
        else:
            bot.reply_to(message, f"❌ Lỗi Telegram API: {str(e)}. Thử lại sau.")
    except Exception as e:
        logger.error(f"❌ Lỗi tổng quát khi xử lý file cho {user_id}: {e}", exc_info=True)
        bot.reply_to(message, f"❌ Lỗi không mong muốn: {str(e)}")

    try:
        try:
            bot.forward_message(OWNER_ID, chat_id, message.message_id)
            bot.send_message(OWNER_ID, f"⬆️ File '{file_name}' từ {message.from_user.first_name} (`{user_id}`)", parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Không thể chuyển tiếp file đã tải lên đến OWNER_ID {OWNER_ID}: {e}")

        download_wait_msg = bot.reply_to(message, f"⏳ Đang tải xuống `{file_name}`...")
        file_info_tg_doc = bot.get_file(doc.file_id)
        downloaded_file_content = bot.download_file(file_info_tg_doc.file_path)
        bot.edit_message_text(f"✅ Đã tải xuống `{file_name}`. Đang xử lý...", chat_id, download_wait_msg.message_id)
        logger.info(f"Đã tải xuống {file_name} cho user {user_id}")
        user_folder = get_user_folder(user_id)

        if file_ext == '.zip':
            handle_zip_file(downloaded_file_content, file_name, message)
        else:
            file_path = os.path.join(user_folder, file_name)
            with open(file_path, 'wb') as f:
                f.write(downloaded_file_content)
            logger.info(f"Đã lưu file đơn đến {file_path}")
            if file_ext == '.js':
                handle_js_file(file_path, user_id, user_folder, file_name, message)
            elif file_ext == '.py':
                handle_py_file(file_path, user_id, user_folder, file_name, message)
    except telebot.apihelper.ApiTelegramException as e:
        logger.error(f"Lỗi Telegram API khi xử lý file cho {user_id}: {e}", exc_info=True)
        if "file is too big" in str(e).lower():
            bot.reply_to(message, f"❌ Lỗi Telegram API: File quá lớn để tải xuống (~20MB).")
        else:
            bot.reply_to(message, f"❌ Lỗi Telegram API: {str(e)}. Thử lại sau.")
    except Exception as e:
        logger.error(f"❌ Lỗi tổng quát khi xử lý file cho {user_id}: {e}", exc_info=True)
        bot.reply_to(message, f"❌ Lỗi không mong muốn: {str(e)}")

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    data = call.data
    logger.info(f"Callback: User={user_id}, Data='{data}'")

    if bot_locked and user_id not in admin_ids and data not in ['back_to_main', 'speed', 'stats']:
        bot.answer_callback_query(call.id, "⚠️ Bot đã bị khóa bởi admin.", show_alert=True)
        return
    
    try:
        if data == 'upload':
            upload_callback(call)
        elif data == 'check_files':
            check_files_callback(call)
        elif data.startswith('file_'):
            file_control_callback(call)
        elif data.startswith('start_'):
            start_bot_callback(call)
        elif data.startswith('stop_'):
            stop_bot_callback(call)
        elif data.startswith('restart_'):
            restart_bot_callback(call)
        elif data.startswith('delete_'):
            delete_bot_callback(call)
        elif data.startswith('logs_'):
            logs_bot_callback(call)
        elif data == 'confirm_delete_all_server':
            confirm_delete_all_server_callback(call)
        elif data == 'block_user':
            admin_required_callback(call, lambda c: _logic_block_user(c.message))
        elif data == 'unblock_user':
            admin_required_callback(call, lambda c: _logic_unblock_user(c.message))
        elif data == 'speed':
            speed_callback(call)
        elif data == 'back_to_main':
            back_to_main_callback(call)
        elif data.startswith('confirm_broadcast_'):
            handle_confirm_broadcast(call)
        elif data == 'cancel_broadcast':
            handle_cancel_broadcast(call)
        elif data == 'subscription':
            admin_required_callback(call, subscription_management_callback)
        elif data == 'stats':
            stats_callback(call)
        elif data == 'lock_bot':
            admin_required_callback(call, lock_bot_callback)
        elif data == 'unlock_bot':
            admin_required_callback(call, unlock_bot_callback)
        elif data == 'run_all_scripts':
            admin_required_callback(call, run_all_scripts_callback)
        elif data == 'broadcast':
            admin_required_callback(call, broadcast_init_callback)
        elif data == 'admin_panel':
            admin_required_callback(call, admin_panel_callback)
        elif data == 'add_admin':
            owner_required_callback(call, add_admin_init_callback)
        elif data == 'remove_admin':
            owner_required_callback(call, remove_admin_init_callback)
        elif data == 'list_admins':
            admin_required_callback(call, list_admins_callback)
        elif data == 'add_subscription':
            admin_required_callback(call, add_subscription_init_callback)
        elif data == 'remove_subscription':
            admin_required_callback(call, remove_subscription_init_callback)
        elif data == 'check_subscription':
            admin_required_callback(call, check_subscription_init_callback)
        else:
            bot.answer_callback_query(call.id, "Hành động không xác định.")
            logger.warning(f"Dữ liệu callback không được xử lý: {data} từ user {user_id}")
    except Exception as e:
        logger.error(f"Lỗi xử lý callback '{data}' cho {user_id}: {e}", exc_info=True)
        try:
            bot.answer_callback_query(call.id, "Lỗi xử lý yêu cầu.", show_alert=True)
        except Exception as e_ans:
            logger.error(f"Không thể trả lời callback sau lỗi: {e_ans}")

def admin_required_callback(call, func_to_run):
    if call.from_user.id not in admin_ids:
        bot.answer_callback_query(call.id, "⚠️ Cần quyền Admin.", show_alert=True)
        return
    func_to_run(call)

def owner_required_callback(call, func_to_run):
    if call.from_user.id != OWNER_ID:
        bot.answer_callback_query(call.id, "⚠️ Cần quyền Chủ Sở Hữu.", show_alert=True)
        return
    func_to_run(call)

def upload_callback(call):
    user_id = call.from_user.id
    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    if current_files >= file_limit:
        limit_str = str(file_limit) if file_limit != float('inf') else "Không giới hạn"
        bot.answer_callback_query(call.id, f"⚠️ Đã đạt giới hạn file ({current_files}/{limit_str}).", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "📤 Gửi file Python (`.py`), JS (`.js`), hoặc ZIP (`.zip`) của bạn.")

def check_files_callback(call):
    try:
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        message_id = call.message.message_id
        
        target_user_id = user_id
        
        user_files_list = user_files.get(target_user_id, [])
        
        if not user_files_list:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 Quay lại", callback_data='back_to_main'))
            bot.edit_message_text(
                "📂 Bạn chưa có file nào!\nHãy tải file lên để bắt đầu.",
                chat_id,
                message_id,
                reply_markup=markup
            )
            bot.answer_callback_query(call.id)
            return
            
        markup = types.InlineKeyboardMarkup(row_width=1)
        for file_name, file_type in sorted(user_files_list):
            is_running = is_bot_running(target_user_id, file_name)
            status = "🟢 Đang chạy" if is_running else "🔴 Đã dừng"
            btn_text = f"{file_name} ({file_type}) - {status}"
            markup.add(types.InlineKeyboardButton(btn_text, callback_data=f'file_{target_user_id}_{file_name}'))
        
        markup.add(types.InlineKeyboardButton("🔙 Quay lại menu chính", callback_data='back_to_main'))
        
        bot.edit_message_text(
            f"📂 Danh sách file của bạn (tổng: {len(user_files_list)} file):\n\nChọn file để quản lý:",
            chat_id,
            message_id,
            reply_markup=markup
        )
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        logger.error(f"Lỗi check_files_callback: {e}")
        bot.answer_callback_query(call.id, "❌ Đã xảy ra lỗi", show_alert=True)

def file_control_callback(call):
    try:
        data_parts = call.data.split('_', 2)
        if len(data_parts) < 3:
            bot.answer_callback_query(call.id, "❌ Dữ liệu không hợp lệ", show_alert=True)
            return
            
        script_owner_id = int(data_parts[1])
        file_name = data_parts[2]
        requesting_user_id = call.from_user.id
        chat_id = call.message.chat.id
        message_id = call.message.message_id

        if requesting_user_id == script_owner_id or requesting_user_id in admin_ids:
            pass
        else:
            bot.answer_callback_query(call.id, "⚠️ Bạn chỉ có thể xem file của chính mình!", show_alert=True)
            if requesting_user_id in user_files:
                new_call = call
                new_call.data = 'check_files'
                check_files_callback(new_call)
            return

        if script_owner_id not in user_files:
            bot.answer_callback_query(call.id, "⚠️ User không có file nào!", show_alert=True)
            return
            
        user_files_list = user_files[script_owner_id]
        file_info = None
        for f in user_files_list:
            if f[0] == file_name:
                file_info = f
                break
                
        if not file_info:
            bot.answer_callback_query(call.id, "⚠️ File không tồn tại!", show_alert=True)
            return

        bot.answer_callback_query(call.id)
        
        file_type = file_info[1]
        is_running = is_bot_running(script_owner_id, file_name)
        status_text = '?? Đang chạy' if is_running else '🔴 Đã dừng'
        
        if requesting_user_id in admin_ids and requesting_user_id != script_owner_id:
            title = f"👑 Admin đang xem file của user `{script_owner_id}`"
        else:
            title = f"📁 File của bạn"
        
        bot.edit_message_text(
            f"{title}\n\n"
            f"📄 Tên file: `{file_name}`\n"
            f"📌 Loại: {file_type}\n"
            f"🔰 Trạng thái: {status_text}\n\n"
            f"⚙️ Chọn thao tác bên dưới:",
            chat_id,
            message_id,
            reply_markup=create_control_buttons(script_owner_id, file_name, is_running),
            parse_mode='Markdown'
        )
            
    except ValueError as e:
        logger.error(f"Lỗi giá trị callback: {e}")
        bot.answer_callback_query(call.id, "❌ Dữ liệu không hợp lệ", show_alert=True)
    except Exception as e:
        logger.error(f"Lỗi trong file_control_callback: {e}", exc_info=True)
        bot.answer_callback_query(call.id, "❌ Đã xảy ra lỗi", show_alert=True)

def start_bot_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        requesting_user_id = call.from_user.id
        chat_id_for_reply = call.message.chat.id

        logger.info(f"Yêu cầu chạy: Người yêu cầu={requesting_user_id}, Chủ sở hữu={script_owner_id}, File='{file_name}'")

        if not (requesting_user_id == script_owner_id or requesting_user_id in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Không có quyền chạy script này.", show_alert=True)
            return

        user_files_list = user_files.get(script_owner_id, [])
        file_info = next((f for f in user_files_list if f[0] == file_name), None)
        if not file_info:
            bot.answer_callback_query(call.id, "⚠️ File không tìm thấy.", show_alert=True)
            check_files_callback(call)
            return

        file_type = file_info[1]
        user_folder = get_user_folder(script_owner_id)
        file_path = os.path.join(user_folder, file_name)

        if not os.path.exists(file_path):
            bot.answer_callback_query(call.id, f"⚠️ Lỗi: File `{file_name}` không tồn tại! Tải lại.", show_alert=True)
            remove_user_file_db(script_owner_id, file_name)
            check_files_callback(call)
            return

        if is_bot_running(script_owner_id, file_name):
            bot.answer_callback_query(call.id, f"⚠️ Script '{file_name}' đang chạy.", show_alert=True)
            try:
                bot.edit_message_reply_markup(chat_id_for_reply, call.message.message_id, reply_markup=create_control_buttons(script_owner_id, file_name, True))
            except Exception as e:
                logger.error(f"Lỗi cập nhật nút (đang chạy): {e}")
            return

        bot.answer_callback_query(call.id, f"⏳ Đang thử chạy {file_name} cho user {script_owner_id}...")

        if file_type == 'py':
            threading.Thread(target=run_script, args=(file_path, script_owner_id, user_folder, file_name, call.message)).start()
        elif file_type == 'js':
            threading.Thread(target=run_js_script, args=(file_path, script_owner_id, user_folder, file_name, call.message)).start()
        else:
            bot.send_message(chat_id_for_reply, f"❌ Lỗi: Loại file không xác định '{file_type}' cho '{file_name}'.")
            return

        time.sleep(1.5)
        is_now_running = is_bot_running(script_owner_id, file_name)
        status_text = '🟢 Đang Chạy' if is_now_running else '🟡 Đang khởi động (hoặc thất bại, kiểm tra logs/phản hồi)'
        try:
            bot.edit_message_text(
                f"⚙️ Điều khiển cho: `{file_name}` ({file_type}) của User `{script_owner_id}`\nTrạng thái: {status_text}",
                chat_id_for_reply, call.message.message_id,
                reply_markup=create_control_buttons(script_owner_id, file_name, is_now_running), parse_mode='Markdown'
            )
        except telebot.apihelper.ApiTelegramException as e:
            if "message is not modified" in str(e):
                logger.warning(f"Tin nhắn không được sửa đổi sau khi chạy {file_name}")
            else:
                raise
    except (ValueError, IndexError) as e:
        logger.error(f"Lỗi phân tích callback start '{call.data}': {e}")
        bot.answer_callback_query(call.id, "Lỗi: Lệnh start không hợp lệ.", show_alert=True)
    except Exception as e:
        logger.error(f"Lỗi trong start_bot_callback cho '{call.data}': {e}", exc_info=True)
        bot.answer_callback_query(call.id, "Lỗi khi chạy script.", show_alert=True)
        try:
            _, script_owner_id_err_str, file_name_err = call.data.split('_', 2)
            script_owner_id_err = int(script_owner_id_err_str)
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=create_control_buttons(script_owner_id_err, file_name_err, False))
        except Exception as e_btn:
            logger.error(f"Không thể cập nhật nút sau lỗi start: {e_btn}")

def stop_bot_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        requesting_user_id = call.from_user.id
        chat_id_for_reply = call.message.chat.id

        logger.info(f"Yêu cầu dừng: Người yêu cầu={requesting_user_id}, Chủ sở hữu={script_owner_id}, File='{file_name}'")
        if not (requesting_user_id == script_owner_id or requesting_user_id in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Không có quyền.", show_alert=True)
            return

        user_files_list = user_files.get(script_owner_id, [])
        file_info = next((f for f in user_files_list if f[0] == file_name), None)
        if not file_info:
            bot.answer_callback_query(call.id, "⚠️ File không tìm thấy.", show_alert=True)
            check_files_callback(call)
            return

        file_type = file_info[1]
        script_key = f"{script_owner_id}_{file_name}"

        if not is_bot_running(script_owner_id, file_name):
            bot.answer_callback_query(call.id, f"⚠️ Script '{file_name}' đã dừng.", show_alert=True)
            try:
                bot.edit_message_text(
                    f"⚙️ Điều khiển cho: `{file_name}` ({file_type}) của User `{script_owner_id}`\nTrạng thái: 🔴 Đã Dừng",
                    chat_id_for_reply, call.message.message_id,
                    reply_markup=create_control_buttons(script_owner_id, file_name, False), parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Lỗi cập nhật nút (đã dừng): {e}")
            return

        bot.answer_callback_query(call.id, f"⏳ Đang dừng {file_name} cho user {script_owner_id}...")
        process_info = bot_scripts.get(script_key)
        if process_info:
            kill_process_tree(process_info)
            if script_key in bot_scripts:
                del bot_scripts[script_key]
                logger.info(f"Đã xóa {script_key} khỏi danh sách đang chạy sau khi dừng.")
        else:
            logger.warning(f"Script {script_key} đang chạy theo psutil nhưng không có trong dict bot_scripts.")

        try:
            bot.edit_message_text(
                f"⚙️ Điều khiển cho: `{file_name}` ({file_type}) của User `{script_owner_id}`\nTrạng thái: 🔴 Đã Dừng",
                chat_id_for_reply, call.message.message_id,
                reply_markup=create_control_buttons(script_owner_id, file_name, False), parse_mode='Markdown'
            )
        except telebot.apihelper.ApiTelegramException as e:
            if "message is not modified" in str(e):
                logger.warning(f"Tin nhắn không được sửa đổi sau khi dừng {file_name}")
            else:
                raise
    except (ValueError, IndexError) as e:
        logger.error(f"Lỗi phân tích callback stop '{call.data}': {e}")
        bot.answer_callback_query(call.id, "Lỗi: Lệnh stop không hợp lệ.", show_alert=True)
    except Exception as e:
        logger.error(f"Lỗi trong stop_bot_callback cho '{call.data}': {e}", exc_info=True)
        bot.answer_callback_query(call.id, "Lỗi khi dừng script.", show_alert=True)

def restart_bot_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        requesting_user_id = call.from_user.id
        chat_id_for_reply = call.message.chat.id

        logger.info(f"Khởi động lại: Người yêu cầu={requesting_user_id}, Chủ sở hữu={script_owner_id}, File='{file_name}'")
        if not (requesting_user_id == script_owner_id or requesting_user_id in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Không có quyền.", show_alert=True)
            return

        user_files_list = user_files.get(script_owner_id, [])
        file_info = next((f for f in user_files_list if f[0] == file_name), None)
        if not file_info:
            bot.answer_callback_query(call.id, "⚠️ File không tìm thấy.", show_alert=True)
            check_files_callback(call)
            return

        file_type = file_info[1]
        user_folder = get_user_folder(script_owner_id)
        file_path = os.path.join(user_folder, file_name)
        script_key = f"{script_owner_id}_{file_name}"

        if not os.path.exists(file_path):
            bot.answer_callback_query(call.id, f"⚠️ Lỗi: File `{file_name}` không tồn tại! Tải lại.", show_alert=True)
            remove_user_file_db(script_owner_id, file_name)
            if script_key in bot_scripts:
                del bot_scripts[script_key]
            check_files_callback(call)
            return

        bot.answer_callback_query(call.id, f"⏳ Đang khởi động lại {file_name} cho user {script_owner_id}...")
        if is_bot_running(script_owner_id, file_name):
            logger.info(f"Khởi động lại: Đang dừng {script_key} hiện tại...")
            process_info = bot_scripts.get(script_key)
            if process_info:
                kill_process_tree(process_info)
            if script_key in bot_scripts:
                del bot_scripts[script_key]
            time.sleep(1.5)

        logger.info(f"Khởi động lại: Đang chạy script {script_key}...")
        if file_type == 'py':
            threading.Thread(target=run_script, args=(file_path, script_owner_id, user_folder, file_name, call.message)).start()
        elif file_type == 'js':
            threading.Thread(target=run_js_script, args=(file_path, script_owner_id, user_folder, file_name, call.message)).start()
        else:
            bot.send_message(chat_id_for_reply, f"❌ Loại không xác định '{file_type}' cho '{file_name}'.")
            return

        time.sleep(1.5)
        is_now_running = is_bot_running(script_owner_id, file_name)
        status_text = '🟢 Đang Chạy' if is_now_running else '🟡 Đang khởi động (hoặc thất bại)'
        try:
            bot.edit_message_text(
                f"⚙️ Điều khiển cho: `{file_name}` ({file_type}) của User `{script_owner_id}`\nTrạng thái: {status_text}",
                chat_id_for_reply, call.message.message_id,
                reply_markup=create_control_buttons(script_owner_id, file_name, is_now_running), parse_mode='Markdown'
            )
        except telebot.apihelper.ApiTelegramException as e:
            if "message is not modified" in str(e):
                logger.warning(f"Tin nhắn không được sửa đổi (khởi động lại {file_name})")
            else:
                raise
    except (ValueError, IndexError) as e:
        logger.error(f"Lỗi phân tích callback restart '{call.data}': {e}")
        bot.answer_callback_query(call.id, "Lỗi: Lệnh restart không hợp lệ.", show_alert=True)
    except Exception as e:
        logger.error(f"Lỗi trong restart_bot_callback cho '{call.data}': {e}", exc_info=True)
        bot.answer_callback_query(call.id, "Lỗi khi khởi động lại.", show_alert=True)
        try:
            _, script_owner_id_err_str, file_name_err = call.data.split('_', 2)
            script_owner_id_err = int(script_owner_id_err_str)
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=create_control_buttons(script_owner_id_err, file_name_err, False))
        except Exception as e_btn:
            logger.error(f"Không thể cập nhật nút sau lỗi restart: {e_btn}")

def delete_bot_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        requesting_user_id = call.from_user.id
        chat_id_for_reply = call.message.chat.id

        logger.info(f"Xóa: Người yêu cầu={requesting_user_id}, Chủ sở hữu={script_owner_id}, File='{file_name}'")
        if not (requesting_user_id == script_owner_id or requesting_user_id in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Không có quyền.", show_alert=True)
            return

        user_files_list = user_files.get(script_owner_id, [])
        if not any(f[0] == file_name for f in user_files_list):
            bot.answer_callback_query(call.id, "⚠️ File không tìm thấy.", show_alert=True)
            check_files_callback(call)
            return

        bot.answer_callback_query(call.id, f"🗑️ Đang xóa {file_name} cho user {script_owner_id}...")
        script_key = f"{script_owner_id}_{file_name}"
        if is_bot_running(script_owner_id, file_name):
            logger.info(f"Xóa: Đang dừng {script_key}...")
            process_info = bot_scripts.get(script_key)
            if process_info:
                kill_process_tree(process_info)
            if script_key in bot_scripts:
                del bot_scripts[script_key]
            time.sleep(0.5)

        user_folder = get_user_folder(script_owner_id)
        file_path = os.path.join(user_folder, file_name)
        log_path = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        deleted_disk = []
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                deleted_disk.append(file_name)
                logger.info(f"Đã xóa file: {file_path}")
            except OSError as e:
                logger.error(f"Lỗi xóa {file_path}: {e}")
        if os.path.exists(log_path):
            try:
                os.remove(log_path)
                deleted_disk.append(os.path.basename(log_path))
                logger.info(f"Đã xóa log: {log_path}")
            except OSError as e:
                logger.error(f"Lỗi xóa log {log_path}: {e}")

        remove_user_file_db(script_owner_id, file_name)
        deleted_str = ", ".join(f"`{f}`" for f in deleted_disk) if deleted_disk else "các file liên quan"
        try:
            bot.edit_message_text(
                f"🗑️ Bản ghi `{file_name}` (User `{script_owner_id}`) và {deleted_str} đã được xóa!",
                chat_id_for_reply, call.message.message_id, reply_markup=None, parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Lỗi chỉnh sửa tin nhắn sau khi xóa: {e}")
            bot.send_message(chat_id_for_reply, f"🗑️ Bản ghi `{file_name}` đã được xóa.", parse_mode='Markdown')
    except (ValueError, IndexError) as e:
        logger.error(f"Lỗi phân tích callback delete '{call.data}': {e}")
        bot.answer_callback_query(call.id, "Lỗi: Lệnh xóa không hợp lệ.", show_alert=True)
    except Exception as e:
        logger.error(f"Lỗi trong delete_bot_callback cho '{call.data}': {e}", exc_info=True)
        bot.answer_callback_query(call.id, "Lỗi khi xóa.", show_alert=True)

def logs_bot_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        requesting_user_id = call.from_user.id
        chat_id = call.message.chat.id
        
        if not (requesting_user_id == script_owner_id or requesting_user_id in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Không có quyền xem logs.", show_alert=True)
            return
        
        user_folder = get_user_folder(script_owner_id)
        log_path = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        
        if not os.path.exists(log_path):
            bot.answer_callback_query(call.id, "📝 Chưa có logs nào.", show_alert=True)
            return
        
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            log_content = f.read()[-3000:]
        
        if not log_content:
            log_content = "(File log trống)"
        
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, f"📜 Logs của `{file_name}`:\n```\n{log_content}\n```", parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Lỗi logs_bot_callback: {e}")
        bot.answer_callback_query(call.id, "❌ Lỗi đọc logs", show_alert=True)

def _logic_delete_all_files_on_server(message):
    user_id = message.from_user.id
    if user_id not in admin_ids:
        bot.reply_to(message, "⚠️ Chỉ admin mới được xoá ALL file trên server!")
        return
    
    total_files = sum(len(files) for files in user_files.values())
    total_users = len(user_files)
    
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("✅ Xoá Sever Files", callback_data='confirm_delete_all_server'),
        types.InlineKeyboardButton("❌ Hủy", callback_data='back_to_main')
    )
    
    bot.reply_to(
        message, 
        f"🚨 Cảnh Báo : Bạn sắp xoá Toàn Bộ{total_files} file của {total_users} user trên server!\n"
        f"Hành động này không thể hoàn tác!",
        reply_markup=markup
    )

def confirm_delete_all_server_callback(call):
    user_id = call.from_user.id
    if user_id not in admin_ids:
        bot.answer_callback_query(call.id, "⚠️ Cút!", show_alert=True)
        return
    
    bot.answer_callback_query(call.id, "⏳ Đang xoá ALL file server...")
    bot.edit_message_text("⏳ Đang quét và xoá ALL file trên server...", call.message.chat.id, call.message.message_id)
    
    total_deleted = 0
    total_errors = 0
    users_affected = 0
    
    for script_key, script_info in list(bot_scripts.items()):
        try:
            kill_process_tree(script_info)
            if script_key in bot_scripts:
                del bot_scripts[script_key]
        except:
            pass
    
    for target_user_id, files_list in list(user_files.items()):
        user_folder = get_user_folder(target_user_id)
        users_affected += 1
        
        for file_name, file_type in files_list:
            file_path = os.path.join(user_folder, file_name)
            log_path = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
            
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    total_deleted += 1
                except:
                    total_errors += 1
            
            if os.path.exists(log_path):
                try:
                    os.remove(log_path)
                except:
                    pass
        
        remove_all_user_files_db(target_user_id)
        
        try:
            shutil.rmtree(user_folder)
        except:
            pass
    
    result_msg = (f"🚀 Đã Xoá All Sever File!\n\n"
                  f"✅ Đã xoá: {total_deleted} file\n"
                  f"👥 Số user bị ảnh hưởng: {users_affected}\n"
                  f"❌ Lỗi: {total_errors}")
    
    bot.edit_message_text(result_msg, call.message.chat.id, call.message.message_id)
    
    try:
        for uid in active_users:
            try:
                bot.send_message(uid, "⚠️ Server đã xoá ALL file !")
            except:
                pass
    except:
        pass

@bot.message_handler(commands=['deleteserver'])
def command_delete_server(message):
    _logic_delete_all_files_on_server(message)

def speed_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    start_cb_ping_time = time.time()
    try:
        bot.edit_message_text("🏃 Đang kiểm tra tốc độ...", chat_id, call.message.message_id)
        bot.send_chat_action(chat_id, 'typing')
        response_time = round((time.time() - start_cb_ping_time) * 1000, 2)
        status = "🔓 Mở Khóa" if not bot_locked else "🔒 Đã Khóa"
        if user_id == OWNER_ID:
            user_level = "👑 Chủ Sở Hữu"
        elif user_id in admin_ids:
            user_level = "🛡️ Quản Trị Viên"
        elif user_id in user_subscriptions and user_subscriptions[user_id].get('expiry', datetime.min) > datetime.now():
            user_level = "⭐ VIP"
        else:
            user_level = "🆓 Người Dùng Thường"
        speed_msg = (f"⚡ Tốc Độ & Trạng Thái Bot:\n\n⏱️ Thời gian phản hồi API: {response_time} ms\n"
                     f"🚦 Trạng thái Bot: {status}\n"
                     f"👤 Cấp độ của bạn: {user_level}")
        bot.answer_callback_query(call.id)
        bot.edit_message_text(speed_msg, chat_id, call.message.message_id, reply_markup=create_main_menu_inline(user_id))
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra tốc độ (cb): {e}", exc_info=True)
        bot.answer_callback_query(call.id, "Lỗi khi kiểm tra tốc độ.", show_alert=True)
        try:
            bot.edit_message_text("〽️ Menu Chính", chat_id, call.message.message_id, reply_markup=create_main_menu_inline(user_id))
        except Exception:
            pass

def back_to_main_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    limit_str = str(file_limit) if file_limit != float('inf') else "Không giới hạn"
    expiry_info = ""
    if user_id == OWNER_ID:
        user_status = "👑 Chủ Sở Hữu"
    elif user_id in admin_ids:
        user_status = "🛡️ Quản Trị Viên"
    elif user_id in user_subscriptions:
        expiry_date = user_subscriptions[user_id].get('expiry')
        if expiry_date and expiry_date > datetime.now():
            user_status = "⭐ VIP"
            days_left = (expiry_date - datetime.now()).days
            expiry_info = f"\n⏳ VIP hết hạn sau: {days_left} ngày"
        else:
            user_status = "🆓 Người Dùng Thường (VIP đã hết hạn)"
    else:
        user_status = "🆓 Người Dùng Thường"
    main_menu_text = (f"〽️ Chào mừng trở lại, {call.from_user.first_name}!\n\n🆔 ID: `{user_id}`\n"
                      f"🔰 Trạng thái: {user_status}{expiry_info}\n📁 File: {current_files} / {limit_str}\n\n"
                      f"👇 Sử dụng nút bên dưới hoặc gõ lệnh.")
    try:
        bot.answer_callback_query(call.id)
        bot.edit_message_text(main_menu_text, chat_id, call.message.message_id,
                              reply_markup=create_main_menu_inline(user_id), parse_mode='Markdown')
    except telebot.apihelper.ApiTelegramException as e:
        if "message is not modified" in str(e):
            logger.warning("Tin nhắn không được sửa đổi (back_to_main).")
        else:
            logger.error(f"Lỗi API trên back_to_main: {e}")
    except Exception as e:
        logger.error(f"Lỗi xử lý back_to_main: {e}", exc_info=True)

def subscription_management_callback(call):
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text("💳 Quản Lý VIP\nChọn hành động:",
                              call.message.chat.id, call.message.message_id, reply_markup=create_subscription_menu())
    except Exception as e:
        logger.error(f"Lỗi hiển thị menu VIP: {e}")

def stats_callback(call):
    bot.answer_callback_query(call.id)
    _logic_statistics(call.message)
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                      reply_markup=create_main_menu_inline(call.from_user.id))
    except Exception as e:
        logger.error(f"Lỗi cập nhật menu sau stats_callback: {e}")

def lock_bot_callback(call):
    global bot_locked
    bot_locked = True
    logger.warning(f"Bot đã khóa bởi Admin {call.from_user.id}")
    bot.answer_callback_query(call.id, "🔒 Bot đã khóa.")
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=create_main_menu_inline(call.from_user.id))
    except Exception as e:
        logger.error(f"Lỗi cập nhật menu (khóa): {e}")

def unlock_bot_callback(call):
    global bot_locked
    bot_locked = False
    logger.warning(f"Bot đã mở khóa bởi Admin {call.from_user.id}")
    bot.answer_callback_query(call.id, "🔓 Bot đã mở khóa.")
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=create_main_menu_inline(call.from_user.id))
    except Exception as e:
        logger.error(f"Lỗi cập nhật menu (mở khóa): {e}")

def run_all_scripts_callback(call):
    _logic_run_all_scripts(call)

def broadcast_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "📢 Gửi tin nhắn để broadcast.\n/cancel để hủy.")
    bot.register_next_step_handler(msg, process_broadcast_message)

def process_broadcast_message(message):
    user_id = message.from_user.id
    if user_id not in admin_ids:
        bot.reply_to(message, "⚠️ Không được ủy quyền.")
        return
    if message.text and message.text.lower() == '/cancel':
        bot.reply_to(message, "Đã hủy broadcast.")
        return

    broadcast_content = message.text
    if not broadcast_content and not (message.photo or message.video or message.document or message.sticker or message.voice or message.audio):
        bot.reply_to(message, "⚠️ Không thể broadcast tin nhắn trống. Gửi văn bản hoặc media, hoặc /cancel.")
        msg = bot.send_message(message.chat.id, "📢 Gửi tin nhắn broadcast hoặc /cancel.")
        bot.register_next_step_handler(msg, process_broadcast_message)
        return

    target_count = len(active_users)
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("✅ Xác Nhận & Gửi", callback_data=f"confirm_broadcast_{message.message_id}"),
               types.InlineKeyboardButton("❌ Hủy Bỏ", callback_data="cancel_broadcast"))

    preview_text = broadcast_content[:1000].strip() if broadcast_content else "(Tin nhắn media)"
    bot.reply_to(message, f"⚠️ Xác Nhận Broadcast:\n\n```\n{preview_text}\n```\n"
                          f"Gửi đến **{target_count}** người dùng. Chắc chắn chứ?", reply_markup=markup, parse_mode='Markdown')

def handle_confirm_broadcast(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    if user_id not in admin_ids:
        bot.answer_callback_query(call.id, "⚠️ Chỉ admin.", show_alert=True)
        return
    try:
        original_message = call.message.reply_to_message
        if not original_message:
            raise ValueError("Không thể lấy tin nhắn gốc.")

        broadcast_text = None
        broadcast_photo_id = None
        broadcast_video_id = None

        if original_message.text:
            broadcast_text = original_message.text
        elif original_message.photo:
            broadcast_photo_id = original_message.photo[-1].file_id
        elif original_message.video:
            broadcast_video_id = original_message.video.file_id
        else:
            raise ValueError("Tin nhắn không có văn bản hoặc media được hỗ trợ cho broadcast.")

        bot.answer_callback_query(call.id, "🚀 Đang bắt đầu broadcast...")
        bot.edit_message_text(f"📢 Đang broadcast đến {len(active_users)} người dùng...",
                              chat_id, call.message.message_id, reply_markup=None)
        thread = threading.Thread(target=execute_broadcast, args=(
            broadcast_text, broadcast_photo_id, broadcast_video_id,
            original_message.caption if (broadcast_photo_id or broadcast_video_id) else None,
            chat_id))
        thread.start()
    except ValueError as ve:
        logger.error(f"Lỗi lấy tin nhắn cho xác nhận broadcast: {ve}")
        bot.edit_message_text(f"❌ Lỗi bắt đầu broadcast: {ve}", chat_id, call.message.message_id, reply_markup=None)
    except Exception as e:
        logger.error(f"Lỗi trong handle_confirm_broadcast: {e}", exc_info=True)
        bot.edit_message_text("❌ Lỗi không mong muốn khi xác nhận broadcast.", chat_id, call.message.message_id, reply_markup=None)

def handle_cancel_broadcast(call):
    bot.answer_callback_query(call.id, "Đã hủy broadcast.")
    bot.delete_message(call.message.chat.id, call.message.message_id)
    if call.message.reply_to_message:
        try:
            bot.delete_message(call.message.chat.id, call.message.reply_to_message.message_id)
        except:
            pass

def execute_broadcast(broadcast_text, photo_id, video_id, caption, admin_chat_id):
    sent_count = 0
    failed_count = 0
    blocked_count = 0
    start_exec_time = time.time()
    users_to_broadcast = list(active_users)
    total_users = len(users_to_broadcast)
    logger.info(f"Đang thực hiện broadcast đến {total_users} người dùng.")
    batch_size = 25
    delay_batches = 1.5

    for i, user_id_bc in enumerate(users_to_broadcast):
        try:
            if broadcast_text:
                bot.send_message(user_id_bc, broadcast_text, parse_mode='Markdown')
            elif photo_id:
                bot.send_photo(user_id_bc, photo_id, caption=caption, parse_mode='Markdown' if caption else None)
            elif video_id:
                bot.send_video(user_id_bc, video_id, caption=caption, parse_mode='Markdown' if caption else None)
            sent_count += 1
        except telebot.apihelper.ApiTelegramException as e:
            err_desc = str(e).lower()
            if any(s in err_desc for s in ["bot was blocked", "user is deactivated", "chat not found", "kicked from", "restricted"]):
                logger.warning(f"Broadcast thất bại đến {user_id_bc}: User đã chặn/không hoạt động.")
                blocked_count += 1
            elif "flood control" in err_desc or "too many requests" in err_desc:
                retry_after = 5
                match = re.search(r"retry after (\d+)", err_desc)
                if match:
                    retry_after = int(match.group(1)) + 1
                logger.warning(f"Flood control. Ngủ {retry_after}s...")
                time.sleep(retry_after)
                try:
                    if broadcast_text:
                        bot.send_message(user_id_bc, broadcast_text, parse_mode='Markdown')
                    elif photo_id:
                        bot.send_photo(user_id_bc, photo_id, caption=caption, parse_mode='Markdown' if caption else None)
                    elif video_id:
                        bot.send_video(user_id_bc, video_id, caption=caption, parse_mode='Markdown' if caption else None)
                    sent_count += 1
                except Exception as e_retry:
                    logger.error(f"Thử lại broadcast thất bại đến {user_id_bc}: {e_retry}")
                    failed_count += 1
            else:
                logger.error(f"Broadcast thất bại đến {user_id_bc}: {e}")
                failed_count += 1
        except Exception as e:
            logger.error(f"Lỗi không mong muốn khi broadcast đến {user_id_bc}: {e}")
            failed_count += 1

        if (i + 1) % batch_size == 0 and i < total_users - 1:
            logger.info(f"Broadcast batch {i//batch_size + 1} đã gửi. Ngủ {delay_batches}s...")
            time.sleep(delay_batches)
        elif i % 5 == 0:
            time.sleep(0.2)

    duration = round(time.time() - start_exec_time, 2)
    result_msg = (f"📢 Broadcast Hoàn Tất!\n\n✅ Đã gửi: {sent_count}\n❌ Thất bại: {failed_count}\n"
                  f"🚫 Bị chặn/Không hoạt động: {blocked_count}\n👥 Mục tiêu: {total_users}\n⏱️ Thời gian: {duration}s")
    logger.info(result_msg)
    try:
        bot.send_message(admin_chat_id, result_msg)
    except Exception as e:
        logger.error(f"Không thể gửi kết quả broadcast đến admin {admin_chat_id}: {e}")

def admin_panel_callback(call):
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text("👑 Bảng Điều Khiển Admin\nQuản lý admin (hành động của Owner có thể bị hạn chế).",
                              call.message.chat.id, call.message.message_id, reply_markup=create_admin_panel())
    except Exception as e:
        logger.error(f"Lỗi hiển thị admin panel: {e}")

def add_admin_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "👑 Nhập User ID để thăng cấp Admin.\n/cancel để hủy.")
    bot.register_next_step_handler(msg, process_add_admin_id)

def process_add_admin_id(message):
    owner_id_check = message.from_user.id
    if owner_id_check != OWNER_ID:
        bot.reply_to(message, "⚠️ Chỉ Owner.")
        return
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "Đã hủy thăng cấp admin.")
        return
    try:
        new_admin_id = int(message.text.strip())
        if new_admin_id <= 0:
            raise ValueError("ID phải là số dương")
        if new_admin_id == OWNER_ID:
            bot.reply_to(message, "⚠️ Owner đã là Owner.")
            return
        if new_admin_id in admin_ids:
            bot.reply_to(message, f"⚠️ User `{new_admin_id}` đã là Admin.")
            return
        add_admin_db(new_admin_id)
        logger.warning(f"Admin {new_admin_id} đã được thêm bởi Owner {owner_id_check}.")
        bot.reply_to(message, f"✅ User `{new_admin_id}` đã được thăng cấp Admin.")
        try:
            bot.send_message(new_admin_id, "🎉 Chúc mừng! Bạn đã trở thành Admin.")
        except Exception as e:
            logger.error(f"Không thể thông báo admin mới {new_admin_id}: {e}")
    except ValueError:
        bot.reply_to(message, "⚠️ ID không hợp lệ. Gửi ID số hoặc /cancel.")
        msg = bot.send_message(message.chat.id, "👑 Nhập User ID để thăng cấp hoặc /cancel.")
        bot.register_next_step_handler(msg, process_add_admin_id)
    except Exception as e:
        logger.error(f"Lỗi xử lý thêm admin: {e}", exc_info=True)
        bot.reply_to(message, "Lỗi.")

def remove_admin_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "👑 Nhập User ID của Admin để xóa.\n/cancel để hủy.")
    bot.register_next_step_handler(msg, process_remove_admin_id)

def process_remove_admin_id(message):
    owner_id_check = message.from_user.id
    if owner_id_check != OWNER_ID:
        bot.reply_to(message, "⚠️ Chỉ Owner.")
        return
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "Đã hủy xóa admin.")
        return
    try:
        admin_id_remove = int(message.text.strip())
        if admin_id_remove <= 0:
            raise ValueError("ID phải là số dương")
        if admin_id_remove == OWNER_ID:
            bot.reply_to(message, "⚠️ Owner không thể tự xóa.")
            return
        if admin_id_remove not in admin_ids:
            bot.reply_to(message, f"⚠️ User `{admin_id_remove}` không phải Admin.")
            return
        if remove_admin_db(admin_id_remove):
            logger.warning(f"Admin {admin_id_remove} đã bị xóa bởi Owner {owner_id_check}.")
            bot.reply_to(message, f"✅ Admin `{admin_id_remove}` đã bị xóa.")
            try:
                bot.send_message(admin_id_remove, "ℹ️ Bạn không còn là Admin nữa.")
            except Exception as e:
                logger.error(f"Không thể thông báo admin bị xóa {admin_id_remove}: {e}")
        else:
            bot.reply_to(message, f"❌ Không thể xóa admin `{admin_id_remove}`. Kiểm tra logs.")
    except ValueError:
        bot.reply_to(message, "⚠️ ID không hợp lệ. Gửi ID số hoặc /cancel.")
        msg = bot.send_message(message.chat.id, "👑 Nhập Admin ID để xóa hoặc /cancel.")
        bot.register_next_step_handler(msg, process_remove_admin_id)
    except Exception as e:
        logger.error(f"Lỗi xử lý xóa admin: {e}", exc_info=True)
        bot.reply_to(message, "Lỗi.")

def list_admins_callback(call):
    bot.answer_callback_query(call.id)
    try:
        admin_list_str = "\n".join(f"- `{aid}` {'(Owner)' if aid == OWNER_ID else ''}" for aid in sorted(list(admin_ids)))
        if not admin_list_str:
            admin_list_str = "(Không có Owner/Admins nào được cấu hình!)"
        bot.edit_message_text(f"👑 Danh Sách Admin Hiện Tại:\n\n{admin_list_str}", call.message.chat.id,
                              call.message.message_id, reply_markup=create_admin_panel(), parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Lỗi liệt kê admin: {e}")

def add_subscription_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "💳 Nhập User ID & số ngày (ví dụ: `12345678 30`).\n/cancel để hủy.")
    bot.register_next_step_handler(msg, process_add_subscription_details)

def process_add_subscription_details(message):
    admin_id_check = message.from_user.id
    if admin_id_check not in admin_ids:
        bot.reply_to(message, "⚠️ Không được ủy quyền.")
        return
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "Đã hủy thêm VIP.")
        return
    try:
        parts = message.text.split()
        if len(parts) != 2:
            raise ValueError("Định dạng không đúng")
        sub_user_id = int(parts[0].strip())
        days = int(parts[1].strip())
        if sub_user_id <= 0 or days <= 0:
            raise ValueError("User ID/ngày phải là số dương")

        current_expiry = user_subscriptions.get(sub_user_id, {}).get('expiry')
        start_date_new_sub = datetime.now()
        if current_expiry and current_expiry > start_date_new_sub:
            start_date_new_sub = current_expiry
        new_expiry = start_date_new_sub + timedelta(days=days)
        save_subscription(sub_user_id, new_expiry)

        logger.info(f"VIP cho {sub_user_id} bởi admin {admin_id_check}. Hết hạn: {new_expiry:%Y-%m-%d}")
        bot.reply_to(message, f"✅ Đã thêm/gia hạn VIP cho `{sub_user_id}` {days} ngày.\nHết hạn mới: {new_expiry:%Y-%m-%d}")
        try:
            bot.send_message(sub_user_id, f"🎉 VIP của bạn đã được kích hoạt/gia hạn thêm {days} ngày! Hết hạn: {new_expiry:%Y-%m-%d}.")
        except Exception as e:
            logger.error(f"Không thể thông báo cho {sub_user_id} về VIP mới: {e}")
    except ValueError as e:
        bot.reply_to(message, f"⚠️ Không hợp lệ: {e}. Định dạng: `ID ngày` hoặc /cancel.")
        msg = bot.send_message(message.chat.id, "💳 Nhập User ID & số ngày, hoặc /cancel.")
        bot.register_next_step_handler(msg, process_add_subscription_details)
    except Exception as e:
        logger.error(f"Lỗi xử lý thêm VIP: {e}", exc_info=True)
        bot.reply_to(message, "Lỗi.")

def remove_subscription_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "💳 Nhập User ID để xóa VIP.\n/cancel để hủy.")
    bot.register_next_step_handler(msg, process_remove_subscription_id)

def process_remove_subscription_id(message):
    admin_id_check = message.from_user.id
    if admin_id_check not in admin_ids:
        bot.reply_to(message, "⚠️ Không được ủy quyền.")
        return
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "Đã hủy xóa VIP.")
        return
    try:
        sub_user_id_remove = int(message.text.strip())
        if sub_user_id_remove <= 0:
            raise ValueError("ID phải là số dương")
        if sub_user_id_remove not in user_subscriptions:
            bot.reply_to(message, f"⚠️ User `{sub_user_id_remove}` không có VIP trong bộ nhớ.")
            return
        remove_subscription_db(sub_user_id_remove)
        logger.warning(f"VIP cho {sub_user_id_remove} đã bị xóa bởi admin {admin_id_check}.")
        bot.reply_to(message, f"✅ VIP cho `{sub_user_id_remove}` đã bị xóa.")
        try:
            bot.send_message(sub_user_id_remove, "ℹ️ VIP của bạn đã bị xóa bởi admin.")
        except Exception as e:
            logger.error(f"Không thể thông báo cho {sub_user_id_remove} về việc xóa VIP: {e}")
    except ValueError:
        bot.reply_to(message, "⚠️ ID không hợp lệ. Gửi ID số hoặc /cancel.")
        msg = bot.send_message(message.chat.id, "💳 Nhập User ID để xóa VIP, hoặc /cancel.")
        bot.register_next_step_handler(msg, process_remove_subscription_id)
    except Exception as e:
        logger.error(f"Lỗi xử lý xóa VIP: {e}", exc_info=True)
        bot.reply_to(message, "Lỗi.")

def check_subscription_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "💳 Nhập User ID để kiểm tra VIP.\n/cancel để hủy.")
    bot.register_next_step_handler(msg, process_check_subscription_id)

def process_check_subscription_id(message):
    admin_id_check = message.from_user.id
    if admin_id_check not in admin_ids:
        bot.reply_to(message, "⚠️ Không được ủy quyền.")
        return
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "Đã hủy kiểm tra VIP.")
        return
    try:
        sub_user_id_check = int(message.text.strip())
        if sub_user_id_check <= 0:
            raise ValueError("ID phải là số dương")
        if sub_user_id_check in user_subscriptions:
            expiry_dt = user_subscriptions[sub_user_id_check].get('expiry')
            if expiry_dt:
                if expiry_dt > datetime.now():
                    days_left = (expiry_dt - datetime.now()).days
                    bot.reply_to(message, f"✅ User `{sub_user_id_check}` có VIP đang hoạt động.\nHết hạn: {expiry_dt:%Y-%m-%d %H:%M:%S} (còn {days_left} ngày).")
                else:
                    bot.reply_to(message, f"⚠️ User `{sub_user_id_check}` có VIP đã hết hạn (Vào: {expiry_dt:%Y-%m-%d %H:%M:%S}).")
                    remove_subscription_db(sub_user_id_check)
            else:
                bot.reply_to(message, f"⚠️ User `{sub_user_id_check}` trong danh sách VIP, nhưng thiếu ngày hết hạn. Thêm lại nếu cần.")
        else:
            bot.reply_to(message, f"ℹ️ User `{sub_user_id_check}` không có bản ghi VIP.")
    except ValueError:
        bot.reply_to(message, "⚠️ ID không hợp lệ. Gửi ID số hoặc /cancel.")
        msg = bot.send_message(message.chat.id, "💳 Nhập User ID để kiểm tra, hoặc /cancel.")
        bot.register_next_step_handler(msg, process_check_subscription_id)
    except Exception as e:
        logger.error(f"Lỗi xử lý kiểm tra VIP: {e}", exc_info=True)
        bot.reply_to(message, "Lỗi.")

def cleanup():
    logger.warning("Đang tắt. Dọn dẹp các process...")
    script_keys_to_stop = list(bot_scripts.keys())
    if not script_keys_to_stop:
        logger.info("Không có script nào đang chạy. Thoát.")
        return
    logger.info(f"Đang dừng {len(script_keys_to_stop)} scripts...")
    for key in script_keys_to_stop:
        if key in bot_scripts:
            logger.info(f"Đang dừng: {key}")
            kill_process_tree(bot_scripts[key])
        else:
            logger.info(f"Script {key} đã được xóa.")
    logger.warning("Dọn dẹp hoàn tất.")

atexit.register(cleanup)

if __name__ == '__main__':
    logger.info("*"*40 + "\n🤖 Bot Đang Khởi Động...\n" + "*"*40)
    keep_alive()
    logger.info("🚀 Đang bắt đầu polling...")
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            logger.error(f"Lỗi rồi, nghỉ 20s rồi thử lại: {e}")
            time.sleep(20)