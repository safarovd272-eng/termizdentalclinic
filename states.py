from aiogram.fsm.state import State, StatesGroup

class Reg(StatesGroup):
    lang  = State()
    name  = State()
    phone = State()

class Book(StatesGroup):
    doctor    = State()
    date      = State()
    time      = State()
    complaint = State()
    file      = State()

class PatChat(StatesGroup):
    msg = State()

class AdmChat(StatesGroup):
    pick = State()
    msg  = State()

class AdmReply(StatesGroup):
    msg = State()

class Broadcast(StatesGroup):
    msg = State()

class Rate(StatesGroup):
    score = State()
