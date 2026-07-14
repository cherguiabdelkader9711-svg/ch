import os
import sys
import time
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
    return "Target Multi-Adder is Active and Running!"

# --- بيانات التفعيل الخاصة بك ---
api_id = 30239790  
api_hash = '2bb90bba711403595cec91e69479a976'  
phone = '+213771538043'  

client = TelegramClient('render_session_v1', api_id, api_hash)

def run_telegram_bot():
    print("📢 [THREAD] بدء تشغيل سكربت سحب الأعضاء من المجموعات...")
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
    
    # 🔥 المجموعات المستهدفة والمستقبلة المحدثة
    target_group = 'https://t.me/usdtalg' # الجروب الجديد المراد السحب منه 🎯
    my_group = 'actechup' # مجموعتك العامة المستقبلة 📥

    print(f"📬 جاري الاتصال بالجروب المستهدف ({target_group}) وجلب قائمة الأعضاء...")
    group_entity = await client.get_entity(target_group)
    my_group_entity = await client.get_entity(my_group)

    # جلب الأعضاء (أول 100 عضو كمرحلة أولى)
    participants = await client(GetParticipantsRequest(
        group_entity, ChannelParticipantsSearch(''), offset=0, limit=100, hash=0
    ))
    
    print(f"🚀 تم العثور على {len(participants.users)} عضو. بدء النقل والمضاعفة تدريجياً...")
    added_count = 0
    
    for user in participants.users:
        if user.bot or user.deleted:
            continue
            
        user_display = f"@{user.username}" if user.username else f"ID: {user.id}"
        print(f"👤 محاولة نقل العضو: {user_display}")
        
        try:
            user_to_add = await client.get_input_entity(user.id)
            
            # 🌟 تجربة الطريقة الأولى: Supergroup
            try:
                await client(InviteToChannelRequest(my_group_entity, [user_to_add]))
                added_count += 1
                print(f"👍 [نجاح] تمت إضافة {user_display}! إجمالي المضافين: {added_count}")
                time.sleep(45) # وقت أمان لمنع الحظر
                continue
            except Exception as e1:
                # إذا فشلت الأولى نجرب الطريقة الثانية للمجموعات العادية
                try:
                    await client(AddChatUserRequest(chat_id=my_group_entity.id, user_id=user_to_add, fwd_limit=0))
                    added_count += 1
                    print(f"👍 [نجاح بالطريقة 2] تمت إضافة {user_display}! إجمالي المضافين: {added_count}")
                    time.sleep(45)
                    continue
                except Exception as e2:
                    # إذا فشلت الطريقتان معاً ننتقل للعضو التالي
                    print(f"⚠️ تخطي {user_display} بسبب قيود تليجرام.")
                    
        except PeerFloodError:
            print("❌ حظر مؤقت (Flood) من تليجرام، نوم عميق لحماية رقمك لمدة ساعتين...")
            time.sleep(7200)
        except UserPrivacyRestrictedError:
            print(f"⚠️ تخطي: {user_display} يغلق إعدادات الخصوصية.")
        except Exception as e:
            print(f"⚠️ تخطي {user_display} لسبب آخر: {e}")
            continue

threading.Thread(target=run_telegram_bot, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
