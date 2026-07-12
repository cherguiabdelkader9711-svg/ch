import os
import sys
import time
import json
import csv
import asyncio
import threading
import re
from flask import Flask
from telethon import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest
from telethon.errors import FloodWaitError, UserPrivacyRestrictedError, PeerIdInvalidError

sys.stdout.reconfigure(line_buffering=True)

app = Flask(__name__)

@app.route('/')
def home():
    return "<h1>Advanced CSV Adder Engine is Fully Active!</h1>"

# تحميل الإعدادات الثابتة الخاصة بك
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

# دالة ذكية مرنة متوافقة تماماً مع بنية ملف الأعضاء المجموع
def load_target_members_from_csv():
    members_list = []
    if not os.path.exists(CSV_FILE):
        print(f"❌ ملف الأعضاء {CSV_FILE} غير موجود في المجلد الحالي!")
        return members_list

    with open(CSV_FILE, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
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
        print(f"❌ [CRITICAL ENGINE ERROR]: {e}")

async def core_adder_process():
    print(f"⏳ [SYSTEM] جاري بدء المحرك واستدعاء الجلسة المستقرة {SESSION_FILE}...")
    client = TelegramClient(SESSION_FILE, api_id, api_hash, receive_updates=False)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("❌ [Fatal Error] ملف الجلسة السحابية غير فعال أو يحتاج لإعادة توثيق.")
        return

    print("✅ تم ربط محرك الإضافة بالجلسة بنجاح!")
    
    # محاولة الانضمام للجروب المستهدف تلقائياً بالحساب إن لم يكن منضماً
    try:
        await client(JoinChannelRequest(group_target))
    except Exception:
        pass

    processed_users = load_processed_users()
    users_to_add = load_target_members_from_csv()
    print(f"📦 تم تحميل ({len(users_to_add)}) عضو جاهز للمعالجة من ملف CSV.")

    for user in users_to_add:
        user_id = user['user_id']
        username = user['username']

        # تخطي الأعضاء الذين تمت محاولتهم مسبقاً لحفظ الوقت والجهد
        if str(user_id) in processed_users:
            continue

        user_display = f"@{username}" if username else f"ID: {user_id}"
        print(f"👤 جاري النقل الذكي للعضو: {user_display}")

        try:
            my_group_entity = await client.get_entity(group_target)
            
            # محاولة جلب الكيان البرمجي بناءً على ما تم مواجهته في الجلسة أو اليوزر
            if username:
                user_peer = await client.get_input_entity(username)
            else:
                user_peer = await client.get_input_entity(int(user_id))
            
            # تنفيذ طلب الإضافة الفعلي للجروب الخاص بك
            await client(InviteToChannelRequest(my_group_entity, [user_peer]))
            print(f"👍 [نجاح تام] تم نقل {user_display} إلى المجموعة بنجاح!")
            
            processed_users.add(str(user_id))
            save_processed_user(user_id)
            
            # استراحة أمان ذكية وثابتة لمنع الحظر السريع للجروب والحساب
            await asyncio.sleep(40)

        except FloodWaitError as e:
            # معالجة حظر تليجرام المؤقت وإيقاف السكربت مؤقتاً لحماية الحساب
            print(f"🚨 [تنبيه Flood] تليجرام يطلب التوقف المؤقت لمدة {e.seconds} ثانية.")
            print("💤 السكربت يدخل في سبات آمن الآن ولن يفقد العضو الحالي أو يحرق القائمة...")
            await asyncio.sleep(e.seconds + 15)
            print("🔄 انتهت مدة الحظر المؤقت! جاري استئناف العمل على العضو الحالي...")
            continue

        except UserPrivacyRestrictedError:
            print(f"⚠️ تخطي: إعدادات الخصوصية للعضو {user_display} تمنع إضافته.")
            processed_users.add(str(user_id))
            save_processed_user(user_id)
            await asyncio.sleep(5)

        except (ValueError, PeerIdInvalidError):
            print(f"⚠️ تخطي: العضو {user_display} لا يمكن لتليجرام العثور عليه بدون الهاش الخاص به.")
            processed_users.add(str(user_id))
            save_processed_user(user_id)
            await asyncio.sleep(5)

        except Exception as e:
            error_msg = str(e)
            # احتياط إضافي إذا ظهر خطأ الـ Wait بصيغة نصية أخرى
            if "wait" in error_msg.lower():
                seconds_match = re.search(r'\d+', error_msg)
                wait_seconds = int(seconds_match.group()) if seconds_match else 3600
                print(f"🚨 [Flood كاشف نصي] نوم مؤقت لمدة {wait_seconds} ثانية.")
                await asyncio.sleep(wait_seconds + 10)
                continue
                
            print(f"❌ تعذر نقل {user_display} بسبب خطأ غير معروف: {error_msg}")
            processed_users.add(str(user_id))
            save_processed_user(user_id)
            await asyncio.sleep(5)

    print("🎉 تم إنهاء العمل على كامل الملف المرفوع بنجاح وتصفية الداتا.")

# تشغيل البوت التليجرامي في الخلفية لضمان عمل خادم ويب Flask
threading.Thread(target=run_telegram_bot, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
