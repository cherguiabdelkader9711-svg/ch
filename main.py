import os
import asyncio
import random
from telethon import TelegramClient
from telethon.tl.functions.channels import GetParticipantsRequest, InviteToChannelRequest
from telethon.tl.types import ChannelParticipantsSearch

async def main():
    # إعدادات تليجرام الأساسية من البيئة
    api_id = int(os.environ.get("API_ID"))
    api_hash = os.environ.get("API_HASH")
    
    client = TelegramClient('session_cloud', api_id, api_hash)
    await client.start()
    
    if not await client.is_user_authorized():
        print("❌ خطأ: الجلسة السحابية غير صالحة.")
        return

    print("✅ تم الاتصال بنجاح بالجلسة السحابية المستقرة!")

    target_group_username = 'usdtalg'  # جروب مراد المستهدف
    my_group_username = 'actechup'    # جروبك التقني

    try:
        target_group_entity = await client.get_entity(target_group_username)
        my_group_entity = await client.get_entity(my_group_username)

        print(f"📡 جاري سحب دفعة أعضاء عشوائية من جروب ({target_group_username})...")
        
        # توليد إزاحة عشوائية لتنويع الأعضاء وتفادي التكرار قدر الإمكان
        random_offset = random.randint(0, 1000)
        
        participants = await client(GetParticipantsRequest(
            target_group_entity, ChannelParticipantsSearch(''), offset=random_offset, limit=100, hash=0
        ))
        
        users = participants.users
        random.shuffle(users) # خلط الأعضاء لزيادة الأمان
        
        print(f"🚀 تم جلب {len(users)} عضو بنجاح. بدء عملية النقل...")

        success_count = 0

        for user in users:
            if user.bot or user.deleted:
                continue
                
            user_display = f"@{user.username}" if user.username else f"ID: {user.id}"
            
            try:
                # محاولة إضافة العضو
                await client(InviteToChannelRequest(my_group_entity, [user]))
                success_count += 1
                print(f"👍 [تمت الإضافة] بنجاح: {user_display} | إجمالي الدورة: {success_count}")
                
                # وقت الأمان الثابت لحماية الحساب
                await asyncio.sleep(45)

            except Exception as e:
                error_msg = str(e)
                if "PEER_FLOOD" in error_msg:
                    print("⚠️ تليجرام فرض حظر مؤقت (Peer Flood). السكربت سيتوقف مؤقتاً لحماية رقمك.")
                    break
                elif "USER_PRIVACY_RESTRICTED" in error_msg:
                    print(f"🔒 [تخطّي] بسبب قيود الخصوصية للعضو: {user_display}")
                    await asyncio.sleep(1)
                elif "USER_ALREADY_PARTICIPANT" in error_msg:
                    print(f"⏭️ [تخطّي] العضو موجود بالفعل في مجموعتك: {user_display}")
                    await asyncio.sleep(1)
                else:
                    print(f"❌ لم تنجح الإضافة لـ {user_display}. السبب: {error_msg}")
                    await asyncio.sleep(2)

        print(f"🏁 انتهت دورة النقل الحالية بنجاح! تم إضافة {success_count} عضو جديد.")

    except Exception as e:
        print(f"🚨 حدث خطأ غير متوقع: {e}")

# تشغيل السكربت الأصلي
if __name__ == "__main__":
    asyncio.run(main())
