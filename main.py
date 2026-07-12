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

sys.stdout.reconfigure(line_buffering=True)

app = Flask(__name__)

@app.route('/')
def home():
    return "<h1>CSV Adder Engine is Active and Running!</h1>"

# تحميل الإعدادات
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.loads(f.read())

api_id = int(config['api_id'])
api_hash = config['api_hash']
group_target = config['group_target']

PROCESSED_USERS_FILE = "processed_users.txt"
CSV_FILE = "members.csv"
SESSION_FILE = "render_session_v1"

def load_processed_users():
    if os.path.exists(PROCESSED_USERS_FILE):
        with open(PROCESSED_USERS_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_processed_user(user_id):
    with open(PROCESSED_USERS_FILE, "a") as f:
        f.write(f"{user_id}\n")

# دالة مخصصة لملفك الحالي لقراءة الـ ID والـ Username بدقة
def load_target_members_from_csv():
    members_list = []
    if not os.path.exists(CSV_FILE):
        print(f"❌ ملف {CSV_FILE} غير موجود في المجلد الرئيسي!")
        return members_list

    with open(CSV_FILE, mode='r', encoding='utf-8-sig') as f:
        # قراءة الملف كـ DictReader بناءً على الهيدر الحالي (ID, Username)
        reader = csv.DictReader(f)
        
        for row in reader:
            # جلب البيانات مع تنظيف الفراغات
            u_id = row.get('ID') or row.get('id')
            u_name = row.get('Username') or row.get('username') or ''
            
            if u_id:
                members_list.append({
                    'user_id': u_id.strip(),
                    'username': u_name.strip()
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
    
    client = TelegramClient(SESSION_FILE, api_id, api_hash, receive_updates=False)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("❌ [Fatal Error] ملف الجلسة render_session_v1 غير فعال أو انتهت صلاحيته.")
        return

    print("✅ تم الاتصال بنجاح وتوثيق الحساب السحابي المرفوع!")
    
    try:
        await client(JoinChannelRequest(group_target))
    except Exception:
        pass

    processed_users = load_processed_users()
    users_to_add = load_target_members_from_csv()
    print(f"📦 تم قراءة ملف الـ CSV بنجاح: العثور على ({len(users_to_add)}) عضو جاهز للإضافة.")

    if not users_to_add:
        print("⚠️ لا توجد داتا صالحة للإضافة بداخل الملف. يتوقف النظام.")
        return

    for user in users_to_add:
        user_id = user['user_id']
        username = user['username']

        if str(user_id) in processed_users:
            continue

        # تحديد طريقة الاستدعاء: نفضل اليوزر نيم لضمان تخطي حماية الـ Access Hash
        user_display = f"@{username}" if username else f"ID: {user_id}"
        print(f"👤 جاري محاولة نقل العضو: {user_display}")

        try:
            my_group_entity = await client.get_entity(group_target)
            
            # جلب الكيان البرمجي للعضو بناءً على اليوزر نيم أولاً أو الآيدي
            if username:
                user_peer = await client.get_input_entity(username)
            else:
                user_peer = await client.get_input_entity(int(user_id))
            
            await client(InviteToChannelRequest(my_group_entity, [user_peer]))
            print(f"👍 [نجاح] تم إضافة {user_display} بنجاح!")
            
            processed_users.add(str(user_id))
            save_processed_user(user_id)
            
            # استراحة أمان 35 ثانية لحماية حسابك وجروبك من الحظر السريع
            await asyncio.sleep(35)

        except Exception as e:
            error_msg = str(e)
            print(f"⚠️ تعذر نقل العضو بسبب: {error_msg}")
            
            if "PEER_FLOOD" in error_msg:
                print("🚨 الحساب تلقى حظراً مؤقتاً (Flood). يتوقف السكربت تلقائياً لحماية الحساب.")
                break
                
            processed_users.add(str(user_id))
            save_processed_user(user_id)
            await asyncio.sleep(5)
            continue

    print("🎉 تم الانتهاء من العمل على الملف بالكامل.")

# تشغيل البوت في الخلفية ليبقى سيرفر Flask مستقراً
threading.Thread(target=run_telegram_bot, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
