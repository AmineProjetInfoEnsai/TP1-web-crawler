"""
TP1 - Développement d'un Web Crawler
-----------------------------------
Ce script implémente les bases d’un crawler web en Python.
L'objectif est de créer un crawler en python qui explor les pages d'un site web en priorisant certaines pages.

Auteur : Raffali Amine
Date : 12/01/2026
"""

#Liste des librairies utiles, les plus importants pour le TP étant BeautifulSoup et urllib
from bs4 import BeautifulSoup
import heapq
import time
import urllib.request
import urllib.robotparser
from urllib.parse import urlparse, urljoin
import json
import argparse


########### Partie 1: Configuration initiale #############

#Pour commenceer, nous allons ajuster la politesse pour la suite de notre TP
#En fixant les variables suivantes:

#  1) Nombre maximum de pages à crawler, nous fixons à 50 dans le cadre du TP.
MAX_PAGES_TO_CRAWL = 50

# 2) Temps d'attente entre deux requêtes HTTP
REQUEST_DELAY_SECONDS = 1.0

# 3) User-Agent explicite pour identifier notre crawler
USER_AGENT = "TP-WebCrawler/1.0 (Student Project)"

# La fonction suivante applique un délai entre deux requêtes HTTP, afin de respecter au mieux les règles de po
def apply_politeness_delay():
    """
    Applique un délai entre deux requêtes HTTP afin de respecter
    les règles de politesse envers le serveur distant.
    """
    time.sleep(REQUEST_DELAY_SECONDS)


######### Fonctions de base pour les requêtes HTPP #########
def fetch_url_content(url: str) -> str | None:
    """
    Envoie une requête HTTP GET vers une URL donnée.

    Paramètres
    ----------
    url : str
        L'URL de la page à récupérer.

    Retour
    ------
    str | None
        Le contenu HTML de la page si la requête réussit,
        None en cas d'erreur réseau ou HTTP.
    """
    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT}
        )

        with urllib.request.urlopen(request) as response:
            html_bytes = response.read()
            return html_bytes.decode("utf-8", errors="ignore")

    except Exception as error:
        print(f"[ERREUR] Impossible d'accéder à {url} : {error}")
        return None

# Nous créeons ici une fonction qui permet de vérifier si l'url peut être crawlée ou pas à l'aide des fichiers
# robots.txt des sites.

def is_url_allowed_by_robots(url: str, user_agent: str = USER_AGENT) -> bool:
    """
    Vérifie si une URL peut être crawlée selon le fichier robots.txt du site.

    Paramètres
    ----------
    url : str
        L'URL à vérifier.
    user_agent : str
        Le User-Agent utilisé par le crawler.

    Retour
    ------
    bool
        True si l'accès est autorisé, False sinon.
    """
    parsed_url = urlparse(url)
    robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"

    robot_parser = urllib.robotparser.RobotFileParser()
    robot_parser.set_url(robots_url)

    try:
        robot_parser.read()
        return robot_parser.can_fetch(user_agent, url)
    except Exception:
        return False



### Partie 2: Extraction du contenu ####

#Pour extraire le contenu, nous allons procéder en différentes étapes

#Tout d'abord, il faut s'assurer que le crawler a le droit de parser une page
# pour cela, on utilise la fonction is_url_allowed_by_robots dans une méthode.
def can_parse_page(url: str) -> bool:
    """
    Vérifie si le crawler est autorisé à accéder ET parser une page web.


    Paramètres
    ----------
    url : str
        L'URL de la page à analyser.

    Retour
    ------
    bool
        True si le crawler est autorisé à parser la page, False sinon.
    """
    return is_url_allowed_by_robots(url)

#S'il est possible de parser une page, alors nous la parsons avec la fonction suivante.
# nous nous aiderons de BeautifulSoup.
def parse_html_content(html_content: str) -> BeautifulSoup:
    """
    Parse le contenu HTML brut à l'aide de BeautifulSoup.

    Paramètres
    ----------
    html_content : str
        Le contenu HTML brut d'une page web.

    Retour
    ------
    BeautifulSoup
        Objet BeautifulSoup représentant la structure HTML de la page.
    """
    return BeautifulSoup(html_content, "html.parser")

#Maintenant que la page est parsé, on va extraire le titre et le premier paragraphe de la page
#on utilisera principaleemnt les méthodes get et find.
def extract_title_and_first_paragraph(soup: BeautifulSoup) -> tuple[str | None, str | None]:
    """
    Extrait le titre de la page et le premier paragraphe du contenu.

    Paramètres
    ----------
    soup : BeautifulSoup
        Objet BeautifulSoup représentant le HTML parsé.

    Retour
    ------
    tuple[str | None, str | None]
        - Le titre de la page
        - Le texte du premier paragraphe
        Retourne None si l'élément est absent.
    """
    title_text = None
    first_paragraph_text = None

    if soup.title:
        title_text = soup.title.get_text(strip=True)

    first_paragraph = soup.find("p")
    if first_paragraph:
        first_paragraph_text = first_paragraph.get_text(strip=True)

    return title_text, first_paragraph_text

#on extrait également les liens.
def extract_internal_links(
    soup: BeautifulSoup,
    base_url: str
) -> list[dict]:
    """
    Extrait les liens internes présents dans le body de la page HTML.


    Paramètres
    ----------
    soup : BeautifulSoup
        Objet BeautifulSoup représentant le HTML parsé.
    base_url : str
        URL de la page actuellement analysée (page source).

    Retour
    ------
    list[dict]
        Liste de dictionnaires contenant :
        - 'url' : lien interne trouvé
        - 'source_page' : URL d'origine du lien
    """
    internal_links = []

    parsed_base_url = urlparse(base_url)
    base_domain = parsed_base_url.netloc

    for anchor in soup.find_all("a", href=True):
        raw_href = anchor["href"]
        absolute_url = urljoin(base_url, raw_href)
        parsed_link = urlparse(absolute_url)

        # On ne garde que les liens internes
        if parsed_link.netloc == base_domain:
            internal_links.append({
                "url": absolute_url,
                "source_page": base_url
            })

    return internal_links


######### Partie 3: Logique de crawling ##########

#On implémente un système de priorité, en fonction de la présence du token "product". on teste simplement
#si le token est dans l'url.
def compute_url_priority(url: str) -> int:
    """
    Calcule la priorité d'une URL en fonction de son contenu.

    Les URLs contenant le token 'product' sont prioritaires.

    Paramètres
    ----------
    url : str
        L'URL à analyser.

    Retour
    ------
    int
        0 si l'URL est prioritaire (contient 'product'),
        1 sinon.
    """
    return 0 if "product" in url.lower() else 1

def crawl_website(start_url: str) -> list[dict]:
    """
    Lance le processus de crawling à partir d'une URL initiale.

    Le crawler :
    - explore les pages internes
    - priorise les URLs contenant le token 'product'
    - s'arrête après avoir visité MAX_PAGES_TO_CRAWL pages

    Paramètres
    ----------
    start_url : str
        URL de départ du crawl.

    Retour
    ------
    list[dict]
        Liste des données extraites pour chaque page visitée.
    """
    visited_urls = set()
    urls_to_visit = []
    crawled_pages_data = []

    # Initialisation de la file de priorité; on utilise la fonction plus haut.
    start_priority = compute_url_priority(start_url)
    heapq.heappush(urls_to_visit, (start_priority, start_url))

    while urls_to_visit and len(visited_urls) < MAX_PAGES_TO_CRAWL:
        current_priority, current_url = heapq.heappop(urls_to_visit)

        if current_url in visited_urls:
            continue

        print(f"[CRAWL] {current_url} (priorité {current_priority})")

        if not can_parse_page(current_url):
            print(f"[SKIP] Accès interdit par robots.txt : {current_url}")
            continue

        apply_politeness_delay()

        html_content = fetch_url_content(current_url)
        if html_content is None:
            continue

        soup = parse_html_content(html_content)

        title, first_paragraph = extract_title_and_first_paragraph(soup)
        links = extract_internal_links(soup, current_url)

        # Marquer la page comme visitée
        visited_urls.add(current_url)

        # Stocker les données extraites
        crawled_pages_data.append({
            "url": current_url,
            "title": title,
            "first_paragraph": first_paragraph,
            "outgoing_links": links
        })

        # Ajouter les nouveaux liens à la file d'attente
        for link in links:
            link_url = link["url"]

            if link_url not in visited_urls:
                priority = compute_url_priority(link_url)
                heapq.heappush(urls_to_visit, (priority, link_url))

    return crawled_pages_data


####### Partie 4: Stockage des résulats#######

#Fonction pour sauvegarder les résultats dans un fichier json, nous importons json plus haut.

def save_crawled_data_to_json(crawled_data: list[dict], filename: str = "crawled_data.json"):
    """
    Sauvegarde les données crawlées dans un fichier JSON.

    Paramètres
    ----------
    crawled_data : list[dict]
        Liste des pages et des informations extraites par le crawler.
    filename : str
        Nom du fichier JSON de sortie.

    Retour
    ------
    None
    """
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(crawled_data, f, ensure_ascii=False, indent=4)
        print(f"[INFO] Données sauvegardées dans {filename}")
    except Exception as e:
        print(f"[ERREUR] Impossible de sauvegarder le fichier : {e}")


####### Partie finale: le test et (éventuellement) des optimisations #######
# Rappelons qu'il faut crawler un site web qui contient des pages produits. C'est une première étape avant une indexation
#demain

def main():
    """
    Point d'entrée principal du crawler.
    Prend en entrée :
    - URL de départ
    - Nombre maximum de pages à visiter (j'ai pris le choix de tester avec 5 dans mon environnement local)
    Produit un fichier JSON en sortie.
    """
    parser = argparse.ArgumentParser(description="Web Crawler TP1")
    parser.add_argument(
        "start_url", type=str,
        help="URL de départ pour le crawl"
    )
    parser.add_argument(
        "max_pages", type=int,
        help="Nombre maximum de pages à visiter"
    )
    args = parser.parse_args()

    # Mise à jour de la constante globale pour ce crawl
    global MAX_PAGES_TO_CRAWL
    MAX_PAGES_TO_CRAWL = args.max_pages

    crawled_data = crawl_website(args.start_url)

    print(f"{len(crawled_data)} pages crawlées.")
    save_crawled_data_to_json(crawled_data)

if __name__ == "__main__":
    main()
