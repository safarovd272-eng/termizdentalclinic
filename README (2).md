# 🦷 Dental Clinic Telegram Bot
### 2 rol: Bemor + Admin

---

## ⚡ Ishga tushirish — 3 qadam

### 1. config.py ni oching va sozlang:
```python
BOT_TOKEN = "TOKEN"          # @BotFather dan oling

ADMIN_ID = 123456789         # Sizning Telegram ID
                             # → @userinfobot ga /start yozing

CLINIC_ADDRESS = "..."       # Klinika manzili
CLINIC_PHONE = "+998 ..."
CLINIC_LATITUDE = 41.2995    # Google Maps dan nusxalang
CLINIC_LONGITUDE = 69.2401

DOCTORS = [                  # Shifokorlar ro'yxati (faqat ismlar)
    "Dr. Aliyev Jasur — Terapevt",
    "Dr. Karimova Nilufar — Ortodont",
]
```

### 2. O'rnatish:
```bash
pip install -r requirements.txt
```

### 3. Ishga tushirish:
```bash
python bot.py
```

---

## 👤 BEMOR uchun funksiyalar

| # | Funksiya | Tavsif |
|---|----------|--------|
| 1 | 🌐 Til tanlash | O'zbek yoki Rus |
| 2 | 📝 Ro'yxatdan o'tish | Ism + Telefon |
| 3 | 📅 Navbat olish | Shifokor → Sana → Vaqt |
| 4 | 🗓 Kalendar | Bugundan 30 kun (max 2026-yil oxiri) |
| 5 | 🟢🔴 Vaqt holati | Band/bo'sh ko'rinadi |
| 6 | 📝 Shikoyat | Qisqacha muammo yozish |
| 7 | 📎 Fayl/rasm | Tish rasmi, tahlil yuborish |
| 8 | 🔔 Navbat holati | "Sizdan oldin X kishi bor" |
| 9 | 📋 Mening qabullarim | Barcha tarix, holat, davolash |
| 10 | 💬 Admin bilan chat | Xabar + fayl yuborish |
| 11 | 📍 Klinika manzili | Xarita bilan avtomatik |
| 12 | ⭐ Reyting | Qabul tugagach 1-5 yulduz |

---

## 🔐 ADMIN uchun funksiyalar

| # | Funksiya | Tavsif |
|---|----------|--------|
| 1 | 📅 Bugungi navbatlar | Bugun kelishi kerak bemorlar |
| 2 | ⏳ Kutayotganlar | Tasdiqlanmagan navbatlar |
| 3 | ✅ Tasdiqlash | Navbatni tasdiqlash → bemorga xabar |
| 4 | ❌ Bekor qilish | Bekor → bemorga xabar |
| 5 | ✔️ Bajarildi | Tugadi → bemorga baho so'rovi |
| 6 | 💬 Bemor bilan chat | Istalgan bemorga xabar/fayl |
| 7 | 📊 Statistika | Bugun/hafta/oy + eng band kunlar |
| 8 | 👥 Bemorlar | Ro'yxat (ism + telefon) |
| 9 | 📢 Xabar yuborish | Barcha bemorlaarga broadcast |
| 10 | ⭐ Reyting | Shifokorlar reytingi ko'rish |

---

## 🔔 Avtomatik bildirishnomalar

- ✅ Yangi bemor → Admin ga xabar
- 🔔 Navbat olindi → Adminga navbat + boshqaruv tugmalari
- ✅ Admin tasdiqlaganda → Bemorga xabar
- ❌ Admin bekor qilganda → Bemorga xabar
- ✔️ Qabul tugaganda → Bemorga baho so'rovi

---

## 📁 Fayllar
```
dental_bot/
├── bot.py          ← Ishga tushirish
├── config.py       ← SIZI SOZLAYDIGAN FAYL
├── database.py     ← SQLite baza
├── handlers.py     ← Barcha logika
├── keyboards.py    ← Tugmalar
├── locales.py      ← Uz/Ru tarjimalar
├── states.py       ← FSM
└── requirements.txt
```
