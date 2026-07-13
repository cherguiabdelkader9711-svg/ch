import os
import sys
import time
import random
import asyncio
import threading
from flask import Flask
from telethon import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest, GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsSearch
from telethon.errors.rpcerrorlist import FloodWaitError, UserPrivacyRestrictedError, PeerFloodError, PeerIdInvalidError

sys.stdout.reconfigure(line_buffering=True)

app = Flask(__name__)

@app.route('/')
def home():
    return "<h1>Live Group Scraper & Adder Pro V3 is Fully Stable!</h1>"

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

    print("✅ متصل بنجاح! بدء محرك السحب الحي المستقر...")
    processed_users = load_processed_users()

    target_group = 'https://t.me/usdtalg' 
    my_group = 'actechup' 

    total_success_added = 0

    while total_success_added < TARGET_SUCCESS_COUNT:
        try:
            # التأكد من إعادة الاتصال إذا تم فصله في الدورة السابقة بسبب الحظر
            if not client.is_connected():
                await client.connect()

            print(f"\n📬 [دورة سحب حية] المؤشر المؤكد: ({total_success_added}/{TARGET_SUCCESS_COUNT})")
            
            group_entity = await client.get_entity(target_group)
            my_group_entity = await client.get_entity(my_group)
            
            initial_count = my_group_entity.participants_count if hasattr(my_group_entity, 'participants_count') else 0
            if initial_count == 0:
                my_group_entity = await client.get_entity(my_group)
                initial_count = my_group_entity.participants_count or 0

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

                if not user.username:
                    processed_users.add(str(user.id))
                    save_processed_user(user.id)
                    continue

                user_display = f"@{user.username}"
                print(f"👤 محاولة نقل العضو المكتشف حياً: {user_display}")
                
                try:
                    user_to_add = await client.get_input_entity(user.username)
                    await client(InviteToChannelRequest(my_group_entity, [user_to_add]))
                    
                    await asyncio.sleep(4) 
                    check_group = await client.get_entity(my_group)
                    new_count = check_group.participants_count or 0
                    
                    if new_count > initial_count:
                        total_success_added += 1
                        initial_count = new_count
                        print(f"👍 [نجاح حقيقي مؤكد] تم نقل {user_display}! عدد مجموعتك الآن: {new_count}")
                        
                        processed_users.add(str(user.id))
                        save_processed_user(user.id)
                        await asyncio.sleep(50) 
                    else:
                        print(f"⚠️ [تنبيه حظر صامت] تليجرام لم يقبل إضافة {user_display} فعلياً.")
                        print("💤 فصل آمن للجلسة والنوم لمدة 20 دقيقة لتنظيف الـ IP...")
                        await client.disconnect()
                        await asyncio.sleep(1200)
                        break

                except FloodWaitError as e:
                    print(f"❌ حظر مؤقت حاد (FloodWait). النوم الآمن لمدة {e.seconds} ثانية.")
                    await client.disconnect()
                    await asyncio.sleep(e.seconds + 10)
                    break

                except PeerFloodError:
                    print("❌ خطأ PeerFlood (إساءة استخدام حادة). فصل الاتصال بسلام والنوم لمدة 45 دقيقة لحماية الرقم...")
                    await client.disconnect() # فصل العميل أولاً لحماية المهام من التدمير العشوائي
                    await asyncio.sleep(2700) # سبات آمن بدون مشاكل الـ Task destroyed
                    break

                except UserPrivacyRestrictedError:
                    print(f"🔒 تخطي: إعدادات خصوصية {user_display} تمنع الإضافة.")
                    processed_users.add(str(user.id))
                    save_processed_user(user.id)
                    await asyncio.sleep(3)
                except Exception as e:
                    print(f"⚠️ تخطي العضو بسبب عائق: {e}")
                    processed_users.add(str(user.id))
                    save_processed_user(user.id)
                    await asyncio.sleep(3)

            if client.is_connected():
                print("🏁 انتهت معالجة الدفعة الحالية. تبريد الجلسة لمدة 4 دقائق...")
                await asyncio.sleep(240)

        except Exception as e:
            print(f"🚨 خطأ في الدورة العامة: {e}. إعادة المحاولة بعد دقيقة...")
            await asyncio.sleep(60)

    print(f"🎉 مبارك! تم الوصول للهدف.")

threading.Thread(target=run_telegram_bot, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
