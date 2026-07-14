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
    return "<h1>Target Multi-Adder Pro is Active and Verifying!</h1>"

# --- بيانات التفعيل الخاصة بك ---
api_id = 30239790  
api_hash = '2bb90bba711403595cec91e69479a976'  
SESSION_FILE = 'render_session_v1'

def run_telegram_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(mass_scaler_process())
    except Exception as e:
        print(f"❌ [CRITICAL ERROR]: {e}")

async def mass_scaler_process():
    print(f"⏳ جاري فحص الاتصال بالجلسة السحابية {SESSION_FILE}...")
    client = TelegramClient(SESSION_FILE, api_id, api_hash, receive_updates=False)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("❌ ملف الجلسة غير صالح!")
        return

    print("✅ متصل بنجاح! بدء النقل الذكي والمؤكد...")
    
    target_group = 'https://t.me/usdtalg' # الجروب المراد السحب منه 🎯
    my_group = 'actechup' # مجموعتك المستقبلة 📥

    added_count = 0

    while True:
        try:
            if not client.is_connected():
                await client.connect()

            group_entity = await client.get_entity(target_group)
            my_group_entity = await client.get_entity(my_group)

            # قراءة عدد الأعضاء الحالي بدقة قبل المحاولة
            initial_count = my_group_entity.participants_count if hasattr(my_group_entity, 'participants_count') else 0
            if initial_count == 0:
                my_group_entity = await client.get_entity(my_group)
                initial_count = my_group_entity.participants_count or 0

            # سحب دفعة عشوائية لتجنب التكرار والنمط الثابت
            random_offset = random.randint(0, 500)
            participants = await client(GetParticipantsRequest(
                group_entity, ChannelParticipantsSearch(''), offset=random_offset, limit=50, hash=0
            ))
            
            if not participants.users:
                print("⚠️ لم يتم العثور على أعضاء في هذا النطاق، استراحة قصيرة...")
                await asyncio.sleep(60)
                continue

            for user in participants.users:
                if user.bot or user.deleted:
                    continue
                
                # تخطي الحسابات التي لا تملك معرفاً عاماً لتجنب مشاكل الهاش
                if not user.username:
                    continue
                    
                user_display = f"@{user.username}"
                print(f"👤 محاولة نقل العضو: {user_display}")
                
                try:
                    # جلب الكيان الفريش باستخدام اليوزر نيم لضمان صحة الهاش
                    user_to_add = await client.get_input_entity(user.username)
                    
                    # إرسال طلب الدعوة للمجموعة
                    await client(InviteToChannelRequest(my_group_entity, [user_to_add]))
                    
                    # استراحة أمان دقيقة قبل فحص العداد الفعلي للجروب
                    await asyncio.sleep(5) 
                    
                    # التحقق من تحديث العداد الفعلي في مجموعتك
                    check_group = await client.get_entity(my_group)
                    new_count = check_group.participants_count or 0
                    
                    if new_count > initial_count:
                        added_count += 1
                        initial_count = new_count
                        print(f"👍 [نجاح مؤكد بالعداد] تمت إضافة {user_display}! إجمالي المضافين فعلياً: {added_count} | مجموعتك الآن: {new_count}")
                        await asyncio.sleep(45) # وقت أمان بين الإضافات الناجحة
                    else:
                        print(f"⚠️ [حظر صامت مكتشف] تليجرام أوهم السكريبت بالقبول لكن العضو لم ينضم. تبريد وقائي لمدة 20 دقيقة...")
                        await client.disconnect()
                        await asyncio.sleep(1200)
                        break
                        
                except FloodWaitError as e:
                    print(f"❌ حظر مؤقت حاد (FloodWait). فصل آمن والنوم لمدة {e.seconds} ثانية...")
                    await client.disconnect()
                    await asyncio.sleep(e.seconds + 10)
                    break
                except PeerFloodError:
                    print("❌ خطأ إساءة استخدام (PeerFlood). الحساب يحتاج استراحة حقيقية، نوم وقائي لمدة ساعة...")
                    await client.disconnect()
                    await asyncio.sleep(3600)
                    break
                except UserPrivacyRestrictedError:
                    print(f"🔒 تخطي: إعدادات خصوصية {user_display} تمنع الإضافة القسرية.")
                    await asyncio.sleep(3)
                except Exception as e:
                    print(f"⚠️ تخطي {user_display} لسبب آخر: {e}")
                    await asyncio.sleep(3)

            print("🏁 انتهت الدورة الحالية. تبريد الجلسة لمدة 3 دقائق...")
            await asyncio.sleep(180)

        except Exception as e:
            print(f"🚨 خطأ في الدورة العامة للسكربت: {e}. إعادة المحاولة بعد دقيقة...")
            await asyncio.sleep(60)

threading.Thread(target=run_telegram_bot, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
