import os
import csv
import time
import threading
from flask import Flask
from telethon.sync import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest, GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsSearch, InputPeerChannel
from telethon.errors.rpcerrorlist import PeerFloodError, UserPrivacyRestrictedError

# --- إعداد سيرفر الويب لتفادي إغلاق Render للمشروع ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Telegram Adder Bot is Running Perfectly on Render 24/7!"

# --- بيانات المطور والرقم الجزائري الجديد المحدث ---
api_id = 30239790  
api_hash = '2bb90bba711403595cec91e69479a976'  
phone = '+213771538043'  

# الاتصال باستخدام ملف الجلسة render_session_v1 المرفوع مسبقاً
client = TelegramClient('render_session_v1', api_id, api_hash)

def run_telegram_bot():
    time.sleep(10) # انتظار ثوانٍ حتى يستقر السيرفر السحابي
    loop = client.loop
    loop.run_until_complete(worker_process())

async def worker_process():
    print("⏳ جاري الاتصال بتليجرام باستخدام ملف الجلسة السحابي والبيانات الجديدة...")
    await client.connect()
    if not await client.is_user_authorized():
        print("❌ خطأ: ملف الجلسة الحالي غير متوافق مع البيانات الجديدة أو يتطلب إعادة توليد.")
        return

    target_group = 'https://t.me/usdtalg' # المجموعة المراد السحب منها
    my_group = 'tech_ac1' # مجموعتك الشخصية المستهدفة

    print("📬 جاري جلب عينة من أعضاء جروب usdtalg...")
    group = await client.get_entity(target_group)
    my_group_entity = await client.get_entity(my_group)
    input_group = InputPeerChannel(my_group_entity.id, my_group_entity.access_hash)

    # سحب أول 200 عضو للبدء بالنقل التدريجي الآمن
    participants = await client(GetParticipantsRequest(group, ChannelParticipantsSearch(''), offset=0, limit=200, hash=0))
    
    print(f"🚀 بدء نقل {len(participants.users)} عضو تدريجياً في الخلفية...")
    for user in participants.users:
        if user.bot:
            continue
        try:
            print(f"👤 محاولة إضافة العضو: {user.id}")
            user_to_add = await client.get_input_entity(user.id)
            await client(InviteToChannelRequest(input_group, [user_to_add]))
            print("👍 تمت الإضافة بنجاح!")
            time.sleep(45) # الانتظار الآمن لحماية الحساب من الحظر
        except PeerFloodError:
            print("❌ حظر مؤقت (Flood)، نوم عميق للكود لمدة ساعتين لحماية الحساب...")
            time.sleep(7200)
        except UserPrivacyRestrictedError:
            print("⚠️ تخطي: إعدادات خصوصية العضو تمنع إضافته.")
        except Exception as e:
            print(f"⚠️ تخطي بسبب: {e}")
            continue

# تشغيل كود تليجرام في خلفية سيرفر الويب (Background Thread)
threading.Thread(target=run_telegram_bot, daemon=True).start()

if __name__ == '__main__':
    # تشغيل السيرفر على البورت المطلوب من منصة Render تلقائياً
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
