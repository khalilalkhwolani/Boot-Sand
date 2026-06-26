import re
import aiosqlite
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import database

router = Router()

DB_PATH = database.DB_PATH

async def init_reactions_db():
    """تهيئة جدول التفاعلات الخاص بمنشورات القنوات"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS channel_reactions (
                channel_id INTEGER,
                message_id INTEGER,
                user_id INTEGER,
                reaction_type TEXT,
                PRIMARY KEY (channel_id, message_id, user_id)
            )
        """)
        await db.commit()

def get_reaction_keyboard(likes: int = 0, dislikes: int = 0, channel_id: int = 0, message_id: int = 0) -> InlineKeyboardMarkup:
    """توليد لوحة الأزرار الشفافة للتفاعل أسفل منشور القناة"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"👍 {likes}", 
                callback_data=f"react_{channel_id}_{message_id}_like"
            ),
            InlineKeyboardButton(
                text=f"👎 {dislikes}", 
                callback_data=f"react_{channel_id}_{message_id}_dislike"
            )
        ]
    ])
    return keyboard

# --- إضافة الأزرار التفاعلية تلقائياً للمنشورات الجديدة في القناة ---
@router.channel_post()
async def on_new_channel_post(message: Message, bot: Bot):
    await init_reactions_db()
    
    # إضافة الأزرار التفاعلية 👍 و 👎 أسفل المنشور في القناة
    try:
        await bot.edit_message_reply_markup(
            chat_id=message.chat.id,
            message_id=message.message_id,
            reply_markup=get_reaction_keyboard(
                likes=0, 
                dislikes=0, 
                channel_id=message.chat.id, 
                message_id=message.message_id
            )
        )
    except Exception:
        pass

    # ميزة النشر المتقاطع (Cross-Posting): إعادة نشر منشور القناة في جميع المجموعات المشتركة
    # جلب جميع معرفات المجموعات المسجلة في البوت
    group_ids = []
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT group_id FROM groups") as cursor:
                rows = await cursor.fetchall()
                group_ids = [row[0] for row in rows]
    except Exception:
        pass

    for g_id in group_ids:
        try:
            # نسخ الرسالة بالكامل إلى المجموعات (مع الحفاظ على التنسيقات والصور)
            await message.copy_to(chat_id=g_id)
        except Exception:
            pass

# --- معالجة الضغط على أزرار التفاعل (👍 / 👎) في القناة أو المجموعات ---
@router.callback_query(F.data.startswith("react_"))
async def process_channel_reaction(callback: CallbackQuery):
    await init_reactions_db()
    
    # تحليل البيانات المستلمة
    # react_{channel_id}_{message_id}_{type}
    data_parts = callback.data.split("_")
    channel_id = int(data_parts[1])
    message_id = int(data_parts[2])
    reaction_type = data_parts[3] # "like" أو "dislike"
    user_id = callback.from_user.id

    async with aiosqlite.connect(DB_PATH) as db:
        # التحقق مما إذا كان المستخدم قد تفاعل سابقاً على هذا المنشور
        async with db.execute(
            "SELECT reaction_type FROM channel_reactions WHERE channel_id = ? AND message_id = ? AND user_id = ?",
            (channel_id, message_id, user_id)
        ) as cursor:
            existing_reaction = await cursor.fetchone()
            
        if existing_reaction:
            current_type = existing_reaction[0]
            if current_type == reaction_type:
                # إذا ضغط على نفس التفاعل مرة أخرى -> نقوم بإلغاء التفاعل (حذفه)
                await db.execute(
                    "DELETE FROM channel_reactions WHERE channel_id = ? AND message_id = ? AND user_id = ?",
                    (channel_id, message_id, user_id)
                )
                await callback.answer("تم إزالة تفاعلك.")
            else:
                # إذا غير رأيه وضغط على التفاعل الآخر -> نقوم بتحديث التفاعل
                await db.execute(
                    "UPDATE channel_reactions SET reaction_type = ? WHERE channel_id = ? AND message_id = ? AND user_id = ?",
                    (reaction_type, channel_id, message_id, user_id)
                )
                await callback.answer("تم تغيير تفاعلك.")
        else:
            # إذا كان تفاعل جديد -> نقوم بإضافته
            await db.execute(
                "INSERT INTO channel_reactions (channel_id, message_id, user_id, reaction_type) VALUES (?, ?, ?, ?)",
                (channel_id, message_id, user_id, reaction_type)
            )
            await callback.answer("تم تسجيل تفاعلك بنجاح!")
            
        await db.commit()

        # حساب إجمالي التفاعلات الحالي للمنشور
        async with db.execute(
            "SELECT COUNT(*) FROM channel_reactions WHERE channel_id = ? AND message_id = ? AND reaction_type = 'like'",
            (channel_id, message_id)
        ) as cursor:
            row_likes = await cursor.fetchone()
            likes_count = row_likes[0] if row_likes else 0

        async with db.execute(
            "SELECT COUNT(*) FROM channel_reactions WHERE channel_id = ? AND message_id = ? AND reaction_type = 'dislike'",
            (channel_id, message_id)
        ) as cursor:
            row_dislikes = await cursor.fetchone()
            dislikes_count = row_dislikes[0] if row_dislikes else 0

    # تحديث لوحة التفاعل أسفل المنشور في القناة بالقيم الجديدة
    try:
        await callback.message.edit_reply_markup(
            reply_markup=get_reaction_keyboard(
                likes=likes_count, 
                dislikes=dislikes_count, 
                channel_id=channel_id, 
                message_id=message_id
            )
        )
    except Exception:
        pass
