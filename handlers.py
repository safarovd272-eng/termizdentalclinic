from aiogram import Dispatcher, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from datetime import datetime

import database as db
from config import (ADMIN_ID, DOCTORS,
                    CLINIC_NAME, CLINIC_ADDRESS, CLINIC_PHONE,
                    CLINIC_LATITUDE, CLINIC_LONGITUDE)
from locales import t
from states import Reg, Book, PatChat, AdmChat, AdmReply, Broadcast, Rate
from keyboards import (lang_kb, phone_kb, main_kb, admin_kb,
                       doctors_kb, calendar_kb, times_kb, skip_kb,
                       rating_kb, appt_actions_kb, patients_kb)

ADDRESS_WORDS = ["manzil", "адрес", "qayerda", "где", "address",
                 "joylashuv", "location", "ko'cha", "улица"]


def lg(user) -> str:
    return (user["lang"] if user and user["lang"] else "uz")


def is_admin(uid): return uid == ADMIN_ID


# ══════════════════════════════════════════════════════════
#  START
# ══════════════════════════════════════════════════════════

async def on_start(msg: Message, state: FSMContext):
    await state.clear()
    uid = msg.from_user.id

    # --- ADMIN ---
    if is_admin(uid):
        await msg.answer(t("uz", "adm_welcome"), reply_markup=admin_kb())
        return

    # --- EXISTING PATIENT ---
    user = await db.get_user(uid)
    if user and user["full_name"] and user["phone"]:
        await msg.answer(t(lg(user), "welcome_back"), reply_markup=main_kb(lg(user)))
        return

    # --- NEW USER: choose language ---
    await msg.answer(t("uz", "choose_lang"), reply_markup=lang_kb())
    await state.set_state(Reg.lang)


# ══════════════════════════════════════════════════════════
#  REGISTRATION
# ══════════════════════════════════════════════════════════

async def cb_lang(cb: CallbackQuery, state: FSMContext):
    language = cb.data.split("_")[1]           # uz | ru
    await state.update_data(lang=language)
    await cb.message.edit_text(t(language, "enter_name"))
    await state.set_state(Reg.name)
    await cb.answer()


async def reg_name(msg: Message, state: FSMContext):
    d = await state.get_data()
    language = d.get("lang", "uz")
    await state.update_data(name=msg.text.strip())
    await msg.answer(t(language, "enter_phone"), reply_markup=phone_kb(language))
    await state.set_state(Reg.phone)


async def reg_phone(msg: Message, state: FSMContext, bot: Bot):
    d = await state.get_data()
    language = d.get("lang", "uz")
    phone = msg.contact.phone_number if msg.contact else msg.text.strip()
    name  = d["name"]

    await db.save_user(msg.from_user.id, name, phone, language)
    await msg.answer(t(language, "registered", name=name, phone=phone),
                     reply_markup=main_kb(language))
    await state.clear()

    try:
        await bot.send_message(
            ADMIN_ID,
            f"🆕 <b>Yangi bemor!</b>\n"
            f"👤 {name}\n📞 {phone}\n🆔 {msg.from_user.id}"
        )
    except Exception:
        pass


# ══════════════════════════════════════════════════════════
#  BOOKING
# ══════════════════════════════════════════════════════════

async def btn_book(msg: Message, state: FSMContext):
    user = await db.get_user(msg.from_user.id)
    if not user:
        await on_start(msg, state); return
    await msg.answer(t(lg(user), "pick_doctor"), reply_markup=doctors_kb())
    await state.set_state(Book.doctor)


async def cb_doctor(cb: CallbackQuery, state: FSMContext):
    idx = int(cb.data.split("_")[1])
    doctor = DOCTORS[idx]
    await state.update_data(doctor=doctor)
    user = await db.get_user(cb.from_user.id)
    start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    await cb.message.edit_text(t(lg(user), "pick_date"),
                               reply_markup=calendar_kb(start))
    await state.set_state(Book.date)
    await cb.answer()


async def cb_date(cb: CallbackQuery, state: FSMContext):
    date_str = cb.data.replace("date_", "")
    await state.update_data(date=date_str)
    d = await state.get_data()
    user = await db.get_user(cb.from_user.id)
    booked = await db.booked_times(date_str, d["doctor"])
    await cb.message.edit_text(t(lg(user), "pick_time"),
                               reply_markup=times_kb(booked))
    await state.set_state(Book.time)
    await cb.answer()


async def cb_busy(cb: CallbackQuery):
    await cb.answer("❌ Bu vaqt band! Boshqasini tanlang.", show_alert=True)


async def cb_time(cb: CallbackQuery, state: FSMContext):
    time_str = cb.data.replace("time_", "")
    await state.update_data(time=time_str)
    user = await db.get_user(cb.from_user.id)
    await cb.message.delete()
    await cb.message.answer(t(lg(user), "enter_complaint"),
                             reply_markup=skip_kb(lg(user)))
    await state.set_state(Book.complaint)
    await cb.answer()


async def book_complaint(msg: Message, state: FSMContext):
    user = await db.get_user(msg.from_user.id)
    complaint = "" if msg.text in ["/skip", t(lg(user), "skip")] else msg.text
    await state.update_data(complaint=complaint)
    await msg.answer(t(lg(user), "send_file"), reply_markup=skip_kb(lg(user)))
    await state.set_state(Book.file)


async def book_file(msg: Message, state: FSMContext, bot: Bot):
    user = await db.get_user(msg.from_user.id)
    d    = await state.get_data()
    language = lg(user)

    file_id = file_type = None
    if msg.photo:
        file_id, file_type = msg.photo[-1].file_id, "photo"
    elif msg.document:
        file_id, file_type = msg.document.file_id, "document"

    appt_id = await db.create_appt(
        msg.from_user.id, user["full_name"], user["phone"],
        d["doctor"], d["date"], d["time"],
        d.get("complaint", ""), file_id, file_type
    )

    await msg.answer(
        t(language, "appt_ok", doctor=d["doctor"], date=d["date"], time=d["time"]),
        reply_markup=main_kb(language)
    )

    pos = await db.queue_position(d["date"], d["time"], d["doctor"])
    await msg.answer(t(language, "queue", n=pos) if pos > 0 else t(language, "queue_first"))

    # notify admin
    txt = (
        f"🔔 <b>Yangi navbat #{appt_id}</b>\n\n"
        f"👤 {user['full_name']}\n📞 {user['phone']}\n"
        f"🆔 {msg.from_user.id}\n"
        f"👨‍⚕️ {d['doctor']}\n"
        f"📅 {d['date']} — 🕐 {d['time']}\n"
        f"📝 {d.get('complaint') or '—'}"
    )
    try:
        await bot.send_message(ADMIN_ID, txt, reply_markup=appt_actions_kb(appt_id))
        if file_id:
            fn = bot.send_photo if file_type == "photo" else bot.send_document
            await fn(ADMIN_ID, file_id, caption=f"📎 Bemor fayli | #{appt_id}")
    except Exception:
        pass

    await state.clear()


# ══════════════════════════════════════════════════════════
#  MY APPOINTMENTS
# ══════════════════════════════════════════════════════════

async def btn_my(msg: Message):
    user = await db.get_user(msg.from_user.id)
    language = lg(user)
    appts = await db.patient_appts(msg.from_user.id)
    if not appts:
        await msg.answer(t(language, "no_appts")); return

    sm = {
        "pending":   t(language, "st_pending"),
        "confirmed": t(language, "st_confirmed"),
        "completed": t(language, "st_completed"),
        "cancelled": t(language, "st_cancelled"),
    }
    text = t(language, "my_title")
    for a in appts:
        text += (
            f"━━━━━━━━━━━━━━\n"
            f"📅 <b>{a['appt_date']}</b> 🕐 <b>{a['appt_time']}</b>\n"
            f"👨‍⚕️ {a['doctor']}\n"
            f"📝 {a['complaint'] or '—'}\n"
            f"💊 {a['treatment'] or '—'}\n"
            f"Holat: {sm.get(a['status'], a['status'])}\n"
        )
    await msg.answer(text)


# ══════════════════════════════════════════════════════════
#  ADDRESS
# ══════════════════════════════════════════════════════════

async def send_address(msg: Message):
    user = await db.get_user(msg.from_user.id)
    language = lg(user) if user else "uz"
    await msg.answer(
        t(language, "addr_text",
          name=CLINIC_NAME, address=CLINIC_ADDRESS, phone=CLINIC_PHONE)
    )
    await msg.answer_location(latitude=CLINIC_LATITUDE, longitude=CLINIC_LONGITUDE)


async def text_fallback(msg: Message, state: FSMContext):
    """Catch address keywords anywhere in conversation"""
    if msg.text and any(w in msg.text.lower() for w in ADDRESS_WORDS):
        await send_address(msg)


# ══════════════════════════════════════════════════════════
#  PATIENT → ADMIN CHAT
# ══════════════════════════════════════════════════════════

async def btn_chat(msg: Message, state: FSMContext):
    user = await db.get_user(msg.from_user.id)
    language = lg(user)
    await msg.answer(t(language, "chat_prompt"))
    await state.set_state(PatChat.msg)


async def patient_chat(msg: Message, state: FSMContext, bot: Bot):
    user = await db.get_user(msg.from_user.id)
    language = lg(user)
    header = (
        f"💬 <b>Bemordan xabar:</b>\n"
        f"👤 {user['full_name']} | 📞 {user['phone']}\n"
        f"🆔 {msg.from_user.id}\n\n"
    )
    try:
        if msg.text:
            await db.save_msg(msg.from_user.id, ADMIN_ID, text=msg.text)
            await bot.send_message(ADMIN_ID, header + msg.text)
        elif msg.photo:
            fid = msg.photo[-1].file_id
            await db.save_msg(msg.from_user.id, ADMIN_ID, file_id=fid, file_type="photo")
            await bot.send_photo(ADMIN_ID, fid, caption=header + (msg.caption or ""))
        elif msg.document:
            fid = msg.document.file_id
            await db.save_msg(msg.from_user.id, ADMIN_ID, file_id=fid, file_type="doc")
            await bot.send_document(ADMIN_ID, fid, caption=header)
        await msg.answer(t(language, "chat_sent"), reply_markup=main_kb(language))
    except Exception:
        pass
    await state.clear()


# ══════════════════════════════════════════════════════════
#  ADMIN → PATIENT CHAT
# ══════════════════════════════════════════════════════════

async def adm_chat_btn(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id): return
    patients = await db.all_users()
    if not patients:
        await msg.answer("👥 Hali bemor yo'q."); return
    await msg.answer("👤 Qaysi bemor bilan chat?", reply_markup=patients_kb(patients))
    await state.set_state(AdmChat.pick)


async def cb_pick_patient(cb: CallbackQuery, state: FSMContext):
    pid = int(cb.data.split("_")[1])
    await state.update_data(pid=pid)
    await cb.message.edit_text("✉️ Xabar yoki fayl yuboring:")
    await state.set_state(AdmChat.msg)
    await cb.answer()


async def adm_chat_send(msg: Message, state: FSMContext, bot: Bot):
    d = await state.get_data()
    pid = d["pid"]
    patient = await db.get_user(pid)
    language = lg(patient) if patient else "uz"
    header = t(language, "from_admin")
    try:
        if msg.text:
            await bot.send_message(pid, header + msg.text)
        elif msg.photo:
            await bot.send_photo(pid, msg.photo[-1].file_id,
                                 caption=header + (msg.caption or ""))
        elif msg.document:
            await bot.send_document(pid, msg.document.file_id, caption=header)
        await msg.answer("✅ Yuborildi.", reply_markup=admin_kb())
    except Exception:
        await msg.answer("❌ Xatolik. Bemor botni bloklagan bo'lishi mumkin.")
    await state.clear()


# ══════════════════════════════════════════════════════════
#  ADMIN INLINE REPLY (from appt notification)
# ══════════════════════════════════════════════════════════

async def cb_adm_reply(cb: CallbackQuery, state: FSMContext):
    appt_id = int(cb.data.split("_")[1])
    appt = await db.get_appt(appt_id)
    if appt:
        await state.update_data(pid=appt["patient_id"])
        await cb.message.answer(f"✉️ {appt['patient_name']} ga javob yozing:")
        await state.set_state(AdmReply.msg)
    await cb.answer()


async def adm_reply_send(msg: Message, state: FSMContext, bot: Bot):
    d = await state.get_data()
    pid = d.get("pid")
    patient = await db.get_user(pid)
    language = lg(patient) if patient else "uz"
    header = t(language, "from_admin")
    try:
        if msg.text:
            await bot.send_message(pid, header + msg.text)
        elif msg.photo:
            await bot.send_photo(pid, msg.photo[-1].file_id, caption=header)
        elif msg.document:
            await bot.send_document(pid, msg.document.file_id, caption=header)
        await msg.answer("✅ Yuborildi.", reply_markup=admin_kb())
    except Exception:
        await msg.answer("❌ Xatolik.")
    await state.clear()


# ══════════════════════════════════════════════════════════
#  ADMIN APPOINTMENT ACTIONS
# ══════════════════════════════════════════════════════════

async def cb_aok(cb: CallbackQuery, bot: Bot):
    appt_id = int(cb.data.split("_")[1])
    await db.update_appt(appt_id, "confirmed")
    appt = await db.get_appt(appt_id)
    await cb.answer("✅ Tasdiqlandi")
    try: await cb.message.edit_reply_markup(reply_markup=None)
    except: pass
    if appt:
        patient = await db.get_user(appt["patient_id"])
        language = lg(patient) if patient else "uz"
        try:
            await bot.send_message(
                appt["patient_id"],
                t(language, "notify_confirmed",
                  doctor=appt["doctor"],
                  date=appt["appt_date"],
                  time=appt["appt_time"])
            )
        except: pass


async def cb_ano(cb: CallbackQuery, bot: Bot):
    appt_id = int(cb.data.split("_")[1])
    await db.update_appt(appt_id, "cancelled")
    appt = await db.get_appt(appt_id)
    await cb.answer("❌ Bekor qilindi")
    try: await cb.message.edit_reply_markup(reply_markup=None)
    except: pass
    if appt:
        patient = await db.get_user(appt["patient_id"])
        language = lg(patient) if patient else "uz"
        try:
            await bot.send_message(appt["patient_id"], t(language, "notify_cancelled"))
        except: pass


async def cb_ado(cb: CallbackQuery, bot: Bot):
    appt_id = int(cb.data.split("_")[1])
    await db.update_appt(appt_id, "completed")
    appt = await db.get_appt(appt_id)
    await cb.answer("✔️ Bajarildi")
    try: await cb.message.edit_reply_markup(reply_markup=None)
    except: pass
    if appt:
        patient = await db.get_user(appt["patient_id"])
        language = lg(patient) if patient else "uz"
        try:
            await bot.send_message(
                appt["patient_id"],
                t(language, "notify_done"),
                reply_markup=rating_kb()
            )
        except: pass


# ══════════════════════════════════════════════════════════
#  ADMIN: TODAY / PENDING
# ══════════════════════════════════════════════════════════

async def adm_today(msg: Message):
    if not is_admin(msg.from_user.id): return
    today = datetime.now().strftime("%Y-%m-%d")
    appts = await db.appts_by_date(today)
    if not appts:
        await msg.answer("📅 Bugun qabul yo'q."); return
    icons = {"pending": "⏳", "confirmed": "✅", "completed": "✔️", "cancelled": "❌"}
    text = f"📅 <b>Bugungi qabullar — {today}</b>\n\n"
    for a in appts:
        text += (
            f"{icons.get(a['status'],'❓')} <b>{a['appt_time']}</b> — {a['patient_name']}\n"
            f"📞 {a['patient_phone']} | 👨‍⚕️ {a['doctor']}\n"
            f"📝 {a['complaint'] or '—'}\n\n"
        )
    await msg.answer(text)


async def adm_pending(msg: Message):
    if not is_admin(msg.from_user.id): return
    appts = await db.appts_by_status("pending")
    if not appts:
        await msg.answer("✅ Kutayotgan navbat yo'q."); return
    text = "⏳ <b>Kutayotgan navbatlar:</b>\n\n"
    for a in appts:
        text += (
            f"🆔 #{a['id']} | 📅 {a['appt_date']} 🕐 {a['appt_time']}\n"
            f"👤 {a['patient_name']} | 📞 {a['patient_phone']}\n"
            f"👨‍⚕️ {a['doctor']}\n\n"
        )
    await msg.answer(text)


# ══════════════════════════════════════════════════════════
#  ADMIN: STATS
# ══════════════════════════════════════════════════════════

async def adm_stats(msg: Message):
    if not is_admin(msg.from_user.id): return
    s = await db.get_stats()
    docs = "\n".join(f"  👨‍⚕️ {r[0]}: {r[1]} ta" for r in s["doctors"]) or "  —"
    days = "\n".join(f"  📆 {r[0]}: {r[1]} ta" for r in s["days"])    or "  —"
    await msg.answer(
        f"📊 <b>Statistika</b>\n\n"
        f"👥 Jami bemorlar: <b>{s['total']}</b>\n"
        f"📅 Bugun: <b>{s['today']}</b>\n"
        f"📆 Bu hafta: <b>{s['week']}</b>\n"
        f"🗓 Bu oy: <b>{s['month']}</b>\n\n"
        f"👨‍⚕️ <b>Shifokorlar:</b>\n{docs}\n\n"
        f"📈 <b>Eng ko'p kunlar:</b>\n{days}"
    )


# ══════════════════════════════════════════════════════════
#  ADMIN: PATIENTS
# ══════════════════════════════════════════════════════════

async def adm_patients(msg: Message):
    if not is_admin(msg.from_user.id): return
    patients = await db.all_users()
    if not patients:
        await msg.answer("👥 Hali bemor yo'q."); return
    text = f"👥 <b>Bemorlar ({len(patients)} ta):</b>\n\n"
    for i, p in enumerate(patients, 1):
        text += f"{i}. 👤 {p['full_name']} | 📞 {p['phone']}\n"
        if len(text) > 3800:
            await msg.answer(text); text = ""
    if text:
        await msg.answer(text)


# ══════════════════════════════════════════════════════════
#  ADMIN: BROADCAST
# ══════════════════════════════════════════════════════════

async def adm_broadcast_start(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id): return
    await msg.answer(t("uz", "broadcast_ask"))
    await state.set_state(Broadcast.msg)


async def adm_broadcast_send(msg: Message, state: FSMContext, bot: Bot):
    ids = await db.all_user_ids()
    count = 0
    for pid in ids:
        try:
            if msg.text:
                await bot.send_message(pid, msg.text)
            elif msg.photo:
                await bot.send_photo(pid, msg.photo[-1].file_id, caption=msg.caption or "")
            elif msg.document:
                await bot.send_document(pid, msg.document.file_id, caption=msg.caption or "")
            count += 1
        except Exception:
            pass
    await msg.answer(t("uz", "broadcast_done", count=count), reply_markup=admin_kb())
    await state.clear()


# ══════════════════════════════════════════════════════════
#  ADMIN: RATINGS
# ══════════════════════════════════════════════════════════

async def adm_ratings(msg: Message):
    if not is_admin(msg.from_user.id): return
    rows = await db.doctor_ratings()
    if not rows:
        await msg.answer("⭐ Hali baho yo'q."); return
    text = "⭐ <b>Shifokorlar reytingi:</b>\n\n"
    for r in rows:
        avg = float(r[1])
        text += f"👨‍⚕️ {r[0]}\n{'⭐'*round(avg)} {avg}/5 ({r[2]} ta)\n\n"
    await msg.answer(text)


# ══════════════════════════════════════════════════════════
#  RATING (patient)
# ══════════════════════════════════════════════════════════

async def cb_rate(cb: CallbackQuery, state: FSMContext):
    score = int(cb.data.split("_")[1])
    user  = await db.get_user(cb.from_user.id)
    language = lg(user)
    appts = await db.patient_appts(cb.from_user.id)
    completed = [a for a in appts if a["status"] == "completed"]
    if completed:
        a = completed[0]
        await db.save_rating(cb.from_user.id, a["id"], a["doctor"], score)
    await cb.message.edit_text(t(language, "rate_done", stars="⭐"*score))
    await cb.answer()


# ══════════════════════════════════════════════════════════
#  REGISTER
# ══════════════════════════════════════════════════════════

def register(dp: Dispatcher):
    # start
    dp.message.register(on_start, CommandStart())

    # registration
    dp.callback_query.register(cb_lang, Reg.lang, F.data.startswith("lang_"))
    dp.message.register(reg_name,  Reg.name)
    dp.message.register(reg_phone, Reg.phone)

    # booking
    dp.message.register(btn_book, F.text.in_({"📅 Navbat olish", "📅 Записаться"}))
    dp.callback_query.register(cb_doctor, Book.doctor, F.data.startswith("doc_"))
    dp.callback_query.register(cb_date,   Book.date,   F.data.startswith("date_"))
    dp.callback_query.register(cb_busy,   Book.time,   F.data == "busy")
    dp.callback_query.register(cb_time,   Book.time,   F.data.startswith("time_"))
    dp.message.register(book_complaint, Book.complaint)
    dp.message.register(book_file,      Book.file)

    # my appointments
    dp.message.register(btn_my, F.text.in_({"📋 Mening qabullarim", "📋 Мои записи"}))

    # address button
    dp.message.register(send_address, F.text.in_({"📍 Klinika manzili", "📍 Адрес клиники"}))

    # patient chat
    dp.message.register(btn_chat, F.text.in_({"💬 Admin bilan bog'lanish",
                                               "💬 Связаться с администратором"}))
    dp.message.register(patient_chat, PatChat.msg)

    # admin chat with patient
    dp.message.register(adm_chat_btn, F.text == "💬 Bemor bilan chat")
    dp.callback_query.register(cb_pick_patient, AdmChat.pick, F.data.startswith("cp_"))
    dp.message.register(adm_chat_send, AdmChat.msg)

    # admin reply from appt button
    dp.callback_query.register(cb_adm_reply, F.data.startswith("arp_"))
    dp.message.register(adm_reply_send, AdmReply.msg)

    # appt action buttons
    dp.callback_query.register(cb_aok, F.data.startswith("aok_"))
    dp.callback_query.register(cb_ano, F.data.startswith("ano_"))
    dp.callback_query.register(cb_ado, F.data.startswith("ado_"))

    # admin menu
    dp.message.register(adm_today,           F.text == "📅 Bugungi navbatlar")
    dp.message.register(adm_pending,          F.text == "⏳ Kutayotganlar")
    dp.message.register(adm_stats,            F.text == "📊 Statistika")
    dp.message.register(adm_broadcast_start,  F.text == "📢 Xabar yuborish")
    dp.message.register(adm_broadcast_send,   Broadcast.msg)
    dp.message.register(adm_patients,         F.text == "👥 Bemorlar")
    dp.message.register(adm_ratings,          F.text == "⭐ Reyting")

    # rating callback
    dp.callback_query.register(cb_rate, F.data.startswith("rate_"))

    # address keyword fallback (must be LAST)
    dp.message.register(text_fallback, F.text)
