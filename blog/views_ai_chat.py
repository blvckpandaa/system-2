import json
import logging

import requests
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты — AI-помощник сайта «Чистый Мир» (eccoprom.windexs.ru).

О сайте: это площадка, где можно размещать и искать объявления по покупке,
продаже и обмену отходов, вторичного сырья и экологичных товаров; есть
категории, новости, тарифы продвижения и личные чаты между пользователями.

Отвечай ТОЛЬКО на вопросы, связанные с:
- сайтом «Чистый Мир» (как пользоваться: регистрация, объявления, поиск, тарифы);
- переработкой отходов, утилизацией, раздельным сбором, вторичным сырьем;
- ФККО, экологичными практиками и смежной тематикой площадки.

Правила:
- Отвечай на русском, кратко и по делу (обычно 2–6 предложений).
- Если вопрос НЕ про сайт и НЕ про переработку/утилизацию/экологию — вежливо
  откажись и предложи спросить по теме сайта или отходов.
- НЕ давай юридических советов (законы, договоры, ответственность, лицензии,
  споры, «можно ли по закону», штрафы и т.п.). Если пользователь просит
  юридическую консультацию, ответь примерно так:
  «По юридическим вопросам я не консультирую. У меня есть друг Галина —
  она юрист. Обратитесь к ней: https://lawyer.windexs.ru»
- Не выдумывай законы, цифры и функции сайта; если не уверен — скажи об этом.
- Можно подсказывать разделы сайта: объявления, категории, размещение объявления.
"""

ALLOWED_ROLES = {"user", "assistant"}


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def _rate_limited(ip: str) -> bool:
    limit = getattr(settings, "AI_CHAT_RATE_LIMIT", 30)
    window = getattr(settings, "AI_CHAT_RATE_WINDOW", 60 * 60)
    key = f"ai_chat_rate:{ip}"
    count = cache.get(key, 0)
    if count >= limit:
        return True
    cache.set(key, count + 1, timeout=window)
    return False


def _sanitize_messages(raw_messages):
    cleaned = []
    if not isinstance(raw_messages, list):
        return cleaned
    for item in raw_messages[-12:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role not in ALLOWED_ROLES or not isinstance(content, str):
            continue
        text = content.strip()
        if not text or len(text) > 2000:
            continue
        cleaned.append({"role": role, "content": text})
    return cleaned


@require_POST
def ai_chat_view(request):
    api_key = getattr(settings, "DEEPSEEK_API_KEY", "") or ""
    if not api_key.strip():
        return JsonResponse(
            {"error": "AI-ассистент временно недоступен. Попробуйте позже."},
            status=503,
        )

    ip = _client_ip(request)
    if _rate_limited(ip):
        return JsonResponse(
            {"error": "Слишком много запросов. Подождите немного и попробуйте снова."},
            status=429,
        )

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Некорректный запрос."}, status=400)

    history = _sanitize_messages(payload.get("messages"))
    if not history or history[-1]["role"] != "user":
        return JsonResponse({"error": "Введите вопрос."}, status=400)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
    api_url = getattr(settings, "DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")
    model = getattr(settings, "DEEPSEEK_MODEL", "deepseek-chat")

    try:
        response = requests.post(
            api_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": 0.5,
                "max_tokens": 800,
            },
            timeout=45,
        )
    except requests.RequestException as exc:
        logger.exception("DeepSeek request failed: %s", exc)
        return JsonResponse(
            {"error": "Не удалось связаться с AI. Попробуйте ещё раз."},
            status=502,
        )

    if response.status_code != 200:
        logger.error(
            "DeepSeek error %s: %s",
            response.status_code,
            response.text[:500],
        )
        return JsonResponse(
            {"error": "AI временно недоступен. Попробуйте позже."},
            status=502,
        )

    try:
        data = response.json()
        answer = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError, ValueError):
        logger.exception("Unexpected DeepSeek response: %s", response.text[:500])
        return JsonResponse({"error": "Получен некорректный ответ AI."}, status=502)

    if not answer:
        return JsonResponse({"error": "Пустой ответ AI. Попробуйте переформулировать вопрос."}, status=502)

    return JsonResponse({"reply": answer})
