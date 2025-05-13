from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
import logging

# Импортируем состояния выбора языка
from .trip_planning_states import LanguageSelection

# Импортируем нашу функцию для локализации и словарь языков
from utils.localization import get_text, SUPPORTED_LANGUAGES

# Импортируем CRUD операции и сессию БД
from database import crud
from sqlalchemy.ext.asyncio import AsyncSession

user_commands_router = Router(name="user_commands_router")


async def offer_language_selection(message: Message, state: FSMContext, user_id: int):
    """Вспомогательная функция для предложения выбора языка."""
    lang_buttons = []
    for lang_name, lang_code in SUPPORTED_LANGUAGES.items():
        lang_buttons.append([InlineKeyboardButton(text=lang_name, callback_data=f"select_lang_{lang_code}")])

    language_keyboard = InlineKeyboardMarkup(inline_keyboard=lang_buttons)

    prompt_ru = get_text("language_selection_prompt", "ru")
    prompt_en = get_text("language_selection_prompt", "en")
    # Убираем дублирование приветствия для французского, если оно есть
    prompt_fr_full = get_text("language_selection_prompt", "fr")
    prompt_fr = prompt_fr_full.split(":")[-1].strip() if ":" in prompt_fr_full else prompt_fr_full

    await message.answer(
        f"{prompt_ru}\n{prompt_en}\n{prompt_fr}",
        reply_markup=language_keyboard
    )
    await state.set_state(LanguageSelection.waiting_for_language_choice)
    logging.info(f"Пользователю {user_id} предложен выбор языка. Состояние: {await state.get_state()}")


@user_commands_router.message(CommandStart())
async def handle_start_command(message: Message, state: FSMContext, session: AsyncSession):
    user_id = message.from_user.id
    telegram_username = message.from_user.username or "N/A"
    logging.info(f"Пользователь {user_id} ({telegram_username}) вызвал /start.")

    # Пытаемся загрузить язык пользователя из БД
    user_language = await crud.get_user_language(session, user_id)

    if user_language:
        await state.update_data(user_language=user_language)
        logging.info(f"Для пользователя {user_id} язык '{user_language}' загружен из БД и сохранен в state.")

        # Приветствуем пользователя на его языке
        # Ключ "welcome_back" должен быть в твоем файле localization.py
        # Пример: "welcome_back": "С возвращением! Ваш язык: {language}. Начните планирование с /plan_trip или смените язык с /language."
        # ВАЖНО: нужно передать сам язык в get_text, если он используется в строке
        welcome_message = get_text(
            "welcome_back",
            user_language,
            language=SUPPORTED_LANGUAGES.get(user_language, user_language)  # Отобразит полное имя языка
        )
        await message.answer(welcome_message)
        await state.set_state(None)  # Сбрасываем состояние, так как язык уже известен
    else:
        logging.info(f"Для пользователя {user_id} язык в БД не найден. Предлагаем выбор.")
        await offer_language_selection(message, state, user_id)


@user_commands_router.callback_query(LanguageSelection.waiting_for_language_choice, F.data.startswith("select_lang_"))
async def process_language_selection(callback_query: CallbackQuery, state: FSMContext, session: AsyncSession):
    user_id = callback_query.from_user.id
    selected_lang_code = callback_query.data.split("_")[2]

    # Сохраняем/обновляем язык пользователя в БД
    try:
        await crud.create_or_update_user_language(session, user_id, selected_lang_code)
        logging.info(f"Язык '{selected_lang_code}' для пользователя {user_id} сохранен/обновлен в БД.")
    except Exception as e:
        logging.error(f"Ошибка сохранения языка для пользователя {user_id} в БД: {e}")
        # Можно уведомить пользователя об ошибке или просто продолжить, сохранив только в state
        # Для простоты, пока просто логируем.
        await callback_query.answer(get_text("db_error_lang_save", "en"),
                                    show_alert=True)  # Предполагаем такой ключ для ошибки
        return

    await state.update_data(user_language=selected_lang_code)

    greeting_text = get_text("welcome_language_selected", selected_lang_code)
    try:
        await callback_query.message.edit_text(greeting_text)
    except Exception as e:
        logging.warning(f"Не удалось отредактировать сообщение после выбора языка для {user_id}: {e}. Отправляю новое.")
        await callback_query.message.answer(greeting_text)  # Отправить новым, если редактирование не удалось

    await callback_query.answer()  # Закрыть pop-up уведомление на кнопке
    await state.set_state(None)

    logging.info(
        f"Пользователь {user_id} выбрал язык: {selected_lang_code}. Данные state: {await state.get_data()}")


@user_commands_router.message(Command("language"))
async def cmd_change_language(message: Message, state: FSMContext, session: AsyncSession):  # Добавили session
    user_id = message.from_user.id
    telegram_username = message.from_user.username or "N/A"
    logging.info(f"Пользователь {user_id} ({telegram_username}) вызвал /language для смены языка.")
    # Эта команда просто перезапускает процесс выбора языка
    await offer_language_selection(message, state, user_id)