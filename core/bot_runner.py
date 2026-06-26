import asyncio
import sys
import os
import subprocess
import logging
import database

logger = logging.getLogger(__name__)

# قاموس لتتبع العمليات الجارية للبوتات: {bot_id: (process_handle, log_file_handle)}
running_bots = {}

async def start_bot(bot_id: int) -> bool:
    """تشغيل عملية البوت كعملية فرعية (Subprocess)"""
    if bot_id in running_bots:
        # التحقق هل لا زالت تعمل فعلياً
        proc, _ = running_bots[bot_id]
        if proc.returncode is None:
            logger.info(f"البوت {bot_id} قيد التشغيل بالفعل.")
            return True
        else:
            # العملية انتهت بشكل غير متوقع، نقوم بتنظيفها
            await stop_bot(bot_id)

    bot_info = await database.get_bot(bot_id)
    if not bot_info:
        logger.error(f"لم يتم العثور على معلومات البوت {bot_id} في قاعدة البيانات.")
        return False

    # تحضير البيئة وتمرير التوكن الخاص بالبوت عبر متغيرات البيئة
    env = os.environ.copy()
    env["BOT_TOKEN"] = bot_info["token"]
    
    # فتح ملف السجلات للكتابة
    log_path = "bot_run.log"
    try:
        log_file = open(log_path, "a", encoding="utf-8")
    except Exception as e:
        logger.error(f"فشل فتح ملف السجلات: {e}")
        return False

    # تشغيل العملية الفرعية للبوت
    try:
        # استخدام sys.executable لضمان تشغيل نفس مفسر بايثون الحالي
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "bot.py",
            stdout=log_file,
            stderr=subprocess.STDOUT,
            env=env
        )
        running_bots[bot_id] = (proc, log_file)
        await database.update_bot_status(bot_id, "running")
        logger.info(f"🚀 تم بدء تشغيل البوت {bot_info['name']} (ID: {bot_id}) بنجاح.")
        return True
    except Exception as e:
        logger.error(f"فشل بدء تشغيل العملية الفرعية للبوت: {e}")
        log_file.close()
        return False

async def stop_bot(bot_id: int) -> bool:
    """إيقاف عملية البوت وإنهاء تشغيلها"""
    if bot_id not in running_bots:
        await database.update_bot_status(bot_id, "stopped")
        return True

    proc, log_file = running_bots[bot_id]
    try:
        if proc.returncode is None:
            proc.terminate()
            # الانتظار لمدة 3 ثوان كحد أقصى لتتوقف العملية بشكل طبيعي
            try:
                await asyncio.wait_for(proc.wait(), timeout=3.0)
            except asyncio.TimeoutError:
                # إذا لم تستجب، نقتلها بالقوة
                proc.kill()
                await proc.wait()
        
        log_file.close()
        logger.info(f"🛑 تم إيقاف البوت {bot_id} بنجاح.")
    except Exception as e:
        logger.error(f"حدث خطأ أثناء محاولة إيقاف البوت {bot_id}: {e}")
    finally:
        if bot_id in running_bots:
            del running_bots[bot_id]
        await database.update_bot_status(bot_id, "stopped")
        
    return True

async def stop_all_bots():
    """إيقاف جميع البوتات الجارية (مفيد عند إغلاق المنصة)"""
    for bot_id in list(running_bots.keys()):
        await stop_bot(bot_id)

def get_bot_runner_status(bot_id: int) -> str:
    """الحصول على حالة تشغيل العملية الحقيقية"""
    if bot_id in running_bots:
        proc, _ = running_bots[bot_id]
        if proc.returncode is None:
            return "running"
    return "stopped"

def get_live_logs(limit: int = 100) -> str:
    """قراءة آخر الأسطر من ملف سجلات تشغيل البوت"""
    log_path = "bot_run.log"
    if not os.path.exists(log_path):
        return "لا توجد سجلات تشغيل متوفرة حالياً."
    
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            last_lines = lines[-limit:]
            return "".join(last_lines)
    except Exception as e:
        return f"خطأ أثناء قراءة السجلات: {e}"

async def monitor_bots_loop():
    """حلقة مراقبة خلفية للتأكد من حالة العمليات وتحديث قاعدة البيانات تلقائياً"""
    while True:
        await asyncio.sleep(5)
        for bot_id, (proc, log_file) in list(running_bots.items()):
            if proc.returncode is not None:
                # العملية انتهت بشكل مستقل أو حدث خطأ
                log_file.close()
                if bot_id in running_bots:
                    del running_bots[bot_id]
                await database.update_bot_status(bot_id, "stopped")
                logger.warning(f"⚠️ البوت {bot_id} خرج برمز العودة: {proc.returncode}")
