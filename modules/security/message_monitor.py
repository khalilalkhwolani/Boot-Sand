import re
import logging
import asyncio
import time
from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.types import Message, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton

import database
from .utils import get_bot_info, is_time_in_range
from .filters import QUICK_SPAM_TRIGGERS, QUICK_SPAM_WORDS, LINK_REGEX, is_suspicious
from .keyboards import build_help_keyboard, build_main_keyboard
from .callbacks import show_group_settings
from .moderation import _delete_and_warn, handle_admin_manual_moderation_reply

logger = logging.getLogger(__name__)
router = Router()

# تتبع زمن وصول الرسائل لمنع الإغراق
flood_tracker = {}

async def _process_text_commands(message: Message, text: str, is_admin: bool, is_creator: bool, settings: dict, bot: Bot) -> bool:
    """معالجة الأوامر النصية وتفعيل القفل بالرسائل. ترجع True إذا تم تنفيذ أمر ويجب إيقاف المعالجة."""
    if text.startswith("/"):
        parts = text.split(" ", 1)
        command = parts[0].split("@", 1)[0]
        rest = parts[1] if len(parts) > 1 else ""
        text = command + (" " + rest if rest else "")
        if text in {"/help", "/settings", "/setting"}:
            text = "مساعدة"

    if text == "/start":
        await message.answer("اهلا بك ☘ ارسل مساعدة لمعرفة 💎 كيفية استخدام البوت 🤖🍁")
        return True

    if text == "مساعدة":
        await message.reply("كيفية استخدام البوت 📋🔻", reply_markup=build_help_keyboard())
        return True

    if is_admin and text in {"اعدادات", "الاعدادات", "الإعدادات", "اعدادات البوت", "الاعدادات العامة", "الضبط"}:
        await show_group_settings(message)
        return True

    if text == "الوقت":
        now = datetime.now()
        await message.reply(f"🕛 البلد : السودان/المملكة\n🕛 الساعة : {now.strftime('%I')}\n🕛 الدقيقة : {now.strftime('%M')}")
        return True

    if text == "التاريخ":
        today = datetime.now().date()
        await message.reply(
            f"📆 البلد : السودان/المملكة \n📆  السنة : {today.year} \n📆 الشهر : {today.month} \n📆 اليوم : {today.day}"
        )
        return True

    if text == "عدد الرسائل":
        count_label = "مجموعتك متفاعلة 💯" if message.message_id > 1000 else "للاسف❗️مجموعتك غير متفاعلة 🚹💭"
        await message.reply(f"عدد 📈 رسائل المجموعة 👥🔹  : *{message.message_id}*\n{count_label}", parse_mode="Markdown")
        return True

    if text == "معلومات":
        target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
        username = target.username or "غير موجود"
        await message.reply(
            f"💭الاسم : {target.first_name}\n💭المعرف : @{username}\n💭الايدي : {target.id}\n💭اسم المجموعة : {message.chat.title or 'خاصة'}\n💭ايدي المجموعة : {message.chat.id}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text='تابع جديدنا 📪', callback_data='channel')]
            ])
        )
        return True

    if text == "غادر":
        if not is_admin:
            try:
                await message.chat.kick(user_id=message.from_user.id)
                await message.chat.unban(user_id=message.from_user.id)
                await message.reply("وداعا عزيزي ✨")
            except Exception:
                pass
        else:
            await message.reply("عذرا ‼️ انت مشرف في المجموعة 🚹🔒")
        return True

    if text == "غادر المجموعة":
        if is_creator:
            await message.reply("غادرت المجموعة بناءً على طلب المنشئ 👋")
            try:
                await message.chat.leave()
            except Exception:
                pass
        else:
            await message.reply('عذرا ‼️ فقط منشئ المجموعة 👥 يمكنه استخدام هاذا الامر ♻️🔺')
        return True

    # أوامر القفل والفتح
    lock_commands = {
        "اقفل الملصقات": ("anti_sticker", "تم قفل الملصقات 🗾🔒", "الملصقات مقفولة 🗾🔒"),
        "افتح الملصقات": ("anti_sticker", "الملصقات مفتوحة 🗾🔓", "تم فتح الملصقات 🗾🔓"),
        "اقفل الصور": ("anti_photo", "تم قفل الصور 📷🔒", "الصور مقفولة 📷🔒"),
        "افتح الصور": ("anti_photo", "الصور مفتوحة 📷🔓", "تم فتح الصور 📷🔓"),
        "اقفل التوجيه": ("anti_fwd", "تم قفل التوجيه 🔄🔒", "التوجيه مقفول 🔄🔒"),
        "افتح التوجيه": ("anti_fwd", "التوجيه مفتوح 🔄🔓", "تم فتح التوجيه 🔄🔓"),
        "اقفل الدردشة": ("anti_chat", "تم قفل الدردشة 📧🔒", "الدردشة مقفول 📧🔒"),
        "افتح الدردشة": ("anti_chat", "الدردشة مفتوح 📧🔓", "تم فتح الدردشة 📧🔓"),
        "اقفل الروابط": ("anti_link", "تم قفل الروابط 💎🔒", "الروابط مقفولة 💎🔒"),
        "افتح الروابط": ("anti_link", "الروابط مفتوحة 💎🔓", "تم فتح الروابط 💎🔓"),
        "اقفل الاشعارات": ("anti_join", "تم ✅ قفل اشعارات الدخول والخروج 📛🔒", "الاشعارات مقفول 📛🔒"),
        "افتح الاشعارات": ("anti_join", "الاشعارات مفتوح 📛🔓", "تم فتح الاشعارات 📛🔓"),
        "اقفل الصوتيات": ("anti_voice", "تم قفل الصوتيات  🎙🔒", "الصوتيات  مقفولة 🎙🔒"),
        "افتح الصوتيات": ("anti_voice", "الصوتيات  مفتوحة 🎙🔓", "تم فتح الصوتيات  🎙🔓"),
        "اقفل الاغاني": ("anti_audio", "تم قفل الاغاني  🎵🔒", "الاغاني  مقفولة 🎵🔒"),
        "افتح الاغاني": ("anti_audio", "الاغاني  مفتوحة 🎵🔓", "تم فتح الاغاني  🎵🔓"),
        "اقفل الصور المتحركة": ("anti_gif", "تم قفل الصور المتحركة  🎆🔒", "الصور المتحركة  مقفولة 🎆🔒"),
        "افتح الصور المتحركة": ("anti_gif", "الصور المتحركة  مفتوحة 🎆🔓", "تم فتح الصور المتحركة  🎆🔓"),
        "اقفل جهات الاتصال": ("anti_contact", "تم قفل جهات الاتصال  📱🔒", "جهات الاتصال  مقفولة 📱🔒"),
        "افتح جهات الاتصال": ("anti_contact", "جهات الاتصال  مفتوحة 📱🔓", "تم فتح جهات الاتصال  📱🔓"),
        "اقفل الكلايش": ("anti_list", "تم قفل الكلايش  🗒🔒", "الكلايش  مقفولة 🗒🔒"),
        "افتح الكلايش": ("anti_list", "الكلايش  مفتوحة 🗒🔓", "تم فتح الكلايش  🗒🔓"),
    }

    if is_admin and text in lock_commands:
        setting_key, reply_true, reply_false = lock_commands[text]
        current_val = settings.get(setting_key, 0)
        
        if text.startswith("اقفل"):
            if current_val == 0:
                await database.update_group_setting(message.chat.id, setting_key, 1)
                if setting_key == "anti_contact":
                    await database.update_group_setting(message.chat.id, "anti_document", 1)
                await message.reply(reply_true)
            else:
                await message.reply(reply_false)
        else:
            if current_val == 1:
                await database.update_group_setting(message.chat.id, setting_key, 0)
                if setting_key == "anti_contact":
                    await database.update_group_setting(message.chat.id, "anti_document", 0)
                await message.reply(reply_true)
            else:
                await message.reply(reply_false)
        return True

    return False


async def _process_reply_actions(message: Message, text: str, is_admin: bool, bot: Bot) -> bool:
    """معالجة إجراءات الرد للمشرفين (طرد، كتم، حضر عام، إلخ). ترجع True إذا تم التنفيذ."""
    if not is_admin or not message.reply_to_message or not text:
        return False
        
    target_user = message.reply_to_message.from_user
    if not target_user:
        return False

    if text == "طرد":
        bot_info = await get_bot_info(bot)
        if target_user.id == bot_info.id:
            await message.reply('لا يمكنك ➖❕ طردي هكذا ‼️')
        else:
            try:
                await message.chat.kick(user_id=target_user.id)
                await message.chat.unban(user_id=target_user.id)
                await message.reply(
                    'تم ✅ طرد العضو 🚹🔻',
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text=target_user.first_name or 'عضو', url=f"https://telegram.me/{target_user.username}" if target_user.username else "https://telegram.me/")]
                    ])
                )
            except Exception:
                await message.reply("❌ تعذر طرد العضو.")
        return True

    if text == "كتم":
        permissions = ChatPermissions(can_send_messages=False)
        try:
            await message.chat.restrict(user_id=target_user.id, permissions=permissions)
            await message.reply("تم ✅ كتم العضو 👤🔕")
        except Exception:
            await message.reply("❌ تعذر كتم العضو.")
        return True

    if text == "افتح الكتم":
        permissions = ChatPermissions(
            can_send_messages=True, can_send_media_messages=True,
            can_send_audios=True, can_send_documents=True,
            can_send_photos=True, can_send_videos=True,
            can_send_polls=True, can_send_other_messages=True
        )
        try:
            await message.chat.restrict(user_id=target_user.id, permissions=permissions)
            await message.reply("تم فتح الكتم 📧🔓")
        except Exception:
            await message.reply("❌ تعذر إلغاء الكتم.")
        return True

    if text == "حضر عام":
        try:
            await database.add_global_ban(target_user.id, reason="حظر عام من مشرف المجموعة")
            await message.chat.ban(user_id=target_user.id)
            await message.reply(f"العضو 🚹 : {target_user.id}\nتم ✅ حضره عام ‼️")
        except Exception:
            await message.reply("❌ تعذر الحظر العام.")
        return True

    if text == "الغاء العام":
        try:
            await database.remove_global_ban(target_user.id)
            await message.chat.unban(user_id=target_user.id)
            await message.reply(f"العضو 🚹 : @{target_user.username or 'لا يوجد'}\nتم ✅ الغاء حضره من عام ‼️ ")
        except Exception:
            await message.reply("❌ تعذر إلغاء الحظر العام.")
        return True

    return False


async def _apply_security_checks(message: Message, settings: dict, bot: Bot) -> bool:
    """تطبيق جميع فلاتر الحماية والرقابة التلقائية على الأعضاء العاديين. ترجع True إذا تم الحذف/المعالجة."""
    # === 0. فحص القفل المجدول للمجموعة ===
    if settings.get("lock_enabled", 0) == 1:
        lock_start = settings.get("lock_start", "23:00")
        lock_end = settings.get("lock_end", "06:00")
        if is_time_in_range(lock_start, lock_end):
            try:
                await message.delete()
            except Exception:
                pass
            try:
                alert = await message.answer(
                    f"🔒 عذراً {message.from_user.full_name}، المجموعة مغلقة حالياً حسب الإعدادات المجدولة (من {lock_start} إلى {lock_end})."
                )
                async def delete_alert_later(msg):
                    await asyncio.sleep(5)
                    try:
                        await msg.delete()
                    except Exception:
                        pass
                asyncio.create_task(delete_alert_later(alert))
            except Exception:
                pass
            return True

    # === 0.1. فحص الإغراق والرسائل المتكررة (Anti-Flood) ===
    if settings.get("anti_flood", 0) == 1:
        chat_id = message.chat.id
        user_id = message.from_user.id
        now_ts = time.time()
        
        if len(flood_tracker) > 100:
            inactive_keys = [k for k, v in flood_tracker.items() if not v or now_ts - v[-1] > 10]
            for k in inactive_keys:
                del flood_tracker[k]
                
        user_key = (chat_id, user_id)
        if user_key not in flood_tracker:
            flood_tracker[user_key] = []
        
        flood_tracker[user_key] = [ts for ts in flood_tracker[user_key] if now_ts - ts <= 3]
        flood_tracker[user_key].append(now_ts)
        
        if len(flood_tracker[user_key]) > 5:
            try:
                await message.delete()
            except Exception:
                pass
            try:
                restrict_perms = ChatPermissions(can_send_messages=False)
                await message.chat.restrict(user_id=user_id, permissions=restrict_perms, until_date=int(now_ts + 600))
                user_mention = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
                await message.answer(
                    f"🚫 تم كتم العضو {user_mention} تلقائياً لمدة 10 دقائق بسبب الإغراق وإرسال رسائل متكررة (أكثر من 5 رسائل في 3 ثوانٍ)."
                )
            except Exception as ex:
                logger.error(f"Failed to restrict user for flood: {ex}")
            return True

    # === 0.1أ. فحص قفل الدردشة بالكامل ===
    if settings.get("anti_chat", 0) == 1:
        try:
            await message.delete()
        except Exception:
            pass
        return True

    # === 0.2. فحص فلترة الوسائط والملصقات (Media Filter) ===
    has_media_violation = False
    media_type_label = ""
    
    if message.sticker and settings.get("anti_sticker", 0) == 1:
        has_media_violation = True
        media_type_label = "الملصقات (Stickers)"
    elif message.animation and settings.get("anti_gif", 0) == 1:
        has_media_violation = True
        media_type_label = "الصور المتحركة (GIFs)"
    elif message.photo and settings.get("anti_photo", 0) == 1:
        has_media_violation = True
        media_type_label = "الصور (Photos)"
    elif message.video and settings.get("anti_video", 0) == 1:
        has_media_violation = True
        media_type_label = "الفيديوهات (Videos)"
    elif message.document and settings.get("anti_document", 0) == 1:
        has_media_violation = True
        media_type_label = "الملفات والكتب (Documents)"
    elif (message.forward_from or message.forward_from_chat or message.forward_sender_name) and settings.get("anti_fwd", 0) == 1:
        has_media_violation = True
        media_type_label = "إعادة التوجيه (Forwarded Messages)"
    elif message.voice and settings.get("anti_voice", 0) == 1:
        has_media_violation = True
        media_type_label = "الرسائل الصوتية (Voice Messages)"
    elif message.audio and settings.get("anti_audio", 0) == 1:
        has_media_violation = True
        media_type_label = "الملفات الصوتية والموسيقى (Audio)"
    elif message.contact and settings.get("anti_contact", 0) == 1:
        has_media_violation = True
        media_type_label = "جهات الاتصال (Contacts)"
        
    if has_media_violation:
        logger.info(f"[DEBUG] Media violation detected: {media_type_label}. Deleting...")
        await _delete_and_warn(message, f"إرسال وسائط غير مسموح بها: {media_type_label}")
        return True

    text_to_check = ""
    if message.text:
        text_to_check += message.text
    if message.caption:
        text_to_check += " " + message.caption
    text_to_check = text_to_check.strip()

    # === 0.3أ. فحص الكلايش والرسائل الطويلة ===
    if text_to_check and settings.get("anti_list", 0) == 1 and len(text_to_check.split()) > 70:
        logger.info(f"[DEBUG] Long message (cliche) detected. Deleting...")
        await _delete_and_warn(message, "إرسال رسالة طويلة جداً (كليشة)")
        return True

    # === 0.3. فحص فلترة الكلمات البذيئة والشتائم (Censorship) ===
    if settings.get("censorship_enabled", 0) == 1 and text_to_check:
        banned_words_str = settings.get("banned_words", "")
        if banned_words_str:
            banned_words = []
            for part in re.split(r'[,\n\r]+', banned_words_str):
                w = part.strip().lower()
                if w:
                    banned_words.append(w)
            matched_banned = [w for w in banned_words if w in text_to_check.lower()]
            if matched_banned:
                logger.info(f"[DEBUG] Censorship match: {matched_banned}. Deleting...")
                await _delete_and_warn(message, f"استخدام ألفاظ غير لائقة ({matched_banned[0]})")
                return True

    # === 1. فحص الروابط (فوري بدون Gemini) ===
    if settings.get("anti_link", 1) == 1:
        has_link = False
        link_str = ""
        entities = message.entities or message.caption_entities
        if entities:
            for entity in entities:
                if entity.type in ("url", "text_link"):
                    has_link = True
                    start = entity.offset
                    end = entity.offset + entity.length
                    if message.text:
                        link_str = message.text[start:end]
                    elif message.caption:
                        link_str = message.caption[start:end]
                    break

        if not has_link and text_to_check:
            match = LINK_REGEX.search(text_to_check)
            if match:
                has_link = True
                link_str = match.group(0)

        if has_link:
            logger.info(f"[DEBUG] Link detected: {link_str}. Triggering _delete_and_warn...")
            reason_text = "إرسال رابط غير مسموح به"
            if link_str:
                reason_text += f" ({link_str})"
            await _delete_and_warn(message, reason_text)
            return True

    # === 2. فحص الاعلانات والسبام والارقام ===
    if settings.get("anti_spam", 1) == 1 and text_to_check:
        text_lower = text_to_check.lower()
        
        phone_match = None
        for p in QUICK_SPAM_TRIGGERS:
            m = re.search(p, text_lower)
            if m:
                phone_match = m.group(0)
                break
        
        try:
            db_keywords = await database.get_all_spam_keywords()
        except Exception as e:
            logger.error(f"Failed to fetch spam keywords from database: {e}")
            db_keywords = []
        all_spam_words = list(set(QUICK_SPAM_WORDS + db_keywords))
        
        matched_words = []
        for word in all_spam_words:
            if word in text_lower:
                matched_words.append(word)

        has_phone = phone_match is not None
        keyword_matches = len(matched_words)

        is_obvious_spam = (has_phone and keyword_matches >= 1) or (keyword_matches >= 3)

        if is_obvious_spam:
            logger.info(f"[DEBUG] Obvious ad/phone detected locally ({keyword_matches} keywords matched). Deleting...")
            reasons = []
            if has_phone:
                reasons.append(f"رقم اتصال ({phone_match})")
            if matched_words:
                words_str = "، ".join(matched_words[:3])
                reasons.append(f"كلمات إعلانية ({words_str})")
            
            reason_text = "يحتوي على " + " و ".join(reasons)
            await _delete_and_warn(message, reason_text)
            return True

        elif is_suspicious(text_to_check, all_spam_words):
            logger.info("[DEBUG] Text is suspicious. Sending to Gemini AI...")
            if settings.get("gemini_enabled", 1) == 1:
                from handlers.gemini_ai import gemini_check_message
                result = await gemini_check_message(text_to_check)
                logger.info(f"[DEBUG] Gemini decision: {result}")

                if result.get("delete", False):
                    await _delete_and_warn(message, result.get("reason", "محتوى مخالف لقواعد المجموعة"))
                    
                    spam_words = result.get("spam_words", [])
                    if spam_words:
                        logger.info(f"[DEBUG] Gemini extracted spam words to auto-learn: {spam_words}")
                        for word in spam_words:
                            try:
                                await database.add_spam_keyword(word, added_by='gemini_auto')
                            except Exception as ex:
                                logger.error(f"Failed to auto-learn spam word '{word}': {ex}")
                    return True
            else:
                logger.info("[DEBUG] Gemini disabled but message is suspicious. Deleting...")
                await _delete_and_warn(message, "محتوى إعلاني أو ترويجي مشتبه به")
                return True

    return False


def _get_auto_reply(text: str):
    """الرد على الرسائل القصيرة التي تسأل عن المساعدة أو الإعدادات أو الخاص للتوجيه العام"""
    text_clean = text.strip().lower()

    if text_clean.startswith("/"):
        return None

    words = text_clean.split()
    if len(words) > 4:
        return None

    has_help = any(w in text_clean for w in ["مساعدة", "مساعده", "مسعده", "help"])
    has_settings = any(w in text_clean for w in ["الاعدادات", "الاعدادت", "إعدادات", "إعدادت", "settings", "الإعدادات"])
    has_private = any(w in text_clean for w in ["خاص", "الخاص", "خاصني", "بالخاص", "dm"])

    if has_help or has_settings or has_private:
        return "⚠️ هذه مجموعة عامة، يرجى كتابة طلبك أو سؤالك بوضوح هنا ليتمكن الجميع من مساعدتك."

    return None


# ---- الدالة الرئيسية لمراقبة الرسائل ----
@router.message(F.chat.type.in_({"group", "supergroup"}))
async def monitor_messages(message: Message, bot: Bot):
    settings = await database.get_group_settings(message.chat.id)

    if settings.get("anti_join", 0) == 1 and (message.new_chat_members or message.left_chat_member):
        try:
            await message.delete()
        except Exception:
            pass
        return

    if not message.from_user:
        return

    if await database.is_globally_banned(message.from_user.id):
        try:
            await message.reply(
                "انت محضور عام من البوت ‼️\nيبدو انك اسئت الاستخدام 🤖❕\nتنبيه للجميع سيتم حضرك 💎\nاذا اسأت الاستخدام 💡 نرجو منكم \nعدم ❌ الاسائة داخل المجموعات التي يتواجد فيها البوت 🤖❄️",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="راسل 📬 الدعم لازالة الحضر ‼️", url="https://telegram.me/K00lil")]
                ])
            )
            await message.delete()
        except Exception:
            pass
        try:
            await message.chat.ban(user_id=message.from_user.id)
        except Exception:
            pass
        return

    me = await get_bot_info(bot)
    invite_link = None
    if message.chat.username:
        invite_link = f"https://t.me/{message.chat.username}"
    else:
        try:
            chat = await bot.get_chat(message.chat.id)
            invite_link = chat.invite_link
            if not invite_link:
                invite_link = await bot.export_chat_invite_link(message.chat.id)
        except Exception:
            pass
    await database.add_group(message.chat.id, me.id, message.chat.title, invite_link)

    is_admin = False
    is_creator = False
    try:
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        is_admin = member.status in ("administrator", "creator")
        is_creator = member.status == "creator"
    except Exception:
        pass

    text = message.text or ""

    if text:
        command_handled = await _process_text_commands(message, text, is_admin, is_creator, settings, bot)
        if command_handled:
            return

    if is_admin and message.reply_to_message and text:
        reply_handled = await _process_reply_actions(message, text, is_admin, bot)
        if reply_handled:
            return
        moderation_handled = await handle_admin_manual_moderation_reply(message, bot)
        if moderation_handled:
            return

    if is_admin:
        logger.info(f"[DEBUG] User {message.from_user.id} is an admin/owner, bypassing security filters.")
        if message.text:
            await database.log_message(
                group_id=message.chat.id,
                user_id=message.from_user.id,
                username=message.from_user.username or "",
                full_name=message.from_user.full_name,
                message_text=message.text
            )
        return

    security_handled = await _apply_security_checks(message, settings, bot)
    if security_handled:
        return

    if text:
        try:
            response = await database.get_trigger(message.chat.id, text.strip())
            if response:
                await message.reply(response)
                return
        except Exception as e:
            logger.error(f"Failed to fetch trigger: {e}")

        reply = _get_auto_reply(text)
        if reply:
            await message.reply(reply)
            return

    if text:
        await database.log_message(
            group_id=message.chat.id,
            user_id=message.from_user.id,
            username=message.from_user.username or "",
            full_name=message.from_user.full_name,
            message_text=text
        )
