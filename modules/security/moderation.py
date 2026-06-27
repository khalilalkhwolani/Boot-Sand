from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from filters.admin_check import IsAdminFilter
import database
import logging
import asyncio

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("spamwords"), IsAdminFilter(), F.chat.type.in_({"group", "supergroup"}))
async def list_spam_words(message: Message):
    try:
        keywords = await database.get_all_spam_keywords_details()
        if not keywords:
            await message.reply("📋 لا توجد كلمات مشبوهة مضافة في قاعدة البيانات حالياً.")
            return
        
        words_list = []
        for kw in sorted(keywords, key=lambda x: (x.get('is_approved', 0), x.get('weight', 0)), reverse=True):
            word = kw.get('keyword', '')
            is_approved = kw.get('is_approved', 0)
            weight = kw.get('weight', 1)
            
            if is_approved == 1 or weight >= 3:
                status_icon = "✅"
                approved_label = "معتمدة"
            else:
                status_icon = "⏳"
                approved_label = f"تحت التجميع {weight}/3"
                
            words_list.append(f"{status_icon} **{word}** ({approved_label})")
            
        full_list = "\n".join(words_list)
        await message.reply(
            f"📋 **قائمة الكلمات المشبوهة وحالة التعلم**:\n\n"
            f"{full_list}\n\n"
            f"💡 الكلمات المسبوقة بـ (⏳) تحتاج تكرارها 3 مرات ليتم فلترتها تلقائياً، أو يمكنك اعتمادها يدوياً باستخدام أمر:\n`/approvespam [الكلمة]`",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error listing spam words: {e}")
        await message.reply("❌ حدث خطأ أثناء جلب قائمة الكلمات المشبوهة.")

@router.message(Command("removespam"), IsAdminFilter(), F.chat.type.in_({"group", "supergroup"}))
async def remove_spam_word(message: Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("⚠️ يرجى كتابة الكلمة التي تريد حذفها بعد الأمر. مثال:\n`/removespam كلمة`", parse_mode="Markdown")
        return
    
    word_to_remove = args[1].strip().lower()
    try:
        removed = await database.remove_spam_keyword(word_to_remove)
        if removed:
            await message.reply(f"✅ تم حذف الكلمة « **{word_to_remove}** » بنجاح من قاعدة البيانات ولم تعد مشبوهة.", parse_mode="Markdown")
        else:
            await message.reply(f"❌ الكلمة « **{word_to_remove}** » غير موجودة بالفعل في قائمة الكلمات المشبوهة.", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error removing spam word: {e}")
        await message.reply("❌ حدث خطأ أثناء محاولة حذف الكلمة.")

@router.message(Command("addspam"), IsAdminFilter(), F.chat.type.in_({"group", "supergroup"}))
async def add_spam_word(message: Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("⚠️ يرجى كتابة الكلمة التي تريد إضافتها بعد الأمر. مثال:\n`/addspam كلمة`", parse_mode="Markdown")
        return
    
    word_to_add = args[1].strip().lower()
    try:
        added = await database.add_spam_keyword(word_to_add, added_by=f"admin_manual_{message.from_user.id}")
        if added:
            await message.reply(f"✅ تم إضافة الكلمة « **{word_to_add}** » بنجاح واعتمادها للفلترة المباشرة.", parse_mode="Markdown")
        else:
            await message.reply(f"❌ فشل إضافة الكلمة أو أنها مضافة بالفعل.", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error adding spam word: {e}")
        await message.reply("❌ حدث خطأ أثناء إضافة الكلمة.")

@router.message(Command("approvespam"), IsAdminFilter(), F.chat.type.in_({"group", "supergroup"}))
async def approve_spam_word(message: Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("⚠️ يرجى كتابة الكلمة التي تريد اعتمادها بعد الأمر. مثال:\n`/approvespam كلمة`", parse_mode="Markdown")
        return
    
    word_to_approve = args[1].strip().lower()
    try:
        approved = await database.approve_spam_keyword(word_to_approve)
        if approved:
            await message.reply(f"✅ تم اعتماد الكلمة « **{word_to_approve}** » بنجاح للفلترة المباشرة وترقيتها.", parse_mode="Markdown")
        else:
            await message.reply(f"❌ الكلمة غير موجودة في قاعدة البيانات لإعتمادها.", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error approving spam word: {e}")
        await message.reply("❌ حدث خطأ أثناء اعتماد الكلمة.")

@router.message(Command("learnstats"), IsAdminFilter(), F.chat.type.in_({"group", "supergroup"}))
async def show_learn_stats(message: Message):
    try:
        stats = await database.get_learn_stats()
        await message.reply(
            f"🧠 **إحصائيات نظام التعلم وحماية المجموعة**:\n\n"
            f"📊 **مجموع الكلمات المخزنة**: {stats['total']}\n"
            f"✅ **الكلمات النشطة/المعتمدة**: {stats['approved']}\n"
            f"⏳ **الكلمات قيد الجمع والتجميع**: {stats['pending']}",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error showing learn stats: {e}")
        await message.reply("❌ حدث خطأ أثناء جلب إحصائيات التعلم.")

@router.message(Command("resetlearn"), IsAdminFilter(), F.chat.type.in_({"group", "supergroup"}))
async def reset_learned_spam_words(message: Message):
    try:
        success = await database.reset_learned_keywords()
        if success:
            await message.reply("🧹 تم تصفير الكلمات المتعلمة تلقائياً (التي لم تعتمد ولم يزد وزنها عن 3) وحذفها بنجاح.")
        else:
            await message.reply("❌ فشل تصفير الكلمات المتعلمة.")
    except Exception as e:
        logger.error(f"Error resetting learned keywords: {e}")
        await message.reply("❌ حدث خطأ أثناء محاولة تصفير الكلمات.")


# ---- الدالة المساعدة لحذف الرسالة وإرسال تنبيه منسق وتسجيل التحذير ----
async def _delete_and_warn(message: Message, reason: str):
    logger.info(f"[DEBUG] _delete_and_warn called for reason: {reason}")
    try:
        await message.delete()
        logger.info("[DEBUG] Message deleted successfully.")
    except Exception as e:
        logger.error(f"[DEBUG] Failed to delete message: {e}")

    try:
        prior_warnings = await database.get_warnings(message.chat.id, message.from_user.id)
    except Exception:
        prior_warnings = 0

    warn_count = 1
    try:
        warn_count = await database.add_warning(message.chat.id, message.from_user.id)
        logger.info(f"[DEBUG] Warning added. User {message.from_user.id} has {warn_count}/10 warnings.")
    except Exception as e:
        logger.error(f"[DEBUG] Failed to add warning: {e}")

    user_mention = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name

    suspicious_badge = ""
    if prior_warnings > 0:
        suspicious_badge = "⚠️ **تصنيف الحساب**: حساب مشبوه (لديه سوابق إعلانات ومخالفات)\n"

    warn_text = (
        f"👑 العضو « {user_mention} »\n"
        f"🚨 **المخالفة**: {reason} (تم حذف الرسالة تلقائياً)\n"
        f"{suspicious_badge}"
        f"📊 **مجموع التحذيرات**: {warn_count} من 10\n"
        f"-\n"
        f"🛡️ بوت سَنَد لحماية المجموعات | 🇸🇦"
    )

    try:
        await message.answer(warn_text)
        logger.info("[DEBUG] Warning message sent to chat.")
    except Exception as e:
        logger.error(f"[DEBUG] Failed to send warning message: {e}")

    if warn_count >= 10:
        try:
            await message.chat.ban(user_id=message.from_user.id)
            await database.reset_warnings(message.chat.id, message.from_user.id)
            await message.answer(
                f"🚫 تم حظر العضو {message.from_user.full_name} تلقائياً بعد وصوله لـ 10 مخالفات متكررة."
            )
            logger.info(f"[DEBUG] User {message.from_user.id} banned due to 10 warnings.")
        except Exception as e:
            logger.error(f"[DEBUG] Warning/ban database logic failed: {e}")


# ---- أمر يدوي للمشرفين لحذف الإعلانات والتعلم منها عبر الرد (Reply) ----
async def handle_admin_manual_moderation_reply(message: Message, bot: Bot) -> bool:
    if not message.text:
        return False

    text_clean = message.text.strip().lower()
    
    admin_commands = ["اعلان", "إعلان", "محتوى اعلاني", "محتوى إعلاني", "مشبوه", "حساب مشبوه", "حذف", "احذفه", "سبام", "spam", "شيل", "امسح"]
    is_command = any(cmd == text_clean or f" {cmd} " in f" {text_clean} " for cmd in admin_commands)
    
    if not is_command:
        settings = await database.get_group_settings(message.chat.id)
        if settings.get("gemini_enabled", 1) == 1:
            from handlers.gemini_ai import gemini_check_admin_intent
            is_command = await gemini_check_admin_intent(message.text)
            
    if not is_command:
        return False

    try:
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        if member.status not in ("administrator", "creator"):
            return False
    except Exception:
        return False

    target_msg = message.reply_to_message
    if not target_msg or not target_msg.from_user:
        return False

    try:
        target_member = await bot.get_chat_member(message.chat.id, target_msg.from_user.id)
        if target_member.status in ("administrator", "creator"):
            await message.reply("❌ لا يمكن حذف رسائل المشرفين الآخرين.")
            return True
    except Exception:
        pass

    logger.info(f"[DEBUG] Admin {message.from_user.id} triggered manual moderation on msg {target_msg.message_id}")

    reason = "محتوى إعلاني مخالف (إشراف يدوي)"
    if "مشبوه" in text_clean:
        reason = "حساب مشتبه به وسلوك مخالف (إشراف يدوي)"
    elif "حذف" in text_clean or "احذفه" in text_clean:
        reason = "محتوى مخالف لقواعد المجموعة (إشراف يدوي)"

    try:
        await message.delete()
    except Exception:
        pass

    await _delete_and_warn(target_msg, reason)

    target_text = (target_msg.text or "") + " " + (target_msg.caption or "")
    target_text = target_text.strip()
    
    if target_text:
        settings = await database.get_group_settings(message.chat.id)
        if settings.get("gemini_enabled", 1) == 1:
            async def learn_in_background():
                try:
                    from handlers.gemini_ai import gemini_check_message
                    res = await gemini_check_message(target_text)
                    spam_words = res.get("spam_words", [])
                    for sw in spam_words:
                        await database.add_spam_keyword(sw, added_by=f'gemini_auto_manual_{message.from_user.id}')
                    logger.info(f"[DEBUG] Background Gemini extraction learned: {spam_words}")
                except Exception as ex:
                    logger.error(f"Background Gemini learning failed: {ex}")
            
            asyncio.create_task(learn_in_background())
            
    return True
