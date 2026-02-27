import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ── Sozlamalar (config.py o'rniga) ──────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "BU_YERGA_TOKENNI_YOZING")
ADMIN_ID  = int(os.environ.get("ADMIN_ID", "6551375195"))

CLINIC_NAME     = "DENTAL-SERVIS-TERMIZ"
CLINIC_ADDRESS  = "Alisher Navoiy ko'chasi, 42D, Termiz"
CLINIC_PHONE    = "+998-90-247-52-36"
CLINIC_LATITUDE  = 37.242882004548896
CLINIC_LONGITUDE = 67.29951953830746

WORK_START    = 9
WORK_END      = 19
SLOT_DURATION = 30

DOCTORS = [
    "Dr. Radjabov Alisher — Stomatolog",
    "Dr. Safarova Asila — Stomatolog",
]

# config moduli sifatida import qilinadigan joylar uchun
import types
config = types.ModuleType("config")
config.BOT_TOKEN       = BOT_TOKEN
config.ADMIN_ID        = ADMIN_ID
config.CLINIC_NAME     = CLINIC_NAME
config.CLINIC_ADDRESS  = CLINIC_ADDRESS
config.CLINIC_PHONE    = CLINIC_PHONE
config.CLINIC_LATITUDE  = CLINIC_LATITUDE
config.CLINIC_LONGITUDE = CLINIC_LONGITUDE
config.WORK_START      = WORK_START
config.WORK_END        = WORK_END
config.SLOT_DURATION   = SLOT_DURATION
config.DOCTORS         = DOCTORS
import sys
sys.modules["config"] = config

# ── Bot ─────────────────────────────────────────────────
from database import init_db
from handlers import register

async def main():
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    dp = Dispatcher(storage=MemoryStorage())
    await init_db()
    register(dp)
    print("✅ Bot ishga tushdi!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
