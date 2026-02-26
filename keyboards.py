from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from datetime import datetime, timedelta
from locales import t
from config import DOCTORS, WORK_START, WORK_END, SLOT_DURATION


def lang_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🇺🇿 O'zbek", callback_data="lang_uz")
    kb.button(text="🇷🇺 Русский", callback_data="lang_ru")
    return kb.as_markup()


def phone_kb(lang):
    kb = ReplyKeyboardBuilder()
    kb.button(text=t(lang, "share_phone_btn"), request_contact=True)
    return kb.as_markup(resize_keyboard=True, one_time_keyboard=True)


def patient_menu(lang):
    kb = ReplyKeyboardBuilder()
    kb.button(text=t(lang, "btn_new_appt"))
    kb.button(text=t(lang, "btn_my_appts"))
    kb.button(text=t(lang, "btn_chat"))
    kb.button(text=t(lang, "btn_address"))
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)


def admin_menu():
    kb = ReplyKeyboardBuilder()
    kb.button(text="📅 Bugungi navbatlar")
    kb.button(text="⏳ Kutayotganlar")
    kb.button(text="📊 Statistika")
    kb.button(text="📢 Xabar yuborish")
    kb.button(text="👥 Bemorlar")
    kb.button(text="⭐ Reyting")
    kb.button(text="💬 Bemor bilan chat")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)


def doctors_kb():
    kb = InlineKeyboardBuilder()
    for i, doc in enumerate(DOCTORS):
        kb.button(text=f"👨‍⚕️ {doc}", callback_data=f"doc_{i}")
    kb.adjust(1)
    return kb.as_markup()


def calendar_kb(start_date: datetime):
    kb = InlineKeyboardBuilder()
    max_date = min(start_date + timedelta(days=30), datetime(2026, 12, 31))
    
    row = []
    current = start_date
    while current <= max_date:
        weekday_names = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"]
        wd = current.weekday()
        label = f"{current.strftime('%d.%m')} {weekday_names[wd]}"
        row.append(InlineKeyboardButton(
            text=label,
            callback_data=f"date_{current.strftime('%Y-%m-%d')}"
        ))
        if len(row) == 3:
            kb.row(*row)
            row = []
        current += timedelta(days=1)
    if row:
        kb.row(*row)
    
    return kb.as_markup()


def times_kb(booked: list):
    kb = InlineKeyboardBuilder()
    hour = WORK_START
    minute = 0
    while hour < WORK_END:
        slot = f"{hour:02d}:{minute:02d}"
        if slot in booked:
            kb.button(text=f"🔴 {slot}", callback_data="slot_busy")
        else:
            kb.button(text=f"🟢 {slot}", callback_data=f"time_{slot}")
        minute += SLOT_DURATION
        if minute >= 60:
            minute = 0
            hour += 1
    kb.adjust(4)
    return kb.as_markup()


def skip_kb(lang):
    kb = ReplyKeyboardBuilder()
    kb.button(text=t(lang, "skip_btn"))
    return kb.as_markup(resize_keyboard=True, one_time_keyboard=True)


def rating_kb():
    kb = InlineKeyboardBuilder()
    for i in range(1, 6):
        kb.button(text="⭐" * i, callback_data=f"rate_{i}")
    kb.adjust(3)
    return kb.as_markup()


def appt_admin_kb(appt_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Tasdiqlash", callback_data=f"adm_confirm_{appt_id}")
    kb.button(text="❌ Bekor", callback_data=f"adm_cancel_{appt_id}")
    kb.button(text="✔️ Bajarildi", callback_data=f"adm_done_{appt_id}")
    kb.button(text="💬 Javob berish", callback_data=f"adm_reply_{appt_id}")
    kb.adjust(2)
    return kb.as_markup()


def patient_select_kb(patients):
    kb = InlineKeyboardBuilder()
    for p in patients:
        kb.button(
            text=f"👤 {p['full_name']} — {p['phone']}",
            callback_data=f"chatpatient_{p['telegram_id']}"
        )
    kb.adjust(1)
    return kb.as_markup()
