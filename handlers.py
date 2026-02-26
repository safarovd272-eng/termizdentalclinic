from aiogram import Dispatcher, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from datetime import datetime

import database as db
from config import ADMIN_ID, DOCTORS, CLINIC_ADDRESS, CLINIC_PHONE, CLINIC_LATITUDE, CLINIC_LONGITUDE
from locales import t
from states import Reg, Appt, ChatPatient, AdminChat, AdminReply, Broadcast, RatingFlow
from keyboards import (
    lang_kb, phone_kb, patient_menu, admin_menu,
    doctors_kb, calendar_kb, times_kb, skip_kb,
    rating_kb, appt_admin_kb, patient_select_kb
)


def lang(user) -> str:
    return user["language"] if user and user["language"] else "uz"


# ══════════════════════════════════════════════════════════
#  /start
# ══════════════════════════════════════════════════════════

async def cmd_start(message: Message, state: FSMContext):
    await state.clear()

    if message.from_user.id == ADMIN_ID:
        await message.answer(t("uz", "admin_welcome"), reply_markup=admin_menu())
        return

    user = await db.get_user(message.from_user.id)
    if user and user["full_name"] and user["phone"]:
        lg = lang(user)
        await message.answer(t(lg, "main_menu"), reply_markup=patient_menu(lg))
        return

    # New user
    await message.answer(t("uz", "choose_lang"), reply_markup=lang_kb())
    await state.set_state(Reg.lang)


# ══════════════════════════════════════════════════════════
#  REGISTRATION
# ══════════════════════════════════════════════════════════

async def cb_lang(callback: CallbackQuery, state: FSMContext):
    lg = callback.data.split("_")[1]
    await state.update_data(lang=lg)
    await callback.message.edit_text(t(lg, "welcome_new"))
    await state.set_state(Reg.name)


async def reg_name(message: Message, state: FSMContext):
    data = await state.get_data()
    lg = data.get("lang", "uz")
    await state.update_data(name=message.text.strip())
    await message.answer(t(lg, "ask_phone"), reply_markup=phone_kb(lg))
    await state.set_state(Reg.phone)


async def reg_phone(message: Message, state: FSMContext):
    data = await state.get_data()
    lg = data.get("lang", "uz")
    phone = message.contact.phone_number if message.contact else message.text.strip()

    await db.create_or_update_user(message.from_user.id, data["name"], phone, lg)
    await message.answer(
        t(lg, "registered_ok", name=data["name"], phone=phone),
        reply_markup=patient_menu(lg)
    )
    await state.clear()

    # Notify admin
    try:
        await message.bot.send_message(
            ADMIN_ID,
            f"🆕 <b>Yangi bemor ro'yxatdan o'tdi!</b>\n"
            f"👤 {data['name']}\n📞 {phone}\n"
            f"🆔 Telegram: {message.from_user.id}"
        )
    except Exception:
        pass


# ══════════════════════════════════════════════════════════
#  APPOINTMENT
# ══════════════════════════════════════════════════════════

async def btn_new_appt(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    lg = lang(user)
    await message.answer(t(lg, "choose_doctor"), reply_markup=doctors_kb())
    await state.set_state(Appt.doctor)


async def cb_doctor(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split("_")[1])
    doctor_name = DOCTORS[idx]
    await state.update_data(doctor=doctor_name)

    user = await db.get_user(callback.from_user.id)
    lg = lang(user)

    start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    await callback.message.edit_text(t(lg, "choose_date"), reply_markup=calendar_kb(start))
    await state.set_state(Appt.date)


async def cb_date(callback: CallbackQuery, state: FSMContext):
    date_str = callback.data.replace("date_", "")
    await state.update_data(date=date_str)

    data = await state.get_data()
    user = await db.get_user(callback.from_user.id)
    lg = lang(user)

    booked = await db.get_booked_times(date_str, data["doctor"])
    await callback.message.edit_text(t(lg, "choose_time"), reply_markup=times_kb(booked))
    await state.set_state(Appt.time)


async def cb_slot_busy(callback: CallbackQuery):
    await callback.answer("❌ Bu vaqt band! Boshqasini tanlang.", show_alert=True)


async def cb_time(callback: CallbackQuery, state: FSMContext):
    time_str = callback.data.replace("time_", "")
    await state.update_data(time=time_str)

    user = await db.get_user(callback.from_user.id)
    lg = lang(user)

    await callback.message.delete()
    await callback.message.answer(t(lg, "ask_complaint"), reply_markup=skip_kb(lg))
    await state.set_state(Appt.complaint)


async def appt_complaint(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    lg = lang(user)
    complaint = "" if message.text == t(lg, "skip_btn") else message.text
    await state.update_data(complaint=complaint)
    await message.answer(t(lg, "ask_file"), reply_markup=skip_kb(lg))
    await state.set_state(Appt.file)


async def appt_file(message: Message, state: FSMContext, bot: Bot):
    user = await db.get_user(message.from_user.id)
    lg = lang(user)
    data = await state.get_data()

    # Get file if any
    file_id = None
    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.document:
        file_id = message.document.file_id

    # Save to DB
    appt_id = await db.create_appointment(
        patient_id=message.from_user.id,
        patient_name=user["full_name"],
        patient_phone=user["phone"],
        doctor_name=data["doctor"],
        date=data["date"],
        time=data["time"],
        complaint=data.get("complaint", ""),
        file_id=file_id
    )

    # Confirm patient
    await message.answer(
        t(lg, "appt_saved", doctor=data["doctor"], date=data["date"], time=data["time"]),
        reply_markup=patient_menu(lg)
    )

    # Queue info
    queue = await db.get_queue_position(data["date"], data["time"], data["doctor"])
    if queue > 0:
        await message.answer(t(lg, "queue_before", n=queue))
    else:
        await message.answer(t(lg, "queue_first"))

    # Notify admin
    admin_text = (
        f"🔔 <b>Yangi navbat #{appt_id}</b>\n\n"
        f"👤 <b>{user['full_name']}</b>\n"
        f"📞 {user['phone']}\n"
        f"🆔 TG: {message.from_user.id}\n"
        f"👨‍⚕️ {data['doctor']}\n"
        f"📅 {data['date']} — 🕐 {data['time']}\n"
        f"📝 {data.get('complaint') or '—'}"
    )
    try:
        await bot.send_message(ADMIN_ID, admin_text, reply_markup=appt_admin_kb(appt_id))
        if file_id:
            if message.photo:
                await bot.send_photo(ADMIN_ID, file_id, caption=f"📎 Bemor fayli | Navbat #{appt_id}")
            else:
                await bot.send_document(ADMIN_ID, file_id, caption=f"📎 Bemor fayli | Navbat #{appt_id}")
    except Exception:
        pass

    await state.clear()


# ══════════════════════════════════════════════════════════
#  MY APPOINTMENTS
# ══════════════════════════════════════════════════════════

async def btn_my_appts(message: Message):
    user = await db.get_user(message.from_user.id)
    lg = lang(user)

    appts = await db.get_appointments_by_patient(message.from_user.id)
    if not appts:
        await message.answer(t(lg, "no_appts"))
        return

    status_map = {
        "pending": t(lg, "appt_status_pending"),
        "confirmed": t(lg, "appt_status_confirmed"),
        "completed": t(lg, "appt_status_completed"),
        "cancelled": t(lg, "appt_status_cancelled"),
    }

    text = t(lg, "my_appts_title")
    for a in appts:
        status = status_map.get(a["status"], a["status"])
        text += (
            f"━━━━━━━━━━━━━━━\n"
            f"📅 <b>{a['appointment_date']}</b> 🕐 <b>{a['appointment_time']}</b>\n"
            f"👨‍⚕️ {a['doctor_name']}\n"
            f"📝 {a['complaint'] or '—'}\n"
            f"💊 {a['treatment'] or '—'}\n"
            f"Holat: {status}\n"
        )
    await message.answer(text)


# ══════════════════════════════════════════════════════════
#  ADDRESS
# ══════════════════════════════════════════════════════════

async def btn_address(message: Message):
    user = await db.get_user(message.from_user.id)
    lg = lang(user)
    await message.answer(t(lg, "address_msg", address=CLINIC_ADDRESS, phone=CLINIC_PHONE))
    await message.answer_location(latitude=CLINIC_LATITUDE, longitude=CLINIC_LONGITUDE)


async def keyword_address(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        return
    keywords = ["manzil", "адрес", "qayerda", "где", "address", "location"]
    if any(k in message.text.lower() for k in keywords):
        await btn_address(message)


# ══════════════════════════════════════════════════════════
#  PATIENT → ADMIN CHAT
# ══════════════════════════════════════════════════════════

async def btn_chat(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    lg = lang(user)
    await message.answer(t(lg, "chat_ask"))
    await state.set_state(ChatPatient.typing)


async def patient_chat_msg(message: Message, state: FSMContext, bot: Bot):
    user = await db.get_user(message.from_user.id)
    lg = lang(user)

    header = (
        f"💬 <b>Bemordan xabar:</b>\n"
        f"👤 {user['full_name']} | 📞 {user['phone']}\n"
        f"🆔 {message.from_user.id}\n\n"
    )

    try:
        if message.text:
            await db.save_message(message.from_user.id, ADMIN_ID, text=message.text)
            await bot.send_message(ADMIN_ID, header + message.text)
        elif message.photo:
            await db.save_message(message.from_user.id, ADMIN_ID, file_id=message.photo[-1].file_id, file_type="photo")
            await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=header + (message.caption or ""))
        elif message.document:
            await db.save_message(message.from_user.id, ADMIN_ID, file_id=message.document.file_id, file_type="doc")
            await bot.send_document(ADMIN_ID, message.document.file_id, caption=header)
        await message.answer(t(lg, "chat_sent"), reply_markup=patient_menu(lg))
    except Exception:
        pass

    await state.clear()


# ══════════════════════════════════════════════════════════
#  ADMIN → PATIENT CHAT
# ══════════════════════════════════════════════════════════

async def admin_btn_chat(message: Message, state: FSMContext, bot: Bot):
    if message.from_user.id != ADMIN_ID:
        return
    patients = await db.get_all_patients()
    if not patients:
        await message.answer("👥 Hali bemor yo'q.")
        return
    await message.answer("👤 Qaysi bemor bilan chat qilasiz?", reply_markup=patient_select_kb(patients))
    await state.set_state(AdminChat.choose_patient)


async def cb_chat_patient(callback: CallbackQuery, state: FSMContext):
    patient_id = int(callback.data.split("_")[1])
    await state.update_data(patient_id=patient_id)
    await callback.message.edit_text("✉️ Xabar yoki fayl yuboring:")
    await state.set_state(AdminChat.typing)


async def admin_chat_send(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    patient_id = data["patient_id"]
    patient = await db.get_user(patient_id)
    lg = lang(patient) if patient else "uz"
    header = t(lg, "admin_reply_header")

    try:
        if message.text:
            await bot.send_message(patient_id, header + message.text)
        elif message.photo:
            await bot.send_photo(patient_id, message.photo[-1].file_id, caption=header + (message.caption or ""))
        elif message.document:
            await bot.send_document(patient_id, message.document.file_id, caption=header)
        await message.answer("✅ Xabar bemorga yuborildi.", reply_markup=admin_menu())
    except Exception:
        await message.answer("❌ Xatolik. Bemor botni bloklagan bo'lishi mumkin.")

    await state.clear()


# ══════════════════════════════════════════════════════════
#  ADMIN REPLY (from appt notification inline button)
# ══════════════════════════════════════════════════════════

async def cb_admin_reply(callback: CallbackQuery, state: FSMContext):
    appt_id = int(callback.data.split("_")[2])
    appt = await db.get_appointment_by_id(appt_id)
    if appt:
        await state.update_data(patient_id=appt["patient_id"])
        await callback.message.answer(f"✉️ {appt['patient_name']} ga xabar yuboring:")
        await state.set_state(AdminReply.typing)
    await callback.answer()


async def admin_reply_send(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    patient_id = data.get("patient_id")
    patient = await db.get_user(patient_id)
    lg = lang(patient) if patient else "uz"
    header = t(lg, "admin_reply_header")

    try:
        if message.text:
            await bot.send_message(patient_id, header + message.text)
        elif message.photo:
            await bot.send_photo(patient_id, message.photo[-1].file_id, caption=header)
        elif message.document:
            await bot.send_document(patient_id, message.document.file_id, caption=header)
        await message.answer("✅ Yuborildi.", reply_markup=admin_menu())
    except Exception:
        await message.answer("❌ Xatolik.")
    await state.clear()


# ══════════════════════════════════════════════════════════
#  ADMIN: Appointment actions
# ══════════════════════════════════════════════════════════

async def cb_adm_confirm(callback: CallbackQuery, bot: Bot):
    appt_id = int(callback.data.split("_")[2])
    await db.update_appointment(appt_id, "confirmed")
    appt = await db.get_appointment_by_id(appt_id)
    await callback.answer("✅ Tasdiqlandi")
    await callback.message.edit_reply_markup()

    if appt:
        patient = await db.get_user(appt["patient_id"])
        lg = lang(patient) if patient else "uz"
        try:
            await bot.send_message(
                appt["patient_id"],
                t(lg, "appt_confirmed_notify",
                  doctor=appt["doctor_name"],
                  date=appt["appointment_date"],
                  time=appt["appointment_time"])
            )
        except Exception:
            pass


async def cb_adm_cancel(callback: CallbackQuery, bot: Bot):
    appt_id = int(callback.data.split("_")[2])
    await db.update_appointment(appt_id, "cancelled")
    appt = await db.get_appointment_by_id(appt_id)
    await callback.answer("❌ Bekor qilindi")
    await callback.message.edit_reply_markup()

    if appt:
        patient = await db.get_user(appt["patient_id"])
        lg = lang(patient) if patient else "uz"
        try:
            await bot.send_message(appt["patient_id"], t(lg, "appt_cancelled_notify"))
        except Exception:
            pass


async def cb_adm_done(callback: CallbackQuery, bot: Bot):
    appt_id = int(callback.data.split("_")[2])
    await db.update_appointment(appt_id, "completed")
    appt = await db.get_appointment_by_id(appt_id)
    await callback.answer("✔️ Bajarildi")
    await callback.message.edit_reply_markup()

    if appt:
        patient = await db.get_user(appt["patient_id"])
        lg = lang(patient) if patient else "uz"
        try:
            await bot.send_message(
                appt["patient_id"],
                t(lg, "appt_completed_notify"),
                reply_markup=rating_kb()
            )
        except Exception:
            pass


# ══════════════════════════════════════════════════════════
#  ADMIN: Today + Pending
# ══════════════════════════════════════════════════════════

async def admin_today(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    today = datetime.now().strftime("%Y-%m-%d")
    appts = await db.get_appointments_by_date(today)

    if not appts:
        await message.answer("📅 Bugun qabul yo'q.")
        return

    text = f"📅 <b>Bugungi qabullar — {today}</b>\n\n"
    for a in appts:
        status_icons = {"pending": "⏳", "confirmed": "✅", "completed": "✔️", "cancelled": "❌"}
        icon = status_icons.get(a["status"], "❓")
        text += (
            f"{icon} <b>{a['appointment_time']}</b> — {a['patient_name']}\n"
            f"📞 {a['patient_phone']} | 👨‍⚕️ {a['doctor_name']}\n"
            f"📝 {a['complaint'] or '—'}\n\n"
        )
    await message.answer(text)


async def admin_pending(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    appts = await db.get_all_appointments(status="pending")
    if not appts:
        await message.answer("✅ Kutayotgan navbat yo'q.")
        return
    text = "⏳ <b>Kutayotgan navbatlar:</b>\n\n"
    for a in appts:
        text += (
            f"🆔 #{a['id']} | 📅 {a['appointment_date']} 🕐 {a['appointment_time']}\n"
            f"👤 {a['patient_name']} | 📞 {a['patient_phone']}\n"
            f"👨‍⚕️ {a['doctor_name']}\n\n"
        )
        # Send with action buttons
    await message.answer(text)


# ══════════════════════════════════════════════════════════
#  ADMIN: Statistics
# ══════════════════════════════════════════════════════════

async def admin_stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    s = await db.get_stats()

    docs = "\n".join([f"  👨‍⚕️ {r[0]}: {r[1]} ta" for r in s["top_doctors"]]) or "  —"
    days = "\n".join([f"  📆 {r[0]}: {r[1]} ta" for r in s["top_days"]]) or "  —"

    text = (
        f"📊 <b>Statistika:</b>\n\n"
        f"👥 Jami bemorlar: <b>{s['total_patients']}</b>\n\n"
        f"📅 Bugun: <b>{s['today']}</b> ta qabul\n"
        f"📆 Bu hafta: <b>{s['week']}</b> ta\n"
        f"🗓 Bu oy: <b>{s['month']}</b> ta\n\n"
        f"👨‍⚕️ <b>Shifokorlar bo'yicha:</b>\n{docs}\n\n"
        f"📈 <b>Eng ko'p murojaat kunlari:</b>\n{days}"
    )
    await message.answer(text)


# ══════════════════════════════════════════════════════════
#  ADMIN: Patients list
# ══════════════════════════════════════════════════════════

async def admin_patients(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    patients = await db.get_all_patients()
    if not patients:
        await message.answer("👥 Hali bemor yo'q.")
        return
    text = f"👥 <b>Bemorlar ({len(patients)} ta):</b>\n\n"
    for i, p in enumerate(patients, 1):
        text += f"{i}. 👤 {p['full_name']} | 📞 {p['phone']}\n"
        if len(text) > 3500:
            await message.answer(text)
            text = ""
    if text:
        await message.answer(text)


# ══════════════════════════════════════════════════════════
#  ADMIN: Broadcast
# ══════════════════════════════════════════════════════════

async def admin_broadcast_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer(t("uz", "broadcast_ask"))
    await state.set_state(Broadcast.typing)


async def admin_broadcast_send(message: Message, state: FSMContext, bot: Bot):
    patient_ids = await db.get_all_patient_ids()
    count = 0
    for pid in patient_ids:
        try:
            if message.text:
                await bot.send_message(pid, message.text)
            elif message.photo:
                await bot.send_photo(pid, message.photo[-1].file_id, caption=message.caption or "")
            elif message.document:
                await bot.send_document(pid, message.document.file_id, caption=message.caption or "")
            count += 1
        except Exception:
            pass
    await message.answer(t("uz", "broadcast_done", count=count), reply_markup=admin_menu())
    await state.clear()


# ══════════════════════════════════════════════════════════
#  ADMIN: Ratings
# ══════════════════════════════════════════════════════════

async def admin_ratings(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    ratings = await db.get_ratings_by_doctor()
    if not ratings:
        await message.answer("⭐ Hali baho yo'q.")
        return
    text = "⭐ <b>Shifokorlar reytingi:</b>\n\n"
    for r in ratings:
        avg = round(r[1], 1)
        stars = "⭐" * round(avg)
        text += f"👨‍⚕️ {r[0]}\n{stars} {avg}/5 ({r[2]} ta baho)\n\n"
    await message.answer(text)


# ══════════════════════════════════════════════════════════
#  RATING (patient)
# ══════════════════════════════════════════════════════════

async def cb_rate(callback: CallbackQuery, state: FSMContext):
    score = int(callback.data.split("_")[1])
    await state.update_data(score=score)
    user = await db.get_user(callback.from_user.id)
    lg = lang(user)
    await callback.message.edit_text(t(lg, "rate_comment"))
    await state.set_state(RatingFlow.comment)


async def rate_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    user = await db.get_user(message.from_user.id)
    lg = lang(user)
    comment = "" if message.text == "/skip" else message.text

    # Get last completed appointment
    appts = await db.get_appointments_by_patient(message.from_user.id)
    completed = [a for a in appts if a["status"] == "completed"]
    if completed:
        a = completed[0]
        await db.save_rating(message.from_user.id, a["id"], a["doctor_name"], data["score"], comment)

    await message.answer(t(lg, "rate_saved") + f"\n{'⭐' * data['score']}", reply_markup=patient_menu(lg))
    await state.clear()


# ══════════════════════════════════════════════════════════
#  REGISTER ALL HANDLERS
# ══════════════════════════════════════════════════════════

def register_all_handlers(dp: Dispatcher):
    # Start
    dp.message.register(cmd_start, CommandStart())

    # Registration
    dp.callback_query.register(cb_lang, Reg.lang, F.data.startswith("lang_"))
    dp.message.register(reg_name, Reg.name)
    dp.message.register(reg_phone, Reg.phone)

    # Appointment flow
    dp.message.register(btn_new_appt, F.text.contains("Navbat olish") | F.text.contains("Записаться"))
    dp.callback_query.register(cb_doctor, Appt.doctor, F.data.startswith("doc_"))
    dp.callback_query.register(cb_date, Appt.date, F.data.startswith("date_"))
    dp.callback_query.register(cb_slot_busy, Appt.time, F.data == "slot_busy")
    dp.callback_query.register(cb_time, Appt.time, F.data.startswith("time_"))
    dp.message.register(appt_complaint, Appt.complaint)
    dp.message.register(appt_file, Appt.file)

    # My appointments
    dp.message.register(btn_my_appts, F.text.contains("qabullarim") | F.text.contains("записи"))

    # Address
    dp.message.register(btn_address, F.text.contains("manzili") | F.text.contains("Адрес"))
    dp.message.register(keyword_address, F.text)

    # Patient → Admin chat
    dp.message.register(btn_chat, F.text.contains("bog'lanish") | F.text.contains("администратором"))
    dp.message.register(patient_chat_msg, ChatPatient.typing)

    # Admin → Patient chat
    dp.message.register(admin_btn_chat, F.text == "💬 Bemor bilan chat")
    dp.callback_query.register(cb_chat_patient, AdminChat.choose_patient, F.data.startswith("chatpatient_"))
    dp.message.register(admin_chat_send, AdminChat.typing)

    # Admin reply from appt button
    dp.callback_query.register(cb_admin_reply, F.data.startswith("adm_reply_"))
    dp.message.register(admin_reply_send, AdminReply.typing)

    # Admin appointment actions
    dp.callback_query.register(cb_adm_confirm, F.data.startswith("adm_confirm_"))
    dp.callback_query.register(cb_adm_cancel, F.data.startswith("adm_cancel_"))
    dp.callback_query.register(cb_adm_done, F.data.startswith("adm_done_"))

    # Admin menu buttons
    dp.message.register(admin_today, F.text == "📅 Bugungi navbatlar")
    dp.message.register(admin_pending, F.text == "⏳ Kutayotganlar")
    dp.message.register(admin_stats, F.text == "📊 Statistika")
    dp.message.register(admin_broadcast_start, F.text == "📢 Xabar yuborish")
    dp.message.register(admin_broadcast_send, Broadcast.typing)
    dp.message.register(admin_patients, F.text == "👥 Bemorlar")
    dp.message.register(admin_ratings, F.text == "⭐ Reyting")

    # Rating
    dp.callback_query.register(cb_rate, RatingFlow.score | F.data.startswith("rate_"))
    dp.callback_query.register(cb_rate, F.data.startswith("rate_"))
    dp.message.register(rate_comment, RatingFlow.comment)
