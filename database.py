import aiosqlite
import os
import json
import time

DB_PATH = "bot_data.db"

def db_connect():
    return aiosqlite.connect(DB_PATH, timeout=30.0)

async def init_db():
    """تهيئة قاعدة البيانات وإنشاء الجداول إذا لم تكن موجودة"""
    async with db_connect() as db:
        # 1. جدول البوتات لدعم البوتات المتعددة
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bots (
                bot_id INTEGER PRIMARY KEY,
                token TEXT UNIQUE NOT NULL,
                name TEXT,
                owner_id INTEGER,
                status TEXT DEFAULT 'stopped',
                created_at INTEGER
            )
        """)

        # 2. جدول المجموعات
        await db.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                group_id INTEGER PRIMARY KEY,
                bot_id INTEGER,
                title TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)

        # 3. جدول الموديولات وإعداداتها الديناميكية لكل مجموعة
        await db.execute("""
            CREATE TABLE IF NOT EXISTS group_modules (
                group_id INTEGER,
                module_name TEXT,
                is_enabled INTEGER DEFAULT 1,
                settings_json TEXT DEFAULT '{}',
                PRIMARY KEY (group_id, module_name)
            )
        """)

        # 4. جدول تحذيرات الأعضاء
        await db.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                group_id INTEGER,
                user_id INTEGER,
                warn_count INTEGER DEFAULT 0,
                PRIMARY KEY (group_id, user_id)
            )
        """)

        # 5. جدول سجلات الرسائل لتلخيص النقاشات
        await db.execute("""
            CREATE TABLE IF NOT EXISTS message_logs (
                group_id INTEGER,
                user_id INTEGER,
                username TEXT,
                full_name TEXT,
                message_text TEXT,
                timestamp INTEGER
            )
        """)

        # 6. جدول الردود التلقائية المخصصة (Triggers)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS triggers (
                group_id INTEGER,
                keyword TEXT,
                response TEXT,
                PRIMARY KEY (group_id, keyword)
            )
        """)

        # 7. جدول الكلمات المشبوهة للتعلم التلقائي والضبط اليدوي
        await db.execute("""
            CREATE TABLE IF NOT EXISTS spam_keywords (
                keyword TEXT PRIMARY KEY,
                added_by TEXT DEFAULT 'system',
                created_at INTEGER,
                weight INTEGER DEFAULT 1,
                category TEXT DEFAULT 'general',
                is_approved INTEGER DEFAULT 0
            )
        """)

        # 8. جدول الحظر العام
        await db.execute("""
            CREATE TABLE IF NOT EXISTS global_bans (
                user_id INTEGER PRIMARY KEY,
                reason TEXT,
                created_at INTEGER
            )
        """)

        # ترقية جدول groups القديم لإضافة الأعمدة الجديدة إذا لم تكن موجودة
        try:
            await db.execute("ALTER TABLE groups ADD COLUMN bot_id INTEGER")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE groups ADD COLUMN title TEXT")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE groups ADD COLUMN is_active INTEGER DEFAULT 1")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE groups ADD COLUMN invite_link TEXT")
        except Exception:
            pass

        # ترقية جدول spam_keywords لإضافة الأعمدة الجديدة
        try:
            await db.execute("ALTER TABLE spam_keywords ADD COLUMN weight INTEGER DEFAULT 1")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE spam_keywords ADD COLUMN category TEXT DEFAULT 'general'")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE spam_keywords ADD COLUMN is_approved INTEGER DEFAULT 0")
        except Exception:
            pass

        # إنشاء فهارس لتحسين الأداء وتسريع البحث (Database Indexes)
        try:
            await db.execute("CREATE INDEX IF NOT EXISTS idx_message_logs_group ON message_logs (group_id, timestamp)")
        except Exception:
            pass
        try:
            await db.execute("CREATE INDEX IF NOT EXISTS idx_warnings_user ON warnings (group_id, user_id)")
        except Exception:
            pass
        try:
            await db.execute("CREATE INDEX IF NOT EXISTS idx_spam_keywords_approved ON spam_keywords (is_approved, weight)")
        except Exception:
            pass

        await db.commit()

    # الهجرة من الهيكل القديم للمجموعات إلى هيكل الموديولات الجديد (security)
    await migrate_old_settings()
    # تهيئة الكلمات المشبوهة الافتراضية
    await init_default_spam_keywords()

async def migrate_old_settings():
    try:
        async with db_connect() as db:
            # التحقق هل جدول الموديولات فارغ
            async with db.execute("SELECT COUNT(*) FROM group_modules") as cursor:
                count = (await cursor.fetchone())[0]
            if count == 0:
                # التحقق من وجود الأعمدة القديمة في جدول groups
                db.row_factory = aiosqlite.Row
                # محاولة قراءة المجموعات القديمة
                async with db.execute("SELECT * FROM groups") as cursor:
                    rows = await cursor.fetchall()
                    for r in rows:
                        g_id = r['group_id']
                        r_dict = dict(r)
                        # قد تكون الأعمدة القديمة غير موجودة، لذا نلتقط المفاتيح بأمان
                        sec_settings = {
                            "welcome_message": r_dict.get('welcome_message', 'أهلاً بك {name} في المجموعة! 🌹'),
                            "welcome_enabled": r_dict.get('welcome_enabled', 1),
                            "captcha_enabled": r_dict.get('captcha_enabled', 0),
                            "anti_link": r_dict.get('anti_link', 1),
                            "anti_spam": r_dict.get('anti_spam', 1),
                            "gemini_enabled": r_dict.get('gemini_enabled', 1)
                        }
                        await db.execute(
                            "INSERT OR REPLACE INTO group_modules (group_id, module_name, is_enabled, settings_json) VALUES (?, 'security', 1, ?)",
                            (g_id, json.dumps(sec_settings))
                        )
                await db.commit()
    except Exception:
        # في حال عدم وجود جدول groups القديم أو حدوث خطأ
        pass


# --- وظائف إدارة إعدادات المجموعات (مع الحفاظ على التوافق الخلفي) ---

async def add_group(group_id: int, bot_id: int = None, title: str = None, invite_link: str = None):
    async with db_connect() as db:
        # Check if group already exists
        async with db.execute("SELECT group_id FROM groups WHERE group_id = ?", (group_id,)) as cursor:
            row = await cursor.fetchone()
            
        if not row:
            await db.execute(
                "INSERT INTO groups (group_id, bot_id, title, invite_link) VALUES (?, ?, ?, ?)",
                (group_id, bot_id, title, invite_link)
            )
        else:
            # Update fields if provided
            if bot_id is not None or title is not None or invite_link is not None:
                await db.execute(
                    """
                    UPDATE groups 
                    SET bot_id = COALESCE(?, bot_id), 
                        title = COALESCE(?, title), 
                        invite_link = COALESCE(?, invite_link) 
                    WHERE group_id = ?
                    """,
                    (bot_id, title, invite_link, group_id)
                )
        # تهيئة إعدادات الأمان الافتراضية
        default_settings = {
            "welcome_message": "أهلاً بك {name} في المجموعة! 🌹",
            "welcome_enabled": 1,
            "captcha_enabled": 0,
            "anti_link": 1,
            "anti_spam": 1,
            "gemini_enabled": 1,
            "anti_sticker": 0,
            "anti_gif": 0,
            "anti_photo": 0,
            "anti_video": 0,
            "anti_document": 0,
            "anti_fwd": 0,
            "anti_voice": 0,
            "anti_audio": 0,
            "anti_contact": 0,
            "anti_chat": 0,
            "anti_join": 0,
            "anti_list": 0,
            "lock_enabled": 0,
            "anti_flood": 0,
            "censorship_enabled": 0
        }
        await db.execute(
            "INSERT OR IGNORE INTO group_modules (group_id, module_name, is_enabled, settings_json) VALUES (?, 'security', 1, ?)",
            (group_id, json.dumps(default_settings))
        )
        await db.commit()

async def get_group_settings(group_id: int) -> dict:
    await add_group(group_id)
    async with db_connect() as db:
        async with db.execute(
            "SELECT settings_json FROM group_modules WHERE group_id = ? AND module_name = 'security'",
            (group_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                try:
                    return json.loads(row[0])
                except Exception:
                    pass
            # افتراضات الحماية
            return {
                "welcome_message": "أهلاً بك {name} في المجموعة! 🌹",
                "welcome_enabled": 1,
                "captcha_enabled": 0,
                "anti_link": 1,
                "anti_spam": 1,
                "gemini_enabled": 1,
                "anti_sticker": 0,
                "anti_gif": 0,
                "anti_photo": 0,
                "anti_video": 0,
                "anti_document": 0,
                "anti_fwd": 0,
                "anti_voice": 0,
                "anti_audio": 0,
                "anti_contact": 0,
                "anti_chat": 0,
                "anti_join": 0,
                "anti_list": 0,
                "lock_enabled": 0,
                "anti_flood": 0,
                "censorship_enabled": 0
            }

async def update_group_setting(group_id: int, setting_name: str, value):
    await add_group(group_id)
    settings = await get_group_settings(group_id)
    settings[setting_name] = value
    async with db_connect() as db:
        await db.execute(
            "UPDATE group_modules SET settings_json = ? WHERE group_id = ? AND module_name = 'security'",
            (json.dumps(settings), group_id)
        )
        await db.commit()

# --- وظائف إدارة البوتات المتعددة (المنصة) ---

async def add_bot(bot_id: int, token: str, name: str = None, owner_id: int = None):
    now = int(time.time())
    async with db_connect() as db:
        await db.execute(
            "INSERT OR REPLACE INTO bots (bot_id, token, name, owner_id, status, created_at) VALUES (?, ?, ?, ?, 'stopped', ?)",
            (bot_id, token, name, owner_id, now)
        )
        await db.commit()

async def get_bots():
    async with db_connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM bots") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def get_bot(bot_id: int):
    async with db_connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM bots WHERE bot_id = ?", (bot_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def update_bot_status(bot_id: int, status: str):
    async with db_connect() as db:
        await db.execute("UPDATE bots SET status = ? WHERE bot_id = ?", (status, bot_id))
        await db.commit()

async def remove_bot(bot_id: int):
    async with db_connect() as db:
        await db.execute("DELETE FROM bots WHERE bot_id = ?", (bot_id,))
        await db.commit()

# --- وظائف إدارة المجموعات للوحة التحكم ---

async def get_all_groups():
    async with db_connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM groups") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def remove_group(group_id: int):
    async with db_connect() as db:
        await db.execute("DELETE FROM groups WHERE group_id = ?", (group_id,))
        await db.execute("DELETE FROM group_modules WHERE group_id = ?", (group_id,))
        await db.commit()

# --- وظائف إدارة الموديولات العامة ---

async def get_group_module_settings(group_id: int, module_name: str) -> dict:
    async with db_connect() as db:
        async with db.execute(
            "SELECT settings_json FROM group_modules WHERE group_id = ? AND module_name = ?",
            (group_id, module_name)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                try:
                    return json.loads(row[0])
                except Exception:
                    pass
            return {}

async def update_group_module_settings(group_id: int, module_name: str, settings: dict):
    async with db_connect() as db:
        await db.execute(
            "INSERT OR REPLACE INTO group_modules (group_id, module_name, settings_json) VALUES (?, ?, ?)",
            (group_id, module_name, json.dumps(settings))
        )
        await db.commit()

# --- وظائف إدارة التحذيرات (Warnings) ---

async def get_warnings(group_id: int, user_id: int) -> int:
    async with db_connect() as db:
        async with db.execute(
            "SELECT warn_count FROM warnings WHERE group_id = ? AND user_id = ?",
            (group_id, user_id)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def add_warning(group_id: int, user_id: int) -> int:
    current = await get_warnings(group_id, user_id)
    new_warn = current + 1
    async with db_connect() as db:
        await db.execute(
            "INSERT OR REPLACE INTO warnings (group_id, user_id, warn_count) VALUES (?, ?, ?)",
            (group_id, user_id, new_warn)
        )
        await db.commit()
    return new_warn

async def reset_warnings(group_id: int, user_id: int):
    async with db_connect() as db:
        await db.execute(
            "DELETE FROM warnings WHERE group_id = ? AND user_id = ?",
            (group_id, user_id)
        )
        await db.commit()

async def get_all_warnings():
    async with db_connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM warnings WHERE warn_count > 0") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

# --- وظائف سجلات الرسائل للتلخيص (Message Logging) ---

async def log_message(group_id: int, user_id: int, username: str, full_name: str, message_text: str):
    now = int(time.time())
    async with db_connect() as db:
        await db.execute(
            "INSERT INTO message_logs (group_id, user_id, username, full_name, message_text, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (group_id, user_id, username, full_name, message_text, now)
        )
        await db.execute(
            """
            DELETE FROM message_logs 
            WHERE group_id = ? 
              AND rowid NOT IN (
                  SELECT rowid FROM message_logs 
                  WHERE group_id = ? 
                  ORDER BY timestamp DESC 
                  LIMIT 75
              )
            """,
            (group_id, group_id)
        )
        await db.commit()

async def get_recent_messages(group_id: int, limit: int = 75) -> list:
    async with db_connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM (
                SELECT username, full_name, message_text, timestamp 
                FROM message_logs 
                WHERE group_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ) ORDER BY timestamp ASC
            """,
            (group_id, limit)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def get_global_recent_messages(limit: int = 100) -> list:
    async with db_connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM message_logs ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

# --- وظائف الردود التلقائية (Triggers) ---

async def add_trigger(group_id: int, keyword: str, response: str):
    async with db_connect() as db:
        await db.execute(
            "INSERT OR REPLACE INTO triggers (group_id, keyword, response) VALUES (?, ?, ?)",
            (group_id, keyword.lower(), response)
        )
        await db.commit()

async def remove_trigger(group_id: int, keyword: str) -> bool:
    async with db_connect() as db:
        cursor = await db.execute(
            "DELETE FROM triggers WHERE group_id = ? AND keyword = ?",
            (group_id, keyword.lower())
        )
        await db.commit()
        return cursor.rowcount > 0

async def get_trigger(group_id: int, keyword: str) -> str:
    async with db_connect() as db:
        async with db.execute(
            "SELECT response FROM triggers WHERE group_id = ? AND keyword = ?",
            (group_id, keyword.lower())
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def get_triggers(group_id: int) -> dict:
    async with db_connect() as db:
        async with db.execute(
            "SELECT keyword, response FROM triggers WHERE group_id = ?",
            (group_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}

async def get_all_triggers_list():
    async with db_connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM triggers") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


# --- وظائف إدارة الكلمات المشبوهة الديناميكية (التعلم التلقائي) ---

async def init_default_spam_keywords():
    """تهيئة الكلمات المشبوهة الافتراضية إذا كان الجدول فارغاً"""
    async with db_connect() as db:
        async with db.execute("SELECT COUNT(*) FROM spam_keywords") as cursor:
            count = (await cursor.fetchone())[0]
        
        if count == 0:
            default_keywords = [
                # حل واجبات، كويزات، اختبارات، مشاريع
                "حل واجب", "حل واجبات", "حل كويز", "حل كويزات", "حل اختبار", "حل اختبارات",
                "حل ميد", "حل فاينل", "واجبات", "كويزات", "بحوث", "تقارير", "شرح خصوصي",
                "ملخصات", "سلايدات", "شباتر", "جامعة", "خصوصي", "مدرس خصوصي", "اسايمنت",
                "assignment", "homework", "exam", "quiz", "project", "كتابة بحوث", "كتابة تقارير",
                
                # قنوات وتواصل وترويج ومواقع تواصل
                "سناب", "سنابي", "سناب شات", "واتساب", "قروب", "قروبات", "قناة", "قنوات",
                "اشترك", "اشتراك", "متابعين", "دعم حسابات", "دعم قنوات", "لايكات", "تيك توك",
                "انستقرام", "تويتر", "تليجرام", "تيليجرام", "رابط المجموعه", "راسلني", "تواصل معي",
                "رابط قروب", "رابط قناة", "خاص", "الخاص", "تعال خاص", "كلمني خاص",
                
                # تجارة، سلع، تمويل، قروض، وظائف وهمية
                "سعر", "أسعار", "خدمة", "خدمات", "عرض", "عروض", "خصم", "كود خصم", "كوبون",
                "تمويل", "قرض", "قروض", "تسديد قروض", "بنك", "ربح", "استثمار", "تداول",
                "عملات رقمية", "شغل من البيت", "عمل من المنزل", "وظائف شاغرة", "دخل إضافي",
                "متوفر الان", "يوجد لدينا", "نوفر لكم", "للبيع", "شراء", "شحن"
            ]
            now = int(time.time())
            for kw in default_keywords:
                await db.execute(
                    "INSERT OR IGNORE INTO spam_keywords (keyword, added_by, created_at) VALUES (?, 'system', ?)",
                    (kw.lower(), now)
                )
            await db.commit()

async def add_spam_keyword(keyword: str, added_by: str = 'system', category: str = 'general') -> bool:
    """إضافة كلمة مشبوهة جديدة أو زيادة وزنها وتعديل حالتها إذا كانت موجودة"""
    kw_clean = keyword.strip().lower()
    if not kw_clean:
        return False
    now = int(time.time())
    is_admin = added_by.startswith('admin') or added_by.startswith('gemini_auto_manual')
    
    async with db_connect() as db:
        try:
            # التحقق هل الكلمة موجودة مسبقاً
            async with db.execute("SELECT weight, is_approved FROM spam_keywords WHERE keyword = ?", (kw_clean,)) as cursor:
                row = await cursor.fetchone()
                
            if row:
                current_weight, current_approved = row[0], row[1]
                # لو أدمن يثبت كـ معتمدة بوزن عالي، لو تلقائي نزيد الوزن بمقدار 1
                new_approved = 1 if (is_admin or current_approved == 1) else 0
                new_weight = 10 if is_admin else (current_weight + 1)
                if new_weight >= 3:
                    new_approved = 1
                await db.execute(
                    "UPDATE spam_keywords SET weight = ?, is_approved = ?, added_by = ?, created_at = ? WHERE keyword = ?",
                    (new_weight, new_approved, added_by, now, kw_clean)
                )
            else:
                initial_approved = 1 if is_admin else 0
                initial_weight = 10 if is_admin else 1
                await db.execute(
                    "INSERT INTO spam_keywords (keyword, added_by, created_at, weight, category, is_approved) VALUES (?, ?, ?, ?, ?, ?)",
                    (kw_clean, added_by, now, initial_weight, category, initial_approved)
                )
            await db.commit()
            return True
        except Exception:
            return False

async def get_all_spam_keywords() -> list:
    """جلب الكلمات المشبوهة النشطة (المعتمدة أو التي وزنها >= 3)"""
    async with db_connect() as db:
        async with db.execute("SELECT keyword FROM spam_keywords WHERE is_approved = 1 OR weight >= 3") as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows]

async def get_all_spam_keywords_details() -> list:
    """جلب جميع الكلمات المشبوهة وتفاصيلها للأدمن"""
    async with db_connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM spam_keywords ORDER BY is_approved DESC, weight DESC") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def approve_spam_keyword(keyword: str) -> bool:
    """اعتماد الكلمة المشبوهة يدوياً من الأدمن وترقيتها"""
    kw_clean = keyword.strip().lower()
    async with db_connect() as db:
        try:
            cursor = await db.execute(
                "UPDATE spam_keywords SET is_approved = 1, weight = 10 WHERE keyword = ?",
                (kw_clean,)
            )
            await db.commit()
            return cursor.rowcount > 0
        except Exception:
            return False

async def remove_spam_keyword(keyword: str) -> bool:
    """حذف كلمة مشبوهة من قاعدة البيانات"""
    kw_clean = keyword.strip().lower()
    async with db_connect() as db:
        cursor = await db.execute("DELETE FROM spam_keywords WHERE keyword = ?", (kw_clean,))
        await db.commit()
        return cursor.rowcount > 0

async def get_learn_stats() -> dict:
    """إحصائيات التعلم المشبوه"""
    async with db_connect() as db:
        try:
            async with db.execute("SELECT COUNT(*) FROM spam_keywords") as c:
                total = (await c.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM spam_keywords WHERE is_approved = 1 OR weight >= 3") as c:
                approved = (await c.fetchone())[0]
            return {
                "total": total,
                "approved": approved,
                "pending": total - approved
            }
        except Exception:
            return {"total": 0, "approved": 0, "pending": 0}

async def reset_learned_keywords() -> bool:
    """مسح الكلمات المتعلمة التي لم تعتمد ولم يزد وزنها عن 3"""
    async with db_connect() as db:
        try:
            await db.execute("DELETE FROM spam_keywords WHERE is_approved = 0 AND weight < 3")
            await db.commit()
            return True
        except Exception:
            return False


async def add_global_ban(user_id: int, reason: str = "") -> bool:
    """إضافة مستخدم للحظر العام"""
    now = int(time.time())
    async with db_connect() as db:
        try:
            await db.execute(
                "INSERT OR REPLACE INTO global_bans (user_id, reason, created_at) VALUES (?, ?, ?)",
                (user_id, reason, now)
            )
            await db.commit()
            return True
        except Exception:
            return False


async def remove_global_ban(user_id: int) -> bool:
    """إلغاء الحظر العام عن مستخدم"""
    async with db_connect() as db:
        try:
            cursor = await db.execute("DELETE FROM global_bans WHERE user_id = ?", (user_id,))
            await db.commit()
            return cursor.rowcount > 0
        except Exception:
            return False


async def is_globally_banned(user_id: int) -> bool:
    """التحقق هل المستخدم محظور عام"""
    async with db_connect() as db:
        try:
            async with db.execute("SELECT user_id FROM global_bans WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                return row is not None
        except Exception:
            return False

