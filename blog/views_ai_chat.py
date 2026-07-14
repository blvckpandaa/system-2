import json
import logging

import requests
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты — экологический помощник сайта «Чистый Мир».
Отвечай только на вопросы о переработке отходов, утилизации, раздельном сборе,
вторичном сырье, ФККО, экологичных практиках и связанных темах.

Правила:
- Отвечай на русском языке, кратко и по делу (обычно 2–6 предложений).
- Если вопрос не связан с экологией, переработкой или утилизацией — вежливо
  откажись и предложи спросить про отходы, переработку или утилизацию.
- Не выдумывай законы и цифры; если не уверен — скажи об этом.
- Не давай медицинских, юридических или финансовых советов вне темы экологии.
- Можно мягко упоминать, что на сайте есть объявления и информация по теме."""

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
