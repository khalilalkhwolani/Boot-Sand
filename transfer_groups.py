import os
import asyncio
import json
from telethon import TelegramClient
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.errors import FloodWaitError, UserAlreadyParticipantError

# إعدادات Telegram API الرسمية لتطبيق أندرويد (تعتبر الأكثر استقراراً لتجنب حظر الاتصال)
API_ID = 2899
API_HASH = '3672da51d2f62773f274cb7609cf46fb'

# ملفات الجلسات وحفظ البيانات
SESSION_ACC1 = 'account_1'
SESSION_ACC2 = 'account_2'
DATA_FILE = 'my_groups.json'

async def export_groups():
    """تسجيل الدخول بالحساب الأول واستخراج المجموعات والقنوات العامة والخاصة"""
    client = TelegramClient(
        SESSION_ACC1, 
        API_ID, 
        API_HASH,
        system_version="4.16.30-vxCUSTOM",
        device_model="Android Device",
        app_version="10.4.0"
    )
    await client.start()
    
    print("جاري استخراج المجموعات والقنوات التي تشترك فيها...")
    groups_data = []
    
    async for dialog in client.iter_dialogs():
        entity = dialog.entity
        # التحقق من أن الكيان هو قناة أو مجموعة خارقة (Supergroup) أو مجموعة عادية
        if dialog.is_group or dialog.is_channel:
            group_info = {
                "id": entity.id,
                "title": dialog.name,
                "username": getattr(entity, 'username', None),
                "is_channel": dialog.is_channel,
                "is_group": dialog.is_group
            }
            
            # محاولة الحصول على رابط الدعوة إذا كان الحساب مسؤولاً أو الرابط متاحاً
            invite_link = None
            if not group_info["username"]:
                try:
                    if dialog.is_channel:
                        from telethon.tl.functions.channels import GetFullChannelRequest
                        full = await client(GetFullChannelRequest(entity))
                    else:
                        from telethon.tl.functions.messages import GetFullChatRequest
                        full = await client(GetFullChatRequest(entity.id))
                    
                    if full and full.full_chat and full.full_chat.exported_invite:
                        invite_link = getattr(full.full_chat.exported_invite, 'link', None)
                except Exception:
                    pass
            
            group_info["invite_link"] = invite_link
            groups_data.append(group_info)
            print(f"تم الحفظ: {dialog.name} (عام: {group_info['username'] is not None})")
            
    # حفظ البيانات في ملف json
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(groups_data, f, ensure_ascii=False, indent=4)
        
    print(f"\nتم استخراج {len(groups_data)} مجموعة/قناة وحفظها في {DATA_FILE}")
    await client.disconnect()

async def import_groups():
    """تسجيل الدخول بالحساب الثاني والانضمام للمجموعات المحفوظة"""
    if not os.path.exists(DATA_FILE):
        print(f"الملف {DATA_FILE} غير موجود! الرجاء تشغيل عملية التصدير أولاً.")
        return
        
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        groups_data = json.load(f)
        
    client = TelegramClient(
        SESSION_ACC2, 
        API_ID, 
        API_HASH,
        system_version="4.16.30-vxCUSTOM",
        device_model="Android Device",
        app_version="10.4.0"
    )
    await client.start()
    
    print(f"بدء الانضمام إلى {len(groups_data)} مجموعة/قناة...")
    
    for item in groups_data:
        title = item["title"]
        username = item["username"]
        invite_link = item["invite_link"]
        
        # تخطي المجموعات الخاصة التي لا نملك رابط دعوتها (يجب إضافتها يدوياً أو دعوة الحساب)
        if not username and not invite_link:
            print(f"⚠️ تخطي: '{title}' (مجموعة خاصة بدون رابط دعوة، يجب إضافتك إليها يدوياً)")
            continue
            
        try:
            if username:
                print(f"🔄 جاري الانضمام إلى: {title} (@{username})...")
                await client(JoinChannelRequest(username))
                print(f"✅ تم الانضمام بنجاح!")
            elif invite_link:
                # استخراج كود الدعوة من الرابط باستخدام تعبير نمطي مرن
                import re as regex
                match = regex.search(r'(?:t\.me|telegram\.me|telegram\.dog)/(?:\+|joinchat/)([^/?\s]+)', invite_link)
                if match:
                    code = match.group(1)
                    print(f"🔄 جاري الانضمام إلى: {title} عبر رابط دعوة...")
                    await client(ImportChatInviteRequest(code))
                    print(f"✅ تم الانضمام بنجاح!")
                else:
                    print(f"⚠️ تعذر استخراج كود الدعوة من الرابط: {invite_link}")
                
            # تأخير لتجنب الحظر من التليجرام (مهم جداً)
            await asyncio.sleep(15)
            
        except FloodWaitError as e:
            print(f"🛑 تم إيقاف العمل مؤقتاً بسبب قيود التليجرام. يجب الانتظار {e.seconds} ثانية...")
            await asyncio.sleep(e.seconds)
        except UserAlreadyParticipantError:
            print(f"ℹ️ أنت مشترك بالفعل في: {title}")
        except Exception as e:
            print(f"❌ فشل الانضمام إلى {title}: {str(e)}")
            await asyncio.sleep(5)
            
    print("\n🎉 اكتملت العملية!")
    await client.disconnect()

async def main():
    print("اختر العملية التي تريد القيام بها:")
    print("1) تصدير المجموعات من الحساب الأول (المصدر)")
    print("2) استيراد المجموعات إلى الحساب الثاني (الجديد)")
    choice = input("أدخل رقم الخيار (1 أو 2): ").strip()
    
    if choice == '1':
        await export_groups()
    elif choice == '2':
        await import_groups()
    else:
        print("اختيار غير صحيح.")

if __name__ == '__main__':
    # لتجنب مشاكل تشغيل event loop في بعض البيئات
    asyncio.run(main())
