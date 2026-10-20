import aiosqlite
import datetime
import os
from typing import Optional, List, Dict, Any
from config import settings

DB_FILE = settings.DATABASE_PATH

async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        # Users table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                credits INTEGER DEFAULT 15,
                is_vip INTEGER DEFAULT 0,
                ref_by INTEGER DEFAULT NULL,
                ref_count INTEGER DEFAULT 0,
                conversions_count INTEGER DEFAULT 0,
                used_ig_code_today INTEGER DEFAULT 0,
                last_ig_code_date TEXT,
                is_banned INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Channels table (for dynamic force-join management)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT UNIQUE,
                title TEXT,
                invite_link TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Settings table (for runtime key-value settings)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        # Conversions log
        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                doc_type TEXT,
                pages_count INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Seed default settings if empty
        cursor = await db.execute("SELECT COUNT(*) FROM settings")
        count = (await cursor.fetchone())[0]
        if count == 0:
            default_settings = [
                ("daily_ig_code", settings.DAILY_INSTAGRAM_CODE),
                ("ig_page_url", settings.INSTAGRAM_PAGE_URL),
                ("ig_username", settings.INSTAGRAM_USERNAME),
                ("default_credits", str(settings.DEFAULT_USER_CREDITS)),
                ("referral_bonus", str(settings.REFERRAL_BONUS_CREDITS)),
                ("ig_bonus", str(settings.INSTAGRAM_BONUS_CREDITS)),
            ]
            await db.executemany("INSERT INTO settings (key, value) VALUES (?, ?)", default_settings)
            
        await db.commit()

async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
    return None

async def register_or_update_user(user_id: int, username: Optional[str], first_name: Optional[str], ref_by: Optional[int] = None) -> Dict[str, Any]:
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            existing = await cursor.fetchone()
            
        if existing:
            await db.execute(
                "UPDATE users SET username = ?, first_name = ? WHERE user_id = ?",
                (username, first_name, user_id)
            )
            await db.commit()
            return dict(existing)
        
        # New user
        initial_credits = settings.DEFAULT_USER_CREDITS
        valid_ref_by = None
        
        # Check if ref_by exists and is not the same user
        if ref_by and ref_by != user_id:
            async with db.execute("SELECT user_id FROM users WHERE user_id = ?", (ref_by,)) as cursor:
                ref_user = await cursor.fetchone()
                if ref_user:
                    valid_ref_by = ref_by
                    # Award bonus to referrer
                    await db.execute(
                        "UPDATE users SET credits = credits + ?, ref_count = ref_count + 1 WHERE user_id = ?",
                        (settings.REFERRAL_BONUS_CREDITS, ref_by)
                    )
        
        await db.execute(
            """INSERT INTO users (user_id, username, first_name, credits, ref_by)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, username, first_name, initial_credits, valid_ref_by)
        )
        await db.commit()
        
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row)

async def deduct_user_credits(user_id: int, count: int = 1) -> bool:
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT credits, is_vip FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            if not user:
                return False
            if user["is_vip"]:
                await db.execute("UPDATE users SET conversions_count = conversions_count + 1 WHERE user_id = ?", (user_id,))
                await db.commit()
                return True
            if user["credits"] >= count:
                await db.execute(
                    "UPDATE users SET credits = credits - ?, conversions_count = conversions_count + 1 WHERE user_id = ?",
                    (count, user_id)
                )
                await db.commit()
                return True
            return False

async def add_user_credits(user_id: int, amount: int) -> int:
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("UPDATE users SET credits = credits + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()
        async with db.execute("SELECT credits FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def set_user_vip(user_id: int, is_vip: bool) -> None:
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("UPDATE users SET is_vip = ? WHERE user_id = ?", (1 if is_vip else 0, user_id))
        await db.commit()

async def log_conversion(user_id: int, doc_type: str, pages_count: int = 1):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            "INSERT INTO conversions (user_id, doc_type, pages_count) VALUES (?, ?, ?)",
            (user_id, doc_type, pages_count)
        )
        await db.commit()

# Settings getters and setters
async def get_setting(key: str, default: str = "") -> str:
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else default

async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        await db.commit()

# Instagram Daily Code verification
async def check_and_apply_ig_code(user_id: int, input_code: str) -> tuple[bool, str]:
    today_str = datetime.date.today().isoformat()
    current_code = await get_setting("daily_ig_code", settings.DAILY_INSTAGRAM_CODE)
    
    if input_code.strip().lower() != current_code.strip().lower():
        return False, "❌ کد وارد شده صحیح نیست! لطفاً استوری امروز پیج ما را مجدداً چک کنید."
        
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT last_ig_code_date FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            if user and user["last_ig_code_date"] == today_str:
                return False, "⚠️ شما امروز قبلاً پاداش کد استوری را دریافت کرده‌اید! فردا منتظر کد جدید باشید."
                
        bonus = int(await get_setting("ig_bonus", str(settings.INSTAGRAM_BONUS_CREDITS)))
        await db.execute(
            "UPDATE users SET credits = credits + ?, last_ig_code_date = ?, used_ig_code_today = 1 WHERE user_id = ?",
            (bonus, today_str, user_id)
        )
        await db.commit()
        return True, f"🎉 تبریک! کد تأیید شد و {bonus} اعتبار هدیه به حسابتان اضافه شد!"

# Channels Management
async def get_active_channels() -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM channels WHERE is_active = 1") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def add_channel(channel_id: str, title: str, invite_link: str) -> bool:
    async with aiosqlite.connect(DB_FILE) as db:
        try:
            await db.execute(
                "INSERT OR REPLACE INTO channels (channel_id, title, invite_link, is_active) VALUES (?, ?, ?, 1)",
                (channel_id.strip(), title.strip(), invite_link.strip())
            )
            await db.commit()
            return True
        except Exception:
            return False

async def remove_channel(channel_id: str) -> bool:
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id.strip(),))
        await db.commit()
        return True

# Admin Statistics
async def get_admin_stats() -> Dict[str, Any]:
    today_str = datetime.date.today().isoformat()
    async with aiosqlite.connect(DB_FILE) as db:
        # Total users
        c = await db.execute("SELECT COUNT(*) FROM users")
        total_users = (await c.fetchone())[0]
        
        # New users today
        c = await db.execute("SELECT COUNT(*) FROM users WHERE DATE(created_at) = ?", (today_str,))
        users_today = (await c.fetchone())[0]
        
        # Total conversions
        c = await db.execute("SELECT COUNT(*), COALESCE(SUM(pages_count), 0) FROM conversions")
        row = await c.fetchone()
        total_conversions = row[0]
        total_pages = row[1]
        
        # Conversions today
        c = await db.execute("SELECT COUNT(*), COALESCE(SUM(pages_count), 0) FROM conversions WHERE DATE(created_at) = ?", (today_str,))
        row_today = await c.fetchone()
        conversions_today = row_today[0]
        pages_today = row_today[1]
        
        # Active channels count
        c = await db.execute("SELECT COUNT(*) FROM channels WHERE is_active = 1")
        channels_count = (await c.fetchone())[0]

        return {
            "total_users": total_users,
            "users_today": users_today,
            "total_conversions": total_conversions,
            "total_pages": total_pages,
            "conversions_today": conversions_today,
            "pages_today": pages_today,
            "channels_count": channels_count,
        }

async def get_all_user_ids() -> List[int]:
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT user_id FROM users WHERE is_banned = 0") as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows]
