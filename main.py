import os
import sys
import time
import json
import random
import asyncio
import threading
from datetime import datetime, timedelta
from flask import Flask, request, render_template_string
from telethon import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest, GetParticipantsRequest, JoinChannelRequest
from telethon.tl.types import ChannelParticipantsSearch, UserStatusRecently, UserStatusOffline

sys.stdout.reconfigure(line_buffering=True)

app = Flask(__name__)

# تخزين مؤقت لحالات تسجيل الدخول النشطة
auth_states = {}

# واجهة تحكم بسيطة لبيئة الويب لتمكينك من إدخال كود تليجرام عند الحاجة من المتصفح
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
            <label>1. إذا لم يصلك الكود بعد، اضغط لطلبه:</label>
            <button type="submit" name="action" value="send_code" style="background:#5cb85c; margin-bottom:20px;">طلب كود التحقق (SMS/Telegram)</button>
            
            <label>2. أدخل كود التحقق المستلم:</label>
            <input type="text" name="code" placeholder="أدخل الكود هنا...">
            <button type="submit" name="action" value="login">تأكيد تسجيل الدخول وتفعيل الجلسة</button>
        </form>
        
        {% if msg %}
        <div class="status">{{ msg }}</div>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    with open('config.json', 'r', encoding='utf-8') as f:
        cfg = json.loads(f.read())
    primary_phone = cfg['accounts'][0]
    return render_template_string(HTML_TEMPLATE, phone=primary_phone, msg=request.args.get('msg', ''))

@app.route('/verify', method=['POST'])
def verify():
    phone = request.form.get('phone')
    action = request.form.get('action')
    code = request.form.get('code')
    
    if action == 'send_code':
        asyncio.run_coroutine_threadsafe(trigger_send_code(phone), bot_loop)
        return render_template_string(HTML_TEMPLATE, phone=phone, msg="⏳ جاري إرسال الكود... تفقد تطبيق تليجرام الخاص بك.")
        
    elif action == 'login':
        if phone in auth_states:
            auth_states[phone]['code_to_submit'] = code
            return render_template_string(HTML_TEMPLATE, phone=phone, msg="⚙️ جاري معالجة الكود وتوثيق الجلسة، تفقد اللوج في Render للتحقق من الاتصال الحقيقي!")
            
    return render_template_string(HTML_TEMPLATE, phone=phone, msg="")

# --- إعداد المتغيرات الثابتة ---
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.loads(f.read())

api_id = int(config['api_id'])
api_hash = config['api_hash']
group_source = config['group_source']
group_target = config['group_target']
accounts = config['accounts']
PROCESSED_USERS_FILE = "processed_users.txt"
TARGET_SUCCESS_COUNT = 1000

bot_loop = asyncio.new_event_loop()

def load_processed_users():
    if os.path.exists(PROCESSED_USERS_FILE):
        with open(PROCESSED_USERS_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_processed_user(user_id):
    with open(PROCESSED_USERS_FILE, "a") as f:
        f.write(f"{user_id}\n")

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
        
        # حلقة انتظار ذكية تسمح لك بتسجيل الدخول من المتصفح دون انهيار السكربت
        while not await cli.is_user_authorized():
            print(f"⚠️ الحساب {phone} غير مفعل سحابياً. يرجى فتح رابط خدمة Render الخاص بك لإدخال الكود.")
            if auth_states[phone]['code_to_submit']:
                try:
                    current_code = auth_states[phone]['code_to_submit']
                    current_hash = auth_states[phone]['phone_code_hash']
                    await cli.sign_in(phone, code=current_code, phone_code_hash=current_hash)
                    print(f"✨ تم توثيق وتسجيل الدخول بنجاح للرقم {phone}!")
                    break
                except Exception as auth_err:
                    print(f"❌ خطأ أثناء إدخال الكود: {auth_err}")
                    auth_states[phone]['code_to_submit'] = None
            await asyncio.sleep(10)
            
        try:
            await cli(JoinChannelRequest(group_target))
        except Exception:
            pass
        clients.append({'phone': phone, 'client': cli})
        print(f"✅ الحساب {phone} جاهز تماماً وفي الخدمة النشطة!")

    processed_users = load_processed_users()
    total_success_added = 0
    attempt_counter = 0
    limit_date = datetime.now() - timedelta(days=7)

    while total_success_added < TARGET_SUCCESS_COUNT:
        if len(clients) == 0:
            print("🚨 [توقف فوري]: تم عزل كافة الحسابات النشطة.")
            break

        try:
            scrapper_account = clients[0]['client']
            group_entity = await scrapper_account.get_entity(group_source)
            random_offset = random.randint(0, 1500)
            
            participants = await scrapper_account(GetParticipantsRequest(
                group_entity, ChannelParticipantsSearch(''), offset=random_offset, limit=100, hash=0
            ))
            
            users = participants.users
            if not users:
                await asyncio.sleep(60)
                continue

            random.shuffle(users)

            for user in users:
                if total_success_added >= TARGET_SUCCESS_COUNT or len(clients) == 0:
                    break
                if user.bot or user.deleted or str(user.id) in processed_users:
                    continue

                is_active = False
                if isinstance(user.status, UserStatusRecently):
                    is_active = True
                elif isinstance(user.status, UserStatusOffline):
                    if user.status.was_online.replace(tzinfo=None) > limit_date:
                        is_active = True

                if not is_active:
                    continue

                current_index = attempt_counter % len(clients)
                active_worker = clients[current_index]
                cli_worker = active_worker['client']
                phone_worker = active_worker['phone']

                user_display = f"@{user.username}" if user.username else f"ID: {user.id}"
                print(f"👤 [الحساب: {phone_worker}] محاولة نقل العضو: {user_display}")

                try:
                    my_group_entity = await cli_worker.get_entity(group_target)
                    user_to_add = await cli_worker.get_input_entity(user.id)
                    
                    await cli_worker(InviteToChannelRequest(my_group_entity, [user_to_add]))
                    
                    total_success_added += 1
                    print(f"👍 [نجاح] أضاف {phone_worker} العضو {user_display}! المحصلة: {total_success_added}/{TARGET_SUCCESS_COUNT}")
                    
                    processed_users.add(str(user.id))
                    save_processed_user(user.id)
                    attempt_counter += 1
                    await asyncio.sleep(20)

                except Exception as e:
                    error_msg = str(e)
                    if "PEER_FLOOD" in error_msg:
                        print(f"❌ [حظر مؤقت] عزل الحساب {phone_worker}...")
                        try: await cli_worker.disconnect()
                        except Exception: pass
                        clients.remove(active_worker)
                    else:
                        processed_users.add(str(user.id))
                        save_processed_user(user.id)
                        attempt_counter += 1
                    continue

            print("睡 استراحة 5 دقائق لتبريد كافة الحسابات...")
            await asyncio.sleep(300)

        except Exception as e:
            print(f"🚨 خطأ في الـ Loop: {e}")
            await asyncio.sleep(60)

threading.Thread(target=run_telegram_bot, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
