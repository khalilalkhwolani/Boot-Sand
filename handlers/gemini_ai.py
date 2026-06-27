import asyncio
import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message
from google import genai
import config
import database

logger = logging.getLogger(__name__)
router = Router()

# ---- نظام Rate Limiting المدمج لتجنب تجاوز حد Gemini المجاني ----
# يسمح بـ 10 طلبات في الدقيقة للفحص الأمني (لترك هامش آمن من الـ 15 المجانية)
import time
_check_timestamps: list = []
MAX_CHECKS_PER_MINUTE = 10

def _can_call_gemini_check() -> bool:
    """تحقق إذا يمكن استدعاء Gemini للفحص دون تجاوز حد الطلبات المجانية"""
    global _check_timestamps
    now = time.time()
    # نحذف الطوابع الزمنية الأقدم من دقيقة
    _check_timestamps = [t for t in _check_timestamps if now - t < 60]
    if len(_check_timestamps) < MAX_CHECKS_PER_MINUTE:
        _check_timestamps.append(now)
        return True
    return False


# ---- دالة توليد المحتوى مع التبديل التلقائي بين مفاتيح API المتعددة ----
def _generate_content_with_fallback(prompt: str) -> str:
    """
    توليد المحتوى مع دعم التبديل التلقائي بين مفاتيح API المتعددة عند حدوث ضغط أو نفاد الحصة
    """
    keys = config.GEMINI_API_KEYS
    if not keys:
        raise Exception("لم يتم تهيئة أي مفاتيح API لـ Google Gemini.")
        
    last_exception = None
    for i, api_key in enumerate(keys):
        try:
            logger.info(f"Connecting to Gemini API using key index {i}...")
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            logger.warning(f"Gemini API key index {i} failed: {e}")
            last_exception = e
            continue
            
    raise last_exception if last_exception else Exception("فشلت جميع مفاتيح الاتصال بـ Gemini.")

# ---- دالة الفحص الأمني الذكي ----
async def gemini_check_message(text: str) -> dict:
    """
    يرسل نص الرسالة إلى Gemini ليحدد:
    - هل هي إعلان أو سبام؟
    - هل تحتوي على كلمات مسيئة أو غير لائقة؟
    - الكلمات المفتاحية المسببة للحذف للتعلم التلقائي
    - السبب

    يعيد dict: {"delete": True/False, "reason": "السبب", "spam_words": []}
    """
    if not config.GEMINI_API_KEYS:
        return {"delete": False, "reason": "لا يوجد مفتاح API", "spam_words": []}

    # إذا استُنفد حد الطلبات نعود بالحماية التقليدية ولا نحذف
    if not _can_call_gemini_check():
        logger.warning("Gemini rate limit reached, skipping AI check for this message.")
        return {"delete": False, "reason": "rate_limit", "spam_words": []}

    prompt = f"""أنت مشرف ذكاء اصطناعي لمجموعة تيليجرام تعليمية للطلاب الجامعيين في المملكة العربية السعودية.

مهمتك: تحليل الرسالة التالية وتحديد ما إذا كانت تستحق الحذف بناءً على المعايير التالية:

**احذف الرسالة إذا كانت تحتوي على:**
1. إعلانات حل واجبات أو كويزات أو اختبارات أو مشاريع أو تقارير مقابل المال أو مقابل أي شيء.
2. الترويج لقنوات أو مجموعات أو حسابات تيليجرام أو سناب شات أو واتساب أخرى.
3. رقم هاتف مع عرض خدمة من أي نوع.
4. روابط ترويجية أو دعاية لأي منتج أو خدمة تجارية.
5. طلبات تواصل للحصول على خدمة (مثل: تواصل معي، راسلني، تواصل خاص).
6. شتائم أو إهانات أو كلمات بذيئة بالعربية أو الإنجليزية.

**لا تحذف الرسالة إذا كانت:**
- سؤالاً عاماً للمذاكرة أو الاستفسار الأكاديمي.
- نقاشاً طبيعياً بين الطلاب.
- إعلاناً رسمياً من إدارة المجموعة.
- مشاركة ملفات أو ملاحظات دراسية مجانية.
- دردشة اجتماعية طبيعية.

**الرسالة المراد تحليلها:**
"{text}"

**أجب بالصيغة التالية بدقة ولا تضف أي كلام آخر:**
DELETE: [YES أو NO]
REASON: [سبب قصير جداً بالعربية لا يتجاوز 5 كلمات]
SPAM_WORDS: [اكتب الكلمات أو العبارات الترويجية المسببة للحذف مفصولة بفاصلة فقط إذا كان الجواب YES، وإلا اكتب NONE]"""

    try:
        result_text = await asyncio.to_thread(_generate_content_with_fallback, prompt)

        # تحليل رد Gemini
        delete = False
        reason = "محتوى مخالف"
        spam_words = []

        for line in result_text.splitlines():
            line = line.strip()
            if line.upper().startswith("DELETE:"):
                val = line.split(":", 1)[1].strip().upper()
                delete = val == "YES"
            elif line.upper().startswith("REASON:"):
                reason = line.split(":", 1)[1].strip()
            elif line.upper().startswith("SPAM_WORDS:"):
                val = line.split(":", 1)[1].strip()
                if val.upper() != "NONE":
                    # تقسيم الكلمات بفاصلة وتنظيف الفراغات
                    spam_words = [w.strip().lower() for w in val.split(",") if w.strip()]

        return {"delete": delete, "reason": reason, "spam_words": spam_words}

    except Exception as e:
        logger.error(f"Gemini check error: {e}")
        return {"delete": False, "reason": f"خطأ: {str(e)}", "spam_words": []}


# ---- دالة التلخيص (/summarize) ----
async def get_gemini_summary(messages_list: list) -> str:
    """إرسال الرسائل إلى Gemini للحصول على تلخيص ذكي ومنظم"""
    if not config.GEMINI_API_KEYS:
        return "لم يتم إعداد مفتاح Google Gemini API في ملف .env"

    formatted_messages = []
    for msg in messages_list:
        name = msg.get("full_name", "عضو")
        username = f" (@{msg.get('username')})" if msg.get("username") else ""
        text = msg.get("message_text", "")
        formatted_messages.append(f"- {name}{username}: {text}")

    conversation_history = "\n".join(formatted_messages)

    prompt = (
        "أنت مساعد ذكي متخصص في إدارة وتلخيص محادثات مجموعات التلجرام.\n"
        "إليك قائمة بالرسائل الأخيرة في المجموعة مرتبة من الأقدم للأحدث.\n"
        "قدم تلخيصاً شاملاً ومنظماً باللغة العربية على شكل نقاط واضحة مع رموز تعبيرية.\n\n"
        f"سجل الرسائل:\n{conversation_history}\n\n"
        "التلخيص الذكي:"
    )

    try:
        return await asyncio.to_thread(_generate_content_with_fallback, prompt)
    except Exception as e:
        logger.error(f"Gemini summary error: {e}")
        err_msg = str(e)
        if "503" in err_msg or "UNAVAILABLE" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
            return "⚠️ خوادم الذكاء الاصطناعي مضغوطة حالياً. يرجى إعادة محاولة التلخيص بعد قليل."
        return "⚠️ حدث خطأ أثناء الاتصال بالذكاء الاصطناعي لتلخيص المحادثة."


# ---- دالة الرد الذكي العام ----
async def ask_gemini(user_prompt: str, chat_context: str = "") -> str:
    """إرسال سؤال عام إلى Gemini للحصول على رد ذكي"""
    if not config.GEMINI_API_KEYS:
        return "لم يتم إعداد مفتاح Google Gemini API في ملف .env"

    prompt = (
        "أنت بوت تلجرام ذكي لإدارة وحماية المجموعات. تجيب باختصار ولطف وذكاء باللغة العربية.\n"
        f"{chat_context}\n"
        f"السؤال: {user_prompt}\n"
        "الإجابة:"
    )

    try:
        return await asyncio.to_thread(_generate_content_with_fallback, prompt)
    except Exception as e:
        logger.error(f"Gemini ask error: {e}")
        err_msg = str(e)
        if "503" in err_msg or "UNAVAILABLE" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
            return "⚠️ عذراً، خوادم الذكاء الاصطناعي مضغوطة حالياً. يرجى المحاولة مرة أخرى بعد قليل."
        return "⚠️ عذراً، تعذر الاتصال بمحرك الذكاء الاصطناعي حالياً."


# ---- أمر التلخيص (/summarize) ----
@router.message(Command("summarize"), F.chat.type.in_({"group", "supergroup"}))
async def summarize_chat(message: Message, bot: Bot):
    settings = await database.get_group_settings(message.chat.id)

    if settings.get("gemini_enabled", 1) == 0:
        await message.reply("ميزة الذكاء الاصطناعي معطلة في هذه المجموعة. يمكن للمشرفين تفعيلها من /settings")
        return

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    recent_msgs = await database.get_recent_messages(message.chat.id, limit=75)

    if len(recent_msgs) < 5:
        await message.reply("لا توجد رسائل كافية للتلخيص (5 رسائل على الأقل).")
        return

    status_msg = await message.reply("جاري قراءة وتلخيص نقاشات المجموعة باستخدام Gemini AI...")
    summary = await get_gemini_summary(recent_msgs)

    await status_msg.edit_text(
        f"الملخص الذكي لنقاشات المجموعة الاخيرة:\n\n"
        f"{summary}\n\n"
        f"تم التلخيص بناء على اخر {len(recent_msgs)} رسالة."
    )


async def is_bot_mentioned_or_reply(message: Message, bot: Bot) -> bool:
    if not message.text:
        return False
    # Ignore command messages
    if message.text.strip().startswith("/"):
        return False
    bot_info = await bot.get_me()
    is_mentioned = f"@{bot_info.username}" in message.text
    is_reply_to_bot = (
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == bot_info.id
    )
    return bool(is_mentioned or is_reply_to_bot)

# ---- الرد التفاعلي الذكي عند Mention أو Reply ----
@router.message(F.chat.type.in_({"group", "supergroup"}), is_bot_mentioned_or_reply)
async def auto_ai_reply(message: Message, bot: Bot):
    settings = await database.get_group_settings(message.chat.id)
    if settings.get("gemini_enabled", 1) == 0:
        return

    # If Gemini API keys are not configured, return silently
    if not config.GEMINI_API_KEYS:
        logger.warning("Gemini API keys not configured. Skipping auto_ai_reply.")
        return

    bot_info = await bot.get_me()
    bot_username = bot_info.username
    clean_text = message.text.replace(f"@{bot_username}", "").strip()

    if not clean_text:
        await message.reply("نعم! كيف يمكنني مساعدتك؟")
        return

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    context = f"السائل يدعى {message.from_user.full_name} في مجموعة {message.chat.title}."
    reply_text = await ask_gemini(clean_text, context)
    
    # If the response is an error or key warning, do not reply publicly
    if reply_text.startswith("⚠️") or "لم يتم إعداد" in reply_text:
        logger.warning(f"Gemini error response in group chat: {reply_text}")
        return
        
    await message.reply(reply_text)


# ---- دالة فحص نية المشرف عند الرد ----
async def gemini_check_admin_intent(admin_text: str) -> bool:
    """
    تحليل نية المشرف عند الرد على رسالة للتأكد هل يقصد حذفها أو تصنيفها كإعلان/سبام
    """
    if not config.GEMINI_API_KEYS:
        return False
        
    prompt = f"""تحليل نية مشرف مجموعة تيليجرام من خلال تعليقه بالرد على رسالة أخرى للعامة.
التعليق المكتوب من المشرف بالرد: "{admin_text}"

السؤال: هل هذا التعليق المكتوب يعبر عن رغبة أو أمر (صريح أو ضمني بالعامية السعودية أو الفصحى) لحذف الرسالة المردود عليها، أو التبليغ عنها كإعلان، أو كسبام، أو كحساب مشبوه/مخالف؟
(مثل: احذف، اعلان، مشبوه، مخالف، سبام، شيل هذا، امسح، ايش هذا الاعلان، وسم إعلاني، إلخ)

أجب بكلمة واحدة فقط: YES إذا كان المشرف يريد الحذف/التبليغ، أو NO إذا كان مجرد تعليق أو دردشة عادية ولا يقصد الإجراء الإشرافي الحذف."""

    try:
        res = await asyncio.to_thread(_generate_content_with_fallback, prompt)
        return "YES" in res
    except Exception as e:
        logger.error(f"Error checking admin intent: {e}")
        return False
