# TP2 – Développement d’index pour un moteur de recherche e-commerce

## Objectif du TP

L’objectif de ce TP est de construire différents types d’index à partir d’un jeu de données e-commerce (au format JSONL), afin de préparer la mise en place d’un moteur de recherche.

À partir des documents fournis, nous devons :
- analyser les URLs des produits,
- indexer les champs textuels (titre et description),
- exploiter les avis clients (reviews) pour le ranking,
- indexer certaines caractéristiques produits (features),
- sauvegarder l’ensemble des index dans des fichiers JSON.

---

## Données d’entrée

Le fichier d’entrée est un fichier **JSONL** (`products.jsonl`) contenant **un document par ligne**.

Chaque document peut contenir les champs suivants :
- `url`
- `title`
- `description`
- `product_features`
- `product_reviews`
- `links`

Certaines URLs correspondent à des pages produit (`/product/<id>`), d’autres à des pages de navigation (`/products`, pagination, etc.).

---

## Traitement des URLs

Pour chaque document, nous extrayons :
- **l’identifiant du produit** (`product_id`) à partir du chemin de l’URL (`/product/<id>`),
- **la variante** du produit si elle est présente (`?variant=...`).

Même si ces informations ne donnent pas lieu à un index dédié, cette étape permet de montrer que les URLs sont correctement analysées, comme demandé dans la consigne.

---

## Index produits

Le script génère **exactement 5 index**, chacun sauvegardé dans un fichier JSON distinct.

### 1. `title_index.json` – Index positionnel du titre



**Structure :**


- Le texte du titre est tokenisé par espace.

- Les tokens sont normalisés (minuscules, suppression de la ponctuation).

- Les stopwords sont supprimés.

- Les positions correspondent à l’ordre des tokens après nettoyage.

- Cet index permettra plus tard de faire des recherches plus précises (ex : recherche de phrase).

### 2. description_index.json – Index positionnel de la description

Structure identique à celle du titre :

{
  "token": {
    "url": [positions]
  }
}

La différence est simplement le champ indexé (description au lieu de title).

### 3. brand_index.json – Index inversé sur la marque

Structure :

{
  "brand_name": ["url_1", "url_2"]
}

    La feature brand est traitée comme un champ textuel simple.

    La valeur est normalisée (minuscules, suppression des espaces).

    Chaque clé correspond à une marque, associée à la liste des URLs des produits correspondants.

### 4.  origin_index.json – Index inversé sur l’origine du produit

Structure identique à l’index de marque :

{
  "country": ["url_1", "url_2"]
}

    L’origine est extraite depuis la feature "made in".

    Elle est normalisée de la même manière que la marque.

### 5. reviews_index.json – Index des reviews (non inversé)

Structure :

{
  "url": {
    "review_count": int,
    "average_rating": float | null,
    "last_rating": float | null
  }
}

Cet index ne sert pas à la recherche textuelle, mais au classement des résultats (ranking).

Pour chaque produit, on stocke :

    le nombre total de reviews,

    la note moyenne,

    la dernière note disponible.

## Choix techniques

1) Tokenisation

    Tokenisation simple par espace.

    Suppression de la ponctuation.

    Suppression d’une liste volontairement courte de stopwords (français + anglais).

    Aucune lemmatisation ni stemming, afin de rester simple et lisible.

2) Index positionnel

    Les positions sont calculées après suppression des stopwords.

    Cela simplifie la logique et reste cohérent pour un moteur de recherche basique.

3) Reviews

    Les reviews sont traitées séparément.

    L’index n’est pas inversé, car il est destiné au ranking et non à la recherche.

4) Features

    Seules les features demandées (marque et origine) sont indexées.

    Le traitement est volontairement simple pour rester conforme à la consigne.

## Fonctionnalités supplémentaires

En plus des exigences minimales :

    gestion des lignes JSON invalides avec messages d’erreur explicites,

    normalisation systématique des champs textuels,

    déduplication implicite via les URLs,

    structure des index directement exploitable pour un moteur de recherche.

## Comment lancer le script

    Placer le fichier products.jsonl dans le même dossier que le script python

    Lancer le script en exécutant la commande

python3 tp2_indexing.py

Les fichiers d’index sont générés dans le dossier out_indexes/ pour au final obtenir quelque chose semblable à cette arborescence.

out_indexes/
├── title_index.json
├── description_index.json
├── brand_index.json
├── origin_index.json
└── reviews_index.json

# Conclusion

Ce TP met en place les bases nécessaires à la construction d’un moteur de recherche e-commerce :

    indexation textuelle,

    indexation positionnelle,

    exploitation des avis clients,

    structuration claire des données.

Le code est volontairement simple, lisible et modulaire, afin de pouvoir être facilement étendu lors des prochaines étapes du projet.