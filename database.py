import aiosqlite

DB = "dental.db"

async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            full_name TEXT,
            phone TEXT,
            lang TEXT DEFAULT 'uz',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            patient_name TEXT,
            patient_phone TEXT,
            doctor TEXT,
            appt_date TEXT,
            appt_time TEXT,
            complaint TEXT,
            file_id TEXT,
            file_type TEXT,
            status TEXT DEFAULT 'pending',
            treatment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_id INTEGER,
            to_id INTEGER,
            text TEXT,
            file_id TEXT,
            file_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            appt_id INTEGER,
            doctor TEXT,
            score INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        await db.commit()

# ── Users ──────────────────────────────────────────────────

async def get_user(tid):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE telegram_id=?", (tid,)) as c:
            return await c.fetchone()

async def save_user(tid, name, phone, lang):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT OR REPLACE INTO users(telegram_id,full_name,phone,lang) VALUES(?,?,?,?)",
            (tid, name, phone, lang)
        )
        await db.commit()

async def all_user_ids():
    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT telegram_id FROM users") as c:
            return [r[0] for r in await c.fetchall()]

async def all_users():
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users ORDER BY created_at DESC") as c:
            return await c.fetchall()

# ── Appointments ───────────────────────────────────────────

async def create_appt(patient_id, patient_name, patient_phone, doctor, date, time, complaint, file_id=None, file_type=None):
    async with aiosqlite.connect(DB) as db:
        c = await db.execute(
            "INSERT INTO appointments(patient_id,patient_name,patient_phone,doctor,appt_date,appt_time,complaint,file_id,file_type) VALUES(?,?,?,?,?,?,?,?,?)",
            (patient_id, patient_name, patient_phone, doctor, date, time, complaint, file_id, file_type)
        )
        await db.commit()
        return c.lastrowid

async def get_appt(appt_id):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM appointments WHERE id=?", (appt_id,)) as c:
            return await c.fetchone()

async def update_appt(appt_id, status, treatment=None):
    async with aiosqlite.connect(DB) as db:
        if treatment:
            await db.execute("UPDATE appointments SET status=?,treatment=? WHERE id=?", (status, treatment, appt_id))
        else:
            await db.execute("UPDATE appointments SET status=? WHERE id=?", (status, appt_id))
        await db.commit()

async def patient_appts(patient_id):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM appointments WHERE patient_id=? ORDER BY appt_date DESC,appt_time DESC",
            (patient_id,)
        ) as c:
            return await c.fetchall()

async def appts_by_date(date):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM appointments WHERE appt_date=? ORDER BY appt_time",
            (date,)
        ) as c:
            return await c.fetchall()

async def appts_by_status(status):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM appointments WHERE status=? ORDER BY appt_date,appt_time",
            (status,)
        ) as c:
            return await c.fetchall()

async def booked_times(date, doctor):
    async with aiosqlite.connect(DB) as db:
        async with db.execute(
            "SELECT appt_time FROM appointments WHERE appt_date=? AND doctor=? AND status!='cancelled'",
            (date, doctor)
        ) as c:
            return [r[0] for r in await c.fetchall()]

async def queue_position(date, time, doctor):
    async with aiosqlite.connect(DB) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM appointments WHERE appt_date=? AND appt_time<? AND doctor=? AND status IN('pending','confirmed')",
            (date, time, doctor)
        ) as c:
            r = await c.fetchone()
            return r[0] if r else 0

# ── Stats ──────────────────────────────────────────────────

async def get_stats():
    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT COUNT(*) FROM appointments WHERE appt_date=date('now')") as c:
            today = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM appointments WHERE appt_date>=date('now','-7 days')") as c:
            week = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM appointments WHERE strftime('%Y-%m',appt_date)=strftime('%Y-%m','now')") as c:
            month = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users") as c:
            total = (await c.fetchone())[0]
        async with db.execute("SELECT doctor,COUNT(*) as n FROM appointments GROUP BY doctor ORDER BY n DESC") as c:
            doctors = await c.fetchall()
        async with db.execute("""
            SELECT CASE strftime('%w',appt_date)
            WHEN '1' THEN 'Dushanba' WHEN '2' THEN 'Seshanba'
            WHEN '3' THEN 'Chorshanba' WHEN '4' THEN 'Payshanba'
            WHEN '5' THEN 'Juma' WHEN '6' THEN 'Shanba'
            ELSE 'Yakshanba' END as d, COUNT(*) as n
            FROM appointments GROUP BY strftime('%w',appt_date) ORDER BY n DESC LIMIT 3
        """) as c:
            days = await c.fetchall()
    return dict(today=today, week=week, month=month, total=total, doctors=doctors, days=days)

# ── Messages ───────────────────────────────────────────────

async def save_msg(from_id, to_id, text=None, file_id=None, file_type=None):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO messages(from_id,to_id,text,file_id,file_type) VALUES(?,?,?,?,?)",
            (from_id, to_id, text, file_id, file_type)
        )
        await db.commit()

# ── Ratings ────────────────────────────────────────────────

async def save_rating(patient_id, appt_id, doctor, score):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO ratings(patient_id,appt_id,doctor,score) VALUES(?,?,?,?)",
            (patient_id, appt_id, doctor, score)
        )
        await db.commit()

async def doctor_ratings():
    async with aiosqlite.connect(DB) as db:
        async with db.execute(
            "SELECT doctor,ROUND(AVG(score),1),COUNT(*) FROM ratings GROUP BY doctor ORDER BY AVG(score) DESC"
        ) as c:
            return await c.fetchall()
