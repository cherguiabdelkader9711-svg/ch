import os
import sys
import time
import json
import csv
import asyncio
import threading
from flask import Flask
from telethon import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest
from telethon.tl.types import InputPeerUser

sys.stdout.reconfigure(line_buffering=True)

app = Flask(__name__)

@app.route('/')
def home():
    return "<h1>CSV Adder Engine is Active and Running!</h1>"

# تحميل الإعدادات من الملف النصي المعرف
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.loads(f.read())

api_id = int(config['api_id'])
api_hash = config['api_hash']
group_target = config['group_target']

PROCESSED_USERS_FILE = "processed_users.txt"
CSV_FILE = "members.csv"
SESSION_FILE = "render_session_v1" # اسم ملف الجلسة المرفوع في مستودعك

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

def run_telegram_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(core_adder_process())
    except Exception as e:
        print(f"❌ [CRITICAL ERROR]: {e}")

async def core_adder_process():
    print(f"⏳ [SYSTEM] جاري محاولة فتح الجلسة السحابية المرفوعة {SESSION_FILE}...")
    
    # استخدام ملف الجلسة الموثق المرفوع مباشرة لمنع أخطاء التعبئة
    client = TelegramClient(SESSION_FILE, api_id, api_hash, receive_updates=False)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("❌ [Fatal Error] ملف الجلسة render_session_v1 غير صالح أو انتهت صلاحيته. يرجى تجديده محلياً.")
        return

    print("✅ تم الاتصال بنجاح وتوثيق الحساب السحابي المرفوع!")
    
    try:
        await client(JoinChannelRequest(group_target))
    except Exception:
        pass

    processed_users = load_processed_users()
    users_to_add = load_target_members_from_csv()
    print(f"📦 تم قراءة جدول الـ CSV: العثور على ({len(users_to_add)}) عضو جاهز للإضافة.")

    attempt_counter = 0

    for user in users_to_add:
        user_id = user['user_id']
        access_hash = user['access_hash']
        username = user['username']

        if str(user_id) in processed_users:
            continue

        user_display = f"@{username}" if username else f"ID: {user_id}"
        print(f"👤 جاري محاولة نقل العضو: {user_display}")

        try:
            my_group_entity = await client.get_entity(group_target)
            
            if user_id.isdigit() and access_hash.isdigit() and access_hash != '0':
                user_peer = InputPeerUser(int(user_id), int(access_hash))
            else:
                user_peer = await client.get_input_entity(username if username else user_id)
            
            await client(InviteToChannelRequest(my_group_entity, [user_peer]))
            print(f"👍 [نجاح] تم إضافة {user_display} إلى مجموعتك بنجاح!")
            
            processed_users.add(str(user_id))
            save_processed_user(user_id)
            
            # فترة الانتظار الآمنة لحماية الحساب من الحظر (30 ثانية)
            await asyncio.sleep(30)

        except Exception as e:
            error_msg = str(e)
            print(f"⚠️ تعذر نقل العضو بسبب: {error_msg}")
            
            if "PEER_FLOOD" in error_msg:
                print("🚨 الحساب تلقى حظراً مؤقتاً (Flood). يتوقف السكربت مؤقتاً لحماية الحساب.")
                break
                
            processed_users.add(str(user_id))
            save_processed_user(user_id)
            await asyncio.sleep(5)
            continue

    print("🎉 تم الانتهاء من العمل على الملف بالكامل.")

# تشغيل البوت في الخلفية للحفاظ على خادم الويب متصلاً
threading.Thread(target=run_telegram_bot, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
