import os
import sys
import time
import threading
from flask import Flask
from telethon.sync import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.functions.messages import AddChatUserRequest

# إجبار بايثون على إظهار جمل الطباعة فوراً في سيرفر Render
sys.stdout.reconfigure(line_buffering=True)

app = Flask(__name__)

@app.route('/')
def home():
    return "Testing Single Member Addition to AC_Tech..."

# --- بيانات التفعيل الخاصة بك ---
api_id = 30239790  
api_hash = '2bb90bba711403595cec91e69479a976'  
phone = '+213771538043'  

client = TelegramClient('render_session_v1', api_id, api_hash)

def run_telegram_bot():
    print("📢 [TEST] بدء اختبار إضافة عضو واحد إلى AC_Tech...")
    time.sleep(3)
    try:
        loop = client.loop
        loop.run_until_complete(test_flexible_addition())
    except Exception as e:
        print(f"❌ [CRITICAL ERROR]: {e}")

async def test_flexible_addition():
    print("⏳ جاري الاتصال بتليجرام والتحقق من الجلسة...")
    await client.connect()
    
    if not await client.is_user_authorized():
        print("❌ ملف الجلسة غير صالح أو يتطلب إعادة تفعيل!")
        return

    print("✅ متصل بنجاح!")
    my_group_link = 'https://t.me/actechup' # رابط مجموعتك العام
    
    # 🔥 ضع هنا يوزر حساب حقيقي آخر للتجربة (بدون علامة @ واحرص أن لا يكون بالجروب حالياً)
    test_user = 'Aek_tech' 

    print(f"🎯 جلب بيانات العضو @{test_user} وبيانات المجموعة...")
    group_entity = await client.get_entity(my_group_link)
    user_entity = await client.get_input_entity(test_user)
    
    # 🌟 المحاولة الأولى: التعامل كـ Supergroup (مجموعات عامة مطورة)
    try:
        print("🔄 محاولة الإضافة بالطريقة الأولى (Supergroup)...")
        await client(InviteToChannelRequest(group_entity, [user_entity]))
        print(f"🎉 [نجاح مؤكد] تمت إضافة @{test_user} بالطريقة الأولى كـ Supergroup!")
        return
    except Exception as e1:
        print(f"⚠️ الطريقة الأولى لم تنجح بسبب: {e1}")
        
    # 🌟 المحاولة الثانية: التعامل كـ Normal Group (مجموعات عادية وجديدة)
    try:
        print("🔄 محاولة الإضافة بالطريقة الثانية (Normal Group)...")
        await client(AddChatUserRequest(
            chat_id=group_entity.id,
            user_id=user_entity,
            fwd_limit=0
        ))
        print(f"🎉 [نجاح مؤكد] تمت إضافة @{test_user} بالطريقة الثانية كـ Normal Group!")
        return
    except Exception as e2:
        print(f"❌ فشلت الطريقتان بالكامل. السبب الأخير: {e2}")

# تشغيل الفحص في الخلفية
threading.Thread(target=run_telegram_bot, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
