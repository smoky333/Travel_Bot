from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
import logging

# Импортируем состояния выбора языка
from .trip_planning_states import LanguageSelection  # Предполагаем, что trip_planning_states.py в этой же папке

# Импортируем нашу функцию для локализации и словарь языков
from utils.localization import get_text, SUPPORTED_LANGUAGES

user_commands_router = Router(name="user_commands_router")


# SUPPORTED_LANGUAGES теперь импортируется из utils.localization,
# так что локальное определение не нужно.

# Команда /start теперь будет предлагать выбор языка
@user_commands_router.message(CommandStart())
async def handle_start_command(message: Message, state: FSMContext):
    # Создаем клавиатуру с выбором языка, используя SUPPORTED_LANGUAGES из localization.py
    lang_buttons = []
    for lang_name, lang_code in SUPPORTED_LANGUAGES.items():  # Используем импортированный словарь
        lang_buttons.append([InlineKeyboardButton(text=lang_name, callback_data=f"select_lang_{lang_code}")])

    language_keyboard = InlineKeyboardMarkup(inline_keyboard=lang_buttons)

    # Формируем приветствие на нескольких языках, чтобы пользователь точно понял
    # Ключ "language_selection_prompt" должен быть в твоем файле localization.py
    # Если его нет, get_text вернет плейсхолдер.
    # Для начального приветствия можно составить его вручную или сделать один общий ключ.
    # Здесь я использую твой подход с ручным составлением из нескольких языков.
    prompt_ru = get_text("language_selection_prompt", "ru")
    prompt_en = get_text("language_selection_prompt", "en")
    prompt_fr_full = get_text("language_selection_prompt", "fr")
    # Убираем дублирование приветствия для французского, если оно есть
    prompt_fr = prompt_fr_full.split(":")[-1].strip() if ":" in prompt_fr_full else prompt_fr_full

    await message.answer(
        f"{prompt_ru}\n{prompt_en}\n{prompt_fr}",  # Более чистая конкатенация
        reply_markup=language_keyboard
    )
    await state.set_state(LanguageSelection.waiting_for_language_choice)
    logging.info(f"Пользователь {message.from_user.id} инициировал выбор языка. Состояние: {await state.get_state()}")


# Обработчик нажатия кнопки выбора языка
@user_commands_router.callback_query(LanguageSelection.waiting_for_language_choice, F.data.startswith("select_lang_"))
async def process_language_selection(callback_query: CallbackQuery, state: FSMContext):
    selected_lang_code = callback_query.data.split("_")[2]
    await state.update_data(user_language=selected_lang_code)

    # Получаем локализованное приветствие после выбора языка
    # Ключ "welcome_language_selected" должен быть в твоем файле localization.py
    greeting_text = get_text("welcome_language_selected", selected_lang_code)

    await callback_query.message.edit_text(greeting_text)
    await callback_query.answer()
    await state.set_state(None)  # Выходим из FSM выбора языка, сохраняя данные в state

    logging.info(
        f"Пользователь {callback_query.from_user.id} выбрал язык: {selected_lang_code}. Данные state: {await state.get_data()}")


# Команда /language для смены языка
@user_commands_router.message(Command("language"))
async def cmd_change_language(message: Message, state: FSMContext):
    # Эта команда просто перезапускает процесс выбора языка, как при /start
    await handle_start_command(message, state)