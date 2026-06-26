import importlib
import pkgutil
import logging
from aiogram import Dispatcher

logger = logging.getLogger(__name__)

def load_plugins(dp: Dispatcher):
    """تحميل جميع الإضافات (Plugins) ديناميكياً وتسجيل الراوترات في الموزع (Dispatcher)"""
    import modules
    
    # الحصول على مسار مجلد الإضافات
    plugins_path = modules.__path__
    plugins_prefix = modules.__name__ + "."
    
    loaded_count = 0
    for _, module_name, is_pkg in pkgutil.iter_modules(plugins_path, plugins_prefix):
        if is_pkg:
            try:
                # استيراد الموديول ديناميكياً
                module = importlib.import_module(module_name)
                
                # التحقق من وجود راوتر لتسجيله
                if hasattr(module, "router"):
                    dp.include_router(module.router)
                    logger.info(f"🧩 تم تحميل وتسجيل الإضافة بنجاح: {module_name}")
                    loaded_count += 1
                else:
                    logger.warning(f"⚠️ الإضافة {module_name} لا تحتوى على 'router' لتسجيله.")
            except Exception as e:
                logger.error(f"❌ فشل تحميل الإضافة {module_name}: {e}", exc_info=True)
                
    logger.info(f"📊 إجمالي الإضافات المحملة ديناميكياً: {loaded_count}")
