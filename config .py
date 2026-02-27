import os

# Token — Railway Variables dan olinadi (xavfsiz)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8651517812:AAFZHPIAvP7fc60JFq0BYKk88OpvzqB872s")

# Clinic info
CLINIC_NAME    = "DENTAL-SERVIS-TERMIZ"
CLINIC_ADDRESS = "Alisher Navoiy ko'chasi, 42D, Termiz"
CLINIC_PHONE   = "+998-90-247-52-36"
CLINIC_LATITUDE  = 37.242882004548896
CLINIC_LONGITUDE = 67.29951953830746

# Ish vaqti
WORK_START    = 9
WORK_END      = 19
SLOT_DURATION = 30

# Admin ID — Railway Variables dan olinadi
ADMIN_ID = int(os.environ.get("ADMIN_ID", "6551375195"))

# Shifokorlar
DOCTORS = [
    "Dr. Radjabov Alisher — Stomatolog",
    "Dr. Safarova Asila — Stomatolog",
]
