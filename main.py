import os
import sys
import time
import json
import random
import asyncio
import threading
from datetime import datetime, timedelta
from flask import Flask
from telethon import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest, GetParticipantsRequest, JoinChannelRequest
from telethon.tl.types import ChannelParticipantsSearch, UserStatusRecently, UserStatusOffline, UserStatusLastWeek

sys.stdout.reconfigure(line_buffering=True)

app = Flask(__name__)

@app.route('/')
def home():
    return "<h1>Professional Telegram Multi-Account Adder is running smoothly!</h1>"

PROCESSED_USERS_FILE = "processed_users.txt"
TARGET_SUCCESS_COUNT = 1000

# قراءة الإعدادات ديناميكياً
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.loads(f.read())

api_id = int(config['api_id'])
api_hash = config['api_hash']
group_source = config['group_source']
group_target = config['group_target']
accounts = config['accounts']

def load_processed_users():
    if os.path.exists(PROCESSED_USERS_FILE):
        with open(PROCESSED_USERS_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_processed_user(user_id):
    with open(PROCESSED_USERS_FILE, "a") as f:
        f.write(f"{user_id}\n")

def run_telegram_bot():
    print("📢 [SYSTEM] بدء تشغيل المحرك الذكي لتعدد الحسابات...")
    time.sleep(3)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(core_adder_process())
    except Exception as e:
        print(f"❌ [CRITICAL ERROR]: {e}")

async def core_adder_process():
    clients = []
    
    # 🔄 ربط وتهيئة كافة الجلسات السحابية المتاحة بشكل مستقل
    print(f"⏳ جاري فحص والاتصال بـ ({len(accounts)}) حسابات...")
    for phone in accounts:
        session_name = f"session_{phone.replace('+', '')}"
        cli = TelegramClient(session_name, api_id, api_hash, receive_updates=False)
        await cli.connect()
        
        if await cli.is_user_authorized():
            try:
                await cli(JoinChannelRequest(group_target))
            except Exception:
                pass
            clients.append({'phone': phone, 'client': cli})
            print(f"✅ تم ربط الحساب بنجاح: {phone}")
        else:
            print(f"❌ الحساب {phone} يحتاج إلى تسجيل دخول وتفعيل أولاً!")

    if not clients:
        print("❌ [Fatal] لا توجد حسابات نشطة للعمل. يتوقف النظام.")
        return

    processed_users = load_processed_users()
    total_success_added = 0
    attempt_counter = 0

    # إعداد فلاتر الوقت الفسيولوجية (تخطي الأعضاء الغائبين لأكثر من أسبوع)
    limit_date = datetime.now() - timedelta(days=7)

    while total_success_added < TARGET_SUCCESS_COUNT:
        if len(clients) == 0:
            print("🚨 [توقف]: جميع الحسابات المربوطة تم تقييدها مؤقتاً.")
            break

        try:
            # السحب الحي (Live Scraping) باستخدام الحساب الأول المتاح لتوفير الجهد
            scrapper_account = clients[0]['client']
            group_entity = await scrapper_account.get_entity(group_source)
            
            random_offset = random.randint(0, 1500)
            print(f"\n📡 [سحب ذكي] جلب دفعة أعضاء عشوائية بإزاحة ({random_offset})...")
            
            participants = await scrapper_account(GetParticipantsRequest(
                group_entity, ChannelParticipantsSearch(''), offset=random_offset, limit=120, hash=0
            ))
            
            users = participants.users
            if not users:
                await asyncio.sleep(60)
                continue

            random.shuffle(users)

            for user in users:
                if total_success_added >= TARGET_SUCCESS_COUNT or len(clients) == 0:
                    break
                
                # 1. تصفية البوتات والحسابات المحذوفة والتكرار
                if user.bot or user.deleted or str(user.id) in processed_users:
                    continue

                # 2. الفلترة الاحترافية لآخر ظهور (تخطي المستخدمين غير النشطين)
                is_active = False
                if isinstance(user.status, UserStatusRecently):
                    is_active = True
                elif isinstance(user.status, UserStatusOffline):
                    if user.status.was_online.replace(tzinfo=None) > limit_date:
                        is_active = True

                if not is_active:
                    continue  # تخطي الحساب الميت أو القديم جداً

                # 3. اختيار الحساب الحالي من المصفوفة بالتناوب (Round-Robin) لتقسيم الضغط
                current_index = attempt_counter % len(clients)
                active_worker = clients[current_index]
                cli_worker = active_worker['client']
                phone_worker = active_worker['phone']

                user_display = f"@{user.username}" if user.username else f"ID: {user.id}"
                print(f"👤 [الحساب: {phone_worker}] محاولة نقل العضو المتفاعل: {user_display}")

                try:
                    my_group_entity = await cli_worker.get_entity(group_target)
                    user_to_add = await cli_worker.get_input_entity(user.id)
                    
                    # أمر الإضافة الفردي المحمي بوقت أمان منظم
                    await cli_worker(InviteToChannelRequest(my_group_entity, [user_to_add]))
                    
                    total_success_added += 1
                    print(f"👍 [نجاح] أضاف {phone_worker} العضو {user_display}! المحصلة: {total_success_added}/{TARGET_SUCCESS_COUNT}")
                    
                    processed_users.add(str(user.id))
                    save_processed_user(user.id)
                    attempt_counter += 1
                    
                    # وقت الأمان بين كل محاولة وأخرى لتبريد الجلسة الحالية
                    await asyncio.sleep(20)

                except Exception as e:
                    error_msg = str(e)
                    if "PEER_FLOOD" in error_msg:
                        print(f"❌ [حظر مؤقت] الحساب {phone_worker} تم تقييده. يتم عزله مؤقتاً...")
                        try:
                            await cli_worker.disconnect()
                        except Exception:
                            pass
                        clients.remove(active_worker)
                    else:
                        # في حال الخصوصية أو أي خطأ آخر، نسجل العضو كمفحوص لتجنب تكراره
                        processed_users.add(str(user.id))
                        save_processed_user(user.id)
                        attempt_counter += 1
                    continue

            print("🛌 دفعة انتهت بسلام. استراحة 5 دقائق لتبريد كافة الحسابات النشطة...")
            await asyncio.sleep(300)

        except Exception as e:
            print(f"🚨 خطأ عام في الدورة: {e}. إعادة المحاولة بعد دقيقة...")
            await asyncio.sleep(60)

    print("🎉 مبارك! تم إنهاء المشروع والوصول إلى الهدف بنجاح تام.")

# إطلاق السكربت في الخلفية
threading.Thread(target=run_telegram_bot, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
