import os
import re
import csv
from functools import lru_cache
from typing import List, Dict, Tuple

# rapidfuzz для нормального fuzzy; если нет — fallback на difflib
try:
    from rapidfuzz import fuzz
    _HAS_RF = True
except Exception:
    import difflib
    _HAS_RF = False

    class _FuzzStub:
        @staticmethod
        def ratio(a, b) -> float:
            return difflib.SequenceMatcher(None, a, b).ratio() * 100

        partial_ratio = ratio
        token_set_ratio = ratio

    fuzz = _FuzzStub()  # type: ignore


# Django settings (для BASE_DIR)
try:
    from django.conf import settings
    _HAS_SETTINGS = True
except Exception:
    settings = None
    _HAS_SETTINGS = False

# твоя нормализация
from .text_utils import normalize_text


# ------------------ базовые настройки ------------------ #

SPECIAL_MAP: dict[str, list[tuple[str, str]]] = {
    # ФАНТИКИ
    # Коды и названия здесь должны совпадать с тем, как они записаны в fkko.csv.
    # Если формулировка чуть другая — просто подправь name под свой CSV.
    "фантики": [
        ("30111811724", "Отходы упаковки из разнородных материалов в смеси, загрязнённые пищевым сырьём (фантики)"),
        ("30118228204", "Брак производства конфет (фантики, упаковка)"),
        ("43800000000", "Отходы продукции из пластмасс (в т.ч. полимерные фантики)"),
    ],
    "фантик": [
        ("30111811724", "Отходы упаковки из разнородных материалов в смеси, загрязнённые пищевым сырьём (фантики)"),
        ("30118228204", "Брак производства конфет (фантики, упаковка)"),
        ("43800000000", "Отходы продукции из пластмасс (в т.ч. полимерные фантики)"),
    ],
}

STOP = {
    "продам", "продаю", "продается", "продаётся",
    "куплю", "ищу", "отдам",
    "аренда", "арендую",
    "новый", "новая", "новые", "новое",
    "б", "бу", "б/у", "б\\у",
    "опт", "розница", "наличие"
}


def _tokens(s: str) -> List[str]:
    return [
        t for t in re.findall(r"[a-zа-яё0-9]+", s.lower())
        if t not in STOP
    ]


def _find_fkko_csv() -> str:
    """
    Ищем fkko.csv:
      1) рядом с fkko_search.py
      2) BASE_DIR/data/fkko.csv
    """
    here = os.path.dirname(__file__)
    candidates = [
        os.path.join(here, "fkko.csv"),
    ]
    if _HAS_SETTINGS:
        candidates.append(os.path.join(settings.BASE_DIR, "data", "fkko.csv"))

    for path in candidates:
        if path and os.path.exists(path):
            return path

    raise RuntimeError(
        "fkko.csv не найден. Положи его либо рядом с fkko_search.py, "
        "либо в BASE_DIR/data/fkko.csv"
    )


# ------------------ загрузка ФККО ------------------ #

@lru_cache(maxsize=1)
def load_fkko_data() -> List[Dict[str, str]]:
    """
    Загружаем ФККО-справочник:
      { "code": ..., "name": ..., "name_norm": ... }
    """
    csv_path = _find_fkko_csv()
    data: List[Dict[str, str]] = []

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = (row.get("code") or "").strip()
            name = (row.get("name") or "").strip()
            if not code or not name:
                continue
            name_norm = normalize_text(name)
            data.append(
                {
                    "code": code,
                    "name": name,
                    "name_norm": name_norm,
                }
            )

    return data


def fkko_count() -> int:
    """Для статистики / админки."""
    return len(load_fkko_data())


# ------------------ понимание полимера ------------------ #

def _poly_from_query(q: str) -> str | None:
    """
    Определяем, про какой полимер запрос:
      ПНД, ПВД, ПВХ, ПП, ПЭТ(Ф), ПС, ПК, ПА, АБС, ПММА и т.п.
    Возвращаем ключ (строку), которую потом ищем в name_norm.
    """
    ql = q.lower()

    if "пнд" in ql or "pehd" in ql:
        return "полиэтилен"          # ПНД
    if "пвд" in ql or "pell" in ql:
        return "полиэтилен"          # ПВД
    if "пвх" in ql or "pvc" in ql:
        return "поливинилхлорид"
    if "полипроп" in ql or "пп " in ql or " pp" in ql:
        return "полипропилен"
    if "пэтф" in ql or "пэт " in ql or "pet" in ql:
        return "полиэтилентерефталат"
    if "полистир" in ql or "пс " in ql:
        return "полистирол"
    if "поликарбонат" in ql or "пк " in ql:
        return "поликарбонат"
    if "полиамид" in ql or "па " in ql:
        return "полиамид"
    if "абс" in ql:
        return "акрилонитрилбутадиенстирол"
    if "пмма" in ql:
        return "полиметилметакрилат"
    return None


# ------------------ спец-обогащение запроса ------------------ #

def _expand_query(q: str) -> str:
    """
    Обогащаем запрос под популярные "человеческие" формулировки,
    чтобы они совпадали с описаниями в ФККО.
    """
    ql = q.lower()

    # биг-бэги / биг бэг / мкр
    if any(w in ql for w in ("биг", "big", "бэг", "мкр")):
        q += " мешок мешки мягкая тара бигбэг биг-бэг биг бег плёнка полипропилен изделия незагрязненные"

    # ПЭТ бутылка / ПЭТФ тара / ПЭТ флекса
    if any(w in ql for w in ("пэтф", "пэт ", "пэт-", "pet", "флекс", "флекса", "бутыл")):
        q += " бутылка тара полиэтилентерефталат пэтф пэт изделия лом отходы незагрязненные флекса"

    # ящики
    if "ящик" in ql:
        q += " тара ящик контейнер пластиковый полипропилен полимерные изделия"
        # фантики (конфетные обёртки / упаковка кондитерки)

    if "фантик" in ql or "фантики" in ql or "фанти" in ql:
        q += (
            " обертка обёртка фантик фантики упаковка конфет "
            "упаковка кондитерских изделий оберточная бумага "
            "упаковка пищевых продуктов пленка упаковочная"
        )


    # лом пластика / лом пластмасс
    if "лом пласт" in ql or ("лом" in ql and "пласт" in ql):
        q += " лом отходы изделия пластмассы полимеры вторичные материалы"

    # БОПП
    if "бопп" in ql or "bopp" in ql:
        q += " пленка полипропилен ориентированная биаксиально упаковка"

    # полиэтиленовая плёнка
    if "пленка полиэтилен" in ql:
        q += " пленка полиэтилен упаковочная изделия незагрязненные"

    # стрейч-плёнка
    if "стрейч" in ql or "stretch" in ql:
        q += " пленка полиэтилен стрейч упаковочная растягиваемая"

    # трубы
    if "трубы пнд" in ql or ("трубы" in ql and "пнд" in ql):
        q += " трубы полиэтилен низкой плотности изделия полимерные"
    if "трубы пвх" in ql or ("трубы" in ql and "пвх" in ql):
        q += " трубы поливинилхлорид пвх изделия полимерные"
    if "трубы полипроп" in ql or ("трубы" in ql and "полипроп" in ql):
        q += " трубы полипропилен изделия полимерные"

    # катушки полистирольные / полимерная тара
    if "катуш" in ql:
        q += " катушка тара полимерная полистирол изделия из пластмасс"

    # поликарбонат
    if "поликарбонат" in ql:
        q += " поликарбонат лист обрезки лом отходы изделий"

    # мешки полиэтиленовые
    if "мешки полиэтилен" in ql or ("мешки" in ql and "полиэтилен" in ql):
        q += " мешок мешки пленка полиэтилен тара полимерная"

    # плёнка полиалифиновая
    if "пленка полиалифин" in ql or "полиалифиновая пленка" in ql:
        q += " пленка полиалифиновый упаковка полимерная"

    # канистры / флаконы ПНД
    if "канистр" in ql and "пнд" in ql:
        q += " канистра тара полиэтилен изделия пнд"
    if "флакон" in ql and "пнд" in ql:
        q += " флакон тара полиэтилен изделия пнд"

    # общая логика «дроблёнки / дроблёный»
    if "дробл" in ql or "дроблён" in ql or "дроблен" in ql:
        q += " дробленый измельченный лом отходы вторичный гранулят фракция"

    # подцепляем полимеры по сокращениям
    if "пнд" in ql:
        q += " полиэтилен"
    if "пвд" in ql:
        q += " полиэтилен"
    if "пвх" in ql:
        q += " поливинилхлорид"
    if "полипроп" in ql or "пп " in ql:
        q += " полипропилен"
    if "полистирол" in ql or "пс " in ql:
        q += " полистирол"
    if "полиамид" in ql or "па " in ql:
        q += " полиамид"
    if "абс" in ql:
        q += " акрилонитрилбутадиенстирол"
    if "пмма" in ql:
        q += " полиметилметакрилат"
    if "поликарбонат" in ql or "пк " in ql:
        q += " поликарбонат"

    return q


# ------------------ дроблёнка / контекст лома ------------------ #

def _is_crushed_context(name_norm: str) -> bool:
    """
    Проверяем, что строка действительно про лом/дроблёнку/измельчённые изделия,
    а не про сточные воды, фильтры, картон и т.п.
    """
    n = name_norm.lower()
    good_markers = ("дробл", "измельчен", "лом", "отход издел", "отходы издел")

    if not any(m in n for m in good_markers):
        return False

    bad_markers = (
        "сточн",      # сточные воды
        "шлам",       # шламы
        "картон",     # картон
        "бумага",     # бумага
        "фильтровальн",
        "пыль"
    )
    if any(b in n for b in bad_markers):
        return False

    return True


# ------------------ скоринг ------------------ #

def _score_row(
    row: Dict[str, str],
    q_raw: str,
    q_norm: str,
    poly_key: str | None,
    crushed_only: bool
) -> float:
    """
    Оцениваем, насколько строка из ФККО подходит под запрос.
    """
    name_norm = row["name_norm"]
    name_l = row["name"].lower()
    code = row["code"]

    # прямое совпадение по коду → максимум
    cl = code.replace(" ", "")
    qr = q_raw.replace(" ", "")
    if cl and qr and cl.startswith(qr):
        return 1.0

    # дроблёнка: отбрасываем неподходящие контексты
    if crushed_only and not _is_crushed_context(name_norm):
        return 0.0

    s1 = fuzz.token_set_ratio(q_norm, name_norm) / 100.0
    s2 = fuzz.partial_ratio(q_norm, name_norm) / 100.0
    s3 = fuzz.token_set_ratio(q_raw, name_l) / 100.0

    base = max(s1, s2, s3)

    # небольшой бонус за прямое вхождение токенов запроса
    if any(tok in name_l for tok in _tokens(q_raw)):
        base += 0.05

    # бонус за совпадение полимера
    if poly_key and poly_key in name_norm:
        base += 0.15
    ql = q_raw.lower()
    if ("трубы" in ql or "труба" in ql) and "труб" in name_norm:
        base += 0.10

    if base > 1.0:
        base = 1.0
    return base


# ------------------ основной кэшируемый поиск ------------------ #

@lru_cache(maxsize=1024)
def _suggest_cached(q: str, limit: int) -> Tuple[Tuple[str, str], ...]:
    data = load_fkko_data()

    # расширяем запрос и нормализуем
    q_expanded = _expand_query(q)
    q_norm = normalize_text(q_expanded)
    q_tokens = _tokens(q_norm)

    poly_key = _poly_from_query(q)  # какой полимер
    crushed_query = any("дробл" in t for t in q_tokens)  # дроблёнка/лом?
    tube_query = ("трубы" in q.lower()) or ("труба" in q.lower())

        # будем отдельно собирать «трубные» строки и остальные
    ranked_tube: List[Tuple[float, str, str]] = []
    ranked_other: List[Tuple[float, str, str]] = []

    for row in data:
        name_norm = row["name_norm"]

        # если дроблёнка — фильтруем по контексту
        if crushed_query and not _is_crushed_context(name_norm):
            continue

        # хотя бы один токен должен встретиться
        if q_tokens and not any(t in name_norm for t in q_tokens):
            continue

        sc = _score_row(row, q, q_norm, poly_key, crushed_query)
        if sc < 0.40:
            continue

        has_tube = "труб" in name_norm  # трубы/трубные изделия

        if tube_query and has_tube:
            ranked_tube.append((sc, row["code"], row["name"]))
        else:
            ranked_other.append((sc, row["code"], row["name"]))

    ranked_tube.sort(key=lambda x: x[0], reverse=True)
    ranked_other.sort(key=lambda x: x[0], reverse=True)

    # сначала трубы (если нашли), потом остальные
    ranked = ranked_tube + ranked_other


    seen: set[str] = set()
    out: List[Tuple[str, str]] = []

    for sc, code, name in ranked:
        if code in seen:
            continue
        seen.add(code)
        out.append((code, name))
        if len(out) >= limit:
            break

    return tuple(out)


# ------------------ публичные функции для views ------------------ #

def suggest_fkko(query: str, limit: int = 12) -> List[Dict[str, str]]:
    """
    Используется для автодополнения в форме.
    Возвращает список словарей: {code, name}
    """
    q = (query or "").strip()
    if not q:
        return []
    ql = q.lower()
    for key, items in SPECIAL_MAP.items():
        if key in ql:
            return [
                {"code": code, "name": name}
                for code, name in items[:limit]
            ]

    res = _suggest_cached(q.lower(), int(limit))
    return [{"code": c, "name": n} for c, n in res]


def search_fkko(term: str, limit: int = 12) -> List[Dict[str, str]]:
    """
    Старый интерфейс, который дергается из views.

    1) Сначала пытаемся найти прямые подстрочные совпадения по коду/названию.
    2) Если ничего — используем умный suggest_fkko().
    """
    term = (term or "").strip()
    if not term:
        return []

    data = load_fkko_data()
    term_l = term.lower()
    out: List[Dict[str, str]] = []

    for row in data:
        if term_l in row["code"].lower() or term_l in row["name"].lower():
            out.append({"code": row["code"], "name": row["name"]})
        if len(out) >= limit:
            break

    if not out:
        out = suggest_fkko(term, limit=limit)

    return out
