# TOGO NUMERIQUE INSIGHTS

Tableau de bord décisionnel Streamlit — économie numérique et inclusion financière
au Togo. Six menus, filtres territoriaux et financiers en cascade, carte territoriale
interactive, indicateurs recalculés uniquement à partir de données réelles.

## 1. Installation

Python 3.10+ recommandé.

```bash
cd togo-numerique-insights
python3 -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Lancement

```bash
streamlit run app.py
```

L'application s'ouvre automatiquement dans le navigateur (par défaut sur
`http://localhost:8501`). Aucune clé API ni service externe n'est requis.

## 3. Ce qui a changé dans cette refonte

- **Carte territoriale réellement interactive** (`components/territorial_map.py`) :
  cliquer une région ou une commune met à jour les filtres et zoome automatiquement
  sur le territoire réel ; changer un filtre dans la barre latérale recentre la carte
  de la même façon. Présente sur les menus Vue d'ensemble, Services financiers,
  Mobile Money et Inclusion territoriale (métrique adaptée à chaque page). Les
  anciennes cartes Folium statiques (non synchronisables avec les filtres) ont été
  retirées et remplacées par ce composant unique.
- **Filtres étendus et en cascade** : Région → Préfecture → Commune → Canton, plus
  deux filtres financiers (type d'établissement, opérateur Mobile Money) qui
  recalculent en direct les KPI et graphiques concernés — par simple recombinaison
  de colonnes déjà présentes dans les tables (aucune estimation). Filtre période
  sur le menu Usage numérique, propagé à tous les graphiques marché télécom.
- **KPI n°2 de la Vue d'ensemble revu** : « Établissements financiers » (un simple
  décompte, redondant avec le KPI « Agents Mobile Money » juste à côté) a été
  remplacé par **« Points d'accès pour 10 000 hab. »** — établissements formels et
  agents Mobile Money additionnés puis rapportés à la population. C'est le même
  indicateur que la densité nationale déjà validée dans le catalogue KPI interne,
  complémentaire des autres cartes KPI plutôt que redondant avec elles.
- **Nouvel échelon canton** : 373 cantons (le tableau canton était présent dans les
  données mais pas encore exploité par le tableau de bord), avec un KPI dédié
  (cantons desservis uniquement par Mobile Money) et un détail exploitable sur le
  menu Inclusion territoriale.
- **Tableaux longs remplacés par des graphiques** : les classements par préfecture
  (accessibilité aux établissements formels, aux agents Mobile Money, communes
  MM-only, priorisation) s'affichent désormais en barres classées, avec le détail
  chiffré complet disponible à la demande dans un volet repliable.
- **Aucune mention du support d'analyse d'origine** (notebook, cellules, etc.) nulle
  part dans l'interface.

## 4. Structure du projet

```
togo-numerique-insights/
├── app.py                       # point d'entrée Streamlit
├── requirements.txt
├── .streamlit/config.toml       # thème, mode headless
├── assets/                      # logo, drapeau, favicons, bandeau, GeoJSON régions
├── styles/main.css              # charte graphique (couleurs du drapeau togolais)
├── components/
│   ├── layout.py                 # nav, bandeau, cartes, états vides, cartes reco
│   ├── kpi.py                    # cartes KPI et blocs de statistiques
│   ├── charts.py                 # graphiques Plotly (barres, donuts, courbes…)
│   └── territorial_map.py        # carte territoriale interactive (cœur de la refonte)
├── utils/
│   ├── config.py                  # palette, structure des 6 menus, libellés, filtres
│   ├── data_loader.py             # chargement et cache des tables réelles (data/*.csv)
│   ├── filters.py                 # état des filtres, barre latérale, application
│   ├── metrics.py                 # calculs par page (KPI, tableaux, séries, carte)
│   ├── formatting.py              # formatage numérique à la française
│   └── geo.py                     # géométrie régionale réelle + emprises de zoom
├── views/                       # une vue par menu (6 fichiers, voir §5)
└── data/                        # tables CSV réelles (33 tables)
```

## 5. Les 6 menus (structure imposée, respectée à l'identique)

1. **Vue d'ensemble** — synthèse nationale (KPI, carte territoriale, constats clés)
2. **Usage numérique** — série longue 2000-2024, marché télécom 2013-2019, transition technologique
3. **Accès aux services financiers** — couverture par catégorie d'établissement, disparités
4. **Mobile Money** — distribution des agents, opérateurs, concentration, pôles fragiles
5. **Inclusion territoriale** — croisement avec la population RGPH-5, jusqu'au canton
6. **Recommandations stratégiques** — catalogue chiffré, budget, scénarios, feuille de route

Aucun autre menu n'a été ajouté.

## 6. Origine des données et limites assumées

Toutes les données de `data/*.csv` proviennent de tables déjà calculées et validées
(y compris les deux tables ajoutées lors de cette refonte : présence par canton et
établissements financiers géolocalisés). L'application ne recalcule aucun agrégat
au-delà de filtrages, tris et sommes simples déjà présents dans les tables — y
compris pour les filtres « type d'établissement » et « opérateur Mobile Money »,
qui recombinent des colonnes déjà présentes (ex. `n_banque + n_mf` pour un
sous-ensemble de catégories) selon la même formule que celle déjà utilisée pour
produire les ratios d'origine.

**Géométrie** : seules les 5 régions disposent d'un contour administratif fiable
(GeoJSON). Aucune frontière de préfecture, de commune ou de canton n'existant dans
les données fournies, aucune n'a été inventée : le zoom sur ces échelons s'appuie
sur les coordonnées réelles des communes (et des établissements individuels au
niveau le plus fin), jamais sur un contour approximatif. Le canton reste donc un
filtre et un niveau de lecture tabulaire, sans représentation cartographique dédiée.

Les absences de données (ex. aucune ventilation territoriale de l'usage Internet,
aucune donnée de population au niveau canton) sont signalées explicitement dans
l'interface plutôt que comblées.

## 7. Auteur

DAYO Kokou Cyrille — Ingénieur des Travaux Informatiques, spécialisé data science
et big data.
