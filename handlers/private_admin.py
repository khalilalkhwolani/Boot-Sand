from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from config import ADMIN_IDS
import database
import aiosqlite

router = Router()

class BroadcastState(StatesGroup):
    waiting_for_message = State()

def get_admin_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📢 إرسال إعلان للمجموعات", callback_data="admin_broadcast"),
        ],
        [
            InlineKeyboardButton(text="📊 إحصائيات البوت", callback_data="admin_stats")
        ]
    ])
    return keyboard

@router.message(CommandStart(), F.chat.type == "private")
async def start_private(message: Message, bot: Bot):
    user_id = message.from_user.id
    
    if user_id in ADMIN_IDS:
        await message.reply(
            "أهلاً بك يا مشرف البوت! 💻\n"
            "هذه هي لوحة التحكم الخاصة بك لإدارة البوت ونشر الإعلانات.",
            reply_markup=get_admin_keyboard()
        )
    else:
        from modules.security.handlers import build_main_keyboard
        bot_user = await bot.get_me()
        await message.answer(
            "اهلا بك عزيزي 🚹 في البوت الرسمي 🔶\nالخاص لحماية المجموعات 👥🔒\nيعمل باللغة العربية 📕 ويحتوي \nعلى جميع الاشياء التي تحتاجها 💎\nلعمل مجموعة امنة وجيدة ‼️",
            reply_markup=build_main_keyboard(bot_user.username)
        )

@router.callback_query(F.data == "admin_stats")
async def show_stats(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("غير مصرح لك بالدخول.", show_alert=True)
        return
    
    # حساب عدد المجموعات المفعلة من قاعدة البيانات
    async with aiosqlite.connect(database.DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM groups") as cursor:
            row = await cursor.fetchone()
            group_count = row[0] if row else 0
            
    await callback.message.edit_text(
        f"📊 **إحصائيات البوت الحالية:**\n\n"
        f"👥 عدد المجموعات المسجلة: {group_count}\n",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 عودة للرئيسية", callback_data="admin_home")]
        ])
    )

@router.callback_query(F.data == "admin_home")
async def go_home(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("غير مصرح لك بالدخول.", show_alert=True)
        return
    await callback.message.edit_text(
        "أهلاً بك يا مشرف البوت! 💻\n"
        "هذه هي لوحة التحكم الخاصة بك لإدارة البوت ونشر الإعلانات.",
        reply_markup=get_admin_keyboard()
    )

@router.callback_query(F.data == "admin_broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("غير مصرح لك بالدخول.", show_alert=True)
        return
    
    await state.set_state(BroadcastState.waiting_for_message)
    await callback.message.edit_text(
        "📝 يرجى إرسال الرسالة التي ترغب في بثها لجميع المجموعات.\n"
        "يمكن أن تكون الرسالة نصية، صورة، أو فيديو.\n"
        "لإلغاء العملية أرسل: إلغاء",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ إلغاء", callback_data="cancel_broadcast")]
        ])
    )

@router.callback_query(F.data == "cancel_broadcast")
async def cancel_broadcast_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "❌ تم إلغاء عملية البث.",
        reply_markup=get_admin_keyboard()
    )

@router.message(BroadcastState.waiting_for_message)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    if message.from_user.id not in ADMIN_IDS:
        await state.clear()
        return

    if message.text and message.text.strip().lower() == "إلغاء":
        await state.clear()
        await message.reply("تم إلغاء عملية البث.", reply_markup=get_admin_keyboard())
        return

    await message.reply("⏳ جاري بدء البث إلى المجموعات...")
    await state.clear()

    # جلب جميع معرفات المجموعات من قاعدة البيانات
    group_ids = []
    async with aiosqlite.connect(database.DB_PATH) as db:
        async with db.execute("SELECT group_id FROM groups") as cursor:
            rows = await cursor.fetchall()
            group_ids = [row[0] for row in rows]

    success_count = 0
    fail_count = 0

    for g_id in group_ids:
        try:
            # استخدام copy_to لنسخ أي نوع رسالة (صورة، نص، فيديو، مستند)
            await message.copy_to(chat_id=g_id)
            success_count += 1
        except Exception:
            fail_count += 1

    await message.reply(
        f"✅ انتهت عملية البث بنجاح!\n\n"
        f"🟢 تم الإرسال إلى: {success_count} مجموعة\n"
        f"🔴 فشل الإرسال إلى: {fail_count} مجموعة"
    )
