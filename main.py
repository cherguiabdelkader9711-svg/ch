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
    return "Target Multi-Adder with URL-Based Ban Detection is Active!"

# --- بيانات التفعيل الثابتة الخاصة بك ---
api_id = 30239790  
api_hash = '2bb90bba711403595cec91e69479a976'  
phone = '+213771538043'  

client = TelegramClient('render_session_v1', api_id, api_hash)

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

# ✨ دالة الفحص الذكي المحدثة للكشف عن الحظر باستخدام رابط المجموعة المستهدفة
async def check_account_ban(target_group_url, my_group_entity):
    print("🔍 [فحص الأمان] جاري اختبار صلاحية الحساب وكشف الحظر الصامت عبر الرابط...")
    try:
        # جلب كيان الجروب المستهدف أولاً للتأكد من الاتصال
        target_entity = await client.get_entity(target_group_url)
        
        # محاولة فحص الكيان باستخدام حساب خدمة رسمي معروف (تليجرام) كمثال للاختبار الآمن داخل جروبك
        test_user = await client.get_input_entity('@Telegram')
        await client(InviteToChannelRequest(my_group_entity, [test_user]))
        return False # الحساب سليم وميزة الإضافة تعمل
    except Exception as e:
        error_msg = str(e)
        # إذا كانت الإجابة تفيد بالغرور أو الحظر الصريح
        if "PEER_FLOOD" in error_msg or "USER_BANNED_IN_CHANNEL" in error_msg:
            return True
        # إذا كان الحساب مضافاً بالفعل أو مقيد الخصوصية، فهذا يعني أن البرمجة شتغالة تماماً!
        elif "USER_ALREADY_PARTICIPANT" in error_msg or "USER_PRIVACY_RESTRICTED" in error_msg:
            return False
        
        # أي رفض غامض ومفاجئ للإضافة يعني حظر صامت من السيرفرات
        return True

def run_telegram_bot():
    print("📢 [THREAD] بدء تشغيل سكربت سحب الأعضاء برابط المجموعة وكاشف الحظر...")
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

    print("✅ متصل بنجاح!")
    
    processed_users = load_processed_users()
    target_group = 'https://t.me/usdtalg' # الرابط المستهدف 🎯
    my_group = 'actechup' # مجموعتك 📥

    total_success_added = 0

    while total_success_added < TARGET_SUCCESS_COUNT:
        try:
            my_group_entity = await client.get_entity(my_group)

            # 🚨 كاشف الحظر الصامت يفحص الآن بالرابط قبل الدخول في السحب
            is_banned = await check_account_ban(target_group, my_group_entity)
            if is_banned:
                print("\n🚨🚨🚨 [تحذير حظر صامت] 🚨🚨🚨")
                print("⚠️ تليجرام فرض حظراً مؤقتاً على حسابك الجزائري يمنعك من إضافة الأعضاء (حظر 24 ساعة).")
                print("💤 السكربت سينام الآن لمدة يوم كامل تلقائياً لحماية الرقم من الإغلاق النهائي...")
                print("--------------------------------------------------")
                await asyncio.sleep(86400) # النوم لمدة يوم كامل (24 ساعة)
                continue 

            print(f"\n📬 [دورة جديدة] الحساب سليم وجاهز! المحصلة الحالية: ({total_success_added}/{TARGET_SUCCESS_COUNT})")
            
            group_entity = await client.get_entity(target_group)
            random_offset = random.randint(0, 1500)
            
            participants = await client(GetParticipantsRequest(
                group_entity, ChannelParticipantsSearch(''), offset=random_offset, limit=150, hash=0
            ))
            
            users = participants.users
            if not users:
                await asyncio.sleep(60)
                continue

            random.shuffle(users)

            for user in users:
                if total_success_added >= TARGET_SUCCESS_COUNT:
                    break
                if user.bot or user.deleted or str(user.id) in processed_users:
                    continue
                    
                user_display = f"@{user.username}" if user.username else f"ID: {user.id}"
                print(f"👤 محاولة نقل العضو: {user_display}")
                
                try:
                    user_to_add = await client.get_input_entity(user.id)
                    success_in_this_user = False
                    
                    try:
                        await client(InviteToChannelRequest(my_group_entity, [user_to_add]))
                        success_in_this_user = True
                        print(f"👍 [نجاح 1] تمت إضافة {user_display}!")
                    except Exception as e1:
                        try:
                            await client(AddChatUserRequest(chat_id=my_group_entity.id, user_id=user_to_add, fwd_limit=0))
                            success_in_this_user = True
                            print(f"👍 [نجاح 2] تمت إضافة {user_display}!")
                        except Exception as e2:
                            print(f"🔒 تخطي لـ {user_display} (خصوصية أو قيود).")
                            processed_users.add(str(user.id))
                            save_processed_user(user.id)
                            await asyncio.sleep(1)

                    if success_in_this_user:
                        total_success_added += 1
                        processed_users.add(str(user.id))
                        save_processed_user(user.id)
                        time.sleep(45)

                except PeerFloodError:
                    print("❌ حظر مؤقت صريح (Flood)، نوم عميق لمدة ساعتين...")
                    time.sleep(7200)
                except UserPrivacyRestrictedError:
                    processed_users.add(str(user.id))
                    save_processed_user(user.id)
                except Exception as e:
                    processed_users.add(str(user.id))
                    save_processed_user(user.id)
                    continue

            if total_success_added >= TARGET_SUCCESS_COUNT:
                break

            print("🛌 دورة نظيفة انتهت. استراحة 10 دقائق لتبريد الجلسة...")
            time.sleep(600)

        except Exception as e:
            print(f"🚨 خطأ عام: {e}. إعادة المحاولة بعد دقيقة...")
            time.sleep(60)

    print("🎉 تم الوصول إلى الهدف النهائي (1000 عضو) بنجاح!")

threading.Thread(target=run_telegram_bot, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
