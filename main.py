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

# تخزين مؤقت للحالات
auth_states = {}
bot_loop = None

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>تفعيل جلسات تليجرام</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 50px; background: #f4f6f9; color: #333; text-align: center; }
        .card { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); max-width: 500px; margin: auto; }
        input[type="text"] { width: 100%; padding: 10px; margin: 15px 0; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; text-align: center; font-size: 18px; }
        button { color: white; border: none; padding: 12px 15px; border-radius: 4px; cursor: pointer; width: 100%; font-size: 16px; font-weight: bold; margin-bottom: 10px; }
        .btn-send { background: #5cb85c; }
        .btn-send:hover { background: #4cae4c; }
        .btn-login { background: #0088cc; }
        .btn-login:hover { background: #0077b3; }
        .status { margin-top: 15px; font-weight: bold; color: #d9534f; font-size: 15px; }
    </style>
</head>
<body>
    <div class="card">
        <h2>🔐 تفعيل جلسات تليجرام السحابية</h2>
        <p>الحساب المكتشف: <strong>{{ phone }}</strong></p>
        <form action="/verify" method="post">
            <input type="hidden" name="phone" value="{{ phone }}">
            <button type="submit" name="action" value="send_code" class="btn-send">اضغط هنا لطلب كود التحقق (SMS/Telegram)</button>
            <input type="text" name="code" placeholder="أدخل كود التحقق هنا...">
            <button type="submit" name="action" value="login" class="btn-login">تأكيد تسجيل الدخول وتفعيل الجلسة</button>
        </form>
        {% if msg %}<div class="status">{{ msg }}</div>{% endif %}
    </div>
</body>
</html>
"""

with open('config.json', 'r', encoding='utf-8') as f:
    config = json.loads(f.read())

api_id = int(config['api_id'])
api_hash = config['api_hash']
group_target = config['group_target']
accounts = config['accounts']

CSV_FILE = "members.csv"
PROCESSED_USERS_FILE = "processed_users.txt"

def load_processed_users():
    if os.path.exists(PROCESSED_USERS_FILE):
        with open(PROCESSED_USERS_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_processed_user(user_id):
    with open(PROCESSED_USERS_FILE, "a") as f:
        f.write(f"{user_id}\n")

def load_target_members_from_csv():
    members_list = []
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode='r', encoding='utf-8-sig') as f:
            try:
                dialect = csv.Sniffer().sniff(f.read(2048))
                f.seek(0)
                reader = csv.DictReader(f, dialect=dialect)
            except Exception:
                f.seek(0)
                reader = csv.DictReader(f)
            for row in reader:
                user_id = row.get('user_id') or row.get('id')
                access_hash = row.get('access_hash') or row.get('hash') or '0'
                username = row.get('username') or ''
                if user_id:
                    members_list.append({
                        'user_id': user_id.strip(),
                        'access_hash': access_hash.strip(),
                        'username': username.strip()
                    })
    return members_list

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE, phone=accounts[0], msg=request.args.get('msg', ''))

@app.route('/verify', methods=['POST'])
def verify():
    phone = request.form.get('phone')
    action = request.form.get('action')
    code = request.form.get('code')
    
    if action == 'send_code':
        future = asyncio.run_coroutine_threadsafe(trigger_send_code(phone), bot_loop)
        try:
            success = future.result(timeout=15)
            if success:
                return render_template_string(HTML_TEMPLATE, phone=phone, msg="✅ تم إرسال الكود بنجاح! تفقد حسابك على تليجرام الآن.")
            else:
                return render_template_string(HTML_TEMPLATE, phone=phone, msg="❌ فشل إرسال الكود. تأكد من صحة رقم الهاتف والـ API.")
        except Exception as e:
            return render_template_string(HTML_TEMPLATE, phone=phone, msg=f"⚠️ خطأ أثناء إرسال الكود: {e}")
            
    elif action == 'login':
        if phone in auth_states:
            auth_states[phone]['code_to_submit'] = code
            return render_template_string(HTML_TEMPLATE, phone=phone, msg="⚙️ جاري معالجة الكود في الخلفية والتحقق من التفعيل...")
            
    return render_template_string(HTML_TEMPLATE, phone=phone, msg="")

async def trigger_send_code(phone):
    if phone in auth_states:
        try:
            cli = auth_states[phone]['client']
            if not cli.is_connected():
                await cli.connect()
            print(f"📡 [SYSTEM] جاري إرسال طلب الكود الفعلي إلى تليجرام للرقم: {phone}")
            send_code_req = await cli.send_code_request(phone)
            auth_states[phone]['phone_code_hash'] = send_code_req.phone_code_hash
            return True
        except Exception as e:
            print(f"❌ خطأ تليجرام أثناء طلب الكود: {e}")
            return False
    return False

def start_async_loop():
    global bot_loop
    bot_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(bot_loop)
    bot_loop.run_until_complete(core_adder_process())

async def core_adder_process():
    clients = []
    print(f"⏳ جاري تهيئة الاتصال للحساب: {accounts[0]}")
    
    for phone in accounts:
        session_name = f"session_{phone.replace('+', '')}"
        cli = TelegramClient(session_name, api_id, api_hash, receive_updates=False)
        await cli.connect()
        
        auth_states[phone] = {'client': cli, 'phone_code_hash': None, 'code_to_submit': None}
        
        while not await cli.is_user_authorized():
            if auth_states[phone]['code_to_submit']:
                try:
                    current_code = auth_states[phone]['code_to_submit']
                    current_hash = auth_states[phone]['phone_code_hash']
                    await cli.sign_in(phone, code=current_code, phone_code_hash=current_hash)
                    print(f"✨ تم تفعيل الجلسة وتسجيل الدخول بنجاح للرقم {phone}!")
                    auth_states[phone]['code_to_submit'] = None
                    break
                except Exception as auth_err:
                    print(f"❌ خطأ في الكود المدخل: {auth_err}")
                    auth_states[phone]['code_to_submit'] = None
            await asyncio.sleep(2)
            
        try:
            await cli(JoinChannelRequest(group_target))
        except Exception:
            pass
        clients.append({'phone': phone, 'client': cli})
        print(f"✅ الجلسة {phone} نشطة وجاهزة تماماً.")

    processed_users = load_processed_users()
    users_to_add = load_target_members_from_csv()
    print(f"📦 تم تحميل {len(users_to_add)} عضو من ملف الـ CSV وبدء النقل...")

    attempt_counter = 0
    for user in users_to_add:
        if len(clients) == 0:
            print("🚨 جميع الحسابات مقيدة مؤقتاً.")
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
        print(f"👤 [الحساب: {phone_worker}] محاولة نقل: {user_display}")

        try:
            my_group_entity = await cli_worker.get_entity(group_target)
            if user_id.isdigit() and access_hash.isdigit() and access_hash != '0':
                user_peer = InputPeerUser(int(user_id), int(access_hash))
            else:
                user_peer = await cli_worker.get_input_entity(username if username else user_id)
                
            await cli_worker(InviteToChannelRequest(my_group_entity, [user_peer]))
            print(f"👍 [نجاح] تم إضافة {user_display}")
            
            processed_users.add(str(user_id))
            save_processed_user(user_id)
            attempt_counter += 1
            await asyncio.sleep(30)
            
        except Exception as e:
            error_msg = str(e)
            if "PEER_FLOOD" in error_msg:
                print(f"❌ حظر مؤقت للحساب {phone_worker}")
                clients.remove(active_worker)
            else:
                processed_users.add(str(user_id))
                save_processed_user(user_id)
                attempt_counter += 1
            continue

# تشغيل الـ Loop الخاص بتليجرام في خلفية مستقلة تماماً
threading.Thread(target=start_async_loop, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
