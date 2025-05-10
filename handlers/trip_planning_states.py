from aiogram.fsm.state import State, StatesGroup

class TripPlanning(StatesGroup):
    waiting_for_location = State()
    waiting_for_interests = State()
    waiting_for_budget = State()
    waiting_for_trip_dates = State()      # <--- НОВОЕ СОСТОЯНИЕ для дат
    waiting_for_transport_prefs = State() # <--- НОВОЕ СОСТОЯНИЕ для транспорта

class LanguageSelection(StatesGroup):  # <--- ВОТ ЭТА ГРУППА ДОЛЖНА БЫТЬ
    waiting_for_language_choice = State()
    # Позже мы сюда можем добавить еще, например, waiting_for_confirmation