import re
import time
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, ChatPermissions
from filters.admin_check import IsAdminFilter
import database

router = Router()

def parse_time(time_str: str) -> int:
    """تحليل المدة الزمنية (مثال: 1d, 2h, 30m) وإرجاع طابع وقت الانتهاء Unix timestamp"""
    if not time_str:
        return 0
    match = re.match(r"(\d+)([smhd])", time_str.lower())
    if not match:
        return 0
    val = int(match.group(1))
    unit = match.group(2)
    
    now = int(time.time())
    if unit == 's':
        return now + val
    elif unit == 'm':
        return now + val * 60
    elif unit == 'h':
        return now + val * 3600
    elif unit == 'd':
        return now + val * 86400
    return 0

def get_time_string(time_str: str) -> str:
    """تحويل المدة الزمنية إلى نص عربي مقروء"""
    match = re.match(r"(\d+)([smhd])", time_str.lower())
    if not match:
        return "دائم"
    val = int(match.group(1))
    unit = match.group(2)
    if unit == 's':
        return f"{val} ثانية"
    elif unit == 'm':
        return f"{val} دقيقة"
    elif unit == 'h':
        return f"{val} ساعة"
    elif unit == 'd':
        return f"{val} يوم"
    return "دائم"

# --- الحظر (Ban) ---
@router.message(Command("ban"), IsAdminFilter(), F.chat.type.in_({"group", "supergroup"}))
async def ban_user(message: Message, bot: Bot):
    # التحقق مما إذا كانت الرسالة رداً على مستخدم آخر
    if not message.reply_to_message:
        await message.reply("⚠️ يجب عليك الرد على رسالة الشخص الذي تريد حظره.")
        return
    
    target_user = message.reply_to_message.from_user
    if target_user.id == message.from_user.id:
        await message.reply("❌ لا يمكنك حظر نفسك.")
        return
        
    # قراءة مدة الحظر إذا تم توفيرها (مثل: /ban 1d)
    args = message.text.split()
    duration_str = args[1] if len(args) > 1 else ""
    until_timestamp = parse_time(duration_str)
    
    try:
        await message.chat.ban(user_id=target_user.id, until_date=until_timestamp)
        duration_desc = get_time_string(duration_str) if duration_str else "أبدي"
        await message.reply(
            f"👤 **العضو**: {target_user.full_name}\n"
            f"🚫 **تم حظره بنجاح**\n"
            f"⏱️ **مدة الحظر**: {duration_desc}"
        )
    except Exception as e:
        await message.reply(f"❌ فشل في حظر العضو. تأكد من أن البوت يملك صلاحيات الحظر وأن رتبته أعلى من العضو المستهدف.\n التفاصيل: {str(e)}")

# --- إلغاء الحظر (Unban) ---
@router.message(Command("unban"), IsAdminFilter(), F.chat.type.in_({"group", "supergroup"}))
async def unban_user(message: Message):
    if not message.reply_to_message:
        await message.reply("⚠️ يرجى الرد على رسالة العضو لإلغاء حظره.")
        return
        
    target_user = message.reply_to_message.from_user
    try:
        await message.chat.unban(user_id=target_user.id)
        await message.reply(f"✅ تم إلغاء حظر العضو {target_user.full_name} ويمكنه الانضمام للمجموعة الآن.")
    except Exception as e:
        await message.reply(f"❌ فشل إلغاء الحظر: {str(e)}")

# --- الكتم (Mute) ---
@router.message(Command("mute"), IsAdminFilter(), F.chat.type.in_({"group", "supergroup"}))
async def mute_user(message: Message):
    if not message.reply_to_message:
        await message.reply("⚠️ يجب الرد على رسالة العضو الذي تريد كتمه.")
        return
        
    target_user = message.reply_to_message.from_user
    if target_user.id == message.from_user.id:
        await message.reply("❌ لا يمكنك كتم نفسك.")
        return
        
    args = message.text.split()
    duration_str = args[1] if len(args) > 1 else ""
    until_timestamp = parse_time(duration_str)
    
    # تعطيل جميع صلاحيات إرسال الرسائل والوسائط
    permissions = ChatPermissions(
        can_send_messages=False,
        can_send_media_messages=False,
        can_send_audios=False,
        can_send_documents=False,
        can_send_photos=False,
        can_send_videos=False,
        can_send_video_notes=False,
        can_send_voice_notes=False,
        can_send_polls=False,
        can_send_other_messages=False,
        can_add_web_page_previews=False
    )
    
    try:
        await message.chat.restrict(user_id=target_user.id, permissions=permissions, until_date=until_timestamp)
        duration_desc = get_time_string(duration_str) if duration_str else "أبدي"
        await message.reply(
            f"👤 **العضو**: {target_user.full_name}\n"
            f"🔇 **تم كتمه بنجاح**\n"
            f"⏱️ **مدة الكتم**: {duration_desc}"
        )
    except Exception as e:
        await message.reply(f"❌ فشل كتم العضو: {str(e)}")

# --- إلغاء الكتم (Unmute) ---
@router.message(Command("unmute"), IsAdminFilter(), F.chat.type.in_({"group", "supergroup"}))
async def unmute_user(message: Message):
    if not message.reply_to_message:
        await message.reply("⚠️ يرجى الرد على رسالة العضو لفك كتمه.")
        return
        
    target_user = message.reply_to_message.from_user
    # استعادة الصلاحيات الافتراضية
    permissions = ChatPermissions(
        can_send_messages=True,
        can_send_media_messages=True,
        can_send_audios=True,
        can_send_documents=True,
        can_send_photos=True,
        can_send_videos=True,
        can_send_video_notes=True,
        can_send_voice_notes=True,
        can_send_polls=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True
    )
    
    try:
        await message.chat.restrict(user_id=target_user.id, permissions=permissions)
        await message.reply(f"🔊 تم فك كتم العضو {target_user.full_name} بنجاح.")
    except Exception as e:
        await message.reply(f"❌ فشل فك كتم العضو: {str(e)}")

# --- الطرد (Kick) ---
@router.message(Command("kick"), IsAdminFilter(), F.chat.type.in_({"group", "supergroup"}))
async def kick_user(message: Message):
    if not message.reply_to_message:
        await message.reply("⚠️ يرجى الرد على رسالة العضو الذي تريد طرده.")
        return
        
    target_user = message.reply_to_message.from_user
    if target_user.id == message.from_user.id:
        await message.reply("❌ لا يمكنك طرد نفسك.")
        return
        
    try:
        # الطرد في تيليجرام هو حظر العضو ثم فك الحظر عنه مباشرة ليتمكن من العودة لاحقاً
        await message.chat.ban(user_id=target_user.id)
        await message.chat.unban(user_id=target_user.id)
        await message.reply(f"👢 تم طرد العضو {target_user.full_name} من المجموعة بنجاح.")
    except Exception as e:
        await message.reply(f"❌ فشل طرد العضو: {str(e)}")

# --- التحذيرات (Warnings) ---
@router.message(Command("warn"), IsAdminFilter(), F.chat.type.in_({"group", "supergroup"}))
async def warn_user(message: Message):
    if not message.reply_to_message:
        await message.reply("⚠️ يرجى الرد على رسالة العضو لتوجيه تحذير له.")
        return
        
    target_user = message.reply_to_message.from_user
    if target_user.id == message.from_user.id:
        await message.reply("❌ لا يمكنك تحذير نفسك.")
        return
        
    group_id = message.chat.id
    new_warn_count = await database.add_warning(group_id, target_user.id)
    
    if new_warn_count >= 10:
        # الوصول للحد الأقصى للتحذيرات -> حظر تلقائي
        try:
            await message.chat.ban(user_id=target_user.id)
            await database.reset_warnings(group_id, target_user.id)
            await message.reply(
                f"👤 **العضو**: {target_user.full_name}\n"
                f"🚫 **وصل إلى 10 تحذيرات وتم حظره تلقائياً من المجموعة**."
            )
        except Exception as e:
            await message.reply(f"⚠️ العضو وصل إلى {new_warn_count} تحذيرات، ولكن فشل البوت في حظره تلقائياً: {str(e)}")
    else:
        await message.reply(
            f"👤 **العضو**: {target_user.full_name}\n"
            f"⚠️ **تم توجيه تحذير له ({new_warn_count}/10)**\n"
            f"⚠️ *عند الوصول إلى 10 تحذيرات سيتم الحظر تلقائياً.*"
        )

@router.message(Command("unwarn"), IsAdminFilter(), F.chat.type.in_({"group", "supergroup"}))
async def unwarn_user(message: Message):
    if not message.reply_to_message:
        await message.reply("⚠️ يرجى الرد على رسالة العضو لإزالة التحذيرات عنه.")
        return
        
    target_user = message.reply_to_message.from_user
    group_id = message.chat.id
    await database.reset_warnings(group_id, target_user.id)
    await message.reply(f"✅ تم تصفير جميع تحذيرات العضو {target_user.full_name}.")

# --- قفل وفتح المجموعة (Lock/Unlock) ---
@router.message(Command("lock"), IsAdminFilter(), F.chat.type.in_({"group", "supergroup"}))
async def lock_group(message: Message):
    permissions = ChatPermissions(can_send_messages=False)
    try:
        await message.chat.set_permissions(permissions)
        await message.reply("🔒 **تم قفل المجموعة بنجاح!** لا يمكن للأعضاء العاديين إرسال الرسائل الآن.")
    except Exception as e:
        await message.reply(f"❌ فشل قفل المجموعة: {str(e)}")

@router.message(Command("unlock"), IsAdminFilter(), F.chat.type.in_({"group", "supergroup"}))
async def unlock_group(message: Message):
    permissions = ChatPermissions(
        can_send_messages=True,
        can_send_media_messages=True,
        can_send_audios=True,
        can_send_documents=True,
        can_send_photos=True,
        can_send_videos=True,
        can_send_video_notes=True,
        can_send_voice_notes=True,
        can_send_polls=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True
    )
    try:
        await message.chat.set_permissions(permissions)
        await message.reply("🔓 **تم فتح المجموعة بنجاح!** يمكن للأعضاء إرسال الرسائل الآن.")
    except Exception as e:
        await message.reply(f"❌ فشل فتح المجموعة: {str(e)}")
