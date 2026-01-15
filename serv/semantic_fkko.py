# utils/semantic_fkko.py

import os
import pickle
from django.conf import settings

from sentence_transformers import SentenceTransformer
import faiss

from .fkko_search import load_fkko_data
from .text_utils import normalize_text

# 1) Загружаем наши данные ФККО
fkko_data = load_fkko_data()  # list of {'code','name'}

# 2) Готовим тексты: нормализуем код+название
texts = []
for row in fkko_data:
    raw = f"{row['code']} {row['name']}"
    texts.append(normalize_text(raw))

# 3) Инициализируем модель SBERT (можно заменить на более "русскую" модель)
model = SentenceTransformer('sberbank-ai/sbert_large_nlu_ru')

# 4) Пути для кэша FAISS-индекса и метаданных
EMB_INDEX_PATH = os.path.join(settings.BASE_DIR, 'data', 'fkko_embeddings.faiss')
EMB_META_PATH  = os.path.join(settings.BASE_DIR, 'data', 'fkko_meta.pkl')

def build_index(force: bool = False):
    """
    Строит или загружает FAISS-индекс и сохранённые эмбеддинги.
    """
    global index, embeddings

    if not force and os.path.exists(EMB_INDEX_PATH) and os.path.exists(EMB_META_PATH):
        # Загружаем уже построенный индекс и эмбеддинги
        index = faiss.read_index(EMB_INDEX_PATH)
        with open(EMB_META_PATH, 'rb') as f:
            embeddings = pickle.load(f)
    else:
        # Вычисляем эмбеддинги для всего корпуса
        embeddings = model.encode(
            texts,
            show_progress_bar=True,
            convert_to_numpy=True
        )

        # L2-нормализуем эмбеддинги — обязательно для правильного cosine Search
        faiss.normalize_L2(embeddings)

        dim = embeddings.shape[1]

        # Создаём HNSW-индекс по InnerProduct (что эквивалентно cosine после нормализации)
        index = faiss.IndexHNSWFlat(dim, 32, faiss.METRIC_INNER_PRODUCT)
        index.hnsw.efConstruction = 200

        # Добавляем все эмбеддинги в индекс
        index.add(embeddings)

        # Сохраняем на диск
        faiss.write_index(index, EMB_INDEX_PATH)
        with open(EMB_META_PATH, 'wb') as f:
            pickle.dump(embeddings, f)

# Построим индекс один раз при импорте модуля
build_index()


def semantic_search_fkko(
    query: str,
    top_k: int = 5,
    threshold: float = 0.45
):
    """
    Семантический поиск по 9000+ записям ФККО.

    Возвращает список словарей:
      {'code': код, 'name': название, 'score': cosine_similarity}
    Фильтрует по threshold (минимальная cosine_similarity).
    """
    q = query.strip()
    if not q:
        return []

    # Нормализуем текст запроса
    q_norm = normalize_text(q)

    # Эмбеддинг и L2-нормировка
    q_emb = model.encode([q_norm], convert_to_numpy=True)
    faiss.normalize_L2(q_emb)

    # Для качества поиска
    index.hnsw.efSearch = 50

    # Находим top_k ближайших по InnerProduct (= cosine similarity)
    distances, indices = index.search(q_emb, top_k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        score = float(dist)  # dist == inner_product == cosine similarity
        if score < threshold:
            continue
        row = fkko_data[idx]
        results.append({
            'code':  row['code'],
            'name':  row['name'],
            'score': round(score, 3)
        })

    return results
