import os
import sys
import time
import random
import asyncio
import threading
import json
from flask import Flask
from telethon import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest, GetParticipantsRequest, JoinChannelRequest
from telethon.tl.functions.messages import AddChatUserRequest
from telethon.tl.types import ChannelParticipantsSearch
from telethon.errors.rpcerrorlist import FloodWaitError, UserPrivacyRestrictedError, PeerFloodError

sys.stdout.reconfigure(line_buffering=True)

app = Flask(__name__)

@app.route('/')
def home():
    return "<h1>Target Multi-Adder Pro is Active with Real-Time Validation!</h1>"

# --- بيانات التفعيل الثابتة المستقرة الخاصة بك ---
api_id = 30239790  
api_hash = '2bb90bba711403595cec91e69479a976'  
SESSION_FILE = 'render_session_v1'

PROCESSED_USERS_FILE = "processed_users.txt"
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
    # إنشاء Loop نقي متوافق تماماً مع البيئة السحابية بدون تجميد السيرفر
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(mass_scaler_process())
    except Exception as e:
        print(f"❌ [CRITICAL ENGINE ERROR]: {e}")

async def mass_scaler_process():
    print("⏳ [SYSTEM] جاري فحص الاتصال بالجلسة السحابية المستقرة...")
    client = TelegramClient(SESSION_FILE, api_id, api_hash, receive_updates=False)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("❌ [Fatal] ملف الجلسة غير فعال أو انتهت صلاحيته!")
        return

    print("✅ متصل بنجاح وموثق بالكامل!")
    
    processed_users = load_processed_users()
    print(f"📦 تم تحميل {len(processed_users)} عضو من الأرشيف لتفادي التكرار.")

    target_group = 'https://t.me/usdtalg' 
    my_group = 'actechup' 

    total_success_added = 0

    # 🏁 حلقة التكرار الذكية القائمة على المتابعة الحية
    while total_success_added < TARGET_SUCCESS_COUNT:
        try:
            print(f"\n📬 [دورة جديدة] الإجمالي الفعلي المؤكد: ({total_success_added}/{TARGET_SUCCESS_COUNT})")
            
            group_entity = await client.get_entity(target_group)
            my_group_entity = await client.get_entity(my_group)
            
            # جلب العدد الأولي الحالي للمجموعة قبل المحاولة للتأكد من الزيادة الفعلية
            initial_count = my_group_entity.participants_count if hasattr(my_group_entity, 'participants_count') else 0
            if initial_count == 0:
                # تحديث الكيان لضمان قراءة العدد
                my_group_entity = await client.get_entity(my_group)
                initial_count = my_group_entity.participants_count or 0

            random_offset = random.randint(0, 1500)
            print(f"📡 جاري جلب دفعة عشوائية بإزاحة ({random_offset})...")

            participants = await client(GetParticipantsRequest(
                group_entity, ChannelParticipantsSearch(''), offset=random_offset, limit=100, hash=0
            ))
            
            users = participants.users
            if not users:
                print("⚠️ لم نجد أعضاء في هذه الإزاحة، استراحة دقيقتين...")
                await asyncio.sleep(120)
                continue

            random.shuffle(users)

            for user in users:
                if total_success_added >= TARGET_SUCCESS_COUNT:
                    break

                if user.bot or user.deleted:
                    continue
                    
                if str(user.id) in processed_users:
                    continue
                    
                user_display = f"@{user.username}" if user.username else f"ID: {user.id}"
                print(f"👤 محاولة نقل: {user_display}")
                
                try:
                    user_to_add = await client.get_input_entity(user.id)
                    
                    # محاولة الإضافة بالطريقة الأولى القياسية للـ Supergroups
                    await client(InviteToChannelRequest(my_group_entity, [user_to_add]))
                    
                    # 🔍 [الفحص الصارم الحاسم]: التحقق الفوري هل ارتفع العدد بالجروب أم الإضافة وهمية؟
                    await asyncio.sleep(3) # استراحة قصيرة لتحديث بيانات تليجرام
                    check_group = await client.get_entity(my_group)
                    new_count = check_group.participants_count or 0
                    
                    if new_count > initial_count:
                        # زيادة فعلية حقيقية بالجروب!
                        total_success_added += 1
                        initial_count = new_count # تحديث المؤشر للدورة القادمة
                        print(f"👍 [نجاح حقيقي مؤكد] تمت إضافة {user_display}! العدد الحالي بالمجموعة أصبح: {new_count}")
                        
                        processed_users.add(str(user.id))
                        save_processed_user(user.id)
                        
                        # استراحة الأمان الحقيقية بين الإضافات الناجحة
                        await asyncio.sleep(45)
                    else:
                        # تليجرام خدع السkربت ولم يضف العضو حقيقةً (Shadow Ban)
                        print(f"⚠️ [إضافة وهمية المظهر] تليجرام رفض النقل الفعلي لـ {user_display} (حظر صامت للحساب).")
                        print("💤 سيقوم السكربت بالنوم لمدة 20 دقيقة لتفادي قفل الحساب نهائياً...")
                        await asyncio.sleep(1200) 
                        break # كسر حلقة الأعضاء الحالية لتغيير الإزاحة وتبريد الجلسة

                except FloodWaitError as e:
                    print(f"❌ حظر مؤقت حاد (FloodWait). يجب النوم التام لمدة {e.seconds} ثانية.")
                    await asyncio.sleep(e.seconds + 10)
                    break
                except PeerFloodError:
                    print("❌ خطأ PeerFlood (إساءة استخدام). النوم لمدة ساعة لحماية الرقم...")
                    await asyncio.sleep(3600)
                    break
                except UserPrivacyRestrictedError:
                    print(f"🔒 تخطي: إعدادات الخصوصية للمستخدم {user_display} تمنع إضافته.")
                    processed_users.add(str(user.id))
                    save_processed_user(user.id)
                    await asyncio.sleep(2)
                except Exception as e:
                    print(f"⚠️ تخطي {user_display} بسبب خطأ عادي: {e}")
                    processed_users.add(str(user.id))
                    save_processed_user(user.id)
                    await asyncio.sleep(2)

            # استراحة أمان ذكية ممتازة ومجربة بين الدفعات الكبيرة
            print(f"🏁 انتهت المعالجة الحالية. السبات المؤقت لمدة 5 دقائق لتبريد الجلسة...")
            await asyncio.sleep(300)

        except Exception as e:
            print(f"🚨 خطأ عام في الدورة الرئيسية: {e}. إعادة المحاولة بعد دقيقة...")
            await asyncio.sleep(60)

    print(f"🎉 تم الوصول للهدف المؤكد المكون من {TARGET_SUCCESS_COUNT} عضو حقيقي داخل مجموعتك!")

# إطلاق الخيط البرمجي المستقل بالتوازي مع الـ Web server
threading.Thread(target=run_telegram_bot, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
