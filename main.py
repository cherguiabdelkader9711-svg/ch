import os
import sys
import asyncio
import threading
from flask import Flask
from telethon import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest, GetParticipantsRequest
from telethon.tl.functions.messages import AddChatUserRequest
from telethon.tl.types import ChannelParticipantsSearch
from telethon.errors.rpcerrorlist import PeerFloodError, UserPrivacyRestrictedError, FloodWaitError

sys.stdout.reconfigure(line_buffering=True)

app = Flask(__name__)

@app.route('/')
def home():
    return "Target Multi-Adder is Active and Running!"

# --- البيانات الحساسة (يفضل رفعها كـ Environment Variables على Render) ---
api_id = int(os.environ.get("API_ID", 30239790))
api_hash = os.environ.get("API_HASH", '2bb90bba711403595cec91e69479a976')

client = TelegramClient('render_session_v1', api_id, api_hash)

def run_telegram_bot():
    print("📢 [THREAD] بدء تشغيل سكربت سحب الأعضاء...")
    # إنشاء Loop جديد خاص بهذا الـ Thread لتجنب المشاكل مع Flask
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(mass_scaler_process())
    except Exception as e:
        print(f"❌ [CRITICAL ERROR]: {e}")

async def mass_scaler_process():
    print("⏳ جاري فحص الاتصال بالجلسة السحابية...")
    await client.connect()
    
    if not await client.is_user_authorized():
        print("❌ ملف الجلسة غير صالح أو يتطلب تسجيل دخول!")
        return

    print("✅ متصل بنجاح!")
    
    target_group = 'https://t.me/usdtalg' 
    my_group = 'actechup' 

    print(f"📬 جاري الاتصال بالجروب المستهدف ({target_group})...")
    try:
        group_entity = await client.get_entity(target_group)
        my_group_entity = await client.get_entity(my_group)
    except Exception as e:
        print(f"❌ فشل جلب بيانات المجموعات: {e}")
        return

    # جلب أول 100 عضو
    participants = await client(GetParticipantsRequest(
        group_entity, ChannelParticipantsSearch(''), offset=0, limit=100, hash=0
    ))
    
    print(f"🚀 تم العثور على {len(participants.users)} عضو. بدء النقل...")
    added_count = 0
    
    for user in participants.users:
        if user.bot or user.deleted:
            continue
            
        user_display = f"@{user.username}" if user.username else f"ID: {user.id}"
        print(f"👤 محاولة نقل العضو: {user_display}")
        
        try:
            user_to_add = await client.get_input_entity(user.id)
            
            # محاولة الإضافة (الطريقة الأولى)
            try:
                await client(InviteToChannelRequest(my_group_entity, [user_to_add]))
                added_count += 1
                print(f"👍 [نجاح] تمت إضافة {user_display}! إجمالي: {added_count}")
                await asyncio.sleep(45) # استخدام النوم الأزامني لحماية الحساب
                
            except (PeerFloodError, FloodWaitError):
                print("❌ حظر مؤقت (Flood)، سيتم إيقاف السكربت مؤقتاً لمدة ساعتين لحماية رقمك...")
                await asyncio.sleep(7200)
            except UserPrivacyRestrictedError:
                print(f"⚠️ تخطي: {user_display} يغلق إعدادات الخصوصية.")
            except Exception:
                # إذا فشلت الأولى لسبب آخر، نجرب الطريقة الثانية
                try:
                    await client(AddChatUserRequest(chat_id=my_group_entity.id, user_id=user_to_add, fwd_limit=0))
                    added_count += 1
                    print(f"👍 [نجاح بالطريقة 2] تمت إضافة {user_display}! إجمالي: {added_count}")
                    await asyncio.sleep(45)
                except (PeerFloodError, FloodWaitError):
                    print("❌ حظر مؤقت (Flood) في الطريقة الثانية، نوم لمدة ساعتين...")
                    await asyncio.sleep(7200)
                except Exception as e2:
                    print(f"⚠️ تعذر إضافة {user_display}: {e2}")

        except Exception as e:
            print(f"⚠️ خطأ في معالجة العضو {user_display}: {e}")
            continue

# تشغيل البوت في Thread منفصل
threading.Thread(target=run_telegram_bot, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
