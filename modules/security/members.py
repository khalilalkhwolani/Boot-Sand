from aiogram import Router, Bot, F
from aiogram.filters import ChatMemberUpdatedFilter, IS_MEMBER
from aiogram.types import (
    ChatMemberUpdated, ChatPermissions, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)
import database
import logging

from .utils import get_bot_info

logger = logging.getLogger(__name__)
router = Router()

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
