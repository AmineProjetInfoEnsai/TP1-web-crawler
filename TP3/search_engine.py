"""
TP3 - Moteur de recherche

Notre objectif sera de développer un moteur de recherche qui utilise les index créés précédemment
pour retourner et classer des résultats pertinents.

Auteur : Raffali Amine
Date : 2026
"""

######### Etape 1 et 2 #########
"""
- chargement des index
- préparation et normalisation des requêtes utilisateur
- augmentation de requête via des synonymes
- filtrage des documents candidats
"""

import json
import string
from pathlib import Path
from nltk.corpus import stopwords
import nltk
import math
nltk.download("stopwords")
STOPWORDS = stopwords.words("english")

INPUT_DIR = Path("input")

INDEX_FILES = {
    "title": "title_index.json",
    "description": "description_index.json",
    "brand": "brand_index.json",
    "origin": "origin_index.json",
    "reviews": "reviews_index.json",
    "origin_synonyms": "origin_synonyms.json"
}

#NB: Les champs brand et origin sont conservés comme métadonnées mais non utilisés
#directement dans le scoring

# Partie 1 – Lecture & préparation

def load_json_file(path: Path) -> dict:
    """
    Charge un fichier JSON et retourne son contenu.

    Paramètres
    ----------
    path : Path
        Chemin vers le fichier JSON.

    Retour
    ------
    dict
    """
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def load_indexes() -> dict:
    """
    Charge l'ensemble des index depuis le dossier input/.

    Retour
    ------
    dict
        Dictionnaire contenant tous les index.
    """
    indexes = {}

    for index_name, filename in INDEX_FILES.items():
        file_path = INPUT_DIR / filename
        indexes[index_name] = load_json_file(file_path)

    return indexes


def tokenize(text: str) -> list[str]:
    """
    Tokenise un texte :
    - mise en minuscule
    - suppression de la ponctuation
    - découpage par espace

    Paramètres
    ----------
    text : str

    Retour
    ------
    list[str]
    """
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    tokens = text.split()
    return tokens


def normalize_tokens(tokens: list[str]) -> list[str]:
    """
    Supprime les stopwords.

    Paramètres
    ----------
    tokens : list[str]

    Retour
    ------
    list[str]
    """
    return [t for t in tokens if t not in STOPWORDS]


def expand_tokens_with_synonyms(tokens: list[str], synonyms: dict) -> set[str]:
    """
    Étend les tokens avec leurs synonymes (si existants).

    Paramètres
    ----------
    tokens : list[str]
    synonyms : dict

    Retour
    ------
    set[str]
        Ensemble de tokens enrichis.
    """
    expanded_tokens = set(tokens)

    for token in tokens:
        if token in synonyms:
            for synonym in synonyms[token]:
                expanded_tokens.add(synonym.lower())

    return expanded_tokens


# Partie 2 – Filtrage des documents

#La fonction suivante vérifie si au moins un des tokens est présent.
def documents_with_any_token(tokens: set[str], index: dict) -> set[str]:
    """
    Retourne les documents contenant au moins un token.

    Paramètres
    ----------
    tokens : set[str]
    index : dict

    Retour
    ------
    set[str]
        Ensemble d'IDs produits.
    """
    matching_docs = set()

    for token in tokens:
        if token in index:
            matching_docs.update(index[token])

    return matching_docs


#La fonction suivante v"rifie la présente de tous les tokens (qui auront été normalisés)
def documents_with_all_tokens(tokens: list[str], index: dict) -> set[str]:
    """
    Retourne les documents contenant tous les tokens (hors stopwords).

    Paramètres
    ----------
    tokens : list[str]
    index : dict

    Retour
    ------
    set[str]
    """
    doc_sets = []

    for token in tokens:
        if token in index:
            doc_sets.append(set(index[token]))
        else:
            # Si un token est absent de l'index → aucun document possible
            return set()

    # Intersection de tous les ensembles
    return set.intersection(*doc_sets) if doc_sets else set()



######## Partie 3; Ranking #########

"""
Dans cette partie, nous allons instauré un ranking simple basé sur BM25, vu en cours
ainsi qu'un score avec des signaux indépendants de la requête, :comme par exemple les avis
utilisateurs et la positions des termes dans les documents
"""


def exact_match_score(query_tokens: list[str], document_tokens: list[str]) -> float:
    """
    Retourne 1.0 si tous les tokens de la requête sont présents, sinon 0.0
    """
    return float(all(token in document_tokens for token in query_tokens))

#BM25
def bm25_score(
    query_tokens: list[str],
    document_tokens: list[str],
    index: dict,
    total_documents: int,
    k1: float = 1.5,
    b: float = 0.75
) -> float:
    """
    Calcule un score BM25 simplifié pour un document.

    Remarque
    --------
    - IDF calculé à partir de l'index inversé
    - Longueur moyenne approximée
    """

    score = 0.0
    doc_length = len(document_tokens)
    avg_doc_length = 100  # approximation volontairement simple

    term_frequencies = {}
    for token in document_tokens:
        term_frequencies[token] = term_frequencies.get(token, 0) + 1

    for token in query_tokens:
        if token not in term_frequencies:
            continue

        tf = term_frequencies[token]
        df = len(index.get(token, [])) if token in index else 1

        idf = math.log(1 + (total_documents - df + 0.5) / (df + 0.5))

        numerator = tf * (k1 + 1)
        denominator = tf + k1 * (1 - b + b * (doc_length / avg_doc_length))

        score += idf * (numerator / denominator)

    return score

#score basé sur la position 
def position_bonus(token_positions: dict) -> float:
    """
    Donne un bonus si les tokens apparaissent tôt dans le document.

    Paramètres
    ----------
    token_positions : dict
        {token: [positions]}

    Retour
    ------
    float
    """
    bonus = 0.0

    for positions in token_positions.values():
        if positions:
            first_position = min(positions)
            bonus += 1 / (1 + first_position)

    return bonus

#score basé sur les reviews
def review_score(review_data: dict) -> float:
    """
    Calcule un score simple basé sur les avis.

    Paramètres
    ----------
    review_data : dict
        {
            "average_rating": float,
            "last_rating": float,
            "total_reviews": int
        }

    Retour
    ------
    float
    """
    if not review_data:
        return 0.0

    avg_rating = review_data.get("average_rating", 0)
    last_rating = review_data.get("last_rating", 0)
    total_reviews = review_data.get("total_reviews", 0)

    return (
        0.6 * avg_rating +
        0.3 * last_rating +
        0.1 * math.log(1 + total_reviews)
    )



## POur finir, le score linéaire final

def compute_document_score(
    query_tokens: list[str],
    title_tokens: list[str],
    description_tokens: list[str],
    title_index: dict,
    description_index: dict,
    review_data: dict,
    token_positions: dict | None,
    total_documents: int
) -> float:
    """
    Combine tous les signaux dans un score final.
    """

    score = 0.0

    # 1. Match exact (boost)
    score += 5.0 * exact_match_score(query_tokens, title_tokens)

    # 2. BM25
    score += 2.0 * bm25_score(
        query_tokens,
        title_tokens,
        title_index,
        total_documents
    )

    score += 1.0 * bm25_score(
        query_tokens,
        description_tokens,
        description_index,
        total_documents
    )

    # 3. Bonus position
    if token_positions:
        score += 1.5 * position_bonus(token_positions)

    # 4. Reviews
    score += 1.0 * review_score(review_data)

    return score


##### Partie 4 : Tests et optimisation #####

"""
Cette partie permet de tester le moteur de recherche à partir de requêtes simples
et d’analyser le comportement du filtrage et du ranking.
"""

def get_test_queries() -> list[str]:
    """
    Retourne une liste de requêtes de test.
    """
    return [
        "chocolate drink",
        "energy drink",
        "gamefuel",
        "gamefuel six pack",
        "cherry chocolate",
        "sports drink"
    ]


def rank_documents(query: str, indexes: dict) -> dict:
    """
    Filtrage et ranking pour une requête donnée.
    Score basé sur :
    - fréquence des tokens dans le titre et la description
    - poids plus élevé pour le titre
    - score des avis
    """

    # Tokenisation + normalisation
    tokens = normalize_tokens(tokenize(query))

    # Expansion avec synonymes (origine)
    expanded_tokens = expand_tokens_with_synonyms(tokens, indexes.get("origin_synonyms", {}))

    # Filtrage STRICT : tous les tokens doivent être présents
    candidate_docs = documents_with_all_tokens(list(expanded_tokens), indexes["title"])

    # Si trop peu de résultats, assouplir le filtrage
    if not candidate_docs:
        candidate_docs = documents_with_any_token(expanded_tokens, indexes["title"])

    results = []

    for doc_id in candidate_docs:
        score = 0.0

        for token in tokens:
            # Fréquence dans ce document selon l'index
            title_freq = len(indexes["title"].get(token, {}).get(doc_id, []))
            desc_freq  = len(indexes["description"].get(token, {}).get(doc_id, []))

            # Ajouter au score (titre ×2)
            score += 2 * math.log(1 + title_freq) + math.log(1 + desc_freq)

        # Ajouter score des avis si présent
        review_data = indexes.get("reviews", {}).get(doc_id, {})
        score += review_score(review_data)

        results.append({
            "document_id": doc_id,
            "score": score
        })

    # Tri décroissant par score
    results.sort(key=lambda x: x["score"], reverse=True)

    return {
        "query": query,
        "total_documents": sum(len(v) for v in indexes["title"].values()),
        "filtered_documents": len(candidate_docs),
        "results": results
    }


def run_tests(indexes: dict) -> list[dict]:
    """
    Lance les tests sur l'ensemble des requêtes, uniquement avec les index.
    """
    outputs = []
    for query in get_test_queries():
        outputs.append(rank_documents(query, indexes))
    return outputs


#### MAIN ADAPTÉ

def main():
    """
    Point d'entrée du moteur de recherche pour le TP3.
    Charge les index, lance les tests et sauvegarde les résultats.
    """
    # 1. Charger les index depuis le dossier input/
    indexes = load_indexes()

    # 2. Lancer les tests (filtrage + ranking)
    results = run_tests(indexes)

    # 3. Créer le dossier de sortie s'il n'existe pas
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    # 4. Sauvegarder les résultats dans un JSON
    output_file = output_dir / "search_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("Tests terminés avec succès.")
    print(f"Résultats sauvegardés dans : {output_file}")


if __name__ == "__main__":
    main()


"""
Quelques remarques (Premier rendu de tp, 12h34)

cf output/search_results 

- Filtrage : Le filtre strict fonctionne, mais certaines requêtes
  renvoient peu ou pas de résultats (ex : "gamefuel", "sports drink").
  On pourrait assouplir le filtre pour inclure au moins un token.

- Ranking : Les scores tiennent compte des occurrences dans le titre,
  la description et les avis. Les variantes de produits sont traitées
  séparément, ce qui explique la multiplication des URLs.

- Améliorations possibles :
  * Pondérer davantage le titre vs la description vs les avis. (à faire)
  * Regrouper ou filtrer les variantes pour plus de lisibilité.
  * Utiliser TF-IDF ou un score basé sur la rareté des tokens.
  * Expansion des synonymes pour capturer plus de requêtes similaires.
"""
