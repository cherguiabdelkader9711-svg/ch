import os
import asyncio
import random
from flask import Flask
from telethon import TelegramClient
from telethon.tl.functions.channels import GetParticipantsRequest, InviteToChannelRequest
from telethon.tl.types import ChannelParticipantsSearch

# إعداد تطبيق Flask لمنصة Render
app = Flask('')

@app.route('/')
def home():
    return "السكربت مبرمج للوصول إلى 1000 عضو ناجح ثم التوقف!"

# إعدادات تليجرام الأساسية
api_id = int(os.environ.get("API_ID"))
api_hash = os.environ.get("API_HASH")
session_string = os.environ.get("SESSION_STRING")

# ملف حفظ الأعضاء المفحوصين لضمان عدم التكرار
PROCESSED_USERS_FILE = "processed_users.txt"
# الهدف النهائي لعدد الأعضاء المضافين بنجاح
TARGET_SUCCESS_COUNT = 1000

def load_processed_users():
    if os.path.exists(PROCESSED_USERS_FILE):
        with open(PROCESSED_USERS_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_processed_user(user_id):
    with open(PROCESSED_USERS_FILE, "a") as f:
        f.write(f"{user_id}\n")

async def main_bot():
    client = TelegramClient('session_cloud', api_id, api_hash)
    await client.start()
    
    if not await client.is_user_authorized():
        print("❌ خطأ: الجلسة السحابية غير صالحة.")
        return

    print("✅ متصل بنجاح بالجلسة السحابية!")

    target_group_username = 'usdtalg'  # جروب مراد المستهدف
    my_group_username = 'actechup'    # جروبك

    processed_users = load_processed_users()
    print(f"📦 تم تحميل {len(processed_users)} عضو سابقين لتفادي التكرار.")

    # 🔢 العداد العام للإضافات الناجحة عبر كل الدورات
    total_success_added = 0

    while total_success_added < TARGET_SUCCESS_COUNT:
        try:
            target_group_entity = await client.get_entity(target_group_username)
            my_group_entity = await client.get_entity(my_group_username)

            print(f"📬 [دورة جديدة] الإجمالي الحالي المضاف بنجاح: ({total_success_added}/{TARGET_SUCCESS_COUNT})")
            print(f"📡 جاري سحب دفعة عشوائية جديدة من ({target_group_username})...")
            
            random_offset = random.randint(0, 2000)
            
            participants = await client(GetParticipantsRequest(
                target_group_entity, ChannelParticipantsSearch(''), offset=random_offset, limit=150, hash=0
            ))
            
            users = participants.users
            
            if not users:
                print("⚠️ لم يتم العثور على أعضاء في هذه الإزاحة، استراحة دقيقة...")
                await asyncio.sleep(60)
                continue

            random.shuffle(users)
            print(f"🚀 تم جلب {len(users)} عضو. جاري التصفية والنقل...")

            for user in users:
                # التحقق أولاً: هل وصلنا للهدف أثناء الدورة الحالية؟
                if total_success_added >= TARGET_SUCCESS_COUNT:
                    break

                if user.bot or user.deleted:
                    continue
                
                if str(user.id) in processed_users:
                    continue
                    
                user_display = f"@{user.username}" if user.username else f"ID: {user.id}"
                
                try:
                    # محاولة الإضافة
                    await client(InviteToChannelRequest(my_group_entity, [user]))
                    total_success_added += 1
                    print(f"👍 [نجاح] تمت إضافة {user_display}! الإجمالي العام الحالي: {total_success_added}/{TARGET_SUCCESS_COUNT}")
                    
                    processed_users.add(str(user.id))
                    save_processed_user(user.id)
                    
                    # وقت الأمان الثابت بين الإضافات الناجحة
                    await asyncio.sleep(45)

                except Exception as e:
                    error_msg = str(e)
                    
                    # تسجيله كمفحوص حتى لو فشل لمنع تكراره
                    processed_users.add(str(user.id))
                    save_processed_user(user.id)

                    if "PEER_FLOOD" in error_msg:
                        print("⚠️ حظر مؤقت (Peer Flood) من تليجرام. السكربت سينام ساعتين لحماية الرقم...")
                        await asyncio.sleep(7200)
                    elif "USER_PRIVACY_RESTRICTED" in error_msg:
                        print(f"🔒 تخطي ذكي لـ {user_display} (حساب مقيد بالخصوصية).")
                        await asyncio.sleep(1)
                    elif "USER_ALREADY_PARTICIPANT" in error_msg:
                        print(f"⏭️ تخطي {user_display} (موجود بالفعل).")
                        await asyncio.sleep(1)
                    else:
                        print(f"❌ فشلت إضافة {user_display}. السبب: {error_msg}")
                        await asyncio.sleep(3)

            # إذا وصلنا للهدف تماماً نخرج من الحلقة الكبيرة
            if total_success_added >= TARGET_SUCCESS_COUNT:
                break

            print(f"🏁 انتهت الدورة الحالية بنجاح. المحصلة الحالية: {total_success_added} عضو ناجح. استراحة 10 دقائق...")
            await asyncio.sleep(600)

        except Exception as e:
            print(f"🚨 خطأ في السكربت: {e}. إعادة المحاولة بعد دقيقة...")
            await asyncio.sleep(60)

    print(f"🎉 مبارك! تم الوصول إلى الهدف النهائي بنجاح وتم نقل {TARGET_SUCCESS_COUNT} عضو إلى مجموعتك دون تكرار. السكربت سيتوقف الآن بسلام.")

def run_bot_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main_bot())

import threading
threading.Thread(target=run_bot_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
