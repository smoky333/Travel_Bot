import json
import logging # Для вывода сообщений в консоль, если что-то пойдет не так

# Это пример ответа, который мог бы дать настоящий AI.
# Мы его возьмем из нашего самого первого обсуждения промта.
# ВАЖНО: Этот JSON должен быть валидным! Проверь его, если будешь копировать.
# Я немного сокращу его для простоты, оставив суть.
SAMPLE_JSON_RESPONSE_STR = """
{
  "query_summary": {
    "location_interpreted": "Париж, Франция (из заглушки)",
    "trip_days": 2,
    "main_interests": ["искусство", "гастрономия", "история"]
  },
  "recommendations": [
    {
      "id": "route_paris_day1_art_leftbank_stub",
      "type": "route",
      "name": "Заглушка: Искусство Левого берега (День 1)",
      "address": "Париж, Левый берег Сены",
      "coordinates": [48.8567, 2.3265],
      "description": "Пешеходный маршрут по знаковым местам Левого берега (это ответ из заглушки).",
      "details": {
        "route_type": "пеший",
        "stops": [
          { "name": "Музей Орсе (заглушка)", "coordinates": [48.859961, 2.326556], "description": "Коллекция импрессионизма." }
        ]
      },
      "distance_or_time": "Примерно 6 км, ~5-7 часов",
      "price_estimate": "Билеты: Орсе ~16€",
      "rating": 4.9,
      "opening_hours": "Музеи обычно 9:30 - 18:00",
      "booking_link": null,
      "images": ["https://images.unsplash.com/photo-1505084432426-93049a223726?q=80&w=200&h=150"]
    },
    {
      "id": "hotel_paris_latinquarter_stub",
      "type": "hotel",
      "name": "Заглушка: Hôtel Paris Centre",
      "address": "Rue de Rivoli, 75004 Paris (заглушка)",
      "coordinates": [48.855, 2.354],
      "description": "Комфортный 3 звезды в центре (это ответ из заглушки).",
      "details": {
        "stars": 3,
        "amenities": ["wifi", "breakfast_included"]
      },
      "distance_or_time": "300 м до Лувра",
      "price_estimate": "120€/ночь",
      "rating": 4.5,
      "booking_link": "https://booking.example.com/stub",
      "images": ["https://images.unsplash.com/photo-1566073771259-6a8506099945?q=80&w=200&h=150"]
    }
  ]
}
"""

SAMPLE_ACCOMPANYING_TEXT = """
Это **заглушечный** ответ от AI! 🤖
Я получил ваши данные и вот примерные рекомендации для Парижа.
Когда мы подключим настоящий AI, здесь будет более подробный и персонализированный план!
"""

async def get_travel_recommendations(user_data: dict) -> tuple[dict | None, str | None]:
    """
    Имитирует получение рекомендаций от AI.
    В будущем здесь будет формирование промта и вызов LLM API.
    Пока что возвращает заранее подготовленные данные (заглушку).

    :param user_data: Словарь с данными, собранными от пользователя.
    :return: Кортеж (словарь_с_JSON_рекомендациями | None, текстовое_сопровождение | None)
    """
    logging.info(f"AI Integration: Получены данные от пользователя для заглушки: {user_data}")

    # TODO: Здесь будет логика формирования промта на основе user_data

    # Просто имитируем задержку, как будто AI думает
    # import asyncio # Если будете использовать asyncio.sleep
    # await asyncio.sleep(2) # Имитация задержки в 2 секунды

    try:
        # Преобразуем нашу строку с JSON в настоящий Python словарь
        recommendations_json = json.loads(SAMPLE_JSON_RESPONSE_STR)
        accompanying_text = SAMPLE_ACCOMPANYING_TEXT

        logging.info("AI Integration: Заглушка успешно вернула данные.")
        return recommendations_json, accompanying_text
    except json.JSONDecodeError as e:
        logging.error(f"AI Integration: Ошибка декодирования JSON из заглушки: {e}")
        return None, "Произошла ошибка при обработке примера данных от AI."
    except Exception as e:
        logging.error(f"AI Integration: Непредвиденная ошибка в заглушке: {e}")
        return None, "Произошла какая-то ошибка в модуле AI (заглушка)."