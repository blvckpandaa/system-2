# utils/fkko_search.py
import os, re, csv
from typing import List, Dict, Tuple
from functools import lru_cache

# rapidfuzz с фолбеком, чтобы сайт не падал
try:
    from rapidfuzz import fuzz
    _RF = True
except Exception:
    import difflib
    _RF = False
    class _FuzzStub:
        @staticmethod
        def ratio(a,b): return difflib.SequenceMatcher(None,a,b).ratio()*100
        partial_ratio = ratio
        token_set_ratio = ratio
    fuzz = _FuzzStub()

try:
    from django.conf import settings
except Exception:
    settings = None

from .text_utils import normalize_text
try:
    from .semantic_fkko import semantic_search_fkko
    _SEM_OK = True
except Exception:
    _SEM_OK = False

# ---------- загрузка csv и предварительная нормализация ----------
_DATA: List[Dict[str,str]] = []

def _fkko_path() -> str:
    if settings and getattr(settings, "FKKO_CSV_PATH", None):
        return settings.FKKO_CSV_PATH
    if settings and getattr(settings, "BASE_DIR", None):
        p = os.path.join(str(settings.BASE_DIR), "fkko.csv")
        if os.path.exists(p): return p
    here = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(here, "fkko.csv")
    if os.path.exists(p): return p
    return os.path.abspath("fkko.csv")

def _pre_norm(s: str) -> str:
    # нормализация чуть агрессивнее: ё→е, дефисы/скобки убираем
    s = s.lower().replace("ё", "е")
    s = re.sub(r"[\(\)\[\]\.,;:/\\\-]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return normalize_text(s)

def _load() -> List[Dict[str,str]]:
    global _DATA
    if _DATA: return _DATA
    path = _fkko_path()
    data: List[Dict[str,str]] = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                code = (row.get("code") or "").strip()
                name = (row.get("name") or "").strip()
                if not code or not name: continue
                name_l = name.lower()
                name_norm = _pre_norm(name)
                data.append({"code": code, "name": name, "name_l": name_l, "name_norm": name_norm})
    _DATA = data
    return _DATA

def fkko_count() -> int:
    return len(_load())

# ---------- быстрые настройки ----------
STOP = {"продам","продаю","куплю","ищу","аренда","продаётся","продается","предлагаю","отдам"}

ALIASES = {
    # биг-бэг (разные написания/опечатки/англ.)
    "биг": ["биг", "бэг", "бег", "big", "bag", "мкр", "мешок"],
    "бэг": ["биг", "бэг", "бег", "big", "bag", "мкр", "мешок"],
    "бег": ["биг", "бэг", "бег", "big", "bag", "мкр", "мешок"],
    "big": ["биг", "бэг", "бег", "big", "bag", "мкр", "мешок"],
    "bag": ["биг", "бэг", "бег", "big", "bag", "мкр", "мешок"],

    # тара/пластики
    "пэтф": ["пэтф","пэт","бутыл"], "пэт": ["пэт","бутыл"], "бутыл": ["пэт","бутыл"],
    "стрейч": ["стрейч","пленк"], "пленк": ["пленк","стрейч","полиэтилен","полиалифин"],
    "бопп": ["бопп","ориентированная","полипропилен","пленк"],
    "канистр": ["канистр","пнд"], "флакон": ["флакон","пнд"],

    # трубы
    "трубы пнд": ["трубы","пнд"], "трубы пвх": ["трубы","пвх","поливинилхлорид"],
    "трубы полипропилен": ["трубы","полипропилен","пп"],

    # полимеры и формы
    "пвх": ["пвх","поливинилхлорид"], "пнд": ["пнд","низкого давлен"], "пвд": ["пвд","высокого давлен"],
    "абс": ["абс","акрилонитрил","бутадиен","стирол"], "пмма": ["пмма","метилметакрилат"],
    "полистирол": ["полистирол","пс"], "поликарбонат": ["поликарбонат"], "полипропилен": ["полипропилен","пп"],
    "дробл": ["дробл"], "флекс": ["флекс","пэт"], "лом пласт": ["лом","пласт"]
}

def _tokens(s: str) -> List[str]:
    return [t for t in re.findall(r"[a-zа-яё0-9]+", s.lower()) if t not in STOP]

def _alias(query_norm: str) -> List[str]:
    for k, vs in ALIASES.items():
        if k in query_norm:
            return vs
    return []

def _score(name_norm: str, code: str, q: str, q_norm: str) -> float:
    # быстрые признаки, без доступа к исходным name_l
    cl = code.lower()
    if cl.startswith(q): return 1.0
    # fuzz только тут, и на ограниченном числе кандидатов
    s1 = fuzz.token_set_ratio(q, name_norm)/100.0
    s2 = fuzz.partial_ratio(q, name_norm)/100.0
    s3 = fuzz.ratio(q, cl)/100.0
    s4 = fuzz.token_set_ratio(q_norm, name_norm)/100.0
    return max(0.7*s1 + 0.2*s2 + 0.1*s3, s4)

# ---------- публичные функции ----------
def search_fkko(term: str, limit: int = 12) -> List[Dict[str,str]]:
    term = (term or "").strip().lower()
    if not term: return []
    out = []
    for r in _load():
        if term in r["code"].lower() or term in r["name_l"]:
            out.append({"code": r["code"], "name": r["name"]})
        if len(out) >= limit: break
    return out

@lru_cache(maxsize=2048)
def _suggest_cached(q: str, limit: int) -> Tuple[Tuple[str,str], ...]:
    data = _load()
    if not data: return tuple()

    # числовой префикс → очень быстро
    if re.fullmatch(r"\d[\d\s\-]*", q):
        pref = re.sub(r"\D+", "", q)
        res = []
        for r in data:
            if r["code"].replace(" ", "").startswith(pref):
                res.append((r["code"], r["name"]))
                if len(res) >= limit: break
        return tuple(res)

    q_norm = _pre_norm(q)
    toks = _tokens(q_norm)
    alias = _alias(q_norm)

    # 1) быстрый отбор: все токены внутри name_norm
    fast = []
    for r in data:
        nm = r["name_norm"]
        if alias and not any(a in nm for a in alias):
            continue
        # все токены должны встретиться
        if all(t in nm for t in toks):
            fast.append(r)

    # 2) если fast пуст — ослабим до «хотя бы один токен»
    if not fast:
        for r in data:
            nm = r["name_norm"]
            if alias and not any(a in nm for a in alias):
                continue
            if any(t in nm for t in toks):
                fast.append(r)

    # ограничим пул для fuzz (ускорение!)
    fast = fast[:250]  # регулируй при необходимости

    # 3) скорим только выбранных
    ranked: List[Tuple[float, str, str]] = []
    for r in fast:
        sc = _score(r["name_norm"], r["code"], q, q_norm=q_norm)
        # умеренный порог — чтобы не терять релевантное
        if sc >= (0.60 if _RF else 0.70):
            ranked.append((sc, r["code"], r["name"]))

    if not ranked and _SEM_OK:
        # бэкап: семантика (нечасто дойдём до сюда)
        try:
            for h in semantic_search_fkko(q, top_k=min(30, limit*3), threshold=0.56):
                ranked.append((h.get("score", 0.8), h["code"], h["name"]))
        except Exception:
            pass

    ranked.sort(key=lambda x: x[0], reverse=True)
    seen, out = set(), []
    for _, code, name in ranked:
        if code in seen: continue
        seen.add(code); out.append((code, name))
        if len(out) >= limit: break
    return tuple(out)

def suggest_fkko(query: str, limit: int = 12) -> List[Dict[str,str]]:
    q = (query or "").strip()
    if not q: return []
    res = _suggest_cached(q.lower(), int(limit))
    return [{"code": c, "name": n} for c, n in res]
