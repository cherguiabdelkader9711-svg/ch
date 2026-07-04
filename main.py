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

# --- كود تليجرام الرئيسي ---
api_id = 30824004  
api_hash = 'c34f61846549444725508b5ea5a2f3fb'  
phone = '+213771538043'  

# نستخدم ملف جلسة ثابت
client = TelegramClient('render_session_v1', api_id, api_hash)

def run_telegram_bot():
    time.sleep(10) # انتظار ثوانٍ حتى يستقر السيرفر
    loop = client.loop
    loop.run_until_complete(worker_process())

async def worker_process():
    await client.connect()
    if not await client.is_user_authorized():
        print("❌ الحساب يحتاج تفعيل! يجب تشغيله محلياً مرة واحدة أولاً لإنشاء ملف الجلسة.")
        return

    target_group = 'https://t.me/usdtalg' # المجموعة المراد السحب منها
    my_group = 'tech_ac1' # مجموعتك

    print("📬 جاري تحديث سحب الأعضاء...")
    group = await client.get_entity(target_group)
    my_group_entity = await client.get_entity(my_group)
    input_group = InputPeerChannel(my_group_entity.id, my_group_entity.access_hash)

    # سحب عينة من الأعضاء
    participants = await client(GetParticipantsRequest(group, ChannelParticipantsSearch(''), offset=0, limit=200, hash=0))
    
    print(f"🚀 بدء نقل {len(participants.users)} عضو تدريجياً...")
    for user in participants.users:
        if user.bot:
            continue
        try:
            print(f"👤 محاولة إضافة العضو: {user.id}")
            user_to_add = await client.get_input_entity(user.id)
            await client(InviteToChannelRequest(input_group, [user_to_add]))
            print("👍 تمت الإضافة بنجاح!")
            time.sleep(45) # الانتظار الآمن
        except PeerFloodError:
            print("❌ حظر مؤقت (Flood)، نوم عميق للكود لمدة ساعتين...")
            time.sleep(7200)
        except UserPrivacyRestrictedError:
            print("⚠️ تخطي: خصوصية العضو مغلقة.")
        except Exception as e:
            print(f"⚠️ تخطي بسبب خطأ: {e}")
            continue

# تشغيل كود تليجرام في خلفية سيرفر الويب (Background Thread)
threading.Thread(target=run_telegram_bot, daemon=True).start()

if __name__ == '__main__':
    # تشغيل السيرفر على البورت المطلوب من Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
