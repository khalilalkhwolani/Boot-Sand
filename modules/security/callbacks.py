from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from filters.admin_check import IsAdminFilter
import database
import logging
from datetime import datetime

from .keyboards import (
    build_main_keyboard, build_help_keyboard, build_offc_keyboard,
    get_settings_keyboard_p1, get_settings_keyboard_p2, get_settings_keyboard_p3
)
from .utils import get_bot_info

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("settings", "setting"), IsAdminFilter(), F.chat.type.in_({"group", "supergroup"}))
async def show_group_settings(message: Message):
    settings = await database.get_group_settings(message.chat.id)
    await message.reply(
        f"🛡️ **لوحة إعدادات الحماية لمجموعة**:\n« {message.chat.title} »\n\n**القسم**: 1️⃣ الحماية والرقابة الأساسية",
        reply_markup=get_settings_keyboard_p1(settings),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("settings_page_"))
async def process_settings_page(callback: CallbackQuery, bot: Bot):
    if callback.message.chat.type not in ("group", "supergroup"):
        await callback.answer("⚠️ إعدادات الحماية يتم ضبطها داخل المجموعة مباشرة لضمان الخصوصية. يرجى تفعيل لوحة الإعدادات في المجموعة بإرسال: /settings", show_alert=True)
        return

    try:
        member = await bot.get_chat_member(callback.message.chat.id, callback.from_user.id)
        if member.status not in ("administrator", "creator"):
            await callback.answer("هذا الإجراء للمشرفين فقط!", show_alert=True)
            return
    except Exception:
        await callback.answer("خطأ في التحقق من الصلاحيات.", show_alert=True)
        return

    page_num = int(callback.data.replace("settings_page_", ""))
    settings = await database.get_group_settings(callback.message.chat.id)
    
    if page_num == 1:
        await callback.message.edit_text(
            f"🛡️ **لوحة إعدادات الحماية لمجموعة**:\n« {callback.message.chat.title} »\n\n**القسم**: 1️⃣ الحماية والرقابة الأساسية",
            reply_markup=get_settings_keyboard_p1(settings),
            parse_mode="Markdown"
        )
    elif page_num == 2:
        await callback.message.edit_text(
            f"🛡️ **لوحة إعدادات الحماية لمجموعة**:\n« {callback.message.chat.title} »\n\n**القسم**: 2️⃣ فلترة الوسائط والمرفقات",
            reply_markup=get_settings_keyboard_p2(settings),
            parse_mode="Markdown"
        )
    elif page_num == 3:
        await callback.message.edit_text(
            f"🛡️ **لوحة إعدادات الحماية لمجموعة**:\n« {callback.message.chat.title} »\n\n**القسم**: 3️⃣ قيود المجموعة المتقدمة",
            reply_markup=get_settings_keyboard_p3(settings),
            parse_mode="Markdown"
        )
    await callback.answer()

@router.callback_query(F.data.startswith("toggle_"))
async def process_toggle_setting(callback: CallbackQuery, bot: Bot):
    if callback.message.chat.type not in ("group", "supergroup"):
        await callback.answer("⚠️ إعدادات الحماية يتم ضبطها داخل المجموعة مباشرة لضمان الخصوصية. يرجى تفعيل لوحة الإعدادات في المجموعة بإرسال: /settings", show_alert=True)
        return

    try:
        member = await bot.get_chat_member(callback.message.chat.id, callback.from_user.id)
        if member.status not in ("administrator", "creator"):
            await callback.answer("هذا الإجراء للمشرفين فقط!", show_alert=True)
            return
    except Exception:
        await callback.answer("خطأ في التحقق من الصلاحيات.", show_alert=True)
        return

    parts = callback.data.split("_")
    if len(parts) >= 3 and parts[1].isdigit():
        page_num = int(parts[1])
        setting_key = "_".join(parts[2:])
    else:
        page_num = 1
        setting_key = "_".join(parts[1:])

    settings = await database.get_group_settings(callback.message.chat.id)
    current_val = settings.get(setting_key, 0)
    new_val = 1 if current_val == 0 else 0

    await database.update_group_setting(callback.message.chat.id, setting_key, new_val)
    
    if setting_key == "anti_contact":
        await database.update_group_setting(callback.message.chat.id, "anti_document", new_val)
        
    updated_settings = await database.get_group_settings(callback.message.chat.id)
    
    if page_num == 1:
        await callback.message.edit_reply_markup(reply_markup=get_settings_keyboard_p1(updated_settings))
    elif page_num == 2:
        await callback.message.edit_reply_markup(reply_markup=get_settings_keyboard_p2(updated_settings))
    elif page_num == 3:
        await callback.message.edit_reply_markup(reply_markup=get_settings_keyboard_p3(updated_settings))
        
    await callback.answer("تم تحديث خيار الحماية!")

@router.callback_query(F.data == "close_settings")
async def close_settings_callback(callback: CallbackQuery):
    await callback.message.delete()

@router.callback_query(F.data.in_({"channel", "channel2", "home", "help", "help_close", "help_open", "help_offc", "offc", "omar"}))
async def securty_menus_callback(callback: CallbackQuery, bot: Bot):
    data = callback.data
    chat_id = callback.message.chat.id
    
    if data in {"help", "help_close", "help_open", "help_offc", "offc", "omar"}:
        try:
            member = await bot.get_chat_member(chat_id, callback.from_user.id)
            if member.status not in ("administrator", "creator"):
                await callback.answer("عذراً، هذه القائمة مخصصة للمشرفين فقط! 🔒", show_alert=True)
                return
        except Exception:
            await callback.answer("خطأ في التحقق من الصلاحيات.", show_alert=True)
            return
            
    bot_user = await get_bot_info(bot)
    
    if data in {"channel", "channel2"}:
        await callback.message.edit_text(
            'تابعنا عبر الروابط التالية 📩',
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text='🌐قناة الدعم📱', url='https://telegram.me/K00lil')],
                [InlineKeyboardButton(text='👑للمزيد👑', url='https://telegram.me/K00lil')],
                [InlineKeyboardButton(text='عودة 🏠 ', callback_data='home')]
            ])
        )
    elif data == "home":
        await callback.message.edit_text(
            "اهلا بك عزيزي 🚹 في البوت الرسمي 🔶\nالخاص لحماية المجموعات 👥🔒\nيعمل باللغة العربية 📕 ويحتوي \n"
            "على جميع الاشياء التي تحتاجها 💎\nلعمل مجموعة امنة وجيدة ‼️",
            reply_markup=build_main_keyboard(bot_user.username)
        )
    elif data == "help":
        await callback.message.edit_text("كيفية استخدام البوت 📋🔻", reply_markup=build_help_keyboard())
    elif data == "help_close":
        if callback.message.chat.type not in ("group", "supergroup"):
            await callback.answer("⚠️ إعدادات الحماية يتم ضبطها داخل المجموعة مباشرة لضمان الخصوصية. يرجى تفعيل لوحة الإعدادات في المجموعة بإرسال: /settings", show_alert=True)
            return
        settings = await database.get_group_settings(callback.message.chat.id)
        await callback.message.edit_text(
            f"🛡️ **لوحة إعدادات الحماية لمجموعة**:\n« {callback.message.chat.title} »\n\n**القسم**: 1️⃣ الحماية والرقابة الأساسية",
            reply_markup=get_settings_keyboard_p1(settings),
            parse_mode="Markdown"
        )
    elif data == "help_open":
        if callback.message.chat.type not in ("group", "supergroup"):
            await callback.answer("⚠️ إعدادات الحماية يتم ضبطها داخل المجموعة مباشرة لضمان الخصوصية. يرجى تفعيل لوحة الإعدادات في المجموعة بإرسال: /settings", show_alert=True)
            return
        settings = await database.get_group_settings(callback.message.chat.id)
        await callback.message.edit_text(
            f"🛡️ **لوحة إعدادات الحماية لمجموعة**:\n« {callback.message.chat.title} »\n\n**القسم**: 2️⃣ فلترة الوسائط والمرفقات",
            reply_markup=get_settings_keyboard_p2(settings),
            parse_mode="Markdown"
        )
    elif data in {"help_offc", "offc"}:
        await callback.message.edit_text("الاوامر العامة في المجموعة ‼️🔻", reply_markup=build_offc_keyboard())
    elif data == "omar":
        await callback.answer("هذا الزر مجرد عرض للأمر. استخدم نص الأمر أو الأزرار العملية بدلاً منه.", show_alert=True)
    await callback.answer()

@router.callback_query(F.data.startswith("lock_") | F.data.startswith("unlock_"))
async def securty_locks_callback(callback: CallbackQuery, bot: Bot):
    data = callback.data
    chat_id = callback.message.chat.id

    if callback.message.chat.type not in ("group", "supergroup"):
        await callback.answer("هذا الزر يعمل فقط داخل المجموعة. افتح البوت في المجموعة ثم اضغط الزر.", show_alert=True)
        return
    
    try:
        member = await bot.get_chat_member(chat_id, callback.from_user.id)
        if member.status not in ("administrator", "creator"):
            await callback.answer("يجب أن تكون مشرفاً في المجموعة لتفعيل هذا الزر.", show_alert=True)
            return
    except Exception:
        await callback.answer("خطأ في التحقق من الصلاحيات.", show_alert=True)
        return

    action, target = data.split("_", 1)
    
    lock_mappings = {
        "link": "anti_link",
        "photo": "anti_photo",
        "fwd": "anti_fwd",
        "sticker": "anti_sticker",
        "list": "anti_list",
        "voice": "anti_voice",
        "audio": "anti_audio",
        "cont": "anti_contact",
        "chat": "anti_chat",
        "join": "anti_join",
    }

    if target not in lock_mappings:
        await callback.answer("الزر غير مدعوم حالياً.", show_alert=True)
        return

    target_setting = lock_mappings[target]
    settings = await database.get_group_settings(chat_id)
    
    current_val = settings.get(target_setting, 0)
    desired_val = 1 if action == "lock" else 0

    arabic_labels = {
        "link": "الروابط",
        "photo": "الصور",
        "fwd": "التوجيه",
        "sticker": "الملصقات",
        "list": "الكلايش",
        "voice": "الصوتيات",
        "audio": "الاغاني",
        "cont": "جهات الاتصال والملفات",
        "chat": "الدردشة",
        "join": "الاشعارات",
    }

    label = arabic_labels[target]

    if current_val == desired_val:
        if action == "lock":
            await callback.answer(f"هذا الخيار مقفل بالفعل بالفعل ✅", show_alert=True)
        else:
            await callback.answer(f"هذا الخيار مفتوح بالفعل بالفعل ✅", show_alert=True)
        return

    await database.update_group_setting(chat_id, target_setting, desired_val)
    if target == "cont":
        await database.update_group_setting(chat_id, "anti_document", desired_val)

    if action == "lock":
        await callback.answer(f"تم قفل {label} بنجاح ✅", show_alert=True)
    else:
        await callback.answer(f"تم فتح {label} بنجاح ✅", show_alert=True)

@router.callback_query(F.data.startswith("cmd_"))
async def securty_commands_callback(callback: CallbackQuery, bot: Bot):
    data = callback.data
    chat_id = callback.message.chat.id

    try:
        member = await bot.get_chat_member(chat_id, callback.from_user.id)
        if member.status not in ("administrator", "creator"):
            await callback.answer("عذراً، هذا الإجراء مخصص للمشرفين فقط! 🔒", show_alert=True)
            return
    except Exception:
        await callback.answer("خطأ في التحقق من الصلاحيات.", show_alert=True)
        return

    if data == "cmd_info":
        if callback.message.chat.type in ("group", "supergroup"):
            try:
                group = await bot.get_chat(chat_id)
                count = await bot.get_chat_member_count(chat_id)
                await callback.message.reply(
                    f"📌 اسم المجموعة: {group.title or 'غير معروف'}\n📌 معرف المجموعة: {chat_id}\n📌 عدد الاعضاء: {count}"
                )
                await callback.answer()
            except Exception:
                await callback.answer("حدث خطأ أثناء جلب معلومات المجموعة.", show_alert=True)
        else:
            await callback.answer("استخدم هذا الزر داخل مجموعة لعرض معلوماتها.", show_alert=True)
            
    elif data == "cmd_time":
        now = datetime.now()
        await callback.answer(f"🕛 الوقت الآن: {now.strftime('%H:%M')}", show_alert=True)
        
    elif data == "cmd_date":
        today = datetime.now().date()
        await callback.answer(f"📅 التاريخ: {today.year}/{today.month}/{today.day}", show_alert=True)
        
    elif data == "cmd_count":
        if callback.message.chat.type in ("group", "supergroup"):
            await callback.message.reply(f"عدد الرسائل حتى الآن في هذه المجموعة هو: {callback.message.message_id}")
            await callback.answer()
        else:
            await callback.answer("استخدم هذا الزر داخل مجموعة لعرض عدد الرسائل.", show_alert=True)
            
    elif data == "cmd_kick":
        await callback.answer("للطرد: قم بالرد على رسالة العضو بكلمة طرد.", show_alert=True)
        
    elif data == "cmd_mute":
        await callback.answer("لكتم عضو: قم بالرد على رسالة العضو بكلمة كتم.", show_alert=True)
        
    elif data == "cmd_unmute":
        await callback.answer("لإلغاء كتم: قم بالرد على رسالة العضو بكلمة افتح الكتم.", show_alert=True)
        
    elif data == "cmd_banall":
        await callback.answer("لحظر عام: قم بالرد على رسالة العضو بكلمة حضر عام.", show_alert=True)
        
    elif data == "cmd_unbanall":
        await callback.answer("لإلغاء الحظر العام: قم بالرد على رسالة العضو بكلمة الغاء العام.", show_alert=True)
        
    elif data == "cmd_leave":
        if callback.message.chat.type in ("group", "supergroup"):
            try:
                member = await bot.get_chat_member(chat_id, callback.from_user.id)
                if member.status != "creator":
                    await callback.answer("عذراً، فقط منشئ المجموعة يمكنه طرد البوت.", show_alert=True)
                    return
                await callback.message.chat.leave()
                await callback.answer("غادر البوت المجموعة بنجاح.", show_alert=True)
            except Exception:
                await callback.answer("تعذر على البوت مغادرة المجموعة.", show_alert=True)
        else:
            await callback.answer("يمكن أن يعمل هذا الزر فقط داخل مجموعة.", show_alert=True)
