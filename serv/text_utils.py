# utils/text_utils.py

import inspect

# Патчим getargspec так, чтобы он возвращал ровно 4 значения
def _getargspec(func):
    full = inspect.getfullargspec(func)
    return full.args, full.varargs, full.varkw, full.defaults

inspect.getargspec = _getargspec

from pymorphy2 import MorphAnalyzer
import re

morph = MorphAnalyzer()

def normalize_text(text: str) -> str:
    tokens = re.findall(r'\w+', text.lower())
    lemmas = [morph.parse(tok)[0].normal_form for tok in tokens]
    return " ".join(lemmas)
