import sqlite3
from datetime import datetime

DB_FILE = "/app/data/database.db"


def _get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _get_conn()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            username TEXT,
            registered TEXT,
            last_visit TEXT,
            visits INTEGER DEFAULT 1,
            source TEXT DEFAULT '',
            referred_by INTEGER DEFAULT 0,
            referral_count INTEGER DEFAULT 0,
            blocked INTEGER DEFAULT 0,
            last_category TEXT DEFAULT '',
            has_ordered INTEGER DEFAULT 0,
            nudge_sent INTEGER DEFAULT 0,
            auto_reply_sent INTEGER DEFAULT 0
        )
    """)

    # Миграция: добавляем недостающие колонки если их нет
    try:
        conn.execute("SELECT source FROM users LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE users ADD COLUMN source TEXT DEFAULT ''")
    
    try:
        conn.execute("SELECT referred_by FROM users LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE users ADD COLUMN referred_by INTEGER DEFAULT 0")
    
    try:
        conn.execute("SELECT referral_count FROM users LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE users ADD COLUMN referral_count INTEGER DEFAULT 0")
    
    try:
        conn.execute("SELECT blocked FROM users LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE users ADD COLUMN blocked INTEGER DEFAULT 0")
    
    try:
        conn.execute("SELECT last_category FROM users LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE users ADD COLUMN last_category TEXT DEFAULT ''")
    
    try:
        conn.execute("SELECT has_ordered FROM users LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE users ADD COLUMN has_ordered INTEGER DEFAULT 0")
    
    try:
        conn.execute("SELECT nudge_sent FROM users LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE users ADD COLUMN nudge_sent INTEGER DEFAULT 0")
    
    try:
        conn.execute("SELECT auto_reply_sent FROM users LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE users ADD COLUMN auto_reply_sent INTEGER DEFAULT 0")

    # Миграция: добавляем недостающие колонки если их нет
    try:
        conn.execute("SELECT blocked FROM users LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE users ADD COLUMN blocked INTEGER DEFAULT 0")

    try:
        conn.execute("SELECT last_category FROM users LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE users ADD COLUMN last_category TEXT DEFAULT ''")

    try:
        conn.execute("SELECT has_ordered FROM users LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE users ADD COLUMN has_ordered INTEGER DEFAULT 0")

    try:
        conn.execute("SELECT nudge_sent FROM users LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE users ADD COLUMN nudge_sent INTEGER DEFAULT 0")

    try:
        conn.execute("SELECT auto_reply_sent FROM users LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE users ADD COLUMN auto_reply_sent INTEGER DEFAULT 0")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            full_name TEXT,
            username TEXT,
            category TEXT,
            subcategory TEXT,
            message TEXT,
            date TEXT,
            status TEXT DEFAULT 'new',
            admin_note TEXT DEFAULT '',
            source TEXT DEFAULT ''
        )
    """)

    # Миграция для таблицы orders
    try:
        conn.execute("SELECT source FROM orders LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE orders ADD COLUMN source TEXT DEFAULT ''")
    
    try:
        conn.execute("SELECT admin_note FROM orders LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE orders ADD COLUMN admin_note TEXT DEFAULT ''")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS faq (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT,
            answer TEXT
        )
    """)

    # Добавляем FAQ по умолчанию если пусто
    count = conn.execute("SELECT COUNT(*) FROM faq").fetchone()[0]
    if count == 0:
        default_faq = [
            ("💰 Сколько стоит сайт?",
             "Простой лендинг — от 15 000₽\nМногостраничный — от 40 000₽\nСложный проект — от 100 000₽\n\nТочную цену назовём после обсуждения задачи."),
            ("⏰ Сколько по времени?",
             "Простой сайт — 3-5 дней\nСредний — 10-15 дней\nСложный — от 20 дней\n\nСроки зависят от сложности и ваших правок."),
            ("💳 Как оплата?",
             "Предоплата 50%, остаток после сдачи проекта.\nПринимаем: карта, расчётный счёт, криптовалюта."),
            ("📝 Что нужно для начала?",
             "Просто оставьте заявку и опишите задачу.\nМы зададим уточняющие вопросы и назовём цену и сроки."),
            ("🔄 Можно ли вносить правки?",
             "Да! В стоимость входит 2 раунда правок.\nДополнительные правки обсуждаются отдельно."),
        ]
        for q, a in default_faq:
            conn.execute("INSERT INTO faq (question, answer) VALUES (?, ?)", (q, a))

    conn.commit()
    conn.close()



# ===== ПОЛЬЗОВАТЕЛИ =====

def add_user(user_id: int, full_name: str, username: str,
             source: str = "", referred_by: int = 0):
    conn = _get_conn()
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    existing = conn.execute(
        "SELECT * FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()

    if existing:
        conn.execute("""
            UPDATE users
            SET full_name=?, username=?, last_visit=?, visits=visits+1
            WHERE user_id=?
        """, (full_name, username, now, user_id))
        conn.commit()
        conn.close()
        return False
    else:
        conn.execute("""
            INSERT INTO users
            (user_id, full_name, username, registered, last_visit, visits,
             source, referred_by, blocked, has_ordered, nudge_sent, auto_reply_sent)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?, 0, 0, 0, 0)
        """, (user_id, full_name, username, now, now, source, referred_by))

        # Увеличиваем счётчик рефералов
        if referred_by:
            conn.execute(
                "UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?",
                (referred_by,)
            )

        conn.commit()
        conn.close()
        return True


def is_blocked(user_id: int) -> bool:
    conn = _get_conn()
    row = conn.execute(
        "SELECT blocked FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    if row:
        return row["blocked"] == 1
    return False


def block_user(user_id: int):
    conn = _get_conn()
    conn.execute("UPDATE users SET blocked = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def unblock_user(user_id: int):
    conn = _get_conn()
    conn.execute("UPDATE users SET blocked = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def set_user_last_category(user_id: int, category: str):
    conn = _get_conn()
    conn.execute(
        "UPDATE users SET last_category = ? WHERE user_id = ?",
        (category, user_id)
    )
    conn.commit()
    conn.close()


def set_user_has_ordered(user_id: int):
    conn = _get_conn()
    conn.execute("UPDATE users SET has_ordered = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def set_nudge_sent(user_id: int):
    conn = _get_conn()
    conn.execute("UPDATE users SET nudge_sent = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def set_auto_reply_sent(order_id: int):
    conn = _get_conn()
    conn.execute(
        "UPDATE orders SET status = CASE WHEN status = 'new' THEN 'new' ELSE status END WHERE id = ?",
        (order_id,)
    )
    conn.commit()
    conn.close()


def get_users_for_nudge_no_action(hours=1):
    """Пользователи которые зашли N часов назад, ничего не нажали, заявок нет"""
    conn = _get_conn()
    rows = conn.execute("""
        SELECT * FROM users
        WHERE has_ordered = 0
          AND last_category = ''
          AND nudge_sent = 0
          AND blocked = 0
          AND visits <= 2
    """).fetchall()
    conn.close()

    now = datetime.now()
    result = []
    for r in rows:
        try:
            reg = datetime.strptime(r["registered"], "%d.%m.%Y %H:%M")
            diff = (now - reg).total_seconds()
            if diff >= hours * 3600:
                result.append(dict(r))
        except Exception:
            pass
    return result


def get_users_for_nudge_no_order(hours=24):
    """Пользователи которые нажимали кнопки но не оставили заявку"""
    conn = _get_conn()
    rows = conn.execute("""
        SELECT * FROM users
        WHERE has_ordered = 0
          AND last_category != ''
          AND nudge_sent = 0
          AND blocked = 0
    """).fetchall()
    conn.close()

    now = datetime.now()
    result = []
    for r in rows:
        try:
            reg = datetime.strptime(r["registered"], "%d.%m.%Y %H:%M")
            diff = (now - reg).total_seconds()
            if diff >= hours * 3600:
                result.append(dict(r))
        except Exception:
            pass
    return result


def get_recent_users(limit=10):
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM users ORDER BY registered DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_user(user_id: int):
    conn = _get_conn()
    row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ===== ЗАЯВКИ =====

def add_order(user_id: int, full_name: str, username: str,
              category: str, subcategory: str, message: str, source: str = ""):
    conn = _get_conn()
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    cursor = conn.execute("""
        INSERT INTO orders
        (user_id, full_name, username, category, subcategory, message, date, status, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'new', ?)
    """, (user_id, full_name, username, category, subcategory, message, now, source))

    order_id = cursor.lastrowid
    conn.commit()
    conn.close()

    set_user_has_ordered(user_id)
    return order_id


def can_submit_order(user_id: int, cooldown_seconds: int) -> bool:
    """Антиспам: проверяем время последней заявки"""
    conn = _get_conn()
    row = conn.execute(
        "SELECT date FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,)
    ).fetchone()
    conn.close()

    if not row:
        return True

    try:
        last = datetime.strptime(row["date"], "%d.%m.%Y %H:%M")
        diff = (datetime.now() - last).total_seconds()
        return diff >= cooldown_seconds
    except Exception:
        return True


def get_all_orders():
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_orders_by_status(status: str):
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM orders WHERE status = ? ORDER BY id DESC", (status,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_orders(limit=10):
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_order_by_id(order_id: int):
    conn = _get_conn()
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_order_status(order_id: int, new_status: str):
    conn = _get_conn()
    conn.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
    conn.commit()
    conn.close()


def add_order_note(order_id: int, note: str):
    conn = _get_conn()
    order = get_order_by_id(order_id)
    if order:
        existing = order.get("admin_note", "")
        now = datetime.now().strftime("%H:%M %d.%m")
        new_note = f"{existing}\n[{now}] {note}" if existing else f"[{now}] {note}"
        conn.execute("UPDATE orders SET admin_note = ? WHERE id = ?", (new_note, order_id))
        conn.commit()
    conn.close()


def get_new_orders_for_auto_reply():
    """Заявки для авто-ответа (новые, старше 60 секунд)"""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM orders WHERE status = 'new'"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ===== FAQ =====

def get_all_faq():
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM faq ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_faq_by_id(faq_id: int):
    conn = _get_conn()
    row = conn.execute("SELECT * FROM faq WHERE id = ?", (faq_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ===== СТАТИСТИКА =====

def get_stats():
    conn = _get_conn()
    today = datetime.now().strftime("%d.%m.%Y")

    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    blocked_users = conn.execute("SELECT COUNT(*) FROM users WHERE blocked=1").fetchone()[0]

    users_today = conn.execute(
        "SELECT COUNT(*) FROM users WHERE registered LIKE ?", (f"{today}%",)
    ).fetchone()[0]

    orders_today = conn.execute(
        "SELECT COUNT(*) FROM orders WHERE date LIKE ?", (f"{today}%",)
    ).fetchone()[0]

    cat_rows = conn.execute(
        "SELECT category, COUNT(*) as cnt FROM orders GROUP BY category"
    ).fetchall()
    by_category = {r["category"]: r["cnt"] for r in cat_rows}

    status_rows = conn.execute(
        "SELECT status, COUNT(*) as cnt FROM orders GROUP BY status"
    ).fetchall()
    by_status = {r["status"]: r["cnt"] for r in status_rows}

    # Источники
    source_rows = conn.execute(
        "SELECT source, COUNT(*) as cnt FROM users WHERE source != '' GROUP BY source"
    ).fetchall()
    by_source = {r["source"]: r["cnt"] for r in source_rows}

    # Рефералы
    total_referrals = conn.execute(
        "SELECT COUNT(*) FROM users WHERE referred_by > 0"
    ).fetchone()[0]

    conn.close()

    return {
        "total_users": total_users,
        "total_orders": total_orders,
        "blocked_users": blocked_users,
        "users_today": users_today,
        "orders_today": orders_today,
        "by_category": by_category,
        "by_status": by_status,
        "by_source": by_source,
        "total_referrals": total_referrals,
    }
