from aiogram.filters import Filter
from aiogram.types import Message
from config import ADMIN_IDS

class IsAdminFilter(Filter):
    """فلتر مخصص للتحقق مما إذا كان مرسل الرسالة مشرفاً في المجموعة أو مالكاً للبوت"""
    async def __call__(self, message: Message) -> bool:
        if not message.chat or message.chat.type == "private":
            return False
        
        # المالك أو المشرف العام للبوت يعتبر مشرفاً دائماً
        if message.from_user and message.from_user.id in ADMIN_IDS:
            return True
            
        try:
            # التحقق من رتبة المستخدم في المجموعة
            member = await message.bot.get_chat_member(
                chat_id=message.chat.id, 
                user_id=message.from_user.id
            )
            return member.status in ("administrator", "creator")
        except Exception:
            return False
