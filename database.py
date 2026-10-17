import aiosqlite
from datetime import datetime
from config import (
    DB_PATH,
    DEFAULT_SEEN_API_KEY,
    DEFAULT_MARGIN_PERCENT,
    DEFAULT_CARD_NUMBER,
    DEFAULT_CARD_HOLDER,
    DEFAULT_MIN_DEPOSIT,
    DEFAULT_REF_BONUS,
    DEFAULT_SUPPORT_USERNAME,
    ADMINS,
    ADMIN_IDS
)

class Database:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path

    async def connect(self):
        return await aiosqlite.connect(self.db_path)

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            # Users table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id BIGINT UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    balance REAL DEFAULT 0.0,
                    spent_total REAL DEFAULT 0.0,
                    referrer_id BIGINT,
                    referrals_count INTEGER DEFAULT 0,
                    referral_earned REAL DEFAULT 0.0,
                    is_banned INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Orders table (SMM orders)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id BIGINT NOT NULL,
                    service_id INTEGER NOT NULL,
                    service_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    link TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price REAL NOT NULL,
                    api_order_id INTEGER,
                    status TEXT DEFAULT 'pending',
                    start_count INTEGER DEFAULT 0,
                    remains INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Virtual numbers table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS numbers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id BIGINT NOT NULL,
                    order_id INTEGER,
                    service_code TEXT NOT NULL,
                    service_title TEXT NOT NULL,
                    country_code INTEGER NOT NULL,
                    country_title TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    sms_code TEXT,
                    price REAL NOT NULL,
                    status TEXT DEFAULT 'WAIT_CODE',
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Deposits table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS deposits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id BIGINT NOT NULL,
                    amount REAL NOT NULL,
                    payment_method TEXT DEFAULT 'karta',
                    receipt_photo_id TEXT,
                    status TEXT DEFAULT 'pending',
                    admin_comment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Services cache table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS services (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service_id INTEGER UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    type TEXT,
                    rate REAL NOT NULL,
                    min INTEGER DEFAULT 10,
                    max INTEGER DEFAULT 100000,
                    description TEXT,
                    is_active INTEGER DEFAULT 1,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Key-Value Settings table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            # Free Orders table (for 24h cooldown)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS free_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id BIGINT NOT NULL,
                    service_type TEXT NOT NULL,
                    link TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Promo Codes table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS promo_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    reward_amount REAL NOT NULL,
                    max_uses INTEGER DEFAULT 0,
                    current_uses INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Promo Code Activations table (ensures each user only redeems once)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS promo_code_activations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    promo_code_id INTEGER NOT NULL,
                    code TEXT NOT NULL,
                    user_id BIGINT NOT NULL,
                    reward_amount REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(promo_code_id, user_id)
                )
            """)

            # Admins table (tracks roles and activity)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id BIGINT UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    role TEXT DEFAULT 'admin',
                    added_by BIGINT,
                    actions_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await db.commit()

        # Seed initial default settings if missing
        default_settings = {
            "seen_api_key": DEFAULT_SEEN_API_KEY,
            "margin_percent": str(DEFAULT_MARGIN_PERCENT),
            "card_number": DEFAULT_CARD_NUMBER,
            "card_holder": DEFAULT_CARD_HOLDER,
            "min_deposit": str(DEFAULT_MIN_DEPOSIT),
            "ref_bonus": str(DEFAULT_REF_BONUS),
            "support_username": DEFAULT_SUPPORT_USERNAME,
            "channel_url": "https://t.me/pixorasmm",
            "is_maintenance": "0",
            "free_services_enabled": "1"
        }
        for k, v in default_settings.items():
            curr = await self.get_setting(k)
            if curr is None:
                await self.set_setting(k, v)

        # Always enforce support username to ismoiluzb022
        await self.set_setting("support_username", DEFAULT_SUPPORT_USERNAME)

        # Ensure card number is not dummy
        current_card = await self.get_setting("card_number")
        if not current_card or "8600 0000" in current_card:
            await self.set_setting("card_number", DEFAULT_CARD_NUMBER)
            await self.set_setting("card_holder", DEFAULT_CARD_HOLDER)

        # Ensure dummy services are permanently removed
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM services WHERE service_id IN (101, 102, 103, 104, 201, 202, 203, 204, 301, 402, 403)")
            await db.commit()

        # Seed default owners into admins table and load into ADMIN_IDS cache
        async with aiosqlite.connect(self.db_path) as db:
            for a_id in ADMINS:
                await db.execute("""
                    INSERT INTO admins (user_id, username, first_name, role)
                    VALUES (?, 'ismoiluzb022', 'Bosh Admin', 'owner')
                    ON CONFLICT(user_id) DO UPDATE SET role = 'owner'
                """, (a_id,))
            await db.commit()

            cursor = await db.execute("SELECT user_id FROM admins")
            rows = await cursor.fetchall()
            for r in rows:
                ADMIN_IDS.add(r[0])

    # User Methods
    async def get_or_create_user(self, user_id: int, username: str = None, first_name: str = None, referrer_id: int = None):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = await cursor.fetchone()
            if user:
                # Update info if changed
                await db.execute("UPDATE users SET username = ?, first_name = ? WHERE user_id = ?", 
                                 (username, first_name, user_id))
                await db.commit()
                return dict(user)

            # Check referrer
            valid_ref = None
            if referrer_id and referrer_id != user_id:
                ref_cur = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (referrer_id,))
                if await ref_cur.fetchone():
                    valid_ref = referrer_id

            await db.execute("""
                INSERT INTO users (user_id, username, first_name, referrer_id)
                VALUES (?, ?, ?, ?)
            """, (user_id, username, first_name, valid_ref))

            if valid_ref:
                await db.execute("UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = ?", (valid_ref,))

            await db.commit()

            cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            return dict(row)

    async def get_user(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_all_users(self):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users ORDER BY id DESC")
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_user_by_username(self, username: str):
        clean_u = username.strip().lstrip('@').lower()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE LOWER(username) = ?", (clean_u,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def search_users(self, query: str):
        clean_q = f"%{str(query).strip().lstrip('@')}%"
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM users 
                WHERE username LIKE ? OR first_name LIKE ? OR CAST(user_id AS TEXT) LIKE ?
                ORDER BY id DESC LIMIT 30
            """, (clean_q, clean_q, clean_q))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def update_balance(self, user_id: int, amount: float):
        """Amount can be positive (add) or negative (deduct)."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
            if amount < 0:
                await db.execute("UPDATE users SET spent_total = spent_total + ? WHERE user_id = ?", (abs(amount), user_id))
            await db.commit()

    # Settings Methods
    async def get_setting(self, key: str, default: str = None) -> str:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = await cursor.fetchone()
            return row[0] if row else default

    async def set_setting(self, key: str, value: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
            await db.commit()

    # SMM Orders
    async def add_order(self, user_id: int, service_id: int, service_name: str, category: str, link: str, quantity: int, price: float, api_order_id: int = None):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO orders (user_id, service_id, service_name, category, link, quantity, price, api_order_id, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
            """, (user_id, service_id, service_name, category, link, quantity, price, api_order_id))
            order_id = cursor.lastrowid
            await db.commit()
            return order_id

    async def get_user_orders(self, user_id: int, limit: int = 10):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def update_order_status(self, order_id: int, status: str, remains: int = 0, start_count: int = 0):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE orders SET status = ?, remains = ?, start_count = ? WHERE id = ?
            """, (status, remains, start_count, order_id))
            await db.commit()

    # Virtual Numbers
    async def add_number(self, user_id: int, order_id: int, service_code: str, service_title: str, country_code: int, country_title: str, phone: str, price: float, expires_at: str):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO numbers (user_id, order_id, service_code, service_title, country_code, country_title, phone, price, expires_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'WAIT_CODE')
            """, (user_id, order_id, service_code, service_title, country_code, country_title, phone, price, expires_at))
            num_id = cursor.lastrowid
            await db.commit()
            return num_id

    async def get_user_numbers(self, user_id: int, limit: int = 10):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM numbers WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_number(self, number_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM numbers WHERE id = ?", (number_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def update_number_sms(self, number_id: int, sms_code: str, status: str = 'RECEIVED'):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE numbers SET sms_code = ?, status = ? WHERE id = ?", (sms_code, status, number_id))
            await db.commit()

    async def update_number_status(self, number_id: int, status: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE numbers SET status = ? WHERE id = ?", (status, number_id))
            await db.commit()

    # Deposits
    async def create_deposit(self, user_id: int, amount: float, receipt_photo_id: str = None):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO deposits (user_id, amount, receipt_photo_id, status)
                VALUES (?, ?, ?, 'pending')
            """, (user_id, amount, receipt_photo_id))
            dep_id = cursor.lastrowid
            await db.commit()
            return dep_id

    async def get_deposit(self, deposit_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM deposits WHERE id = ?", (deposit_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def update_deposit_status(self, deposit_id: int, status: str, admin_comment: str = ""):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE deposits SET status = ?, admin_comment = ? WHERE id = ?", 
                             (status, admin_comment, deposit_id))
            await db.commit()

    # Cached Services
    async def sync_services(self, services_list: list):
        if not services_list:
            return
        async with aiosqlite.connect(self.db_path) as db:
            valid_ids = []
            for s in services_list:
                s_id = int(s.get("service") or s.get("id", 0))
                if not s_id:
                    continue
                valid_ids.append(s_id)
                name = s.get("name", "")
                cat = s.get("category", "Boshqa")
                stype = s.get("type", "Default")
                rate = float(s.get("rate", 0.0))
                min_q = int(s.get("min", 10))
                max_q = int(s.get("max", 100000))
                desc = s.get("desc", s.get("description", ""))

                await db.execute("""
                    INSERT INTO services (service_id, name, category, type, rate, min, max, description, is_active, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
                    ON CONFLICT(service_id) DO UPDATE SET
                        name=excluded.name,
                        category=excluded.category,
                        type=excluded.type,
                        rate=excluded.rate,
                        min=excluded.min,
                        max=excluded.max,
                        description=excluded.description,
                        is_active=1,
                        updated_at=CURRENT_TIMESTAMP
                """, (s_id, name, cat, stype, rate, min_q, max_q, desc))

            # Delete known dummy/fake service IDs permanently
            await db.execute("DELETE FROM services WHERE service_id IN (101, 102, 103, 104, 201, 202, 203, 204, 301, 402, 403)")

            # Deactivate any services that no longer exist in live SeenSMS
            if valid_ids:
                placeholders = ",".join("?" for _ in valid_ids)
                await db.execute(f"UPDATE services SET is_active = 0 WHERE service_id NOT IN ({placeholders})", valid_ids)

            await db.commit()

    async def get_services(self, category: str = None):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if category:
                cursor = await db.execute("SELECT * FROM services WHERE is_active = 1 AND category = ? ORDER BY rate ASC", (category,))
            else:
                cursor = await db.execute("SELECT * FROM services WHERE is_active = 1 ORDER BY rate ASC")
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_service(self, service_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM services WHERE service_id = ?", (service_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_categories(self):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT DISTINCT category FROM services WHERE is_active = 1 ORDER BY category ASC")
            rows = await cursor.fetchall()
            return [r[0] for r in rows]

    # Analytics / Stats
    async def get_stats(self):
        async with aiosqlite.connect(self.db_path) as db:
            u_cur = await db.execute("SELECT COUNT(*), SUM(balance), SUM(spent_total) FROM users")
            u_count, total_balance, total_spent = await u_cur.fetchone()

            o_cur = await db.execute("SELECT COUNT(*), SUM(price) FROM orders")
            o_count, total_orders_sum = await o_cur.fetchone()

            n_cur = await db.execute("SELECT COUNT(*) FROM numbers")
            n_count = (await n_cur.fetchone())[0]

            d_cur = await db.execute("SELECT COUNT(*), SUM(amount) FROM deposits WHERE status = 'approved'")
            d_count, approved_deposits = await d_cur.fetchone()

            p_cur = await db.execute("SELECT COUNT(*) FROM deposits WHERE status = 'pending'")
            pending_deposits = (await p_cur.fetchone())[0]

            return {
                "total_users": u_count or 0,
                "total_user_balance": total_balance or 0.0,
                "total_user_spent": total_spent or 0.0,
                "total_orders": o_count or 0,
                "total_orders_sum": total_orders_sum or 0.0,
                "total_numbers": n_count or 0,
                "approved_deposits": approved_deposits or 0.0,
                "pending_deposits": pending_deposits or 0
            }

    # Free Services
    async def can_use_free_service(self, user_id: int, service_type: str = None) -> tuple[bool, int]:
        async with aiosqlite.connect(self.db_path) as db:
            if service_type:
                cursor = await db.execute("""
                    SELECT created_at FROM free_orders 
                    WHERE user_id = ? AND service_type = ? 
                    ORDER BY id DESC LIMIT 1
                """, (user_id, service_type))
            else:
                cursor = await db.execute("""
                    SELECT created_at FROM free_orders 
                    WHERE user_id = ? 
                    ORDER BY id DESC LIMIT 1
                """, (user_id,))
            row = await cursor.fetchone()
            if not row:
                return True, 0

            from datetime import datetime
            try:
                # sqlite CURRENT_TIMESTAMP format is 'YYYY-MM-DD HH:MM:SS'
                time_str = row[0]
                last_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                now = datetime.utcnow()
                diff_hours = (now - last_time).total_seconds() / 3600
                if diff_hours >= 24:
                    return True, 0
                return False, max(1, int(24 - diff_hours))
            except Exception:
                return True, 0

    async def record_free_service(self, user_id: int, service_type: str, link: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO free_orders (user_id, service_type, link, created_at)
                VALUES (?, ?, ?, datetime('now'))
            """, (user_id, service_type, link))
            await db.commit()

    # Promo Code Methods
    async def create_promo_code(self, code: str, reward_amount: float, max_uses: int = 0) -> int:
        clean_code = str(code).strip().upper()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO promo_codes (code, reward_amount, max_uses, current_uses, is_active)
                VALUES (?, ?, ?, 0, 1)
            """, (clean_code, float(reward_amount), int(max_uses)))
            await db.commit()
            return cursor.lastrowid

    async def get_all_promo_codes(self) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM promo_codes ORDER BY id DESC")
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_promo_code(self, code: str) -> dict | None:
        clean_code = str(code).strip().upper()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM promo_codes WHERE UPPER(code) = ?", (clean_code,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def delete_promo_code(self, promo_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM promo_codes WHERE id = ?", (promo_id,))
            await db.commit()

    async def activate_promo_code(self, user_id: int, code: str) -> dict:
        clean_code = str(code).strip().upper()
        if not clean_code:
            return {"success": False, "error": "Iltimos, promokodni kiriting!"}

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # Verify or ensure user exists
            cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = await cursor.fetchone()
            if not user:
                await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
                await db.commit()
                cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                user = await cursor.fetchone()

            # Find promo code
            cursor = await db.execute("SELECT * FROM promo_codes WHERE UPPER(code) = ?", (clean_code,))
            promo = await cursor.fetchone()
            if not promo:
                return {"success": False, "error": f"❌ '{clean_code}' nomli promokod topilmadi!"}

            if not promo["is_active"]:
                return {"success": False, "error": "⚠️ Ushbu promokod faol emas yoki to'xtatilgan!"}

            # Check usage limit
            max_uses = promo["max_uses"]
            curr_uses = promo["current_uses"]
            if max_uses > 0 and curr_uses >= max_uses:
                return {"success": False, "error": f"⚠️ Ushbu promokoddan foydalanish limiti ({max_uses} ta) tugagan!"}

            # Check if user already activated this promo
            cursor = await db.execute(
                "SELECT id FROM promo_code_activations WHERE promo_code_id = ? AND user_id = ?",
                (promo["id"], user_id)
            )
            already_used = await cursor.fetchone()
            if already_used:
                return {"success": False, "error": "⚠️ Siz ushbu promokodni allaqachon faollashtirgansiz!"}

            reward = float(promo["reward_amount"])

            try:
                await db.execute("""
                    INSERT INTO promo_code_activations (promo_code_id, code, user_id, reward_amount)
                    VALUES (?, ?, ?, ?)
                """, (promo["id"], clean_code, user_id, reward))

                await db.execute("""
                    UPDATE promo_codes SET current_uses = current_uses + 1 WHERE id = ?
                """, (promo["id"],))

                await db.execute("""
                    UPDATE users SET balance = balance + ? WHERE user_id = ?
                """, (reward, user_id))

                await db.commit()
            except Exception as e:
                await db.rollback()
                return {"success": False, "error": f"Xatolik yuz berdi: {str(e)}"}

            cursor = await db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            updated_user = await cursor.fetchone()
            new_balance = updated_user["balance"] if updated_user else (user["balance"] + reward)

            return {
                "success": True,
                "reward": reward,
                "new_balance": new_balance,
                "code": clean_code
            }

    # Admin Management Methods
    async def get_all_admins(self) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM admins ORDER BY actions_count DESC, id ASC")
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_admin(self, user_id: int) -> dict | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM admins WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def add_admin(self, user_id: int, username: str = None, first_name: str = None, role: str = 'admin', added_by: int = None) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO admins (user_id, username, first_name, role, added_by, actions_count)
                VALUES (?, ?, ?, ?, ?, 0)
                ON CONFLICT(user_id) DO UPDATE SET
                    username=coalesce(excluded.username, admins.username),
                    first_name=coalesce(excluded.first_name, admins.first_name),
                    role=excluded.role
            """, (user_id, username, first_name, role, added_by))
            await db.commit()
        ADMIN_IDS.add(user_id)
        return True

    async def remove_admin(self, user_id: int) -> bool:
        if user_id in ADMINS:
            return False
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM admins WHERE user_id = ? AND role != 'owner'", (user_id,))
            await db.commit()
            removed = cursor.rowcount > 0
        if removed:
            ADMIN_IDS.discard(user_id)
        return removed

    async def increment_admin_action(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE admins SET actions_count = actions_count + 1 WHERE user_id = ?", (user_id,))
            await db.commit()

db = Database()
