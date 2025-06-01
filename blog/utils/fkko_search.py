# utils/fkko_search.py

import csv
import os
from django.conf import settings

FKKO_CSV_PATH = os.path.join(settings.BASE_DIR, 'data', 'fkko.csv')

def load_fkko_data():
    try:
        with open(FKKO_CSV_PATH, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except Exception:
        return []

FKKO_DATA = load_fkko_data()

def search_fkko(term: str, limit=15):
    """
    Поиск по коду или названию. Возвращает список словарей {code, name}
    """
    if not term:
        return []
    term = term.lower()
    seen = set()
    results = []
    for row in FKKO_DATA:
        code = row.get('code', '').strip()
        name = row.get('name', '').strip()
        if term in code.lower() or term in name.lower():
            if code not in seen:
                results.append({'code': code, 'name': name})
                seen.add(code)
        if len(results) >= limit:
            break
    return results
