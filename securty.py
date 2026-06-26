import os
import re
import logging
import asyncio
from datetime import datetime, date
from aiogram import Bot, Dispatcher, exceptions, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

TG_DIR = "tg"
STATE_FILES = {
    "sticker": "sticker.txt",
    "photo": "photo.txt",
    "fwd": "fwd.txt",
    "link": "link.txt",
    "voice": "voice.txt",
    "audio": "audio.txt",
    "gif": "gif.txt",
    "cont": "cont.txt",
    "chat": "chat.txt",
    "join": "join.txt",
    "list": "list.txt",
    "silent": "silent.txt",
    "start": "start.txt",
    "banall": "banall.txt",
}

ADMIN_IDS = config.ADMIN_IDS if hasattr(config, "ADMIN_IDS") else []
BOT_TOKEN = config.BOT_TOKEN
BOT_USERNAME = os.getenv("BOT_USERNAME", "khl1404bot")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is required in config.py or environment")

bot = Bot(token=BOT_TOKEN)
DP = Dispatcher()

os.makedirs(TG_DIR, exist_ok=True)
for filename in STATE_FILES.values():
    path = os.path.join(TG_DIR, filename)
    if not os.path.exists(path):
        open(path, "a", encoding="utf-8").close()


def _path(name: str) -> str:
    return os.path.join(TG_DIR, STATE_FILES[name])


def read_set(name: str) -> set:
    try:
        with open(_path(name), "r", encoding="utf-8") as f:
            return {line.strip() for line in f if line.strip()}
    except FileNotFoundError:
        return set()


def write_set(name: str, values: set):
    with open(_path(name), "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(str(v) for v in values if str(v).strip())))


def append_one(name: str, value: str):
    items = read_set(name)
    if str(value) not in items:
        items.add(str(value))
        write_set(name, items)


def remove_one(name: str, value: str):
    items = read_set(name)
    if str(value) in items:
        items.remove(str(value))
        write_set(name, items)


async def get_user_status(chat_id: int, user_id: int) -> str:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status
    except Exception:
        return "unknown"


def is_admin_status(status: str) -> bool:
    return status in ("administrator", "creator")


def contains_link(text: str) -> bool:
    if not text:
        return False
    patterns = [r"https?://", r"t\.me", r"telegram\.me", r"www\."]
    text_lower = text.lower()
    if any(p in text_lower for p in ["t.me", "telegram.me"]):
        return True
    return bool(re.search(r"https?://|http?://|www\.[^\s]+", text_lower))


def build_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="اوامر القفل والفتح 🔒🔓", callback_data="help_close")],
        [InlineKeyboardButton(text="الاوامر العامة 🗒", callback_data="help_offc")],
        [InlineKeyboardButton(text="اضفني الى مجموعتك 🚹➕", url=f"https://telegram.me/{BOT_USERNAME}?startgroup=")],
        [InlineKeyboardButton(text="شارك البوت 🤖🍁", switch_inline_query="")],
        [InlineKeyboardButton(text="الدعم ❔", url="https://telegram.me/K00lil")]
    ])


def build_help_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="اوامر القفل 🔒", callback_data="help_close")],
        [InlineKeyboardButton(text="اوامر الفتح 🔓", callback_data="help_open")],
        [InlineKeyboardButton(text="الاوامر العامة 🗒", callback_data="help_offc")],
        [InlineKeyboardButton(text="الرئيسية 🏠", callback_data="home")]
    ])


def build_close_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="قفل الروابط", callback_data="lock_link"), InlineKeyboardButton(text="قفل الصور", callback_data="lock_photo")],
        [InlineKeyboardButton(text="قفل التوجيه", callback_data="lock_fwd"), InlineKeyboardButton(text="قفل الملصقات", callback_data="lock_sticker")],
        [InlineKeyboardButton(text="قفل الكلايش", callback_data="lock_list"), InlineKeyboardButton(text="قفل الصوتيات", callback_data="lock_voice")],
        [InlineKeyboardButton(text="قفل الاغاني", callback_data="lock_audio"), InlineKeyboardButton(text="قفل جهات الاتصال", callback_data="lock_cont")],
        [InlineKeyboardButton(text="قفل الدردشة", callback_data="lock_chat"), InlineKeyboardButton(text="قفل الاشعارات", callback_data="lock_join")],
        [InlineKeyboardButton(text="عرض اوامر الفتح 🔓", callback_data="help_open")],
        [InlineKeyboardButton(text="عودة للمساعدة 🔙", callback_data="help")]
    ])


def build_open_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="فتح الروابط", callback_data="unlock_link"), InlineKeyboardButton(text="فتح الصور", callback_data="unlock_photo")],
        [InlineKeyboardButton(text="فتح التوجيه", callback_data="unlock_fwd"), InlineKeyboardButton(text="فتح الملصقات", callback_data="unlock_sticker")],
        [InlineKeyboardButton(text="فتح الكلايش", callback_data="unlock_list"), InlineKeyboardButton(text="فتح الصوتيات", callback_data="unlock_voice")],
        [InlineKeyboardButton(text="فتح الاغاني", callback_data="unlock_audio"), InlineKeyboardButton(text="فتح جهات الاتصال", callback_data="unlock_cont")],
        [InlineKeyboardButton(text="فتح الدردشة", callback_data="unlock_chat"), InlineKeyboardButton(text="فتح الاشعارات", callback_data="unlock_join")],
        [InlineKeyboardButton(text="عرض اوامر القفل 🔒", callback_data="help_close")],
        [InlineKeyboardButton(text="عودة للمساعدة 🔙", callback_data="help")]
    ])


def build_offc_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="معلومات المجموعة", callback_data="cmd_info"), InlineKeyboardButton(text="عدد الرسائل", callback_data="cmd_count")],
        [InlineKeyboardButton(text="الوقت", callback_data="cmd_time"), InlineKeyboardButton(text="التاريخ", callback_data="cmd_date")],
        [InlineKeyboardButton(text="طرد عضو", callback_data="cmd_kick"), InlineKeyboardButton(text="كتم عضو", callback_data="cmd_mute")],
        [InlineKeyboardButton(text="إلغاء كتم", callback_data="cmd_unmute"), InlineKeyboardButton(text="حظر عام", callback_data="cmd_banall")],
        [InlineKeyboardButton(text="إلغاء حضر عام", callback_data="cmd_unbanall"), InlineKeyboardButton(text="غادِر المجموعة", callback_data="cmd_leave")],
        [InlineKeyboardButton(text="عودة للمساعدة 🔙", callback_data="help")]
    ])


async def safe_delete_message(chat_id: int, message_id: int):
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except exceptions.TelegramBadRequest:
        pass
    except exceptions.TelegramRetryAfter:
        pass
    except exceptions.TelegramAPIError:
        pass


async def is_group_admin(chat_id: int, user_id: int) -> bool:
    status = await get_user_status(chat_id, user_id)
    return is_admin_status(status)


async def change_lock_state(chat_id: int, name: str, lock: bool) -> bool:
    if lock:
        if str(chat_id) not in read_set(name):
            append_one(name, chat_id)
            return True
        return False
    if str(chat_id) in read_set(name):
        remove_one(name, chat_id)
        return True
    return False


@DP.message()
async def all_messages_handler(message: types.Message):
    text = message.text or ""
    status = await get_user_status(message.chat.id, message.from_user.id)
    is_admin = is_admin_status(status)
    normal_member = status == "member"

    if text.startswith("/"):
        parts = text.split(" ", 1)
        command = parts[0].split("@", 1)[0]
        rest = parts[1] if len(parts) > 1 else ""
        text = command + (" " + rest if rest else "")

        if text == "/help":
            text = "مساعدة"
        elif text == "/settings":
            text = "مساعدة"
        elif text == "/status":
            await message.reply(f"البوت يعمل الآن ✅\nاسم البوت: @{BOT_USERNAME}")
            return
        elif text == "/cancel":
            await message.reply("تم إلغاء الأمر.")
            return
        elif text == "/create":
            await message.reply("أمر الإنشاء غير متوفر في هذا الإصدار.")
            return

    if message.chat.type == "private" and text == "/start":
        await message.answer(
            "اهلا بك عزيزي 🚹 في البوت الرسمي 🔶\nالخاص لحماية المجموعات 👥🔒\nيعمل بل لغة العربية 📕 ويحتوي \nعلى جميع الاشياء التي تحتاجها 💎\nلعمل مجموعة امنة وجيدة ‼️",
            reply_markup=build_main_keyboard()
        )
        append_one("start", message.from_user.id)
        return

    if message.chat.type in {"group", "supergroup"} and text == "/start":
        await message.answer("اهلا بك ☘ ارسل مساعدة لمعرفة 💎 كيفية استخدام البوت 🤖🍁")
        append_one("start", message.chat.id)
        return

    if text and message.chat.type == "supergroup":
        append_one("start", message.chat.id)

    if text and message.chat.type == "private":
        append_one("start", message.from_user.id)

    if text == "مساعدة":
        await message.reply("كيفية استخدام البوت 📋🔻", reply_markup=build_help_keyboard())
        return

    if text == "الوقت":
        now = datetime.now()
        await message.reply(f"🕛 البلد : السودان\n🕛 الساعة : {now.strftime('%I')}\n🕛 الدقيقة : {now.strftime('%M')}")
        return

    if text == "التاريخ":
        today = date.today()
        await message.reply(
            f"📆 البلد : السودان \n📆  السنة : {today.year} \n📆 الشهر : {today.month} \n📆 اليوم : {today.day}"
        )
        return

    if text == "عدد الرسائل" and message.chat.type == "supergroup":
        count_label = "مجموعتك متفاعلة 💯" if message.message_id > 1000 else "للاسف❗️مجموعتك غير متفاعلة 🚹💭"
        await message.reply(f"عدد 📈 رسائل المجموعة 👥🔹  : *{message.message_id}*\n{count_label}", parse_mode="Markdown")
        return

    if text == "غادر" and normal_member and message.chat.type == "supergroup":
        try:
            await message.chat.kick(user_id=message.from_user.id)
        except Exception:
            pass
        await message.reply("وداعا عزيزي ✨")
        return

    if text == "غادر" and not normal_member and message.chat.type == "supergroup":
        await message.reply("عذرا ‼️ انت مشرف في المجموعة 🚹🔒")
        return

    if text == "غادر المجموعة":
        member_status = await get_user_status(message.chat.id, message.from_user.id)
        if member_status == "creator":
            try:
                await message.chat.kick(user_id=(await bot.get_me()).id)
            except Exception:
                pass
        else:
            await message.reply('عذرا ‼️ فقط منشئ المجموعة 👥 يمكنه استخدام هاذا الامر ♻️🔺')
        return

    if text == "معلومات" and not message.reply_to_message:
        username = message.from_user.username or "غير موجود"
        await message.reply(
            f"💭الاسم : {message.from_user.first_name}\n💭المعرف : @{username}\n💭الايدي : {message.from_user.id}\n💭اسم المجموعة : {message.chat.title or 'خاصة'}\n💭ايدي المجموعة : {message.chat.id}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text='تابع جديدنا 📪', callback_data='channel')]
            ])
        )
        return

    if text == "الغاء العام" and is_admin and message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        remove_one("banall", target_id)
        await message.reply(f"العضو 🚹 : @{message.reply_to_message.from_user.username or 'لا يوجد'}\nتم ✅ الغاء حضره من عام ‼️ ")
        return

    if text == "حضر عام" and is_admin and message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        append_one("banall", target_id)
        await message.reply(f"العضو 🚹 : {target_id}\nتم ✅ حضره عام ‼️")
        return

    if text.startswith("/bc") and is_admin:
        payload = text.split("/bc", 1)[1].strip()
        if payload:
            start_set = read_set("start")
            for chat_id in start_set:
                try:
                    await bot.send_message(chat_id=int(chat_id), text=payload)
                except Exception:
                    pass
            await message.reply("تم ارسال الرسالة الى الجميع.")
        return

    if message.reply_to_message and text == "طرد" and is_admin:
        target = message.reply_to_message.from_user
        if target and target.id != (await bot.get_me()).id:
            try:
                await message.chat.kick(user_id=target.id)
            except Exception:
                pass
            await message.reply(
                'تم ✅ طرد العضو 🚹🔻',
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=target.first_name or 'عضو', url=f"https://telegram.me/{target.username}" if target.username else "https://telegram.me/")]
                ])
            )
        elif target and target.id == (await bot.get_me()).id:
            await message.reply('لا يمكنك ➖❕ طردي هكذا ‼️')
        return

    if message.reply_to_message and text == "الغاء الحضر" and is_admin:
        target = message.reply_to_message.from_user
        if target:
            remove_one("banall", target.id)
            await message.reply(
                'تم ✅ الغاء الحضر عن العضو 🚹🔻',
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=target.first_name or 'عضو', url=f"https://telegram.me/{target.username}" if target.username else "https://telegram.me/")]
                ])
            )
        return

    # General content restrictions for group users
    if message.chat.type in ("group", "supergroup") and not is_admin:
        if message.sticker and str(message.chat.id) in read_set("sticker"):
            await safe_delete_message(message.chat.id, message.message_id)
            return
        if message.photo and str(message.chat.id) in read_set("photo"):
            await safe_delete_message(message.chat.id, message.message_id)
            return
        if message.voice and str(message.chat.id) in read_set("voice"):
            await safe_delete_message(message.chat.id, message.message_id)
            return
        if message.audio and str(message.chat.id) in read_set("audio"):
            await safe_delete_message(message.chat.id, message.message_id)
            return
        if message.contact and str(message.chat.id) in read_set("cont"):
            await safe_delete_message(message.chat.id, message.message_id)
            return
        if message.document and str(message.chat.id) in read_set("cont"):
            await safe_delete_message(message.chat.id, message.message_id)
            return
        if message.forward_from or message.forward_from_chat or message.forward_sender_name:
            if str(message.chat.id) in read_set("fwd"):
                await safe_delete_message(message.chat.id, message.message_id)
                return
        if text and contains_link(text) and str(message.chat.id) in read_set("link"):
            await safe_delete_message(message.chat.id, message.message_id)
            return
        if text and str(message.chat.id) in read_set("chat"):
            await safe_delete_message(message.chat.id, message.message_id)
            return
        if len(text.split()) > 70 and str(message.chat.id) in read_set("list"):
            await safe_delete_message(message.chat.id, message.message_id)
            return

    if message.reply_to_message and text == "معلومات":
        target = message.reply_to_message.from_user
        if target:
            await message.reply(f"💭الايدي : {target.id}\n💭اليوزر : @{target.username or 'غير موجود'}")
        return

    if message.text and message.from_user and str(message.from_user.id) in read_set("banall"):
        await message.reply(
            "انت محضور عام من البوت ‼️\nيبدو انك اسئت الاستخدام 🤖❕\nتنبيه للجميع سيتم حضرك 💎\nاذا اسأت الاستخدام 💡 نرجو منكم \nعدم ❌ الاسائة داخل المجموعات التي يتواجد فيها البوت 🤖❄️",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="راسل 📬 الدعم لازالة الحضر ‼️", url="https://telegram.me/K00lil")]
            ])
        )
        try:
            await message.chat.kick(user_id=message.from_user.id)
        except Exception:
            pass
        return

    if message.new_chat_members and str(message.chat.id) in read_set("join"):
        await safe_delete_message(message.chat.id, message.message_id)
        return

    if message.left_chat_member and str(message.chat.id) in read_set("join"):
        await safe_delete_message(message.chat.id, message.message_id)
        return

    # Lock/unlock commands for administrators
    lock_commands = {
        "اقفل الملصقات": ("sticker", "تم قفل الملصقات 🗾🔒", "الملصقات مقفولة 🗾🔒"),
        "افتح الملصقات": ("sticker", "الملصقات مفتوحة 🗾🔓", "تم فتح الملصقات 🗾🔓"),
        "اقفل الصور": ("photo", "تم قفل الصور 📷🔒", "الصور مقفولة 📷🔒"),
        "افتح الصور": ("photo", "الصور مفتوحة 📷🔓", "تم فتح الصور 📷🔓"),
        "اقفل التوجيه": ("fwd", "تم قفل التوجيه 🔄🔒", "التوجيه مقفول 🔄🔒"),
        "افتح التوجيه": ("fwd", "التوجيه مفتوح 🔄🔓", "تم فتح التوجيه 🔄🔓"),
        "اقفل الدردشة": ("chat", "تم قفل الدردشة 📧🔒", "الدردشة مقفول 📧🔒"),
        "افتح الدردشة": ("chat", "الدردشة مفتوح 📧🔓", "تم فتح الدردشة 📧🔓"),
        "اقفل الروابط": ("link", "تم قفل الروابط 💎🔒", "الروابط مقفولة 💎🔒"),
        "افتح الروابط": ("link", "الروابط مفتوحة 💎🔓", "تم فتح الروابط 💎🔓"),
        "اقفل الاشعارات": ("join", "تم ✅ قفل اشعارات الدخول والخروج 📛🔒", "الاشعارات مقفول 📛🔒"),
        "افتح الاشعارات": ("join", "الاشعارات مفتوح 📛🔓", "تم فتح الاشعارات 📛🔓"),
        "اقفل الصوتيات": ("voice", "تم قفل الصوتيات  🎙🔒", "الصوتيات  مقفولة 🎙🔒"),
        "افتح الصوتيات": ("voice", "الصوتيات  مفتوحة 🎙🔓", "تم فتح الصوتيات  🎙🔓"),
        "اقفل الاغاني": ("audio", "تم قفل الاغاني  🎵🔒", "الاغاني  مقفولة 🎵🔒"),
        "افتح الاغاني": ("audio", "الاغاني  مفتوحة 🎵🔓", "تم فتح الاغاني  🎵🔓"),
        "اقفل الصور المتحركة": ("gif", "تم قفل الصور المتحركة  🎆🔒", "الصور المتحركة  مقفولة 🎆🔒"),
        "افتح الصور المتحركة": ("gif", "الصور المتحركة  مفتوحة 🎆🔓", "تم فتح الصور المتحركة  🎆🔓"),
        "اقفل جهات الاتصال": ("cont", "تم قفل جهات الاتصال  📱🔒", "جهات الاتصال  مقفولة 📱🔒"),
        "افتح جهات الاتصال": ("cont", "جهات الاتصال  مفتوحة 📱🔓", "تم فتح جهات الاتصال  📱🔓"),
        "اقفل الكلايش": ("list", "تم قفل الكلايش  🗒🔒", "الكلايش  مقفولة 🗒🔒"),
        "افتح الكلايش": ("list", "الكلايش  مفتوحة 🗒🔓", "تم فتح الكلايش  🗒🔓"),
    }

    if text in lock_commands and is_admin:
        name, reply_true, reply_false = lock_commands[text]
        if text.startswith("اقفل"):
            if str(message.chat.id) not in read_set(name):
                append_one(name, message.chat.id)
                await message.reply(reply_true)
            else:
                await message.reply(reply_false)
        else:
            if str(message.chat.id) in read_set(name):
                remove_one(name, message.chat.id)
                await message.reply(reply_true)
            else:
                await message.reply(reply_false)
        return

    if text == "كتم" and message.reply_to_message and is_admin:
        target_user = message.reply_to_message.from_user
        if target_user and str(target_user.id) not in read_set("silent"):
            append_one("silent", target_user.id)
            await message.reply("تم ✅ كتم العضو 👤🔕")
        else:
            await message.reply("العضو مكتوم 👤🔕")
        return

    if text == "افتح الكتم" and message.reply_to_message and is_admin:
        target_user = message.reply_to_message.from_user
        if target_user and str(target_user.id) in read_set("silent"):
            remove_one("silent", target_user.id)
            await message.reply("تم فتح الكتم 📧🔓")
        else:
            await message.reply("الكتم مفتوح 📧🔓")
        return

    if text == "مغادرة" and normal_member and message.chat.type == "supergroup":
        try:
            await message.chat.kick(user_id=message.from_user.id)
        except Exception:
            pass
        await message.reply("وداعا عزيزي ✨")
        return

    if text == "مغادرة" and not normal_member and message.chat.type == "supergroup":
        await message.reply("عذرا ‼️ انت مشرف في المجموعة 🚹🔒")
        return

    if str(message.chat.id) in read_set("join") and message.new_chat_members:
        await safe_delete_message(message.chat.id, message.message_id)
        return

    if str(message.chat.id) in read_set("join") and message.left_chat_member:
        await safe_delete_message(message.chat.id, message.message_id)
        return

    if text and str(message.from_user.id) in read_set("banall"):
        await message.reply(
            "انت محضور عام من البوت ‼️\nيبدو انك اسئت الاستخدام 🤖❕\nتنبيه للجميع سيتم حضرك 💎\nاذا اسأت الاستخدام 💡 نرجو منكم \nعدم ❌ الاسائة داخل المجموعات التي يتواجد فيها البوت 🤖❄️",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="راسل 📬 الدعم لازالة الحضر ‼️", url="https://telegram.me/K00lil")]
            ])
        )
        try:
            await message.chat.kick(user_id=message.from_user.id)
        except Exception:
            pass
        return


@DP.inline_query()
async def inline_query_handler(inline_query: types.InlineQuery):
    result = types.InlineQueryResultArticle(
        id=str(hash(inline_query.id)),
        title="مشاركة مع اصدقائك",
        input_message_content=types.InputTextMessageContent(
            message_text=("اهلا بك عزيزي 🚹 في البوت الرسمي 🔶\nالخاص لحماية المجموعات 👥🔒\n" 
                          "يعمل بل لغة العربية 📕 ويحتوي \n" 
                          "على جميع الاشياء التي تحتاجها 💎\n" 
                          "لعمل مجموعة امنة وجيدة ‼️"),
            parse_mode="HTML"
        ),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="للدخول الى البوت اضغط هنا ♻️", url=f"https://telegram.me/{bot.username}")]
        ])
    )
    await bot.answer_inline_query(inline_query.id, results=[result], cache_time=1)


@DP.callback_query(lambda c: c.data and (c.data in {"channel", "channel2", "home", "help", "help_close", "help_open", "help_offc", "offc", "omar"} or c.data.startswith(("lock_", "unlock_", "cmd_"))))
async def callback_handler(callback: types.CallbackQuery):
    data = callback.data
    chat_id = callback.message.chat.id

    if data not in {"channel", "channel2", "home"}:
        if not await is_group_admin(chat_id, callback.from_user.id):
            await callback.answer("عذراً، هذا الإجراء مخصص للمشرفين فقط! 🔒", show_alert=True)
            return

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
            "اهلا بك عزيزي 🚹 في البوت الرسمي 🔶\nالخاص لحماية المجموعات 👥🔒\nيعمل بل لغة العربية 📕 ويحتوي \n"
            "على جميع الاشياء التي تحتاجها 💎\nلعمل مجموعة امنة وجيدة ‼️",
            reply_markup=build_main_keyboard()
        )
    elif data == "help":
        await callback.message.edit_text("كيفية استخدام البوت 📋🔻", reply_markup=build_help_keyboard())
    elif data == "help_close":
        await callback.message.edit_text("اوامر القفل في المجموعة 👥🔒", reply_markup=build_close_keyboard())
    elif data == "help_open":
        await callback.message.edit_text("اوامر الفتح في المجموعة 👥🔓", reply_markup=build_open_keyboard())
    elif data == "help_offc" or data == "offc":
        await callback.message.edit_text("الاوامر العامة في المجموعة ‼️🔻", reply_markup=build_offc_keyboard())
    elif data.startswith("lock_") or data.startswith("unlock_"):
        if callback.message.chat.type not in ("group", "supergroup"):
            await callback.answer("هذا الزر يعمل فقط داخل المجموعة. افتح البوت في المجموعة ثم اضغط الزر.", show_alert=True)
            return
        if not await is_group_admin(chat_id, callback.from_user.id):
            await callback.answer("يجب أن تكون مشرفاً في المجموعة لتفعيل هذا الزر.", show_alert=True)
            return

        action, target = data.split("_", 1)
        lock_actions = {
            "link": "link",
            "photo": "photo",
            "fwd": "fwd",
            "sticker": "sticker",
            "list": "list",
            "voice": "voice",
            "audio": "audio",
            "cont": "cont",
            "chat": "chat",
            "join": "join",
        }

        if target not in lock_actions:
            await callback.answer("الزر غير مدعوم حالياً.", show_alert=True)
            return

        target_name = lock_actions[target]
        locked = await change_lock_state(chat_id, target_name, action == "lock")
        if action == "lock":
            await callback.answer(
                "تم قفل {} بنجاح ✅".format({
                    "link": "الروابط",
                    "photo": "الصور",
                    "fwd": "التوجيه",
                    "sticker": "الملصقات",
                    "list": "الكلايش",
                    "voice": "الصوتيات",
                    "audio": "الاغاني",
                    "cont": "جهات الاتصال",
                    "chat": "الدردشة",
                    "join": "الاشعارات",
                }[target]),
                show_alert=True
            ) if locked else await callback.answer("هذا الخيار مقفل بالفعل بالفعل ✅", show_alert=True)
        else:
            await callback.answer(
                "تم فتح {} بنجاح ✅".format({
                    "link": "الروابط",
                    "photo": "الصور",
                    "fwd": "التوجيه",
                    "sticker": "الملصقات",
                    "list": "الكلايش",
                    "voice": "الصوتيات",
                    "audio": "الاغاني",
                    "cont": "جهات الاتصال",
                    "chat": "الدردشة",
                    "join": "الاشعارات",
                }[target]),
                show_alert=True
            ) if locked else await callback.answer("هذا الخيار مفتوح بالفعل ✅", show_alert=True)
        return
    elif data.startswith("cmd_"):
        if data == "cmd_info":
            if callback.message.chat.type in ("group", "supergroup"):
                try:
                    group = await bot.get_chat(chat_id)
                    count = await bot.get_chat_member_count(chat_id)
                    await callback.message.reply(
                        f"📌 اسم المجموعة: {group.title or 'غير معروف'}\n📌 معرف المجموعة: {chat_id}\n📌 عدد الاعضاء: {count}"
                    )
                except Exception:
                    await callback.answer("حدث خطأ أثناء جلب معلومات المجموعة.", show_alert=True)
            else:
                await callback.answer("استخدم هذا الزر داخل مجموعة لعرض معلوماتها.", show_alert=True)
        elif data == "cmd_time":
            now = datetime.now()
            await callback.answer(f"🕛 الوقت الآن: {now.strftime('%H:%M')}", show_alert=True)
        elif data == "cmd_date":
            today = date.today()
            await callback.answer(f"📅 التاريخ: {today.year}/{today.month}/{today.day}", show_alert=True)
        elif data == "cmd_count":
            if callback.message.chat.type in ("group", "supergroup"):
                await callback.message.reply(f"عدد الرسائل حتى الآن في هذه المجموعة هو: {callback.message.message_id}")
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
                    await callback.message.chat.leave()
                except Exception:
                    await callback.answer("تعذر على البوت مغادرة المجموعة. تأكد من أن البوت لديه صلاحية المغادرة.", show_alert=True)
                else:
                    await callback.answer("غادر البوت المجموعة بنجاح.", show_alert=True)
            else:
                await callback.answer("يمكن أن يعمل هذا الزر فقط داخل مجموعة.", show_alert=True)
        return
    elif data == "omar":
        await callback.answer("هذا الزر مجرد عرض للأمر. استخدم نص الأمر أو الأزرار العملية بدلاً منه.", show_alert=True)
        return

    await callback.answer()


async def on_startup() -> None:
    global BOT_USERNAME
    me = await bot.get_me()
    if getattr(me, 'username', None):
        BOT_USERNAME = me.username
    logging.info(f"Bot started as @{BOT_USERNAME}")


async def main() -> None:
    await bot.delete_webhook(drop_pending_updates=True)
    await DP.start_polling(bot, skip_updates=True, on_startup=on_startup)


if __name__ == "__main__":
    asyncio.run(main())
