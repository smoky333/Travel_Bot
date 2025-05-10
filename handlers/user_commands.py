from aiogram import Router, F
from aiogram.filters import CommandStart, Command  # Добавили Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, \
    InlineKeyboardButton  # Добавили CallbackQuery и кнопки
from aiogram.fsm.context import FSMContext  # Добавили FSMContext
import logging  # Добавили logging для вывода информации

# Импортируем состояния выбора языка (убедись, что путь правильный)
# Если trip_planning_states.py в той же папке handlers:
from .trip_planning_states import LanguageSelection

# Если у тебя другая структура, поправь импорт. Предполагаю, что оба файла в папке handlers.

user_commands_router = Router(name="user_commands_router")

# СЛОВАРЬ С ПОДДЕРЖИВАЕМЫМИ ЯЗЫКАМИ И ИХ КОДАМИ
SUPPORTED_LANGUAGES = {
    "🇷🇺 Русский": "ru",
    "🇬🇧 English": "en",
    "🇫🇷 Français": "fr",
}


# Команда /start теперь будет предлагать выбор языка
@user_commands_router.message(CommandStart())
async def handle_start_command(message: Message, state: FSMContext):
    # Создаем клавиатуру с выбором языка
    lang_buttons = []
    for lang_name, lang_code in SUPPORTED_LANGUAGES.items():
        lang_buttons.append([InlineKeyboardButton(text=lang_name, callback_data=f"select_lang_{lang_code}")])

    language_keyboard = InlineKeyboardMarkup(inline_keyboard=lang_buttons)

    await message.answer(
        "👋 Привет! Пожалуйста, выберите язык / Please select your language / Veuillez sélectionner votre langue:",
        reply_markup=language_keyboard
    )
    # Переводим пользователя в состояние ожидания выбора языка
    await state.set_state(LanguageSelection.waiting_for_language_choice)
    logging.info(f"Пользователь {message.from_user.id} инициировал выбор языка. Состояние: {await state.get_state()}")


# Обработчик нажатия кнопки выбора языка
@user_commands_router.callback_query(LanguageSelection.waiting_for_language_choice, F.data.startswith("select_lang_"))
async def process_language_selection(callback_query: CallbackQuery, state: FSMContext):
    selected_lang_code = callback_query.data.split("_")[2]  # Получаем код языка (ru, en, fr)

    # Сохраняем выбранный язык в FSM для текущей сессии планирования
    await state.update_data(user_language=selected_lang_code)

    greeting_text = ""
    if selected_lang_code == "ru":
        greeting_text = (
            f"🇷🇺 Отлично! Выбран русский язык.\n"
            f"Я твой персональный Travel Bot.\n"
            f"Готов помочь спланировать твое лучшее путешествие!\n\n"
            f"Чтобы начать планирование, используй команду /plan_trip"
        )
    elif selected_lang_code == "en":
        greeting_text = (
            f"🇬🇧 Great! English language selected.\n"
            f"I am your personal Travel Bot.\n"
            f"Ready to help you plan your best trip!\n\n"
            f"To start planning, use the /plan_trip command."
        )
    elif selected_lang_code == "fr":
        greeting_text = (
            f"🇫🇷 Parfait ! Langue française sélectionnée.\n"
            f"Je suis votre Travel Bot personnel.\n"
            f"Prêt à vous aider à planifier votre meilleur voyage !\n\n"
            f"Pour commencer la planification, utilisez la commande /plan_trip"
        )
    else:
        greeting_text = "Language selected. Use /plan_trip to start."

    await callback_query.message.edit_text(greeting_text)
    await callback_query.answer()

    # НЕ ОЧИЩАЕМ СОСТОЯНИЕ FSM (state.clear()), чтобы user_language сохранился для /plan_trip
    # Вместо этого, явно выходим из FSM выбора языка, но данные в state остаются
    await state.set_state(None)

    logging.info(
        f"Пользователь {callback_query.from_user.id} выбрал язык: {selected_lang_code}. Данные state: {await state.get_data()}")


# Команда /language для смены языка (если пользователь уже выбрал ранее или хочет сменить)
@user_commands_router.message(Command("language"))
async def cmd_change_language(message: Message, state: FSMContext):
    # Эта команда просто перезапускает процесс выбора языка, как при /start
    await handle_start_command(message, state)