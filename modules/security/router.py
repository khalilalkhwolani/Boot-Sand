from aiogram import Router
from .callbacks import router as callbacks_router
from .members import router as members_router
from .moderation import router as moderation_router
from .message_monitor import router as monitor_router

router = Router()
router.include_router(callbacks_router)
router.include_router(members_router)
router.include_router(moderation_router)
router.include_router(monitor_router)
