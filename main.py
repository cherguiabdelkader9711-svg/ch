import os
import sys
import time
import json
import csv
import asyncio
import threading
from flask import Flask, request, render_template_string
from telethon import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest
from telethon.tl.types import InputPeerUser

sys.stdout.reconfigure(line_buffering=True)

app = Flask(__name__)

auth_states = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Telegram Session Manager</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 50px; background: #f4f6f9; color: #333; }
        .card { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); max-width: 500px; margin: auto; }
        input[type="text"] { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
        button { background: #0088cc; color: white; border: none; padding: 10px 15px; border-radius: 4px; cursor: pointer; width: 100%; font-size: 16px; }
        button:hover { background: #0077b3; }
        .status { margin-top: 15px; font-weight: bold; color: #d9534f; }
    </style>
</head>
<body>
    <div class="card">
        <h2>🔐 تفعيل جلسات تليجرام السحابية</h2>
        <p>الحسابات المكتشفة: <strong>{{ phone }}</strong></p>
        <form action="/verify" method="post">
            <input type="hidden" name="phone" value="{{ phone }}">
            <button type="submit" name="action" value="send_code" style="background:#5cb85c; margin-bottom:20px;">طلب كود التحقق (SMS/Telegram)</button>
            <br>
            <input type="text" name="code" placeholder="أدخل الكود هنا...">
            <button type="submit" name="action" value="login">تأكيد تسجيل الدخول وتفعيل الجلسة</button>
        </form>
        {% if msg %}<div class="status">{{ msg }}</div>{% endif %}
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    with open('config.json', 'r', encoding='utf-8') as f:
        cfg = json.loads(f.read())
    return render_template_string(HTML_TEMPLATE, phone=cfg['accounts'][0], msg=request.args.get('msg', ''))

@app.route('/verify', methods=['POST'])
def verify():
    phone = request.form.get('phone')
    action = request.form.get('action')
    code = request.form.get('code')
    
    if action == 'send_code':
        asyncio.run_coroutine_threadsafe(trigger_send_code(phone), bot_loop)
        return render_template_string(HTML_TEMPLATE, phone=phone, msg="⏳ جاري إرسال الكود... تفقد تطبيق تليجرام.")
    elif action == 'login':
        if phone in auth_states:
            auth_states[phone]['code_to_submit'] = code
            return render_template_string(HTML_TEMPLATE, phone=phone, msg="⚙️ جاري التوثيق وتنشيط الجلسة...")
    return render_template_string(HTML_TEMPLATE, phone=phone, msg="")

# قراءة الإعدادات الثابتة
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.loads(f.read())

api_id = int(config['api_id'])
api_hash = config['api_hash']
group_target = config['group_target']
accounts = config['accounts']

PROCESSED_USERS_FILE = "processed_users.txt"
CSV_FILE = "members.csv"

bot_loop = asyncio.new_event_loop()

def load_processed_users():
    if os.path.exists(PROCESSED_USERS_FILE):
        with open(PROCESSED_USERS_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_processed_user(user_id):
    with open(PROCESSED_USERS_FILE, "a") as f:
        f.write(f"{user_id}\n")

# الدالة الاحترافية لقراءة ومعالجة ملف الـ CSV
def load_target_members_from_csv():
    members_list = []
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode='r', encoding='utf-8-sig') as f:
            # استخدام Sniffer للتعرف التلقائي على الفواصل (سواء كانت فاصلة منقوطة أو عادية)
            try:
                dialect = csv.Sniffer().sniff(f.read(2048))
                f.seek(0)
                reader = csv.DictReader(f, dialect=dialect)
            except Exception:
                f.seek(0)
                reader = csv.DictReader(f)
                
            for row in reader:
                # محاولة جلب المفاتيح الأساسية مع معالجة المسافات الزائدة في الحقول
                user_id = row.get('user_id') or row.get('id') or row.get('username')
                access_hash = row.get('access_hash') or row.get('hash') or '0'
                username = row.get('username') or ''
                
                if user_id:
                    members_list.append({
                        'user_id': user_id.strip(),
                        'access_hash': access_hash.strip(),
                        'username': username.strip()
                    })
    return members_list

async def trigger_send_code(phone):
    if phone in auth_states:
        cli = auth_states[phone]['client']
        print(f"📡 جاري طلب إرسال كود التحقق للرقم: {phone}")
        send_code_req = await cli.send_code_request(phone)
        auth_states[phone]['phone_code_hash'] = send_code_req.phone_code_hash

def run_telegram_bot():
    asyncio.set_event_loop(bot_loop)
    try:
        bot_loop.run_until_complete(core_adder_process())
    except Exception as e:
        print(f"❌ [CRITICAL ERROR]: {e}")

async def core_adder_process():
    clients = []
    
    print(f"⏳ جاري فحص والاتصال بـ ({len(accounts)}) حسابات...")
    for phone in accounts:
        session_name = f"session_{phone.replace('+', '')}"
        cli = TelegramClient(session_name, api_id, api_hash, receive_updates=False)
        await cli.connect()
        
        auth_states[phone] = {'client': cli, 'phone_code_hash': None, 'code_to_submit': None}
        
        while not await cli.is_user_authorized():
            print(f"⚠️ الحساب {phone} يحتاج تفعيل. افتح واجهة الويب لإدخال كود التحقق.")
            if auth_states[phone]['code_to_submit']:
                try:
                    current_code = auth_states[phone]['code_to_submit']
                    current_hash = auth_states[phone]['phone_code_hash']
                    await cli.sign_in(phone, code=current_code, phone_code_hash=current_hash)
                    print(f"✨ تم تسجيل الدخول بنجاح للرقم {phone}!")
                    break
                except Exception as auth_err:
                    print(f"❌ خطأ التوثيق: {auth_err}")
                    auth_states[phone]['code_to_submit'] = None
            await asyncio.sleep(10)
            
        try:
            await cli(JoinChannelRequest(group_target))
        except Exception:
            pass
        clients.append({'phone': phone, 'client': cli})
        print(f"✅ الحساب {phone} جاهز تماماً للعمل.")

    processed_users = load_processed_users()
    users_to_add = load_target_members_from_csv()
    print(f"📦 تم تحميل {len(users_to_add)} عضو بنجاح من ملف الـ CSV المتطور.")

    attempt_counter = 0

    for user in users_to_add:
        if len(clients) == 0:
            print("🚨 [توقف]: جميع الحسابات المربوطة تم حظرها مؤقتاً.")
            break

        user_id = user['user_id']
        access_hash = user['access_hash']
        username = user['username']

        if str(user_id) in processed_users:
            continue

        current_index = attempt_counter % len(clients)
        active_worker = clients[current_index]
        cli_worker = active_worker['client']
        phone_worker = active_worker['phone']

        user_display = f"@{username}" if username else f"ID: {user_id}"
        print(f"👤 [الحساب: {phone_worker}] نقل العضو من ملف CSV: {user_display}")

        try:
            my_group_entity = await cli_worker.get_entity(group_target)
            
            # التحقق مما إذا كان المعرف رقمي أو مجرد نص يوزر نيم
            if user_id.isdigit() and access_hash.isdigit() and access_hash != '0':
                user_peer = InputPeerUser(int(user_id), int(access_hash))
            else:
                user_peer = await cli_worker.get_input_entity(username if username else user_id)
            
            await cli_worker(InviteToChannelRequest(my_group_entity, [user_peer]))
            print(f"👍 [نجاح] أضاف {phone_worker} العضو {user_display}!")
            
            processed_users.add(str(user_id))
            save_processed_user(user_id)
            attempt_counter += 1
            
            # استراحة لمنع الحظر
            await asyncio.sleep(25)

        except Exception as e:
            error_msg = str(e)
            if "PEER_FLOOD" in error_msg:
                print(f"❌ [حظر مؤقت] عزل الحساب {phone_worker} بسبب ضغط السيرفر...")
                try:
                    await cli_worker.disconnect()
                except Exception:
                    pass
                clients
