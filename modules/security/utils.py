import logging
from datetime import datetime
from aiogram import Bot

logger = logging.getLogger(__name__)

_bot_info_cache = None

async def get_bot_info(bot: Bot):
    global _bot_info_cache
    if _bot_info_cache is None:
        _bot_info_cache = await bot.get_me()
    return _bot_info_cache

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
