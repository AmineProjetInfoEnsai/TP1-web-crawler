"""
TP2 - Développement d'index
--------------------------
Ce script implémente les premières étapes de la construction d'index
pour un moteur de recherche e-commerce.

Auteur : Raffali Amine
Date : 13/01/2026
"""

##### Partie 1: Préparatifs #######
#Dans cette première partie, nous nous concentrons sur :
#- La lecture d'un fichier JSONL
-# L'extraction des informations contenues dans les URLs produits

import json
from urllib.parse import urlparse, parse_qs

def read_jsonl_file(file_path: str) -> list[dict]:
    """
    Lit un fichier JSONL et retourne la liste des documents.

    Paramètres
    ------------
    file_path: str
        Chemin vers le fichier JSONL.

    Retour
    ------------
    list[dict]
        Liste de documents (un dictionnaire par ligne)
    """

    documents = []

    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            # On ignore les lignes vides, par sécurité
            if not line:
                continue

            documents.append(json.loads(line))

    return documents

# On extrait maintenant les informations depuis l'url, plus précisément le ID produit
#et la variante

def extract_product_info_from_url(url: str) -> tuple[str | None, str | None]:
    """
    Extrait l'ID produit et la variante (si présente) depuis une URL produit.

    Paramètres
    ----------
    url : str
        URL du produit.

    Retour
    ------
    tuple[str | None, str | None]
        - ID du produit
        - Variante du produit (ou None si absente)
    """
    parsed_url = urlparse(url)

    # Exemple de path : /product/10
    path_parts = parsed_url.path.strip("/").split("/")

    product_id = None
    if len(path_parts) >= 2 and path_parts[-2] == "product":
        product_id = path_parts[-1]

    # Extraction de la variante depuis les paramètres de l'URL
    query_params = parse_qs(parsed_url.query)
    variant = query_params.get("variant", [None])[0]

    return product_id, variant


####### Parite 2: création des index inversés ########

"""
--------------------------

Dans cette partie, nous construisons des index inversés à partir
des champs textuels des documents e-commerce.

Les index créés sont :
- Un index inversé pour le titre
- Un index inversé pour la description

Chaque index associe :
    token -> liste des URLs contenant ce token

"""

import string


# On définit d'abord une liste simple de stopwords (volontairement courte pour rester simple)
# pour que nouis puissons les supprimer
STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for",
    "with", "is", "this", "that", "it"
}

# Table de suppression de la ponctuation
PUNCTUATION_TRANSLATOR = str.maketrans("", "", string.punctuation)

#La fonction suivante va d'abord preprocess un texte, c'est à dir ele nettoyer et le tokenizer par espace.
def preprocess_text(text: str) -> list[str]:
    """
    Nettoie et tokenize un texte.

    Étapes :
    - Mise en minuscule
    - Suppression de la ponctuation
    - Tokenization par espace
    - Suppression des stopwords

    Paramètres
    ----------
    text : str
        Texte à traiter.

    Retour
    ------
    list[str]
        Liste des tokens nettoyés.
    """
    if not text:
        return []

    # Passage en minuscules
    text = text.lower()

    # Suppression de la ponctuation
    text = text.translate(PUNCTUATION_TRANSLATOR)

    # Tokenization par espace
    tokens = text.split()

    # Suppression des stopwords
    cleaned_tokens = [
        token for token in tokens if token not in STOPWORDS
    ]

    return cleaned_tokens

# Enfin, la construction de l'index inversé 
# La fonction suivante peut créer un index inversé pour le titre et le document, selon ce qu'on renseigne
#dans la fonction comme field_name ("title" ou "description")


def build_inverted_index(documents: list[dict], field_name: str) -> dict:
    """
    Construit un index inversé pour un champ donné.

    Paramètres
    ----------
    documents : list[dict]
        Liste des documents e-commerce.
    field_name : str
        Nom du champ à indexer ("title" ou "description").

    Retour
    ------
    dict
        Index inversé sous la forme :
        { token : [url1, url2, ...] }
    """
    inverted_index = {}

    for doc in documents:
        url = doc.get("url")
        field_text = doc.get(field_name, "")

        if not url or not field_text:
            continue

        tokens = preprocess_text(field_text)

        for token in tokens:
            if token not in inverted_index:
                inverted_index[token] = []

            # On évite les doublons d'URL
            if url not in inverted_index[token]:
                inverted_index[token].append(url)

    return inverted_index


####### Partie 3: index des reviews ########

"""
Partie 3 : Index des reviews

Cette partie consiste à construire un index basé sur les reviews
des produits. Contrairement aux index inversés précédents, cet index
ne sert pas à la recherche textuelle mais au classement (ranking)
des documents.

Pour chaque produit, nous stockons :
- Le nombre total de reviews
- La note moyenne
- La dernière note

"""


def build_reviews_index(documents: list[dict]) -> dict:
    """
    Construit un index des reviews pour les produits.

    Paramètres
    ----------
    documents : list[dict]
        Liste des documents e-commerce.

    Retour
    ------
    dict
        Index des reviews sous la forme :
        {
            url : {
                "review_count": int,
                "average_rating": float,
                "last_rating": int | None
            }
        }
    """
    reviews_index = {}

    for doc in documents:
        url = doc.get("url")
        reviews = doc.get("reviews", [])

        if not url or not reviews:
            continue

        ratings = []

        # Extraction des notes depuis les reviews
        for review in reviews:
            rating = review.get("rating")
            if rating is not None:
                ratings.append(rating)

        if not ratings:
            continue

        review_count = len(ratings)
        average_rating = sum(ratings) / review_count
        last_rating = ratings[-1]

        reviews_index[url] = {
            "review_count": review_count,
            "average_rating": round(average_rating, 2),
            "last_rating": last_rating
        }

    return reviews_index


####### Partie 4: index des features #######

"""
Partie 4 : Index des features

Dans cette partie, nous construisons des index inversés pour les
features des produits (marque, origine, etc.).

Chaque feature est traitée comme un champ textuel simple.
Pour chaque valeur de feature, nous stockons la liste des IDs
des produits correspondants.

"""


def build_features_indexes(documents: list[dict]) -> dict:
    """
    Construit des index inversés pour les features des produits.

    Paramètres
    ----------
    documents : list[dict]
        Liste des documents e-commerce.

    Retour
    ------
    dict
        Index des features sous la forme :
        {
            "brand": {
                "nike": ["10", "25", ...],
                "adidas": ["12", ...]
            },
            "origin": {
                "france": ["10", ...]
            }
        }
    """
    features_indexes = {}

    for doc in documents:
        product_id = doc.get("id") 
        features = doc.get("product_features")

        if not product_id or not features:
            continue

        # Parcours de chaque feature (marque, origine, etc.)
        for feature_name, feature_value in features.items():

            if not feature_value:
                continue

            # Initialisation de l'index pour cette feature
            if feature_name not in features_indexes:
                features_indexes[feature_name] = {}

            # Normalisation simple de la valeur (minuscule)
            feature_value_normalized = str(feature_value).lower()

            if feature_value_normalized not in features_indexes[feature_name]:
                features_indexes[feature_name][feature_value_normalized] = []

            # On stocke uniquement les IDs produits
            if product_id not in features_indexes[feature_name][feature_value_normalized]:
                features_indexes[feature_name][feature_value_normalized].append(product_id)

    return features_indexes

###### Partie 5 et 6: Index de position et sauvegarde de tous les index #####

"""
TP2 - Développement d'index
--------------------------
Parties 5 et 6 :
- Index de position (titre et description)
- Sauvegarde des index dans des fichiers JSON

"""
from collections import defaultdict


# Index inversé de position 

def build_position_index(documents: list[dict], field_name: str) -> dict:
    """
    Construit un index inversé de positions pour un champ textuel
    (titre ou description).

    Structure :
    {
        token: {
            doc_id: [pos1, pos2, ...]
        }
    }
    """
    position_index = defaultdict(lambda: defaultdict(list))

    for doc in documents:
        doc_id = doc.get("id")
        field_text = doc.get(field_name)

        if not doc_id or not field_text:
            continue

        tokens = preprocess_text(field_text)

        for position, token in enumerate(tokens):
            position_index[token][doc_id].append(position)

    return position_index


##########################
# Sauvegarde des index   #
##########################

def save_index(index: dict, filename: str):
    """
    Sauvegarde un index dans un fichier JSON.
    """
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)






###### Et pour finir, le main ######

def main():
    """
    Charge les documents, construit tous les index
    et les sauvegarde dans des fichiers JSON.
    """
    # Chargement des documents (JSONL)
    documents = []
    with open("products.jsonl", "r", encoding="utf-8") as file:
        for line in file:
            documents.append(json.loads(line))

    # Index texte classiques
    title_index = build_inverted_index(documents, "title")
    description_index = build_inverted_index(documents, "description")

    # Index de position
    title_position_index = build_position_index(documents, "title")
    description_position_index = build_position_index(documents, "description")

    # Index reviews
    reviews_index = build_reviews_index(documents)

    # Index features
    features_indexes = build_features_indexes(documents)
    brand_index = features_indexes.get("brand", {})
    origin_index = features_indexes.get("origin", {})

    # Sauvegarde des index
    save_index(title_index, "title_index.json")
    save_index(description_index, "description_index.json")
    save_index(title_position_index, "title_position_index.json")
    save_index(description_position_index, "description_position_index.json")
    save_index(reviews_index, "reviews_index.json")
    save_index(brand_index, "brand_index.json")
    save_index(origin_index, "origin_index.json")

    print("Tous les index ont été construits et sauvegardés avec succès.")


if __name__ == "__main__":
    main()

