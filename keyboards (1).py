from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from datetime import datetime, timedelta
from locales import t
from config import DOCTORS, WORK_START, WORK_END, SLOT_DURATION


def lang_kb():
    b = InlineKeyboardBuilder()
    b.button(text="🇺🇿 O'zbek", callback_data="lang_uz")
    b.button(text="🇷🇺 Русский", callback_data="lang_ru")
    return b.as_markup()


def phone_kb(lg):
    b = ReplyKeyboardBuilder()
    b.button(text=t(lg, "share_phone"), request_contact=True)
    return b.as_markup(resize_keyboard=True, one_time_keyboard=True)


def main_kb(lg):
    b = ReplyKeyboardBuilder()
    b.button(text=t(lg, "btn_appt"))
    b.button(text=t(lg, "btn_my"))
    b.button(text=t(lg, "btn_chat"))
    b.button(text=t(lg, "btn_addr"))
    b.adjust(2)
    return b.as_markup(resize_keyboard=True)


def admin_kb():
    b = ReplyKeyboardBuilder()
    b.button(text="📅 Bugungi navbatlar")
    b.button(text="⏳ Kutayotganlar")
    b.button(text="📊 Statistika")
    b.button(text="📢 Xabar yuborish")
    b.button(text="👥 Bemorlar")
    b.button(text="⭐ Reyting")
    b.button(text="💬 Bemor bilan chat")
    b.adjust(2)
    return b.as_markup(resize_keyboard=True)


def doctors_kb():
    b = InlineKeyboardBuilder()
    for i, d in enumerate(DOCTORS):
        b.button(text=f"👨‍⚕️ {d}", callback_data=f"doc_{i}")
    b.adjust(1)
    return b.as_markup()


def calendar_kb(start: datetime):
    b = InlineKeyboardBuilder()
    limit = min(start + timedelta(days=30), datetime(2026, 12, 31))
    days_uz = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"]
    row, cur = [], start
    while cur <= limit:
        row.append(InlineKeyboardButton(
            text=f"{cur.strftime('%d.%m')} {days_uz[cur.weekday()]}",
            callback_data=f"date_{cur.strftime('%Y-%m-%d')}"
        ))
        if len(row) == 3:
            b.row(*row); row = []
        cur += timedelta(days=1)
    if row:
        b.row(*row)
    return b.as_markup()


def times_kb(booked: list):
    b = InlineKeyboardBuilder()
    h, m = WORK_START, 0
    while h < WORK_END:
        slot = f"{h:02d}:{m:02d}"
        if slot in booked:
            b.button(text=f"🔴 {slot}", callback_data="busy")
        else:
            b.button(text=f"🟢 {slot}", callback_data=f"time_{slot}")
        m += SLOT_DURATION
        if m >= 60:
            m = 0; h += 1
    b.adjust(4)
    return b.as_markup()


def skip_kb(lg):
    b = ReplyKeyboardBuilder()
    b.button(text=t(lg, "skip"))
    return b.as_markup(resize_keyboard=True, one_time_keyboard=True)


def rating_kb():
    b = InlineKeyboardBuilder()
    for i in range(1, 6):
        b.button(text="⭐" * i, callback_data=f"rate_{i}")
    b.adjust(3)
    return b.as_markup()


def appt_actions_kb(appt_id):
    b = InlineKeyboardBuilder()
    b.button(text="✅ Tasdiqlash",  callback_data=f"aok_{appt_id}")
    b.button(text="❌ Bekor",       callback_data=f"ano_{appt_id}")
    b.button(text="✔️ Bajarildi",   callback_data=f"ado_{appt_id}")
    b.button(text="💬 Javob berish",callback_data=f"arp_{appt_id}")
    b.adjust(2)
    return b.as_markup()


def patients_kb(patients):
    b = InlineKeyboardBuilder()
    for p in patients:
        b.button(
            text=f"👤 {p['full_name']} {p['phone']}",
            callback_data=f"cp_{p['telegram_id']}"
        )
    b.adjust(1)
    return b.as_markup()
