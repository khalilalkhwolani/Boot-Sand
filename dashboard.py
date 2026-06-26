import asyncio
import logging
import os
import aiohttp
import mimetypes

# إصلاح ترميز الملفات على ويندوز لمنع توقف تشغيل الجافاسكريبت
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")

from fastapi import FastAPI, HTTPException, Body, Path, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import database
import core.bot_runner as bot_runner
import config

# إعداد السجلات
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="AlsManagerBot Platform Admin Dashboard")

# تفعيل CORS لمواجهة أي مشاكل في استدعاء الـ APIs
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def resolve_bot_token(token: str) -> dict:
    """التحقق من توكن البوت وجلب تفاصيله من خوادم تيليجرام"""
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("ok"):
                        result = data["result"]
                        return {
                            "id": result["id"],
                            "name": result["first_name"],
                            "username": result.get("username", "")
                        }
    except Exception as e:
        logger.error(f"حدث خطأ أثناء التحقق من توكن البوت: {e}")
    return None

@app.on_event("startup")
async def startup_event():
    """تهيئة النظام وقاعدة البيانات والتسجيل التلقائي للبوت الافتراضي"""
    # تهيئة قاعدة البيانات والجداول
    await database.init_db()
    
    # تشغيل حلقة مراقبة عمليات البوت الفرعية في الخلفية
    asyncio.create_task(bot_runner.monitor_bots_loop())
    
    # التسجيل التلقائي للبوت الافتراضي الموجود في ملف .env
    if config.BOT_TOKEN:
        try:
            bot_details = await resolve_bot_token(config.BOT_TOKEN)
            if bot_details:
                await database.add_bot(
                    bot_id=bot_details["id"],
                    token=config.BOT_TOKEN,
                    name=bot_details["name"],
                    owner_id=None
                )
                logger.info(f"✅ تم تسجيل البوت الافتراضي بنجاح: {bot_details['name']}")
        except Exception as e:
            logger.error(f"⚠️ فشل في تسجيل البوت الافتراضي تلقائياً: {e}")

    # تشغيل كافة البوتات المسجلة في قاعدة البيانات والتي حالتها "running" تلقائياً
    try:
        bots_list = await database.get_bots()
        for bot in bots_list:
            if bot["status"] == "running":
                await bot_runner.start_bot(bot["bot_id"])
                logger.info(f"✅ تم إعادة تشغيل البوت {bot['name']} تلقائياً عند بدء المنصة.")
    except Exception as e:
        logger.error(f"⚠️ فشل في تشغيل البوتات تلقائياً عند بدء المنصة: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """إيقاف كافة البوتات الجارية عند إغلاق المنصة"""
    logger.info("إغلاق المنصة... إيقاف جميع البوتات الفرعية.")
    await bot_runner.stop_all_bots()

# --- واجهات برمجة التطبيقات (APIs) ---

@app.get("/api/stats")
async def get_stats():
    """إحصائيات المنصة الإجمالية"""
    try:
        bots_list = await database.get_bots()
        groups_list = await database.get_all_groups()
        warnings_list = await database.get_all_warnings()
        
        # معرفة البوت النشط حالياً وحالته الحقيقية
        active_bot = None
        bot_running_status = "stopped"
        if bots_list:
            active_bot = bots_list[0]
            bot_running_status = bot_runner.get_bot_runner_status(active_bot["bot_id"])
            
        return {
            "total_bots": len(bots_list),
            "total_groups": len(groups_list),
            "total_warnings": sum(w["warn_count"] for w in warnings_list),
            "bot_status": bot_running_status,
            "active_bot": active_bot
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/bots")
async def get_bots():
    """الحصول على قائمة البوتات المسجلة"""
    try:
        bots = await database.get_bots()
        # دمج الحالة التشغيلية الحقيقية لكل بوت
        for b in bots:
            b["status"] = bot_runner.get_bot_runner_status(b["bot_id"])
        return bots
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/bots")
async def register_bot(data: dict = Body(...)):
    """تسجيل بوت جديد في المنصة"""
    token = data.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="توكن البوت مطلوب.")
        
    bot_details = await resolve_bot_token(token)
    if not bot_details:
        raise HTTPException(status_code=400, detail="التوكن غير صالح أو تعذر الاتصال بتيليجرام.")
        
    try:
        await database.add_bot(
            bot_id=bot_details["id"],
            token=token,
            name=bot_details["name"],
            owner_id=None
        )
        return {"status": "success", "bot": bot_details}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/bots/{bot_id}")
async def delete_bot(bot_id: int):
    """حذف بوت من المنصة وإيقاف تشغيله"""
    try:
        await bot_runner.stop_bot(bot_id)
        await database.remove_bot(bot_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/bot/{bot_id}/start")
async def start_bot_endpoint(bot_id: int):
    """بدء تشغيل البوت"""
    success = await bot_runner.start_bot(bot_id)
    if success:
        return {"status": "success"}
    raise HTTPException(status_code=500, detail="فشل في تشغيل البوت. راجع السجلات.")

@app.post("/api/bot/{bot_id}/stop")
async def stop_bot_endpoint(bot_id: int):
    """إيقاف البوت"""
    success = await bot_runner.stop_bot(bot_id)
    if success:
        return {"status": "success"}
    raise HTTPException(status_code=500, detail="فشل في إيقاف البوت.")

@app.get("/api/bot/{bot_id}/logs")
async def get_bot_logs(bot_id: int, limit: int = Query(100, ge=10)):
    """جلب سجلات تشغيل البوت المباشرة"""
    logs = bot_runner.get_live_logs(limit)
    return {"logs": logs}

@app.get("/api/groups")
async def get_groups():
    """قائمة المجموعات المراقبة"""
    try:
        return await database.get_all_groups()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/group/{group_id}/settings")
async def get_group_settings(group_id: int):
    """إعدادات الحماية لمجموعة محددة"""
    try:
        settings = await database.get_group_settings(group_id)
        return settings
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/group/{group_id}/settings")
async def update_group_settings(group_id: int, settings: dict = Body(...)):
    """تحديث إعدادات الحماية لمجموعة محددة"""
    try:
        for key, val in settings.items():
            await database.update_group_setting(group_id, key, val)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/group/{group_id}/triggers")
async def get_group_triggers(group_id: int):
    """الردود التلقائية لمجموعة معينة"""
    try:
        triggers = await database.get_triggers(group_id)
        return [{"keyword": k, "response": r} for k, r in triggers.items()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/group/{group_id}/trigger")
async def add_group_trigger(group_id: int, data: dict = Body(...)):
    """إضافة رد تلقائي مخصص لمجموعة"""
    keyword = data.get("keyword")
    response = data.get("response")
    if not keyword or not response:
        raise HTTPException(status_code=400, detail="الكلمة المفتاحية والرد مطلوبان.")
    try:
        await database.add_trigger(group_id, keyword, response)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/group/{group_id}/trigger/{keyword}")
async def delete_group_trigger(group_id: int, keyword: str):
    """حذف رد تلقائي لمجموعة"""
    try:
        removed = await database.remove_trigger(group_id, keyword)
        if removed:
            return {"status": "success"}
        raise HTTPException(status_code=404, detail="الكلمة المفتاحية غير موجودة.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/logs/messages")
async def get_message_logs(limit: int = Query(50, ge=10)):
    """سجل الرسائل الأخيرة الخاضعة للرقابة"""
    try:
        return await database.get_global_recent_messages(limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/warnings")
async def get_warnings():
    """الحصول على قائمة الأعضاء الحاصلين على تحذيرات"""
    try:
        return await database.get_all_warnings()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/warning/reset")
async def reset_warning(data: dict = Body(...)):
    """تصفير تحذيرات العضو"""
    group_id = data.get("group_id")
    user_id = data.get("user_id")
    if not group_id or not user_id:
        raise HTTPException(status_code=400, detail="معرف المجموعة ومعرف العضو مطلوبان.")
    try:
        await database.reset_warnings(group_id, user_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# إنشاء مجلد الملفات الساكنة لخدمته
os.makedirs("frontend/dist", exist_ok=True)

# خدمة واجهة الويب كملف رئيسي
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # تشغيل خادم الويب على المنفذ 8000
    uvicorn.run(app, host="127.0.0.1", port=8000)
