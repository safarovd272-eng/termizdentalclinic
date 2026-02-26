import aiosqlite

DB_PATH = "dental.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                full_name TEXT,
                phone TEXT,
                language TEXT DEFAULT 'uz',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                patient_name TEXT,
                patient_phone TEXT,
                doctor_name TEXT NOT NULL,
                appointment_date TEXT NOT NULL,
                appointment_time TEXT NOT NULL,
                complaint TEXT,
                file_id TEXT,
                status TEXT DEFAULT 'pending',
                treatment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_id INTEGER NOT NULL,
                to_id INTEGER NOT NULL,
                text TEXT,
                file_id TEXT,
                file_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                appointment_id INTEGER NOT NULL,
                doctor_name TEXT,
                score INTEGER NOT NULL,
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

# ─── Users ───────────────────────────────────────────────────────────────────

async def get_user(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,)) as cur:
            return await cur.fetchone()

async def create_or_update_user(telegram_id: int, full_name: str, phone: str, language: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (telegram_id, full_name, phone, language) VALUES (?,?,?,?)",
            (telegram_id, full_name, phone, language)
        )
        await db.commit()

async def update_language(telegram_id: int, language: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET language=? WHERE telegram_id=?", (language, telegram_id))
        await db.commit()

async def get_all_patients():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users ORDER BY created_at DESC") as cur:
            return await cur.fetchall()

async def get_all_patient_ids():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT telegram_id FROM users") as cur:
            rows = await cur.fetchall()
            return [r[0] for r in rows]

# ─── Appointments ─────────────────────────────────────────────────────────────

async def create_appointment(patient_id, patient_name, patient_phone, doctor_name, date, time, complaint, file_id=None):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO appointments 
               (patient_id, patient_name, patient_phone, doctor_name, appointment_date, appointment_time, complaint, file_id) 
               VALUES (?,?,?,?,?,?,?,?)""",
            (patient_id, patient_name, patient_phone, doctor_name, date, time, complaint, file_id)
        )
        await db.commit()
        return cur.lastrowid

async def get_appointments_by_patient(patient_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM appointments WHERE patient_id=? ORDER BY appointment_date DESC, appointment_time DESC",
            (patient_id,)
        ) as cur:
            return await cur.fetchall()

async def get_appointments_by_date(date: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM appointments WHERE appointment_date=? ORDER BY appointment_time",
            (date,)
        ) as cur:
            return await cur.fetchall()

async def get_all_appointments(status=None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if status:
            async with db.execute(
                "SELECT * FROM appointments WHERE status=? ORDER BY appointment_date, appointment_time",
                (status,)
            ) as cur:
                return await cur.fetchall()
        async with db.execute(
            "SELECT * FROM appointments ORDER BY appointment_date DESC, appointment_time DESC"
        ) as cur:
            return await cur.fetchall()

async def get_appointment_by_id(appt_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM appointments WHERE id=?", (appt_id,)) as cur:
            return await cur.fetchone()

async def update_appointment(appt_id: int, status: str, treatment: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        if treatment:
            await db.execute(
                "UPDATE appointments SET status=?, treatment=? WHERE id=?",
                (status, treatment, appt_id)
            )
        else:
            await db.execute("UPDATE appointments SET status=? WHERE id=?", (status, appt_id))
        await db.commit()

async def get_booked_times(date: str, doctor_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT appointment_time FROM appointments WHERE appointment_date=? AND doctor_name=? AND status != 'cancelled'",
            (date, doctor_name)
        ) as cur:
            rows = await cur.fetchall()
            return [r[0] for r in rows]

async def get_queue_position(date: str, time: str, doctor_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM appointments WHERE appointment_date=? AND appointment_time<? AND doctor_name=? AND status IN ('pending','confirmed')",
            (date, time, doctor_name)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0

# ─── Statistics ───────────────────────────────────────────────────────────────

async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM appointments WHERE appointment_date=date('now')") as cur:
            today = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM appointments WHERE appointment_date>=date('now','-7 days')") as cur:
            week = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM appointments WHERE strftime('%Y-%m', appointment_date)=strftime('%Y-%m','now')") as cur:
            month = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            total_patients = (await cur.fetchone())[0]
        async with db.execute(
            "SELECT doctor_name, COUNT(*) as cnt FROM appointments GROUP BY doctor_name ORDER BY cnt DESC"
        ) as cur:
            top_doctors = await cur.fetchall()
        async with db.execute(
            """SELECT CASE strftime('%w', appointment_date)
               WHEN '1' THEN 'Dushanba' WHEN '2' THEN 'Seshanba'
               WHEN '3' THEN 'Chorshanba' WHEN '4' THEN 'Payshanba'
               WHEN '5' THEN 'Juma' WHEN '6' THEN 'Shanba'
               ELSE 'Yakshanba' END as day,
               COUNT(*) as cnt
               FROM appointments
               GROUP BY strftime('%w', appointment_date)
               ORDER BY cnt DESC LIMIT 3"""
        ) as cur:
            top_days = await cur.fetchall()
    return {
        "today": today, "week": week, "month": month,
        "total_patients": total_patients,
        "top_doctors": top_doctors, "top_days": top_days
    }

# ─── Messages ─────────────────────────────────────────────────────────────────

async def save_message(from_id, to_id, text=None, file_id=None, file_type=None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO messages (from_id, to_id, text, file_id, file_type) VALUES (?,?,?,?,?)",
            (from_id, to_id, text, file_id, file_type)
        )
        await db.commit()

# ─── Ratings ─────────────────────────────────────────────────────────────────

async def save_rating(patient_id, appointment_id, doctor_name, score, comment=""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO ratings (patient_id, appointment_id, doctor_name, score, comment) VALUES (?,?,?,?,?)",
            (patient_id, appointment_id, doctor_name, score, comment)
        )
        await db.commit()

async def get_ratings_by_doctor():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT doctor_name, AVG(score) as avg, COUNT(*) as cnt FROM ratings GROUP BY doctor_name ORDER BY avg DESC"
        ) as cur:
            return await cur.fetchall()
