"""
TP2 - Développement d'index
--------------------------
Objectif : Construire 5 index à partir d'un JSONL e-commerce :
- title_index.json (index positionnel)
- description_index.json (index positionnel)
- brand_index.json (index inversé)
- origin_index.json (index inversé)
- reviews_index.json (index non inversé)

Auteur : Raffali Amine
Date : 13/01/2026
"""

from __future__ import annotations

import json
import re
import string
from collections import defaultdict
from pathlib import Path
from typing import Iterator
from urllib.parse import urlparse, parse_qs


# ============================================================
# Pour commenceer, nous allons ajuster la "politesse" du script :
# en fixant les variables suivantes (chemins, stopwords, etc.)
# ============================================================

DATA_PATH = Path("products.jsonl")
OUT_DIR = Path("out_indexes")

STOPWORDS = {
    "le", "la", "les", "un", "une", "des", "de", "du", "d", "et", "ou", "à", "a",
    "the", "an", "and", "or", "to", "of", "in", "for", "with", "on", "at",
}

PUNCT_TABLE = str.maketrans("", "", string.punctuation)
PRODUCT_ID_RE = re.compile(r"^/product/(\d+)/?$")


# ============================================================
# 1) Lecture JSONL + sauvegarde JSON
# ============================================================

def load_jsonl(path: Path) -> Iterator[dict]:
    """
    Load a JSONL file (one JSON object per line).
    """
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON at line {line_number}: {e}") from e


def save_json(obj: object, path: Path) -> None:
    """
    Save a Python object as JSON (pretty, utf-8).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


# ============================================================
# 2) Parsing URL : product_id + variant (utile même si on n'indexe pas tout dessus)
# ============================================================

def extract_product_id(url: str | None) -> str | None:
    """
    Extract product_id from URL path like /product/<id>.
    """
    if not url:
        return None
    parsed = urlparse(url)
    m = PRODUCT_ID_RE.search(parsed.path)
    return m.group(1) if m else None


def extract_variant(url: str | None) -> str | None:
    """
    Extract variant from query (?variant=...).
    """
    if not url:
        return None
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    return qs.get("variant", [None])[0]


# ============================================================
# 3) Tokenization
# ============================================================

def normalize_token(raw: str) -> str:
    """
    Normalize token: lowercase + remove punctuation + remove apostrophes.
    """
    tok = raw.lower().translate(PUNCT_TABLE)
    tok = tok.replace("’", "").replace("'", "")
    return tok


def tokenize(text: str | None) -> list[str]:
    """
    Tokenize text: split spaces + normalize + remove stopwords.
    """
    if not text:
        return []

    out: list[str] = []
    for raw in text.split():
        tok = normalize_token(raw)
        if tok and tok not in STOPWORDS:
            out.append(tok)
    return out


def tokenize_with_positions(text: str | None) -> list[tuple[str, int]]:
    """
    Tokenize and keep positions (positions among kept tokens).
    """
    if not text:
        return []

    out: list[tuple[str, int]] = []
    pos = 0

    # Pour extraire le contenu, on procède en différentes étapes :
    # 1) split
    # 2) normalize
    # 3) filtrer stopwords
    # 4) stocker avec position
    for raw in text.split():
        tok = normalize_token(raw)
        if tok and tok not in STOPWORDS:
            out.append((tok, pos))
            pos += 1

    return out


# ============================================================
# 4) Index positionnel (title + description)
# ============================================================

def build_positional_index(docs: list[dict], field_name: str) -> dict:
    """
    Build positional index:
        token -> { url -> [positions] }
    """
    index = defaultdict(lambda: defaultdict(list))

    for d in docs:
        url = d.get("url")
        text = d.get(field_name, "") or ""
        if not url or not text:
            continue

        for tok, pos in tokenize_with_positions(text):
            index[tok][url].append(pos)

    # Convert defaultdict -> dict (sinon json.dump est moche)
    return {tok: dict(url_map) for tok, url_map in index.items()}


# ============================================================
# 5) Index inversé pour brand / origin
# ============================================================

def build_feature_url_index(docs: list[dict], feature_key: str) -> dict[str, list[str]]:
    """
    Build feature inverted index:
        normalized_feature_value -> sorted list of URLs

    Exemple pour brand:
        "chocodelight" -> [url1, url2, ...]
    """
    index = defaultdict(set)

    for d in docs:
        url = d.get("url")
        features = d.get("product_features", {}) or {}
        if not url or not features:
            continue

        value = features.get(feature_key)
        if value is None or value == "":
            continue

        # Ici je fais simple : la valeur est une marque / un pays,
        # donc je normalize et je colle sans espaces.
        normalized_value = normalize_token(str(value)).replace(" ", "")

        if normalized_value:
            index[normalized_value].add(url)

    return {val: sorted(urls) for val, urls in index.items()}


# ============================================================
# 6) Index reviews (non inversé)
# ============================================================

def build_reviews_index(docs: list[dict]) -> dict:
    """
    Build reviews stats index (NOT inverted):
        url -> {review_count, average_rating, last_rating}
    """
    index = {}

    for d in docs:
        url = d.get("url")
        reviews = d.get("product_reviews", []) or []
        if not url:
            continue

        ratings = []
        for r in reviews:
            if not isinstance(r, dict):
                continue
            rating = r.get("rating")
            if isinstance(rating, (int, float)):
                ratings.append(float(rating))

        if not ratings:
            index[url] = {
                "review_count": 0,
                "average_rating": None,
                "last_rating": None
            }
            continue

        index[url] = {
            "review_count": len(ratings),
            "average_rating": round(sum(ratings) / len(ratings), 2),
            # On prend le dernier rating selon l'ordre du fichier (simple et suffisant ici)
            "last_rating": ratings[-1]
        }

    return index


# ============================================================
# 7) Main : on construit exactement les 5 fichiers attendus
# ============================================================

def main() -> None:
    # Pour commencer, on charge les documents du JSONL
    docs = list(load_jsonl(DATA_PATH))

    # Petite étape utile : on calcule product_id + variant (même si on n’en fait pas un index ici)
    # Ça montre qu'on a bien traité l'URL comme demandé.
    for d in docs:
        url = d.get("url")
        d["product_id"] = extract_product_id(url)
        d["variant"] = extract_variant(url)

    # 1) Title positional index
    title_index = build_positional_index(docs, "title")

    # 2) Description positional index
    description_index = build_positional_index(docs, "description")

    # 3) Brand index (feature_key = "brand")
    brand_index = build_feature_url_index(docs, "brand")

    # 4) Origin index (dans ton dataset c'est "made in")
    origin_index = build_feature_url_index(docs, "made in")

    # 5) Reviews index
    reviews_index = build_reviews_index(docs)

    # Sauvegarde : exactement les 5 fichiers demandés
    save_json(title_index, OUT_DIR / "title_index.json")
    save_json(description_index, OUT_DIR / "description_index.json")
    save_json(brand_index, OUT_DIR / "brand_index.json")
    save_json(origin_index, OUT_DIR / "origin_index.json")
    save_json(reviews_index, OUT_DIR / "reviews_index.json")

    print("les 5 index ont été générés dans out_indexes/")


if __name__ == "__main__":
    main()
