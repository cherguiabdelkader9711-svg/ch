import os
import sys
import time
import threading
from flask import Flask
from telethon.sync import TelegramClient
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsSearch
from telethon.errors.rpcerrorlist import PeerFloodError, UserPrivacyRestrictedError

# إجبار بايثون على إظهار جمل الطباعة فوراً في سيرفر Render
sys.stdout.reconfigure(line_buffering=True)

app = Flask(__name__)

@app.route('/')
def home():
    return "Telegram Invitation Bot is Running Perfectly on Render 24/7!"

# --- بيانات المطور والرقم الجزائري المستقر ---
api_id = 30239790  
api_hash = '2bb90bba711403595cec91e69479a976'  
phone = '+213771538043'  

client = TelegramClient('render_session_v1', api_id, api_hash)

def run_telegram_bot():
    print("📢 [THREAD] تم بدء تشغيل خيط بايثون الخلفي لإرسال الدعوات...")
    time.sleep(5) 
    try:
        loop = client.loop
        loop.run_until_complete(worker_process())
    except Exception as e:
        print(f"❌ [CRITICAL ERROR]: {e}")

async def worker_process():
    print("⏳ جاري الاتصال بتليجرام والتحقق من الجلسة السحابية...")
    await client.connect()
    
    if not await client.is_user_authorized():
        print("❌ خطأ: ملف الجلسة غير صالح أو يتطلب إعادة تفعيل محلي!")
        return

    print("✅ تم الاتصال بنجاح!")
    target_group = 'https://t.me/usdtalg' # المجموعة المراد سحب الأعضاء منها
    my_channel_link = 'https://t.me/tech_ac1' # رابط قناتك التي تروج لها

    # نص رسالة الدعوة الاحترافية (يمكنك تعديلها كما تحب)
    invitation_message = f"""مرحباً بك يا غالي 🌹

ندعوك للانضمام إلى قناتنا الرسمية المهتمة بالتقنية والعمل على الإنترنت:
👉 {my_channel_link}

تشرفنا متابعتك وثقتك! 🚀"""

    print("📬 جاري جلب أعضاء جروب usdtalg لإرسال الدعوات لهم...")
    group = await client.get_entity(target_group)
    participants = await client(GetParticipantsRequest(group, ChannelParticipantsSearch(''), offset=0, limit=200, hash=0))
    
    print(f"🚀 بدء إرسال الرسائل إلى {len(participants.users)} عضو تدريجياً...")
    for user in participants.users:
        if user.bot or user.deleted:
            continue
        try:
            print(f"📩 محاولة إرسال رسالة دعوة للعضو: {user.id}")
            await client.send_message(user.id, invitation_message)
            print(f"👍 تم إرسال الدعوة بنجاح للعضو {user.id}!")
            time.sleep(60) # انتظار دقيقة كاملة بين كل رسالة لسلامة الحساب
        except PeerFloodError:
            print("❌ حظر مؤقت من الإرسال (Flood)، نوم عميق للكود لمدة ساعتين لحماية الرقم...")
            time.sleep(7200)
        except UserPrivacyRestrictedError:
            print("⚠️ تخطي: إعدادات خصوصية العضو تمنع استقبال الرسائل من الغرباء.")
        except Exception as e:
            print(f"⚠️ تخطي بسبب: {e}")
            continue

# تشغيل الكود في الخلفية
threading.Thread(target=run_telegram_bot, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
