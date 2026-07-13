import os
import sys
import time
import random
import asyncio
import threading
from flask import Flask
from telethon import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest, GetParticipantsRequest, JoinChannelRequest
from telethon.tl.types import ChannelParticipantsSearch
from telethon.errors.rpcerrorlist import FloodWaitError, UserPrivacyRestrictedError, PeerFloodError, PeerIdInvalidError

sys.stdout.reconfigure(line_buffering=True)

app = Flask(__name__)

@app.route('/')
def home():
    return "<h1>Live Group Scraper & Adder Pro is Active!</h1>"

# --- بيانات التفعيل الثابتة الخاصة بك ---
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
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(mass_scaler_process())
    except Exception as e:
        print(f"❌ [CRITICAL ENGINE ERROR]: {e}")

async def mass_scaler_process():
    print(f"⏳ [SYSTEM] جاري الاتصال بالجلسة المستقرة {SESSION_FILE}...")
    client = TelegramClient(SESSION_FILE, api_id, api_hash, receive_updates=False)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("❌ [Fatal] ملف الجلسة غير فعال!")
        return

    print("✅ متصل بنجاح! بدء محرك السحب الحي من الرابط مباشرة...")
    
    processed_users = load_processed_users()

    # 🔗 المجموعات مأخوذة مباشرة من الكود هنا
    target_group = 'https://t.me/usdtalg' # الجروب المستهدف للسحب الحي 🎯
    my_group = 'actechup' # مجموعتك المستقبلة 📥

    total_success_added = 0

    while total_success_added < TARGET_SUCCESS_COUNT:
        try:
            print(f"\n📬 [دورة سحب حية] المؤشر المؤكد: ({total_success_added}/{TARGET_SUCCESS_COUNT})")
            
            # جلب بيانات المجموعات حياً من تليجرام
            group_entity = await client.get_entity(target_group)
            my_group_entity = await client.get_entity(my_group)
            
            # قراءة عدد أعضاء مجموعتك الحالي بدقة
            initial_count = my_group_entity.participants_count if hasattr(my_group_entity, 'participants_count') else 0
            if initial_count == 0:
                my_group_entity = await client.get_entity(my_group)
                initial_count = my_group_entity.participants_count or 0

            # توليد إزاحة عشوائية لتغطية كافة أعضاء الجروب المستهدف
            random_offset = random.randint(0, 1200)
            print(f"📡 جاري قراءة دفعة أعضاء من الرابط مباشرة بإزاحة ({random_offset})...")

            participants = await client(GetParticipantsRequest(
                group_entity, ChannelParticipantsSearch(''), offset=random_offset, limit=100, hash=0
            ))
            
            users = participants.users
            if not users:
                print("⚠️ المنطقة فارغة في هذه الإزاحة، استراحة دقيقتين...")
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

                # ⭐ الفلترة الذكية الصارمة: إذا كان الحساب حياً من الرابط ولا يملك Username يتخطاه فوراً لحمايتك
                if not user.username:
                    processed_users.add(str(user.id))
                    save_processed_user(user.id)
                    continue

                user_display = f"@{user.username}"
                print(f"👤 محاولة نقل العضو المكتشف حياً: {user_display}")
                
                try:
                    # البحث الفريش باليوزر نيم لتوليد الهاش الجديد تلقائياً
                    user_to_add = await client.get_input_entity(user.username)
                    
                    # طلب الإضافة
                    await client(InviteToChannelRequest(my_group_entity, [user_to_add]))
                    
                    # الفحص الصارم للتأكد من الزيادة الحقيقية بالجروب
                    await asyncio.sleep(4) 
                    check_group = await client.get_entity(my_group)
                    new_count = check_group.participants_count or 0
                    
                    if new_count > initial_count:
                        total_success_added += 1
                        initial_count = new_count
                        print(f"👍 [نجاح حقيقي مؤكد] تم نقل {user_display}! عدد مجموعتك الآن: {new_count}")
                        
                        processed_users.add(str(user.id))
                        save_processed_user(user.id)
                        await asyncio.sleep(50) # تبريد أمان بين الإضافات الناجحة
                    else:
                        print(f"⚠️ [تنبيه حظر صامت] تليجرام لم يقبل إضافة {user_display} فعلياً.")
                        print("💤 السكربت سيدخل في سبات وقائي لمدة 25 دقيقة لتنظيف الجلسة...")
                        await asyncio.sleep(1500)
                        break

                except FloodWaitError as e:
                    print(f"❌ حظر مؤقت (FloodWait). النوم التام لمدة {e.seconds} ثانية.")
                    await asyncio.sleep(e.seconds + 15)
                    break
                except PeerFloodError:
                    print("❌ خطأ إساءة استخدام (PeerFlood). النوم لمدة ساعة لحماية الخط...")
                    await asyncio.sleep(3600)
                    break
                except UserPrivacyRestrictedError:
                    print(f"🔒 تخطي: إعدادات خصوصية {user_display} تمنع الإضافة القسرية.")
                    processed_users.add(str(user.id))
                    save_processed_user(user.id)
                    await asyncio.sleep(3)
                except Exception as e:
                    print(f"⚠️ تخطي العضو بسبب قيود: {e}")
                    processed_users.add(str(user.id))
                    save_processed_user(user.id)
                    await asyncio.sleep(3)

            print("🏁 انتهت معالجة الدفعة الحالية من الرابط. تبريد الجلسة لمدة 5 دقائق...")
            await asyncio.sleep(300)

        except Exception as e:
            print(f"🚨 خطأ في الدورة العامة: {e}. إعادة المحاولة بعد دقيقة...")
            await asyncio.sleep(60)

    print(f"🎉 مبارك! تم ملء المجموعة بـ {TARGET_SUCCESS_COUNT} عضو حقيقي من الرابط مباشرة.")

threading.Thread(target=run_telegram_bot, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
