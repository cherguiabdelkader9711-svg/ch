import os
import sys
import time
import threading
from flask import Flask
from telethon.sync import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest

sys.stdout.reconfigure(line_buffering=True)

app = Flask(__name__)

@app.route('/')
def home():
    return "Testing Single Member Addition..."

# --- بيانات التفعيل ---
api_id = 30239790  
api_hash = '2bb90bba711403595cec91e69479a976'  
phone = '+213771538043'  

client = TelegramClient('render_session_v1', api_id, api_hash)

def run_telegram_bot():
    print("📢 [TEST] بدء اختبار إضافة عضو واحد مستهدف...")
    time.sleep(3)
    try:
        loop = client.loop
        loop.run_until_complete(test_single_addition())
    except Exception as e:
        print(f"❌ [CRITICAL ERROR]: {e}")

async def test_single_addition():
    print("⏳ جاري الاتصال بتليجرام...")
    await client.connect()
    
    if not await client.is_user_authorized():
        print("❌ ملف الجلسة غير صالح!")
        return

    print("✅ متصل بنجاح!")
    my_group = 'actechup' # مجموعتك العامة
    
    # 🔥 ضع هنا يوزر حساب حقيقي للتجربة (تأكد أنه ليس منضم للجروب حالياً)
    # يمكنك كتابة اليوزر الخاص بحسابك الثاني أو أي شخص بدون علامة @
    test_user = 'Aek_tech' 

    print(f"🎯 محاولة إضافة العضو المستهدف: @{test_user} إلى المجموعة {my_group}...")
    
    try:
        group_entity = await client.get_entity(my_group)
        user_entity = await client.get_input_entity(test_user)
        
        # أمر الإضافة الفعلي
        await client(InviteToChannelRequest(group_entity, [user_entity]))
        print(f"🎉 [نجاح مؤكد] تمت إضافة @{test_user} برمجياً وسيرفر تليجرام وافق على العملية!")
        
    except Exception as e:
        print(f"❌ فشلت الإضافة بسبب القيود التالية: {e}")

# تشغيل الفحص في الخلفية
threading.Thread(target=run_telegram_bot, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
