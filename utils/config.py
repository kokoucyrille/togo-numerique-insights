"""Configuration centrale de TOGO NUMERIQUE INSIGHTS.

Charte graphique, schéma des données réelles et libellés d'interface.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT / "assets"
STYLES_DIR = ROOT / "styles"
DATA_DIR = ROOT / "data"

FAVICON_FILES = {"arms": "armoiries_togo.svg", "logo": "favicon.png"}
BANNER_STEM = "banner_lome"
BANNER_FOCUS = "center 60%"
BANNER_MAX_WIDTH = 2400

APP_TITLE = "TOGO NUMERIQUE INSIGHTS"
APP_SUBTITLE = "Économie numérique et inclusion financière — intelligence territoriale du Togo."
MOTTO = "Travail • Liberté • Patrie"
SLOGAN_LINES = ("Le Togo,", "plus connecté,", "plus inclusif !")

# --------------------------------------------------------------------------- #
# Palette (drapeau togolais + tons institutionnels)
# --------------------------------------------------------------------------- #
COLORS = {
    "green": "#006A4E",
    "green_dark": "#02403A",
    "emerald": "#0E9F6E",
    "ok": "#0A7A50",
    "part": "#3D6A9C",
    "yellow": "#FFCE00",
    "red": "#D21034",
    "navy": "#0B1F33",
    "slate": "#334155",
    "muted": "#64748B",
    "grid": "#E6EBF1",
    "bg": "#F5F7FA",
    "card": "#FFFFFF",
    "empty": "#E9EEF3",
}

REGION_ORDER = ["Grand Lomé", "Maritime intérieur", "Plateaux", "Centrale", "Kara", "Savanes"]
REGION_COLORS = {
    "Grand Lomé": "#064E3B",
    "Maritime intérieur": "#0F8F5F",
    "Plateaux": "#5FAF3D",
    "Centrale": "#B5CC3A",
    "Kara": "#F2B01E",
    "Savanes": "#F28C28",
}
# Le GeoJSON régional (limites administratives) porte le nom "Maritime" pour le
# polygone entier ; les tables distinguent "Grand Lomé" (point) de son reste,
# nommé "Maritime intérieur". Alias utilisé uniquement pour l'appariement carte ↔ données.
REGION_GEO_ALIAS = {"Maritime": "Maritime intérieur"}
FALLBACK_COLORS = ["#0F8F5F", "#5FAF3D", "#B5CC3A", "#F2B01E", "#F28C28", "#2F80ED"]
SECTOR_COLORS = ["#0B6B4F", "#FFCE00", "#2F80ED", "#7B3FBF", "#F2542D"]
EXTRA_COLORS = ["#0F8F5F", "#F28C28", "#5FAF3D", "#06B6D4", "#E11D48", "#8E9AAF"]
OTHER_COLOR = "#A0A7B0"
BAR_GRADIENT = ["#0B6B4F", "#4DA35A", "#9BC53D", "#D4D23A", "#FFCE00"]

# Point (lat, lon) pour Grand Lomé, absente du GeoJSON polygonal (incluse dans Maritime).
GEO_POINTS = {"Grand Lomé": (6.1725, 1.2314)}

# Comparaison de 2 valeurs d'un même champ (ex. 2 régions) : couleurs fixes A / B.
MAX_COMPARE = 2
COMPARE_COLORS = ["#0B6B4F", "#F28C28"]

# Opérateurs
OPERATEUR_COLORS = {
    "Togocom": "#0B6B4F",
    "Moov": "#F2B01E",
    "Moov + Togocom": "#2F80ED",
    "Togocom uniquement": "#0B6B4F",
    "Moov uniquement": "#F2B01E",
    "Non spécifié": "#A0A7B0",
}
# Filtre « opérateur GSM » (page Usage numérique) : libellé -> colonne de part de marché déjà
# présente dans marche_gsm_2013_2019, et préfixe des colonnes par opérateur de la table
# transition_technologique_mobile.
GSM_OPERATEURS = ("Togocom", "Moov")
GSM_SHARE_COLS = {"Togocom": "Part Togocom (%)", "Moov": "Part Moov (%)"}

# Filtre « opérateur Mobile Money » : libellé -> colonne agrégée déjà présente dans
# table_analytique_regions / _prefectures / _communes (comptage réel, aucun recalcul).
MM_OPERATEUR_COLS = {
    "Togocom uniquement": "n_mm_togocom",
    "Moov uniquement": "n_mm_moov",
    "Moov + Togocom": "n_mm_deux_op",
    "Non spécifié": "n_mm_nsp",
}

# Catégories d'établissements financiers formels.
ETAB_CATEGORIES = ["Banque", "Micro-Finance", "Assurance", "Mutuelle"]
ETAB_CATEGORY_COLORS = dict(zip(ETAB_CATEGORIES, SECTOR_COLORS))
# Filtre « type d'établissement » : libellé -> colonne agrégée déjà présente dans
# les mêmes tables analytiques (n_banque, n_mf, n_assurance, n_mutuelle).
ETAB_CATEGORY_COLS = {
    "Banque": "n_banque", "Micro-Finance": "n_mf",
    "Assurance": "n_assurance", "Mutuelle": "n_mutuelle",
}

# Paliers de priorisation (P1 = priorité la plus forte)
PALIER_COLORS = {"P1": "#D21034", "P2": "#F28C28", "P3": "#F2B01E", "P4": "#94A3B8"}
PALIER_LABELS = {
    "P1": "P1 — priorité la plus forte",
    "P2": "P2 — priorité forte",
    "P3": "P3 — priorité modérée",
    "P4": "P4 — priorité faible",
}
# Méthodologie exacte (cf. catalogue KPI K5.1/K5.2 et vérification empirique sur
# la table analytique des communes) : IB = indice de besoin composite (35 % déficit
# d'accès, 25 % population, 20 % absence d'établissement, 20 % isolement) ; LN =
# levier numérique. Paliers définis par quartile de l'IB nationale, P1/P2 étant
# départagés par le levier numérique.
PALIER_DETAILS = {
    "P1": "Indice de besoin (IB) dans le quart supérieur (≥ 3ᵉ quartile national) et levier "
          "numérique déjà présent (≥ médiane) : intervention rapide, effet démultiplicateur attendu.",
    "P2": "Indice de besoin (IB) dans le quart supérieur (≥ 3ᵉ quartile national) mais levier "
          "numérique faible (< médiane) : renforcement structurel nécessaire avant tout effet démultiplicateur.",
    "P3": "Indice de besoin (IB) intermédiaire : entre la médiane et le 3ᵉ quartile nationaux.",
    "P4": "Indice de besoin (IB) sous la médiane nationale : priorité la plus faible.",
}

# --------------------------------------------------------------------------- #
# Menus — structure stricte imposée (6 menus, aucun autre)
# --------------------------------------------------------------------------- #
PAGES = [
    ("vue_ensemble", "Vue d'ensemble", "home"),
    ("usage_numerique", "Usage numérique", "wifi"),
    ("services_financiers", "Services financiers", "account_balance"),
    ("mobile_money", "Mobile Money", "smartphone"),
    ("inclusion_territoriale", "Inclusion territoriale", "public"),
    ("recommandations", "Recommandations", "flag"),
]
PAGE_LABELS = {k: label for k, label, _ in PAGES}

DIM_LABELS = {
    "region": "Région",
    "prefecture": "Préfecture",
    "commune": "Commune",
    "canton": "Canton",
    "palier": "Palier de priorité",
    "axe": "Axe de recommandation",
    "etab_categorie": "Type d'établissement",
    "mm_operateur": "Opérateur Mobile Money",
    "gsm_operateur": "Opérateur GSM",
}
ALL_LABELS = {
    "region": "Toutes les régions",
    "prefecture": "Toutes les préfectures",
    "commune": "Toutes les communes",
    "canton": "Tous les cantons",
    "palier": "Tous les paliers",
    "axe": "Tous les axes",
    "etab_categorie": "Tous les types",
    "mm_operateur": "Tous les opérateurs",
    "gsm_operateur": "Tous les opérateurs",
}

# Bornes de la période d'usage Internet (série longue, 2000-2024)
USAGE_YEAR_MIN, USAGE_YEAR_MAX = 2000, 2024
# Bornes de la période marché télécom / transition technologique (2013-2019)
MARCHE_YEAR_MIN, MARCHE_YEAR_MAX = 2013, 2019

# Année de référence du recensement utilisé pour la population (RGPH-5)
RGPH_YEAR = 2022

SOURCE_NOTE = (
    "Sources : Banque mondiale (IT.NET.USER.ZS), données ouvertes télécoms et établissements "
    "financiers du Togo, agents Mobile Money, RGPH-5 (2022). Indicateurs calculés à partir de "
    "ces sources ; niveaux région / préfecture / commune / canton selon le découpage administratif "
    "officiel."
)

# --------------------------------------------------------------------------- #
# Carte territoriale interactive — marges de recentrage (degrés, ≈ WGS84)
# --------------------------------------------------------------------------- #
MAP_PAD_NATIONAL = 0.30
MAP_PAD_REGION = 0.22
MAP_PAD_PREFECTURE = 0.09
MAP_PAD_COMMUNE = 0.045
MAP_MIN_SPAN = 0.10
