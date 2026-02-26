from aiogram.fsm.state import State, StatesGroup

class Reg(StatesGroup):
    lang = State()
    name = State()
    phone = State()

class Appt(StatesGroup):
    doctor = State()
    date = State()
    time = State()
    complaint = State()
    file = State()

class ChatPatient(StatesGroup):
    typing = State()

class AdminChat(StatesGroup):
    choose_patient = State()
    typing = State()

class AdminReply(StatesGroup):
    typing = State()

class Broadcast(StatesGroup):
    typing = State()

class RatingFlow(StatesGroup):
    score = State()
    comment = State()
