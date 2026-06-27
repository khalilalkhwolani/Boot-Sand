from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

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
    return build_help_keyboard()

def build_open_keyboard() -> InlineKeyboardMarkup:
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
            InlineKeyboardButton(text="⚠️ كتم إشعارات الدخول/الخروج", callback_data="toggle_3_anti_join"),
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
