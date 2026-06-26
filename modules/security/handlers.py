import re
import logging
import asyncio
from aiogram import Router, F, Bot
from aiogram.filters import Command, ChatMemberUpdatedFilter, IS_MEMBER
from aiogram.types import (
    Message, ChatMemberUpdated, InlineKeyboardMarkup,
    InlineKeyboardButton, CallbackQuery, ChatPermissions
)
from filters.admin_check import IsAdminFilter
import database

import time
from datetime import datetime

logger = logging.getLogger(__name__)
router = Router()

# تتبع زمن وصول الرسائل لمنع الإغراق
flood_tracker = {}

def is_time_in_range(start_str, end_str):
    try:
        now = datetime.now().time()
        start = datetime.strptime(start_str, "%H:%M").time()
        end = datetime.strptime(end_str, "%H:%M").time()
        if start <= end:
            return start <= now <= end
        else: # crosses midnight
            return now >= start or now <= end
    except Exception:
        return False

# ---- الكلمات المشبوهة للفلترة المحلية ----
# أرقام الهواتف والتواصل بصيغ مختلفة
QUICK_SPAM_TRIGGERS = [
    r"\b05\d{8}\b", 
    r"\b9665\d{8}\b", 
    r"\b\+9665\d{8}\b", 
    r"\b009665\d{8}\b",
    r"\b05\d{1}\s?\d{3}\s?\d{4}\b", # مثل 055 123 4567
    r"\b\+?966\s?5\d{8}\b",
    r"\b\+?\d{3}[-\s]?\d{3}[-\s]?\d{4}\b" # أرقام جوال عامة
]

QUICK_SPAM_WORDS = [
    # كلمات ترويجية للمعلنين والاعلانات
    "تواصل", "راسلني", "تواصل معي", "واتساب", "سناب", "سناب شات", "انستقرام", "تيك توك",
    "حل واجب", "حل كويز", "تسليم", "مشروع", "تقرير", "بحوث", "واجبات", "مشاريع", "كويزات",
    "اشتراك", "قناة", "قروب", "خدمة", "سعر", "تكليف", "تمويل", "قرض", "تسويق", "ارقام", "أرقام",
    "اتصال", "تليجرام", "تيليجرام", "رابط المجموعه", "كود خصم", "خصم", "متوفر الان", "يوجد لدينا",
    "تصميم", "اعلانات", "اعلان", "أرخص", "ضمان", "مضمون", "شحن", "بيع", "شراء", "حسابات", "ربح",
    "وظيفة", "وظائف", "توظيف", "فرصة", "فرص", "راتب"
]

# تعبير نمطي قوي لكشف الروابط
LINK_REGEX = re.compile(
    r'(https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9.-]+\.(com|net|org|info|xyz|me|edu|co|sa|ly|app|link|club|site|online|tech|vip|top|gov)\b([/?#][^\s]*)?|t\.me/[^\s]+|wa\.me/[^\s]+)',
    re.IGNORECASE
)

def is_suspicious(text: str, custom_words: list = None) -> bool:
    """فحص سريع محلي: هل الرسالة مشبوهة لإرسالها إلى Gemini؟"""
    if not text:
        return False
    text_lower = text.lower()
    
    words_to_use = custom_words if custom_words is not None else QUICK_SPAM_WORDS
    keyword_matches = sum(1 for word in words_to_use if word in text_lower)
    has_phone = any(re.search(p, text_lower) for p in QUICK_SPAM_TRIGGERS)
    
    if (has_phone and keyword_matches >= 1) or keyword_matches >= 2:
        return True
    
    return False


def build_main_keyboard(bot_username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ لوحة التحكم بالحماية والقيود 🛡️", callback_data="help")],
        [InlineKeyboardButton(text="الاوامر العامة والادارة 🗒", callback_data="help_offc")],
        [InlineKeyboardButton(text="اضفني الى مجموعتك 🚹➕", url=f"https://telegram.me/{bot_username}?startgroup=")],
        [InlineKeyboardButton(text="شارك البوت 🤖🍁", switch_inline_query="")],
        [InlineKeyboardButton(text="الدعم والمساعدة ❔", url="https://telegram.me/K00lil")]
    ])


def build_help_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛡️ إعدادات الحماية الأساسية (صفحة 1)", callback_data="settings_page_1")],
        [InlineKeyboardButton(text="🖼️ إعدادات منع الوسائط (صفحة 2)", callback_data="settings_page_2")],
        [InlineKeyboardButton(text="🔒 إعدادات القيود المتقدمة (صفحة 3)", callback_data="settings_page_3")],
        [InlineKeyboardButton(text="🗒️ الأوامر العامة والإدارة", callback_data="help_offc")],
        [InlineKeyboardButton(text="الرئيسية 🏠", callback_data="home")]
    ])


def build_close_keyboard() -> InlineKeyboardMarkup:
    # Deprecated/Mapped to Settings page 1
    return build_help_keyboard()


def build_open_keyboard() -> InlineKeyboardMarkup:
    # Deprecated/Mapped to Settings page 2
    return build_help_keyboard()


def build_offc_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="معلومات المجموعة 📋", callback_data="cmd_info"), InlineKeyboardButton(text="عدد الرسائل 📈", callback_data="cmd_count")],
        [InlineKeyboardButton(text="الوقت 🕛", callback_data="cmd_time"), InlineKeyboardButton(text="التاريخ 📆", callback_data="cmd_date")],
        [InlineKeyboardButton(text="طرد عضو 👢", callback_data="cmd_kick"), InlineKeyboardButton(text="كتم عضو 🔇", callback_data="cmd_mute")],
        [InlineKeyboardButton(text="إلغاء كتم 🔊", callback_data="cmd_unmute"), InlineKeyboardButton(text="حظر عام 🚫", callback_data="cmd_banall")],
        [InlineKeyboardButton(text="إلغاء حضر عام 🟢", callback_data="cmd_unbanall"), InlineKeyboardButton(text="غادِر المجموعة 🚪", callback_data="cmd_leave")],
        [InlineKeyboardButton(text="عودة للمساعدة 🔙", callback_data="help")]
    ])


def get_settings_keyboard_p1(settings: dict) -> InlineKeyboardMarkup:
    def status(val):
        return "🟢 مفعل" if val == 1 else "🔴 معطل"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👋 الترحيب بالأعضاء", callback_data="toggle_1_welcome_enabled"),
            InlineKeyboardButton(text=status(settings.get("welcome_enabled", 1)), callback_data="toggle_1_welcome_enabled")
        ],
        [
            InlineKeyboardButton(text="🛡️ كابتشا التحقق", callback_data="toggle_1_captcha_enabled"),
            InlineKeyboardButton(text=status(settings.get("captcha_enabled", 0)), callback_data="toggle_1_captcha_enabled")
        ],
        [
            InlineKeyboardButton(text="🔗 منع الروابط", callback_data="toggle_1_anti_link"),
            InlineKeyboardButton(text=status(settings.get("anti_link", 1)), callback_data="toggle_1_anti_link")
        ],
        [
            InlineKeyboardButton(text="🚫 منع السبام/الإعلانات", callback_data="toggle_1_anti_spam"),
            InlineKeyboardButton(text=status(settings.get("anti_spam", 1)), callback_data="toggle_1_anti_spam")
        ],
        [
            InlineKeyboardButton(text="🧠 الذكاء الاصطناعي Gemini", callback_data="toggle_1_gemini_enabled"),
            InlineKeyboardButton(text=status(settings.get("gemini_enabled", 1)), callback_data="toggle_1_gemini_enabled")
        ],
        [
            InlineKeyboardButton(text="⏱️ منع الإغراق", callback_data="toggle_1_anti_flood"),
            InlineKeyboardButton(text=status(settings.get("anti_flood", 0)), callback_data="toggle_1_anti_flood")
        ],
        [
            InlineKeyboardButton(text="🙊 منع الشتائم والكلمات", callback_data="toggle_1_censorship_enabled"),
            InlineKeyboardButton(text=status(settings.get("censorship_enabled", 0)), callback_data="toggle_1_censorship_enabled")
        ],
        [
            InlineKeyboardButton(text="🔒 القفل المجدول للمجموعة", callback_data="toggle_1_lock_enabled"),
            InlineKeyboardButton(text=status(settings.get("lock_enabled", 0)), callback_data="toggle_1_lock_enabled")
        ],
        [
            InlineKeyboardButton(text="➡️ الانتقال لصفحة 2", callback_data="settings_page_2")
        ],
        [InlineKeyboardButton(text="❌ إغلاق الإعدادات", callback_data="close_settings")]
    ])
    return keyboard


def get_settings_keyboard_p2(settings: dict) -> InlineKeyboardMarkup:
    def status(val):
        return "🟢 مفعل" if val == 1 else "🔴 معطل"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🧸 منع الملصقات (Stickers)", callback_data="toggle_2_anti_sticker"),
            InlineKeyboardButton(text=status(settings.get("anti_sticker", 0)), callback_data="toggle_2_anti_sticker")
        ],
        [
            InlineKeyboardButton(text="🎬 منع الصور المتحركة (GIF)", callback_data="toggle_2_anti_gif"),
            InlineKeyboardButton(text=status(settings.get("anti_gif", 0)), callback_data="toggle_2_anti_gif")
        ],
        [
            InlineKeyboardButton(text="🖼️ منع إرسال الصور", callback_data="toggle_2_anti_photo"),
            InlineKeyboardButton(text=status(settings.get("anti_photo", 0)), callback_data="toggle_2_anti_photo")
        ],
        [
            InlineKeyboardButton(text="📹 منع مقاطع الفيديو", callback_data="toggle_2_anti_video"),
            InlineKeyboardButton(text=status(settings.get("anti_video", 0)), callback_data="toggle_2_anti_video")
        ],
        [
            InlineKeyboardButton(text="📂 منع رفع الملفات والكتب", callback_data="toggle_2_anti_document"),
            InlineKeyboardButton(text=status(settings.get("anti_document", 0)), callback_data="toggle_2_anti_document")
        ],
        [
            InlineKeyboardButton(text="🎙️ منع الرسائل الصوتية", callback_data="toggle_2_anti_voice"),
            InlineKeyboardButton(text=status(settings.get("anti_voice", 0)), callback_data="toggle_2_anti_voice")
        ],
        [
            InlineKeyboardButton(text="🎵 منع الملفات الموسيقية", callback_data="toggle_2_anti_audio"),
            InlineKeyboardButton(text=status(settings.get("anti_audio", 0)), callback_data="toggle_2_anti_audio")
        ],
        [
            InlineKeyboardButton(text="⬅️ صفحة 1", callback_data="settings_page_1"),
            InlineKeyboardButton(text="➡️ صفحة 3", callback_data="settings_page_3")
        ],
        [InlineKeyboardButton(text="❌ إغلاق الإعدادات", callback_data="close_settings")]
    ])
    return keyboard


def get_settings_keyboard_p3(settings: dict) -> InlineKeyboardMarkup:
    def status(val):
        return "🟢 مفعل" if val == 1 else "🔴 معطل"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 منع إعادة التوجيه (Forward)", callback_data="toggle_3_anti_fwd"),
            InlineKeyboardButton(text=status(settings.get("anti_fwd", 0)), callback_data="toggle_3_anti_fwd")
        ],
        [
            InlineKeyboardButton(text="📱 منع جهات الاتصال", callback_data="toggle_3_anti_contact"),
            InlineKeyboardButton(text=status(settings.get("anti_contact", 0)), callback_data="toggle_3_anti_contact")
        ],
        [
            InlineKeyboardButton(text="📧 قفل الدردشة بالكامل", callback_data="toggle_3_anti_chat"),
            InlineKeyboardButton(text=status(settings.get("anti_chat", 0)), callback_data="toggle_3_anti_chat")
        ],
        [
            InlineKeyboardButton(text="📛 كتم إشعارات الدخول/الخروج", callback_data="toggle_3_anti_join"),
            InlineKeyboardButton(text=status(settings.get("anti_join", 0)), callback_data="toggle_3_anti_join")
        ],
        [
            InlineKeyboardButton(text="🗒️ منع الكلايش والرسائل الطويلة", callback_data="toggle_3_anti_list"),
            InlineKeyboardButton(text=status(settings.get("anti_list", 0)), callback_data="toggle_3_anti_list")
        ],
        [
            InlineKeyboardButton(text="⬅️ العودة لصفحة 2", callback_data="settings_page_2")
        ],
        [InlineKeyboardButton(text="❌ إغلاق الإعدادات", callback_data="close_settings")]
    ])
    return keyboard


# ---- عرض الاعدادات ----
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
    
    # Toggle documents along with contact settings if anti_contact was modified
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


# ---- معالجة أزرار البوت المأخوذة من securty.py ----

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
            
    bot_user = await bot.get_me()
    
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
        "cont": "anti_contact",  # will toggle both anti_contact and anti_document
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

    # Update database
    await database.update_group_setting(chat_id, target_setting, desired_val)
    if target == "cont":
        # Toggle document lock as well
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
                # Check if callback.from_user is owner (creator) or administrator before letting bot leave
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


# ---- الترحيب والكابتشا عند انضمام عضو جديد ----
@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=IS_MEMBER))
async def on_user_join(event: ChatMemberUpdated, bot: Bot):
    new_member = event.new_chat_member.user
    if new_member.is_bot:
        try:
            inviter = event.from_user
            inviter_member = await event.chat.get_member(inviter.id)
            if inviter_member.status not in ("administrator", "creator"):
                await event.chat.ban(user_id=new_member.id)
                await bot.send_message(
                    chat_id=event.chat.id,
                    text=f"تم طرد البوت {new_member.full_name} تلقائياً. إضافة البوتات للمشرفين فقط!"
                )
        except Exception:
            pass
        return

    settings = await database.get_group_settings(event.chat.id)

    # تفعيل كابتشا التحقق للأعضاء الجدد
    if settings.get("captcha_enabled", 0) == 1:
        restrict_perms = ChatPermissions(can_send_messages=False)
        try:
            await event.chat.restrict(user_id=new_member.id, permissions=restrict_perms)
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="اضغط هنا للتحقق انك لست بوت",
                    callback_data=f"verify_{new_member.id}"
                )
            ]])
            await bot.send_message(
                chat_id=event.chat.id,
                text=f"مرحباً {new_member.full_name}! يرجى الضغط على زر التحقق للمشاركة في المجموعة.",
                reply_markup=keyboard
            )
        except Exception:
            pass
    elif settings.get("welcome_enabled", 1) == 1:
        template = settings.get("welcome_message", "أهلاً بك {name} في المجموعة! 🌹")
        await bot.send_message(chat_id=event.chat.id, text=template.format(name=new_member.full_name))


@router.callback_query(F.data.startswith("verify_"))
async def verify_new_user(callback: CallbackQuery):
    target_user_id = int(callback.data.split("_")[1])
    if callback.from_user.id != target_user_id:
        await callback.answer("هذا التحقق ليس لك!", show_alert=True)
        return

    permissions = ChatPermissions(
        can_send_messages=True, can_send_media_messages=True,
        can_send_audios=True, can_send_documents=True,
        can_send_photos=True, can_send_videos=True,
        can_send_polls=True, can_send_other_messages=True
    )
    try:
        await callback.message.chat.restrict(user_id=callback.from_user.id, permissions=permissions)
        await callback.message.delete()
        settings = await database.get_group_settings(callback.message.chat.id)
        template = settings.get("welcome_message", "أهلاً بك {name} في المجموعة! 🌹")
        await callback.message.answer(f"تم التحقق بنجاح!\n{template.format(name=callback.from_user.full_name)}")
    except Exception as e:
        await callback.answer(f"فشل التحقق: {str(e)}", show_alert=True)


# ---- أمر يدوي للمشرفين لحذف الإعلانات والتعلم منها عبر الرد (Reply) ----
@router.message(F.chat.type.in_({"group", "supergroup"}), F.reply_to_message)
async def admin_manual_moderation_reply(message: Message, bot: Bot):
    if not message.text:
        return

    text_clean = message.text.strip().lower()
    
    # 1) فحص محلي سريع وسهل للكلمات المباشرة لتجنب استدعاء الـ API غير الضروري
    admin_commands = ["اعلان", "إعلان", "محتوى اعلاني", "محتوى إعلاني", "مشبوه", "حساب مشبوه", "حذف", "احذفه", "سبام", "spam", "شيل", "امسح"]
    is_command = any(cmd == text_clean or f" {cmd} " in f" {text_clean} " for cmd in admin_commands)
    
    # 2) إذا لم تتطابق الكلمات المباشرة، نقوم بفحص نية المشرف عبر ذكاء Gemini الاصطناعي (إذا كان مفعلاً)
    if not is_command:
        settings = await database.get_group_settings(message.chat.id)
        if settings.get("gemini_enabled", 1) == 1:
            from handlers.gemini_ai import gemini_check_admin_intent
            is_command = await gemini_check_admin_intent(message.text)
            
    if not is_command:
        return

    # التحقق من صلاحيات المرسل (يجب أن يكون مشرفاً)
    try:
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        if member.status not in ("administrator", "creator"):
            return # ليس مشرفاً، نتجاهل الرسالة
    except Exception:
        return

    # الرسالة الأصلية المراد حذفها
    target_msg = message.reply_to_message
    if not target_msg or not target_msg.from_user:
        return

    # استثناء المشرفين من الحذف الذاتي
    try:
        target_member = await bot.get_chat_member(message.chat.id, target_msg.from_user.id)
        if target_member.status in ("administrator", "creator"):
            await message.reply("❌ لا يمكن حذف رسائل المشرفين الآخرين.")
            return
    except Exception:
        pass

    logger.info(f"[DEBUG] Admin {message.from_user.id} triggered manual moderation on msg {target_msg.message_id}")

    # تحديد سبب الحذف بناءً على أمر المشرف
    reason = "محتوى إعلاني مخالف (إشراف يدوي)"
    if "مشبوه" in text_clean:
        reason = "حساب مشتبه به وسلوك مخالف (إشراف يدوي)"
    elif "حذف" in text_clean or "احذفه" in text_clean:
        reason = "محتوى مخالف لقواعد المجموعة (إشراف يدوي)"

    # حذف رسالة المشرف أولاً للحفاظ على نظافة القروب
    try:
        await message.delete()
    except Exception:
        pass

    # حذف الرسالة المستهدفة وتوجيه التنبيه والتحذير للعضو
    await _delete_and_warn(target_msg, reason)

    # التعلم التلقائي من الرسالة المحذوفة
    target_text = (target_msg.text or "") + " " + (target_msg.caption or "")
    target_text = target_text.strip()
    
    if target_text:
        # 1) استخلاص الكلمات محلياً (تجنب حروف الجر الشائعة والكلمات القصيرة)
        arabic_stop_words = {
            "في", "من", "على", "إلى", "الى", "عن", "مع", "هذا", "هذه", "الذي", "التي", "هنا",
            "أو", "او", "أن", "ان", "لا", "ما", "لم", "لن", "ثم", "بل", "لكن", "يا", "و", "بـ", "لـ"
        }
        
        words = re.findall(r'\b\w{3,15}\b', target_text.lower())
        new_keywords = []
        for w in words:
            # التحقق من أن الكلمة ليست من حروف الجر وليست رقماً مجرداً
            if w not in arabic_stop_words and not w.isdigit():
                try:
                    await database.add_spam_keyword(w, added_by=f'admin_manual_{message.from_user.id}')
                    new_keywords.append(w)
                except Exception:
                    pass
        
        logger.info(f"[DEBUG] Auto-learned keywords from manual block: {new_keywords}")

        # 2) إذا كان Gemini مفعلاً، نقوم بالاستعانة به في الخلفية لتنظيف واستخلاص العبارات المترابطة بدقة
        settings = await database.get_group_settings(message.chat.id)
        if settings.get("gemini_enabled", 1) == 1:
            async def learn_in_background():
                try:
                    from handlers.gemini_ai import gemini_check_message
                    res = await gemini_check_message(target_text)
                    spam_words = res.get("spam_words", [])
                    for sw in spam_words:
                        await database.add_spam_keyword(sw, added_by='gemini_auto_manual')
                    logger.info(f"[DEBUG] Background Gemini extraction learned: {spam_words}")
                except Exception as ex:
                    logger.error(f"Background Gemini learning failed: {ex}")
            
            asyncio.create_task(learn_in_background())


# ---- الدالة الرئيسية لمراقبة الرسائل ----
@router.message(F.chat.type.in_({"group", "supergroup"}))
async def monitor_messages(message: Message, bot: Bot):
    # جلب إعدادات المجموعة مبكراً
    settings = await database.get_group_settings(message.chat.id)

    # === 0.0أ. فحص إشعارات الدخول والخروج (anti_join) ===
    if settings.get("anti_join", 0) == 1 and (message.new_chat_members or message.left_chat_member):
        try:
            await message.delete()
        except Exception:
            pass
        return

    if not message.from_user:
        return

    # === 0.0ب. فحص الحظر العام ===
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

    # تسجيل المجموعة والربط بالبوت تلقائياً عند استلام أي رسالة
    me = await bot.get_me()
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

    # التحقق من رتبة العضو (مشرف أو منشئ)
    is_admin = False
    is_creator = False
    try:
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        is_admin = member.status in ("administrator", "creator")
        is_creator = member.status == "creator"
    except Exception:
        pass

    # === 0.0ج. معالجة الأوامر النصية وتفعيل القفل بالرسائل ===
    text = message.text or ""
    if text:
        # Clean commands (removing bot username suffix, e.g., /start@botname -> /start)
        if text.startswith("/"):
            parts = text.split(" ", 1)
            command = parts[0].split("@", 1)[0]
            rest = parts[1] if len(parts) > 1 else ""
            text = command + (" " + rest if rest else "")
            if text in {"/help", "/settings", "/setting"}:
                text = "مساعدة"

        # 1. Start command
        if message.chat.type == "private" and text == "/start":
            bot_user = await bot.get_me()
            await message.answer(
                "اهلا بك عزيزي 🚹 في البوت الرسمي 🔶\nالخاص لحماية المجموعات 👥🔒\nيعمل باللغة العربية 📕 ويحتوي \nعلى جميع الاشياء التي تحتاجها 💎\nلعمل مجموعة امنة وجيدة ‼️",
                reply_markup=build_main_keyboard(bot_user.username)
            )
            return

        if message.chat.type in {"group", "supergroup"} and text == "/start":
            await message.answer("اهلا بك ☘ ارسل مساعدة لمعرفة 💎 كيفية استخدام البوت 🤖🍁")
            return

        # 2. Help command
        if text == "مساعدة":
            await message.reply("كيفية استخدام البوت 📋🔻", reply_markup=build_help_keyboard())
            return

        # Settings command via text
        if is_admin and text in {"اعدادات", "الاعدادات", "الإعدادات", "اعدادات البوت", "الاعدادات العامة", "الضبط"}:
            await show_group_settings(message)
            return

        # 3. Time and Date commands
        if text == "الوقت":
            now = datetime.now()
            await message.reply(f"🕛 البلد : السودان/المملكة\n🕛 الساعة : {now.strftime('%I')}\n🕛 الدقيقة : {now.strftime('%M')}")
            return

        if text == "التاريخ":
            today = datetime.now().date()
            await message.reply(
                f"📆 البلد : السودان/المملكة \n📆  السنة : {today.year} \n📆 الشهر : {today.month} \n📆 اليوم : {today.day}"
            )
            return

        # 4. Message count
        if text == "عدد الرسائل" and message.chat.type in {"group", "supergroup"}:
            count_label = "مجموعتك متفاعلة 💯" if message.message_id > 1000 else "للاسف❗️مجموعتك غير متفاعلة 🚹💭"
            await message.reply(f"عدد 📈 رسائل المجموعة 👥🔹  : *{message.message_id}*\n{count_label}", parse_mode="Markdown")
            return

        # 5. User/Group Info
        if text == "معلومات":
            target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
            username = target.username or "غير موجود"
            await message.reply(
                f"💭الاسم : {target.first_name}\n💭المعرف : @{username}\n💭الايدي : {target.id}\n💭اسم المجموعة : {message.chat.title or 'خاصة'}\n💭ايدي المجموعة : {message.chat.id}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text='تابع جديدنا 📪', callback_data='channel')]
                ])
            )
            return

        # 6. Kick self (leave group for members)
        if text == "غادر" and message.chat.type in {"group", "supergroup"}:
            if not is_admin:
                try:
                    await message.chat.kick(user_id=message.from_user.id)
                    await message.chat.unban(user_id=message.from_user.id)
                    await message.reply("وداعا عزيزي ✨")
                except Exception:
                    pass
            else:
                await message.reply("عذرا ‼️ انت مشرف في المجموعة 🚹🔒")
            return

        # 7. Leave group (creator only)
        if text == "غادر المجموعة" and message.chat.type in {"group", "supergroup"}:
            if is_creator:
                await message.reply("غادرت المجموعة بناءً على طلب المنشئ 👋")
                try:
                    await message.chat.leave()
                except Exception:
                    pass
            else:
                await message.reply('عذرا ‼️ فقط منشئ المجموعة 👥 يمكنه استخدام هاذا الامر ♻️🔺')
            return

        # 8. Admin lock/unlock text commands
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
            return

        # 9. Admin reply-to actions
        if is_admin and message.reply_to_message:
            target_user = message.reply_to_message.from_user
            
            if text == "طرد":
                if target_user.id == (await bot.get_me()).id:
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
                return

            if text == "كتم":
                permissions = ChatPermissions(can_send_messages=False)
                try:
                    await message.chat.restrict(user_id=target_user.id, permissions=permissions)
                    await message.reply("تم ✅ كتم العضو 👤🔕")
                except Exception:
                    await message.reply("❌ تعذر كتم العضو.")
                return

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
                return

            if text == "حضر عام":
                try:
                    await database.add_global_ban(target_user.id, reason="حظر عام من مشرف المجموعة")
                    await message.chat.ban(user_id=target_user.id)
                    await message.reply(f"العضو 🚹 : {target_user.id}\nتم ✅ حضره عام ‼️")
                except Exception:
                    await message.reply("❌ تعذر الحظر العام.")
                return

            if text == "الغاء العام":
                try:
                    await database.remove_global_ban(target_user.id)
                    await message.chat.unban(user_id=target_user.id)
                    await message.reply(f"العضو 🚹 : @{target_user.username or 'لا يوجد'}\nتم ✅ الغاء حضره من عام ‼️ ")
                except Exception:
                    await message.reply("❌ تعذر إلغاء الحظر العام.")
                return

    # استثناء المشرفين من الفلترة
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

    logger.info(f"[DEBUG] Group {message.chat.id} security settings: {settings}")

    # === 0. فحص القفل المجدول للمجموعة ===
    if settings.get("lock_enabled", 0) == 1:
        lock_start = settings.get("lock_start", "23:00")
        lock_end = settings.get("lock_end", "06:00")
        if is_time_in_range(lock_start, lock_end):
            try:
                await message.delete()
            except Exception:
                pass
            # إرسال تنبيه مؤقت للعضو
            try:
                alert = await message.answer(
                    f"🔒 عذراً {message.from_user.full_name}، المجموعة مغلقة حالياً حسب الإعدادات المجدولة (من {lock_start} إلى {lock_end})."
                )
                # حذف التنبيه بعد 5 ثوانٍ لمنع تراكم التنبيهات
                async def delete_alert_later(msg):
                    await asyncio.sleep(5)
                    try:
                        await msg.delete()
                    except Exception:
                        pass
                asyncio.create_task(delete_alert_later(alert))
            except Exception:
                pass
            return

    # === 0.1. فحص الإغراق والرسائل المتكررة (Anti-Flood) ===
    if settings.get("anti_flood", 0) == 1:
        chat_id = message.chat.id
        user_id = message.from_user.id
        now_ts = time.time()
        
        user_key = (chat_id, user_id)
        if user_key not in flood_tracker:
            flood_tracker[user_key] = []
        
        # تنظيف الطوابع الزمنية القديمة (أكبر من 3 ثوانٍ)
        flood_tracker[user_key] = [ts for ts in flood_tracker[user_key] if now_ts - ts <= 3]
        flood_tracker[user_key].append(now_ts)
        
        if len(flood_tracker[user_key]) > 5:
            # تم كشف الإغراق
            try:
                await message.delete()
            except Exception:
                pass
            
            # كتم العضو لمدة 10 دقائق
            try:
                restrict_perms = ChatPermissions(can_send_messages=False)
                await message.chat.restrict(user_id=user_id, permissions=restrict_perms, until_date=int(now_ts + 600))
                user_mention = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
                await message.answer(
                    f"🚫 تم كتم العضو {user_mention} تلقائياً لمدة 10 دقائق بسبب الإغراق وإرسال رسائل متكررة (أكثر من 5 رسائل في 3 ثوانٍ)."
                )
            except Exception as ex:
                logger.error(f"Failed to restrict user for flood: {ex}")
            return

    # === 0.1أ. فحص قفل الدردشة بالكامل ===
    if settings.get("anti_chat", 0) == 1:
        try:
            await message.delete()
        except Exception:
            pass
        return

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
        return

    # تجميع النص والوصف للفحص الشامل (للروابط والإعلانات والأرقام)
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
        return

    # === 0.3. فحص فلترة الكلمات البذيئة والشتائم (Censorship) ===
    if settings.get("censorship_enabled", 0) == 1 and text_to_check:
        banned_words_str = settings.get("banned_words", "")
        if banned_words_str:
            banned_words = [w.strip().lower() for w in banned_words_str.split(",") if w.strip()]
            matched_banned = [w for w in banned_words if w in text_to_check.lower()]
            if matched_banned:
                logger.info(f"[DEBUG] Censorship match: {matched_banned}. Deleting...")
                await _delete_and_warn(message, f"استخدام ألفاظ غير لائقة ({matched_banned[0]})")
                return

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
            return

    # === 2. فحص الاعلانات والسبام والارقام ===
    if settings.get("anti_spam", 1) == 1 and text_to_check:
        text_lower = text_to_check.lower()
        
        # استخراج رقم الهاتف المطابق
        phone_match = None
        for p in QUICK_SPAM_TRIGGERS:
            m = re.search(p, text_lower)
            if m:
                phone_match = m.group(0)
                break
        
        # جلب الكلمات المشبوهة الديناميكية من قاعدة البيانات ودمجها مع القائمة الثابتة
        try:
            db_keywords = await database.get_all_spam_keywords()
        except Exception as e:
            logger.error(f"Failed to fetch spam keywords from database: {e}")
            db_keywords = []
        all_spam_words = list(set(QUICK_SPAM_WORDS + db_keywords))
        
        # حساب وتحديد الكلمات الإعلانية المطابقة
        matched_words = []
        for word in all_spam_words:
            if word in text_lower:
                matched_words.append(word)

        has_phone = phone_match is not None
        keyword_matches = len(matched_words)

        # 1) كشف فوري محلي للإعلانات والأرقام الترويحية الواضحة (منعاً لتسريب أرقام التواصل الخارجي أو تكرار الإعلانات)
        is_obvious_spam = (has_phone and keyword_matches >= 1) or (keyword_matches >= 3) or has_phone

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
            return

        # 2) فحص إضافي عبر Gemini AI للرسائل المشبوهة (كلمتين مشبوهتين أو أكثر)
        elif is_suspicious(text_to_check, all_spam_words):
            logger.info("[DEBUG] Text is suspicious. Sending to Gemini AI...")
            if settings.get("gemini_enabled", 1) == 1:
                from handlers.gemini_ai import gemini_check_message
                result = await gemini_check_message(text_to_check)
                logger.info(f"[DEBUG] Gemini decision: {result}")

                if result.get("delete", False):
                    await _delete_and_warn(message, result.get("reason", "محتوى مخالف لقواعد المجموعة"))
                    
                    # === التعلم التلقائي: استخلاص الكلمات المشبوهة وتخزينها في قاعدة البيانات تلقائياً ===
                    spam_words = result.get("spam_words", [])
                    if spam_words:
                        logger.info(f"[DEBUG] Gemini extracted spam words to auto-learn: {spam_words}")
                        for word in spam_words:
                            try:
                                await database.add_spam_keyword(word, added_by='gemini_auto')
                            except Exception as ex:
                                logger.error(f"Failed to auto-learn spam word '{word}': {ex}")
                    return
            else:
                logger.info("[DEBUG] Gemini disabled but message is suspicious. Deleting...")
                await _delete_and_warn(message, "محتوى إعلاني أو ترويجي مشتبه به")
                return

    # === 3. الردود التلقائية (الكلمات المفتاحية المخصصة + الرد التلقائي العام المدمج) ===
    if message.text:
        # أولاً: فحص الكلمات المفتاحية المخصصة من قاعدة البيانات
        custom_reply = await database.get_trigger(message.chat.id, message.text.strip())
        if custom_reply:
            await message.reply(custom_reply)
            return

        # ثانياً: فحص الردود التلقائية العامة المحددة مسبقاً للكلمات التوجيهية
        reply = _get_auto_reply(message.text.strip())
        if reply:
            await message.reply(reply)

    # === 4. تسجيل الرسالة في السجل ===
    if message.text:
        await database.log_message(
            group_id=message.chat.id,
            user_id=message.from_user.id,
            username=message.from_user.username or "",
            full_name=message.from_user.full_name,
            message_text=message.text
        )


def _get_auto_reply(text: str):
    """الرد على الرسائل القصيرة التي تسأل عن المساعدة أو الإعدادات أو الخاص للتوجيه العام"""
    text_clean = text.strip().lower()

    if text_clean.startswith("/"):
        return None

    # تجاوز الرسائل الطويلة
    words = text_clean.split()
    if len(words) > 4:
        return None

    # التحقق من الكلمات المفتاحية
    has_help = any(w in text_clean for w in ["مساعدة", "مساعده", "مسعده", "help"])
    has_settings = any(w in text_clean for w in ["الاعدادات", "الاعدادت", "إعدادات", "إعدادت", "settings", "الإعدادات"])
    has_private = any(w in text_clean for w in ["خاص", "الخاص", "خاصني", "بالخاص", "dm"])

    if has_help or has_settings or has_private:
        return "⚠️ هذه مجموعة عامة، يرجى كتابة طلبك أو سؤالك بوضوح هنا ليتمكن الجميع من مساعدتك."

    return None


async def _delete_and_warn(message: Message, reason: str):
    """حذف الرسالة وإرسال تنبيه منسق وتسجيل التحذير"""
    logger.info(f"[DEBUG] _delete_and_warn called for reason: {reason}")
    try:
        await message.delete()
        logger.info("[DEBUG] Message deleted successfully.")
    except Exception as e:
        logger.error(f"[DEBUG] Failed to delete message: {e}")

    # جلب تحذيراته الحالية قبل الزيادة لمعرفة هل لديه سوابق مخالفات
    try:
        prior_warnings = await database.get_warnings(message.chat.id, message.from_user.id)
    except Exception:
        prior_warnings = 0

    # تسجيل التحذير الجديد وزيادة العداد
    warn_count = 1
    try:
        warn_count = await database.add_warning(message.chat.id, message.from_user.id)
        logger.info(f"[DEBUG] Warning added. User {message.from_user.id} has {warn_count}/10 warnings.")
    except Exception as e:
        logger.error(f"[DEBUG] Failed to add warning: {e}")

    user_mention = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name

    # صياغة وسم الحساب المشبوه إذا كان لدى المستخدم سوابق إعلانية أو مخالفات
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

    # التحقق من حد الحظر التلقائي (10 مخالفات)
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


# ---- معالجة انضمام البوت أو مغادرته للمجموعات ----
@router.my_chat_member()
async def on_my_chat_member_update(event: ChatMemberUpdated, bot: Bot):
    new_status = event.new_chat_member.status
    old_status = event.old_chat_member.status
    
    logger.info(f"🤖 Bot status changed in chat {event.chat.id} ({event.chat.title}): {old_status} -> {new_status}")
    
    if new_status in ("left", "kicked"):
        logger.info(f"🛑 Bot was removed/kicked from group {event.chat.id}")
        try:
            await database.remove_group(event.chat.id)
            logger.info(f"✅ Group {event.chat.id} database records removed.")
        except Exception as e:
            logger.error(f"❌ Failed to remove group {event.chat.id}: {e}")
    elif new_status in ("member", "administrator"):
        logger.info(f"🟢 Bot was added to group {event.chat.id} ({event.chat.title})")
        try:
            me = await bot.get_me()
            invite_link = None
            if event.chat.username:
                invite_link = f"https://t.me/{event.chat.username}"
            else:
                try:
                    chat = await bot.get_chat(event.chat.id)
                    invite_link = chat.invite_link
                    if not invite_link:
                        invite_link = await bot.export_chat_invite_link(event.chat.id)
                except Exception:
                    pass
            await database.add_group(event.chat.id, me.id, event.chat.title, invite_link)
            logger.info(f"✅ Group {event.chat.id} successfully added/updated in DB.")
        except Exception as e:
            logger.error(f"❌ Failed to add group {event.chat.id} to DB: {e}")
