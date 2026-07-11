import os
import sys
import time
import random
import asyncio
import threading
from flask import Flask
from telethon.sync import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest, GetParticipantsRequest
from telethon.tl.functions.messages import AddChatUserRequest
from telethon.tl.types import ChannelParticipantsSearch
from telethon.errors.rpcerrorlist import PeerFloodError, UserPrivacyRestrictedError

sys.stdout.reconfigure(line_buffering=True)

app = Flask(__name__)

@app.route('/')
def home():
    return "Target Multi-Adder is Active, Running with Smart Filters and Target 1000!"

# --- بيانات التفعيل الثابتة الخاصة بك ---
api_id = 30239790  
api_hash = '2bb90bba711403595cec91e69479a976'  
phone = '+213771538043'  

client = TelegramClient('render_session_v1', api_id, api_hash)

# 📝 ملف حفظ الأعضاء المفحوصين لضمان عدم التكرار نهائياً
PROCESSED_USERS_FILE = "processed_users.txt"
# 🔢 الهدف النهائي لعدد الأعضاء المضافين بنجاح
TARGET_SUCCESS_COUNT = 1000

def load_processed_users():
    if os.path.exists(PROCESSED_USERS_FILE):
        with open(PROCESSED_USERS_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_processed_user(user_id):
    with open(PROCESSED_USERS_FILE, "a") as f:
        f.write(f"{user_id}\n")

def run_telegram_bot():
    print("📢 [THREAD] بدء تشغيل سكربت سحب الأعضاء الذكي والمطور...")
    time.sleep(3)
    try:
        loop = client.loop
        loop.run_until_complete(mass_scaler_process())
    except Exception as e:
        print(f"❌ [CRITICAL ERROR]: {e}")

async def mass_scaler_process():
    print("⏳ جاري فحص الاتصال بالجلسة السحابية...")
    await client.connect()
    
    if not await client.is_user_authorized():
        print("❌ ملف الجلسة غير صالح!")
        return

    print("✅ متصل بنجاح بالجلسة المستقرة!")
    
    # تحميل الحسابات التي تم التعامل معها سابقاً لمنع التكرار
    processed_users = load_processed_users()
    print(f"📦 تم تحميل {len(processed_users)} عضو مضاف/مخطى سابقاً لتفادي تكرارهم.")

    target_group = 'https://t.me/usdtalg' 
    my_group = 'actechup' 

    # العداد العام للإضافات الناجحة عبر كل الدورات
    total_success_added = 0

    # 🔄 حلقة تكرار لانهائية تستمر حتى نصل إلى 1000 عضو مضاف بنجاح
    while total_success_added < TARGET_SUCCESS_COUNT:
        try:
            print(f"\n📬 [دورة جديدة] الإجمالي الحالي المضاف بنجاح: ({total_success_added}/{TARGET_SUCCESS_COUNT})")
            print(f"📡 جاري الاتصال بالجروب المستهدف وجلب دفعة عشوائية...")
            
            group_entity = await client.get_entity(target_group)
            my_group_entity = await client.get_entity(my_group)

            # ميزة 1: توليد إزاحة عشوائية في كل دورة لتغطية الجروب بالكامل وتجنب التكرار من المنبع
            random_offset = random.randint(0, 1500)
            
            # جلب دفعة مكونة من 150 عضو بناءً على الإزاحة العشوائية
            participants = await client(GetParticipantsRequest(
                group_entity, ChannelParticipantsSearch(''), offset=random_offset, limit=150, hash=0
            ))
            
            users = participants.users
            if not users:
                print("⚠️ لم يتم العثور على أعضاء في هذه الإزاحة، استراحة دقيقة...")
                await asyncio.sleep(60)
                continue

            # ميزة 2: خلط قائمة الأعضاء المسحوبة عشوائياً لزيادة الأمان البشري
            random.shuffle(users)
            print(f"🚀 تم جلب {len(users)} عضو بإزاحة ({random_offset}). بدء التصفية والنقل...")

            for user in users:
                # التحقق أولاً: هل وصلنا للهدف تماماً؟
                if total_success_added >= TARGET_SUCCESS_COUNT:
                    break

                if user.bot or user.deleted:
                    continue
                    
                # ميزة 3: الفلترة السريعة ومنع التكرار (تخطي بدون الاتصال بتليجرام لحماية الحساب)
                if str(user.id) in processed_users:
                    continue
                    
                user_display = f"@{user.username}" if user.username else f"ID: {user.id}"
                print(f"👤 محاولة نقل العضو: {user_display}")
                
                try:
                    user_to_add = await client.get_input_entity(user.id)
                    success_in_this_user = False
                    
                    # 🌟 تجربة الطريقة الأولى: Supergroup
                    try:
                        await client(InviteToChannelRequest(my_group_entity, [user_to_add]))
                        success_in_this_user = True
                        print(f"👍 [نجاح الطريقة 1] تمت إضافة {user_display}!")
                    except Exception as e1:
                        # إذا فشلت الأولى نجرب الطريقة الثانية للمجموعات العادية
                        try:
                            await client(AddChatUserRequest(chat_id=my_group_entity.id, user_id=user_to_add, fwd_limit=0))
                            success_in_this_user = True
                            print(f"👍 [نجاح بالطريقة 2] تمت إضافة {user_display}!")
                        except Exception as e2:
                            # إذا فشلت الطريقتان معاً نسجله كمفحوص لتجنب إضاعة الوقت عليه لاحقاً
                            print(f"🔒 تخطي ذكي لـ {user_display} بسبب قيود تليجرام أو الخصوصية.")
                            processed_users.add(str(user.id))
                            save_processed_user(user.id)
                            await asyncio.sleep(1)

                    if success_in_this_user:
                        total_success_added += 1
                        print(f"📈 إجمالي المضافين بنجاح حتى الآن: {total_success_added}/{TARGET_SUCCESS_COUNT}")
                        
                        # تسجيل العضو بنجاح لمنع العودة إليه
                        processed_users.add(str(user.id))
                        save_processed_user(user.id)
                        
                        # ميزة 4: وقت الأمان الثابت والذكي لحماية رقم الهاتف من الحظر
                        time.sleep(45)

                except PeerFloodError:
                    print("❌ حظر مؤقت (Flood) من تليجرام، نوم عميق لحماية رقمك لمدة ساعتين...")
                    time.sleep(7200)
                except UserPrivacyRestrictedError:
                    print(f"⚠️ تخطي: {user_display} يغلق إعدادات الخصوصية.")
                    processed_users.add(str(user.id))
                    save_processed_user(user.id)
                except Exception as e:
                    print(f"⚠️ تخطي {user_display} لسبب آخر: {e}")
                    processed_users.add(str(user.id))
                    save_processed_user(user.id)
                    continue

            # إذا تم تحقيق الهدف نكسر الحلقة الكبيرة وننهي السكربت
            if total_success_added >= TARGET_SUCCESS_COUNT:
                break

            # ميزة 5: استراحة ذكية بين دورات السحب لتهدئة الجلسة تماماً
            print(f"🏁 انتهت الدورة الحالية بنجاح. المحصلة الحالية: {total_success_added} عضو ناجح.")
            print("🛌 السكربت سيستريح لمدة 10 دقائق ثم يسحب دفعة جديدة تلقائياً...")
            time.sleep(600)

        except Exception as e:
            print(f"🚨 خطأ عام في الدورة الحالية: {e}. إعادة المحاولة بعد دقيقة...")
            time.sleep(60)

    print(f"🎉 مبارك يا عبد القادر! تم الوصول إلى الهدف النهائي بنجاح وتم نقل {TARGET_SUCCESS_COUNT} عضو إلى مجموعتك دون أي تكرار. السكربت سيتوقف الآن بسلام.")

threading.Thread(target=run_telegram_bot, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
