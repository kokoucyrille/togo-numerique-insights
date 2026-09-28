"""Calculs alimentant chaque page : rien n'est estimé ni recalculé au-delà de ce que
contiennent déjà les tables analytiques — seuls des filtrages, tris et petits
agrégats (sommes, moyennes pondérées, divisions déjà documentées dans les tables)
sont effectués ici.
"""
from __future__ import annotations

import pandas as pd

from . import config as C
from .data_loader import Datasets
from .filters import (
    Filters, apply_axe, apply_canton, apply_etab_categorie, apply_geo, apply_palier,
    apply_years, with_effective_counts,
)

REGION_COL = "region_a"


def _lv(df: pd.DataFrame, label_col: str, value_col: str) -> pd.DataFrame:
    """Normalise en colonnes (label, valeur) pour les composants de graphique génériques."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["label", "valeur"])
    out = df[[label_col, value_col]].rename(columns={label_col: "label", value_col: "valeur"}).copy()
    order = {r: i for i, r in enumerate(C.REGION_ORDER)}
    if label_col == REGION_COL:
        out["_o"] = out["label"].map(lambda r: order.get(r, 99))
        out = out.sort_values("_o").drop(columns="_o")
    else:
        out = out.sort_values("valeur", ascending=False)
    return out.reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Vue d'ensemble
# --------------------------------------------------------------------------- #
def usage_last(ds: Datasets) -> tuple[int | None, float | None, float | None]:
    """(année, valeur %, gain vs année précédente en pp) — dernière donnée d'usage Internet."""
    u = ds.get("internet_usage_variations")
    if u.empty:
        return None, None, None
    row = u.sort_values("année").iloc[-1]
    return int(row["année"]), float(row["usage Internet (%)"]), (
        float(row["variation (pp)"]) if pd.notna(row["variation (pp)"]) else None
    )


def rupture_info(ds: Datasets) -> tuple[int | None, float | None, float | None]:
    """(année de rupture, rythme avant en pp/an, rythme après en pp/an)."""
    p = ds.get("internet_usage_periodes")
    if p.empty or len(p) < 2:
        return None, None, None
    before, after = p.iloc[0], p.iloc[1]
    year = str(after["période"]).split("–")[0].split("-")[0].strip()
    try:
        year = int(year)
    except ValueError:
        year = None
    return year, float(before["rythme (pp/an)"]), float(after["rythme (pp/an)"])


def rupture_bar_data(ds: Datasets) -> pd.DataFrame:
    """Rythme de progression (pp/an) avant / après la rupture de tendance, prêt pour
    un graphique en barres (remplace le tableau brut à deux lignes)."""
    p = ds.get("internet_usage_periodes")
    if p.empty:
        return pd.DataFrame(columns=["label", "valeur"])
    out = p[["période", "rythme (pp/an)"]].rename(columns={"période": "label", "rythme (pp/an)": "valeur"})
    return out


def national_totals(ds: Datasets) -> dict:
    r = ds.get("table_analytique_regions")
    c = ds.get("table_analytique_communes")
    out = {
        "population": float(r["population"].sum()) if not r.empty else None,
        "n_formel": float(r["n_formel"].sum()) if not r.empty else None,
        "n_mm": float(r["n_mm"].sum()) if not r.empty else None,
        "n_points": float(r["n_points"].sum()) if not r.empty else None,
        "mm_only_communes": int(c["mm_only"].sum()) if not c.empty else None,
        "mm_only_population": float(c.loc[c["mm_only"] == True, "population"].sum()) if not c.empty else None,
    }
    if out["population"] and out["n_points"] is not None:
        out["pts_10k"] = out["n_points"] / out["population"] * 10_000
    if not c.empty and "palier" in c.columns:
        p12 = c[c["palier"].isin(["P1", "P2"])]
        out["p1p2_communes"] = int(len(p12))
        out["p1p2_population"] = float(p12["population"].sum())
    return out


def hhi_last(ds: Datasets) -> tuple[int | None, float | None]:
    m = ds.get("marche_gsm_2013_2019")
    if m.empty:
        return None, None
    row = m.sort_values("annee").iloc[-1]
    return int(row["annee"]), float(row["HHI"])


def overview_kpis(ds: Datasets) -> list:
    from components.kpi import Kpi
    year, usage_val, usage_gain = usage_last(ds)
    tot = national_totals(ds)
    hhi_year, hhi_val = hhi_last(ds)
    kpis = [
        Kpi("usage", "Usage Internet", "wifi", "green", usage_val, "pct", usage_gain, "pts",
           f"vs. {year - 1}" if year else None,
           f"Individus ayant utilisé Internet au cours des 3 derniers mois, {year}. Source : Banque mondiale."),
        Kpi("acces10k", "Points d'accès pour 10 000 hab.", "grid_view", "blue", tot.get("pts_10k"), "dec",
           definition=(f"Établissements financiers formels ({tot['n_formel']:,.0f}) et agents Mobile "
                       f"Money ({tot['n_mm']:,.0f}) additionnés, rapportés à la population pour 10 000 "
                       "habitants — densité nationale de l'accès aux services financiers.").replace(",", " ")),
        Kpi("mm", "Agents Mobile Money", "smartphone", "yellow", tot["n_mm"], "int",
           definition="Agents Mobile Money recensés, tous opérateurs confondus."),
        Kpi("mmonly", "Communes MM-only", "location_off", "red", tot.get("mm_only_communes"), "int",
           delta_label=f"{tot['mm_only_population']:,.0f} hab.".replace(",", " ") if tot.get("mm_only_population") else None,
           definition="Communes sans aucun établissement financier formel, desservies uniquement par des agents Mobile Money."),
        Kpi("prio", "Population en zone prioritaire", "priority_high", "purple", tot.get("p1p2_population"),
           "int", delta_label=f"{tot.get('p1p2_communes', 0)} communes (P1+P2)" if tot.get("p1p2_communes") else None,
           definition="Population des communes classées palier P1 ou P2 (déficit d'accès financier le plus marqué)."),
        Kpi("hhi", "Indice HHI (marché télécom)", "signal_cellular_alt", "teal", hhi_val, "int",
           delta_label=f"{hhi_year}" if hhi_year else None,
           definition="Indice de concentration Herfindahl-Hirschman du marché GSM (duopole : seuil de forte concentration = 2 500)."),
    ]
    return kpis


def regions_map_table(ds: Datasets, f: Filters, value_col: str = "n_points") -> pd.DataFrame:
    df = apply_geo(ds.get("table_analytique_regions"), f)
    return _lv(df, REGION_COL, value_col)


def accessibility_bar(ds: Datasets, f: Filters, value_col: str = "hab_par_formel") -> pd.DataFrame:
    df = apply_geo(ds.get("table_analytique_regions"), f)
    return _lv(df, REGION_COL, value_col)


def accessibility_details(ds: Datasets, f: Filters) -> pd.DataFrame:
    """Table régionale (index = région) qui détaille le graphique « Habitants par établissement
    formel » : population, établissements, densité, parts, représentation et distance médiane."""
    df = apply_geo(ds.get("table_analytique_regions"), f)
    if df.empty:
        return df
    return df.set_index(REGION_COL)


# --------------------------------------------------------------------------- #
# Carte territoriale interactive (components/territorial_map.py)
# --------------------------------------------------------------------------- #
def region_values(ds: Datasets, f: Filters, value_col: str = "n_points") -> pd.DataFrame:
    """Une ligne par région, colonnes déjà présentes recombinées selon les filtres
    finance actifs (catégorie d'établissement / opérateur) — aucune estimation."""
    df = with_effective_counts(ds.get("table_analytique_regions"), f)
    return _lv(df, REGION_COL, value_col)


def commune_points(ds: Datasets, f: Filters, value_col: str = "n_points") -> pd.DataFrame:
    """Une ligne par commune avec ses coordonnées réelles (lon_c/lat_c), pour les
    bulles de la carte territoriale. `dans_perimetre` indique si la commune
    correspond aux filtres territoriaux actifs (région/préfecture/commune/canton)."""
    df = ds.get("table_analytique_communes")
    if df.empty:
        return df
    df = with_effective_counts(df, f)
    scoped = apply_geo(df, f)
    if f.canton:
        cantons = ds.get("table_analytique_cantons_presence")
        keys = cantons.loc[cantons["canton_norm"].isin(f.canton), "cle_commune"].unique()
        scoped = scoped[scoped["cle_commune"].isin(keys)]
    keep = ["commune", "cle_commune", "prefecture", REGION_COL, "lon_c", "lat_c", "population",
           "palier", "classe_taille", value_col]
    keep = [c for c in dict.fromkeys(keep) if c in df.columns]
    out = df[keep].rename(columns={"commune": "label", value_col: "valeur"}).copy()
    out["dans_perimetre"] = out["cle_commune"].isin(scoped["cle_commune"])
    return out.reset_index(drop=True)


def etab_points(ds: Datasets, f: Filters) -> pd.DataFrame:
    """Établissements financiers géolocalisés (points réels), filtrés par catégorie
    et par périmètre territorial — pour l'affichage rapproché sur la carte."""
    df = ds.get("etablissements_detail")
    if df.empty:
        return df
    df = apply_etab_categorie(df, f)
    df = apply_canton(df, f)
    if f.region:
        df = df[df["region_a"].isin(f.region)]
    if f.prefecture:
        df = df[df["prefecture_norm"].isin(f.prefecture)]
    if f.commune:
        communes = ds.get("table_analytique_communes")
        keys = communes.loc[communes["commune"].isin(f.commune), "cle_commune"].unique()
        df = df[df["cle_commune"].isin(keys)]
    return df.reset_index(drop=True)


def cantons_stats(ds: Datasets, f: Filters) -> tuple[pd.DataFrame, dict]:
    """Table canton (n_formel, n_mm, mm_only) + quelques agrégats nationaux.
    Aucune donnée de population n'existe à ce niveau : uniquement des comptages."""
    df = ds.get("table_analytique_cantons_presence")
    if df.empty:
        return df, {}
    scoped = df.copy()
    if f.region:
        scoped = scoped[scoped["region_a"].isin(f.region)]
    if f.prefecture:
        scoped = scoped[scoped["prefecture_norm"].isin(f.prefecture)]
    if f.commune:
        communes = ds.get("table_analytique_communes")
        keys = communes.loc[communes["commune"].isin(f.commune), "cle_commune"].unique()
        scoped = scoped[scoped["cle_commune"].isin(keys)]
    stats = {
        "total": int(len(df)), "mm_only": int(df["mm_only"].sum()),
        "scoped_total": int(len(scoped)), "scoped_mm_only": int(scoped["mm_only"].sum()),
    }
    return scoped.sort_values(["n_mm"], ascending=False).reset_index(drop=True), stats


# --------------------------------------------------------------------------- #
# Usage numérique
# --------------------------------------------------------------------------- #
def usage_series(ds: Datasets, f: Filters) -> pd.Series:
    u = apply_years(ds.get("internet_usage_variations"), f, "année")
    if u.empty:
        return pd.Series(dtype=float)
    return u.set_index("année")["usage Internet (%)"].sort_index()


def usage_vs_abon_sim(ds: Datasets, f: Filters | None = None) -> pd.DataFrame:
    df = ds.get("comparaison_usage_abonnements_sim")
    if f is not None:
        df = apply_years(df, f, "annee")
    if df.empty:
        return df
    table = df.set_index("annee")[["usage_pct", "abon_internet_pen", "sim_gsm_dens"]].sort_index()
    table.columns = ["Usage Internet (%)", "Abonnements Internet (pour 100 hab.)", "Cartes SIM (pour 100 hab.)"]
    return table


def market_share(ds: Datasets, f: Filters | None = None) -> pd.DataFrame:
    """Parts de marché GSM ; le filtre « Opérateur GSM » ne conserve que les opérateurs choisis."""
    df = ds.get("marche_gsm_2013_2019")
    if f is not None:
        df = apply_years(df, f, "annee")
    if df.empty:
        return df
    chosen = [o for o in C.GSM_OPERATEURS if f is not None and o in f.gsm_operateur]
    cols = [C.GSM_SHARE_COLS[o] for o in (chosen or C.GSM_OPERATEURS)]
    return df.set_index("annee")[cols].sort_index()


def market_ca_invest(ds: Datasets, f: Filters | None = None) -> pd.DataFrame:
    df = ds.get("marche_gsm_2013_2019")
    if f is not None:
        df = apply_years(df, f, "annee")
    if df.empty:
        return df
    return df.set_index("annee")[["Chiffre d'affaires (Mds FCFA)", "Investissement (Mds FCFA)"]].sort_index()


def tech_transition(ds: Datasets, f: Filters | None = None) -> pd.DataFrame:
    """Transition 2G / 3G / 4G du mobile. Avec un seul opérateur GSM sélectionné, la table
    fournit pour cet opérateur la part 2G et la part 3G+4G (la ventilation 3G / 4G n'existe
    qu'au niveau national) ; sinon, la ventilation nationale 2G / 3G / 4G."""
    df = ds.get("transition_technologique_mobile")
    if f is not None:
        df = apply_years(df, f, "annee")
    if df.empty:
        return df
    if f is not None and len(f.gsm_operateur) == 1:
        op = f.gsm_operateur[0]
        cols = [f"{op} : part 2G (%)", f"{op} : part 3G+4G (%)"]
        if all(c in df.columns for c in cols):
            table = df.set_index("annee")[cols].sort_index()
            table.columns = ["2G (GPRS/EDGE)", "3G + 4G"]
            return table
    table = df.set_index("annee")[["part 2G (%)", "part 3G (%)", "part 4G (%)"]].sort_index()
    table.columns = ["2G (GPRS/EDGE)", "3G", "4G"]
    return table


def fibre_share(ds: Datasets, f: Filters | None = None) -> pd.Series:
    df = ds.get("internet_fixe_fibre")
    if f is not None:
        df = apply_years(df, f, "annee")
    if df.empty:
        return pd.Series(dtype=float)
    return df.set_index("annee")["part_ftth_total_internet_pct"].sort_index()


def usage_kpis(ds: Datasets, f: Filters) -> list:
    from components.kpi import Kpi
    year, usage_val, usage_gain = usage_last(ds)
    rup_year, rythme_avant, rythme_apres = rupture_info(ds)
    hhi_year, hhi_val = hhi_last(ds)
    m = ds.get("marche_gsm_2013_2019")
    haut_debit = None
    if not m.empty and "part haut débit 3G+4G (%)" not in m.columns:
        t = ds.get("transition_technologique_mobile")
        if not t.empty:
            haut_debit = float(t.sort_values("annee").iloc[-1]["part haut débit 3G+4G (%)"])
    cas = ds.get("comparaison_usage_abonnements_sim")
    abon_par_usager = None
    if not cas.empty:
        abon_par_usager = float(cas.sort_values("annee").iloc[-1]["abonnements_par_utilisateur"])
    return [
        Kpi("usage", f"Usage Internet {year or ''}", "wifi", "green", usage_val, "pct", usage_gain, "pts",
           f"vs. {year - 1}" if year else None, "Individus ayant utilisé Internet (3 derniers mois)."),
        Kpi("rupture", "Rupture de tendance", "trending_up", "blue", rup_year, "int",
           definition="Année où le rythme annuel de progression change durablement."),
        Kpi("rythme", "Rythme post-rupture", "speed", "yellow", rythme_apres, "dec", delta_unit="pp/an",
           definition="Points de pourcentage gagnés par an depuis la rupture de tendance."),
        Kpi("hhi", "HHI marché GSM", "pie_chart", "purple", hhi_val, "int",
           delta_label=str(hhi_year) if hhi_year else None, definition="Indice de concentration du marché mobile."),
        Kpi("abon", "Abonnements / utilisateur", "sim_card", "teal", abon_par_usager, "dec",
           definition="Abonnements Internet pour 100 habitants ÷ usage Internet (%), dernière année disponible."),
    ]


# --------------------------------------------------------------------------- #
# Services financiers
# --------------------------------------------------------------------------- #
def formel_by_region(ds: Datasets, f: Filters) -> pd.DataFrame:
    df = apply_geo(ds.get("table_analytique_regions"), f)
    return _lv(df, REGION_COL, "n_formel")


def formel_category_by_region(ds: Datasets, f: Filters) -> pd.DataFrame:
    df = ds.get("etablissements_categorie_region")
    if df.empty:
        return df
    df = df[df["region_analyse"] != "Togo"]
    if f.region:
        df = df[df["region_analyse"].isin(f.region)]
    cols = list(f.etab_categorie) if f.etab_categorie else ["Banque", "Micro-Finance", "Assurance", "Mutuelle"]
    table = df.set_index("region_analyse")[cols]
    order = {r: i for i, r in enumerate(C.REGION_ORDER)}
    table = table.loc[sorted(table.index, key=lambda r: order.get(r, 99))]
    return table


def national_category_totals(ds: Datasets) -> pd.Series | None:
    df = ds.get("etablissements_categorie_region")
    row = df[df["region_analyse"] == "Togo"]
    if row.empty:
        return None
    return row[["Banque", "Micro-Finance", "Assurance", "Mutuelle"]].iloc[0]


def national_operator_totals(ds: Datasets) -> pd.Series | None:
    df = ds.get("agents_mm_operateur_region")
    row = df[df["region_analyse"] == "Togo"]
    if row.empty:
        return None
    return row[["Moov + Togocom", "Togocom uniquement", "Moov uniquement", "Non spécifié"]].iloc[0]


_LEVEL_TABLE = {"region": "table_analytique_regions", "prefecture": "table_analytique_prefectures",
                "commune": "table_analytique_communes"}
_LEVEL_LABEL = {"region": "region_a", "prefecture": "prefecture", "commune": "commune"}
_LEVEL_CONTEXT = {"region": [], "prefecture": [REGION_COL], "commune": ["prefecture", REGION_COL]}


def _ratio_table(ds: Datasets, f: Filters, level: str, value_cols: list[str], sort_col: str) -> pd.DataFrame:
    df = apply_geo(ds.get(_LEVEL_TABLE[level]), f)
    df = with_effective_counts(df, f)
    if level == "commune":
        df = apply_canton(df, f)
    if df.empty:
        return df
    label = _LEVEL_LABEL[level]
    cols = [label] + [c for c in _LEVEL_CONTEXT[level] if c != label] + ["population"] + value_cols
    cols = [c for c in dict.fromkeys(cols) if c in df.columns]
    out = df[cols].drop_duplicates().sort_values(sort_col, ascending=False, na_position="first")
    return out.reset_index(drop=True)


def formel_ratio_table(ds: Datasets, f: Filters, level: str = "prefecture") -> pd.DataFrame:
    extra = ["classe"] if level == "prefecture" else []
    return _ratio_table(ds, f, level, ["n_formel", "hab_par_formel", "formel_10k"] + extra, "hab_par_formel")


def formel_ratio_bar(ds: Datasets, f: Filters, level: str = "prefecture", n: int = 15) -> pd.DataFrame:
    """Classement (label, valeur=hab_par_formel, classe) pour un graphique en barres —
    les territoires les moins bien desservis (ratio le plus élevé) en tête."""
    table = formel_ratio_table(ds, f, level)
    if table.empty:
        return pd.DataFrame(columns=["label", "valeur", "classe"])
    label_col = _LEVEL_LABEL[level]
    out = table[[label_col, "hab_par_formel"]].rename(columns={label_col: "label", "hab_par_formel": "valeur"})
    out["classe"] = table["classe"] if "classe" in table.columns else None
    return out.dropna(subset=["valeur"]).sort_values("valeur", ascending=False).head(n).reset_index(drop=True)


def financial_kpis(ds: Datasets, f: Filters) -> list:
    from components.kpi import Kpi
    df = with_effective_counts(apply_geo(ds.get("table_analytique_prefectures"), f), f)
    if df.empty:
        return []
    pop, n_formel = float(df["population"].sum()), float(df["n_formel"].sum())
    hab_par_formel = pop / n_formel if n_formel else None
    formel_10k = n_formel / pop * 10_000 if pop else None
    sous_dotees = int((df["classe"] != "Correct").sum()) if not f.etab_categorie else None
    kpis = [
        Kpi("n_formel", "Établissements financiers", "account_balance", "green", n_formel, "int",
           definition="Banques, IMF, assurances, mutuelles — dans le périmètre sélectionné."),
        Kpi("hab_formel", "Habitants par établissement", "groups", "blue", hab_par_formel, "int",
           definition="Population ÷ nombre d'établissements formels (plus faible = mieux desservi)."),
        Kpi("formel10k", "Établissements pour 10 000 hab.", "grid_view", "yellow", formel_10k, "dec",
           definition="Densité relative à la population."),
    ]
    if sous_dotees is not None:
        kpis.append(Kpi("faible", "Préfectures sous-dotées", "warning", "red", sous_dotees, "int",
                       delta_label=f"sur {len(df)}", definition="Préfectures classées « Faible » ou « MM-only »."))
    return kpis


_CLASSE_SEVERITY = {"MM-only": 0, "Faible": 1, "Correct": 2}


def weakest_prefectures(ds: Datasets, f: Filters, n: int = 10) -> pd.DataFrame:
    df = with_effective_counts(apply_geo(ds.get("table_analytique_prefectures"), f), f)
    if df.empty:
        return df
    cols = ["prefecture", REGION_COL, "population", "n_formel", "hab_par_formel", "classe"]
    out = df[cols].copy()
    out["_sev"] = out["classe"].map(_CLASSE_SEVERITY).fillna(9)
    out = out.sort_values(["_sev", "hab_par_formel"], ascending=[True, False], na_position="first")
    return out.drop(columns="_sev").head(n).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Mobile Money
# --------------------------------------------------------------------------- #
def mm_by_region(ds: Datasets, f: Filters) -> pd.DataFrame:
    df = apply_geo(ds.get("table_analytique_regions"), f)
    return _lv(df, REGION_COL, "n_mm")


def mm_operator_by_region(ds: Datasets, f: Filters) -> pd.DataFrame:
    df = ds.get("agents_mm_operateur_region")
    if df.empty:
        return df
    df = df[df["region_analyse"] != "Togo"]
    if f.region:
        df = df[df["region_analyse"].isin(f.region)]
    all_ops = ["Moov + Togocom", "Togocom uniquement", "Moov uniquement", "Non spécifié"]
    cols = list(f.mm_operateur) if f.mm_operateur else all_ops
    table = df.set_index("region_analyse")[cols]
    order = {r: i for i, r in enumerate(C.REGION_ORDER)}
    return table.loc[sorted(table.index, key=lambda r: order.get(r, 99))]


def gini_comparison(ds: Datasets) -> pd.DataFrame:
    df = ds.get("gini_desserte")
    if df.empty:
        return df
    table = df.set_index("niveau")[["Gini établissements formels", "Gini agents MM"]]
    return table


def mm_ratio_table(ds: Datasets, f: Filters, level: str = "prefecture") -> pd.DataFrame:
    return _ratio_table(ds, f, level, ["n_mm", "hab_par_mm", "mm_10k"], "hab_par_mm")


def mm_ratio_bar(ds: Datasets, f: Filters, level: str = "prefecture", n: int = 15) -> pd.DataFrame:
    """Classement (label, valeur=hab_par_mm) pour un graphique en barres — territoires
    les moins couverts en agents Mobile Money en tête."""
    table = mm_ratio_table(ds, f, level)
    if table.empty:
        return pd.DataFrame(columns=["label", "valeur"])
    label_col = _LEVEL_LABEL[level]
    out = table[[label_col, "hab_par_mm"]].rename(columns={label_col: "label", "hab_par_mm": "valeur"})
    return out.dropna(subset=["valeur"]).sort_values("valeur", ascending=False).head(n).reset_index(drop=True)


def mobile_money_kpis(ds: Datasets, f: Filters) -> list:
    from components.kpi import Kpi
    df = with_effective_counts(apply_geo(ds.get("table_analytique_prefectures"), f), f)
    communes = apply_geo(ds.get("table_analytique_communes"), f)
    if df.empty:
        return []
    pop, n_mm = float(df["population"].sum()), float(df["n_mm"].sum())
    hab_par_mm = pop / n_mm if n_mm else None
    mm_10k = n_mm / pop * 10_000 if pop else None
    mm_only = int(communes["mm_only"].sum()) if not communes.empty else None
    return [
        Kpi("n_mm", "Agents Mobile Money", "smartphone", "yellow", n_mm, "int",
           definition="Agents Mobile Money recensés, tous opérateurs — périmètre sélectionné."),
        Kpi("hab_mm", "Habitants par agent MM", "groups", "blue", hab_par_mm, "int",
           definition="Population ÷ nombre d'agents Mobile Money."),
        Kpi("mm10k", "Agents pour 10 000 hab.", "grid_view", "green", mm_10k, "dec",
           definition="Densité relative à la population."),
        Kpi("mmonly", "Communes MM-only", "location_off", "red", mm_only, "int",
           definition="Aucun établissement financier formel dans la commune, seuls des agents MM sont présents."),
    ]


def poles_fragiles(ds: Datasets) -> pd.DataFrame:
    df = ds.get("poles_rattachement_mm_only")
    if df.empty:
        return df
    return df.sort_values("pôle fragile (≤ 2 établissements)", ascending=False)


# --------------------------------------------------------------------------- #
# Inclusion territoriale
# --------------------------------------------------------------------------- #
def communes_mm_only_table(ds: Datasets, f: Filters) -> pd.DataFrame:
    df = ds.get("communes_mm_only")
    if df.empty:
        return df
    if f.region:
        df = df[df["région"].isin(f.region)]
    if f.prefecture:
        df = df[df["préfecture"].isin(f.prefecture)]
    if f.commune:
        df = df[df["commune"].isin(f.commune)]
    return df.sort_values("population", ascending=False).reset_index(drop=True)


def communes_mm_only_bar(ds: Datasets, f: Filters) -> pd.DataFrame:
    table = communes_mm_only_table(ds, f)
    if table.empty:
        return pd.DataFrame(columns=["label", "valeur"])
    return table[["commune", "population"]].rename(columns={"commune": "label", "population": "valeur"})


def typologie_niveau_formel(ds: Datasets) -> pd.DataFrame:
    return ds.get("typologie_desserte_niveau_formel")


def typologie_regions(ds: Datasets, f: Filters) -> pd.DataFrame:
    df = apply_geo(ds.get("typologie_region"), f)
    return df


def dispersion(ds: Datasets) -> pd.DataFrame:
    return ds.get("dispersion_ratios")


def dispersion_bar(ds: Datasets, metric: str = "P90 / P10") -> pd.DataFrame:
    """Tableau pivoté (échelle × réseau) pour un graphique en barres groupées —
    même forme que gini_comparison, appliquée à l'indicateur `metric` de dispersion_ratios."""
    df = dispersion(ds)
    if df.empty or metric not in df.columns:
        return pd.DataFrame()
    order = ["région", "préfecture", "commune"]
    pivot = df.pivot(index="niveau", columns="réseau", values=metric)
    pivot = pivot.reindex([n for n in order if n in pivot.index])
    return pivot.rename(columns={
        "établissements formels (hab./établissement)": "Établissements formels",
        "agents Mobile Money (hab./agent)": "Agents Mobile Money",
    })


def niveau_formel_ranges(ds: Datasets) -> pd.DataFrame:
    """Par niveau de couverture formelle : plage réelle observée de la densité d'établissements
    (pour 10 000 hab.) et distance médiane au point formel, calculées sur les communes — sert
    à expliciter ce que recouvre chaque niveau dans l'info-bulle."""
    c = ds.get("table_analytique_communes")
    if c.empty or "niv_formel" not in c.columns:
        return pd.DataFrame()
    agg = {"dens_min": ("formel_10k", "min"), "dens_max": ("formel_10k", "max")}
    if "dist_med_km" in c.columns:
        agg["dist_med"] = ("dist_med_km", "median")
    return c.groupby("niv_formel").agg(**agg).reset_index()


_DISPERSION_SOURCES = {
    "région": ("table_analytique_regions", "region_a"),
    "préfecture": ("table_analytique_prefectures", "prefecture"),
    "commune": ("table_analytique_communes", "commune"),
}
_DISPERSION_COLS = {
    "établissements formels (hab./établissement)": "hab_par_formel",
    "agents Mobile Money (hab./agent)": "hab_par_mm",
}


def dispersion_extremes(ds: Datasets) -> dict[tuple[str, str], dict]:
    """Territoires les mieux / moins bien desservis et médiane, par (échelle, réseau) — même
    population de territoires que dispersion_ratios (ratio hab./unité fini et > 0)."""
    import numpy as np

    out: dict[tuple[str, str], dict] = {}
    for niveau, (table, name_col) in _DISPERSION_SOURCES.items():
        df = ds.get(table)
        if df.empty or name_col not in df.columns:
            continue
        for reseau, col in _DISPERSION_COLS.items():
            if col not in df.columns:
                continue
            values = pd.to_numeric(df[col], errors="coerce")
            ok = values.notna() & np.isfinite(values) & (values > 0)
            if not ok.any():
                continue
            sub, vals = df[ok], values[ok]
            out[(niveau, reseau)] = {
                "min": float(vals.min()), "min_name": str(sub.loc[vals.idxmin(), name_col]),
                "med": float(vals.median()),
                "max": float(vals.max()), "max_name": str(sub.loc[vals.idxmax(), name_col]),
            }
    return out


def priorisation_prefectures(ds: Datasets, f: Filters) -> pd.DataFrame:
    df = ds.get("priorisation_prefectures")
    if df.empty:
        return df
    if f.region:
        df = df[df["région"].isin(f.region)]
    if f.prefecture:
        df = df[df["prefecture"].isin(f.prefecture)]
    return df.sort_values("population P1/P2", ascending=False).reset_index(drop=True)


def hab_par_formel_national(ds: Datasets) -> float | None:
    """Ratio national habitants / établissement formel (K4.1 du catalogue KPI) — sert de
    référence au calcul du « besoin indicatif » de priorisation_prefectures (K5.5) :
    pour une commune en palier P1/P2, établissements manquants = max(0, ⌈population ÷ ce
    ratio⌉ − établissements existants), sommés par préfecture."""
    df = ds.get("table_analytique_communes")
    if df.empty or "n_formel" not in df.columns:
        return None
    total_formel = df["n_formel"].sum()
    return df["population"].sum() / total_formel if total_formel else None


def priorisation_prefectures_bar(ds: Datasets, f: Filters) -> pd.DataFrame:
    table = priorisation_prefectures(ds, f)
    if table.empty:
        return pd.DataFrame(columns=["label", "valeur"])
    return table[["prefecture", "population P1/P2"]].rename(
        columns={"prefecture": "label", "population P1/P2": "valeur"})


def canton_mm_only_by_region(ds: Datasets, f: Filters) -> pd.DataFrame:
    """Cantons MM-only comptés par région (donnée réelle, aucune donnée de population
    disponible à cet échelon — un simple comptage de cantons)."""
    df, _ = cantons_stats(ds, f)
    if df.empty:
        return pd.DataFrame(columns=["label", "valeur"])
    counts = df[df["mm_only"]].groupby("region_a").size()
    out = pd.DataFrame({"label": counts.index, "valeur": counts.values})
    order = {r: i for i, r in enumerate(C.REGION_ORDER)}
    return out.sort_values("label", key=lambda s: s.map(lambda r: order.get(r, 99))).reset_index(drop=True)


def communes_detail(ds: Datasets, f: Filters) -> pd.DataFrame:
    df = ds.get("table_analytique_communes")
    df = apply_geo(df, f)
    df = apply_palier(df, f)
    return df


def inclusion_kpis(ds: Datasets) -> list:
    from components.kpi import Kpi
    tot = national_totals(ds)
    c = ds.get("table_analytique_communes")
    dist_mm_only = dist_autres = None
    cmo = ds.get("communes_mm_only")
    if not cmo.empty:
        dist_mm_only = float(cmo["distance médiane au point formel (km)"].median())
    if not c.empty:
        autres = c[c["mm_only"] == False]
        if "dist_med_km" in autres.columns and autres["dist_med_km"].notna().any():
            dist_autres = float(autres["dist_med_km"].median())
    _, canton_stats = cantons_stats(ds, Filters())
    canton_pct = (canton_stats["mm_only"] / canton_stats["total"] * 100) if canton_stats.get("total") else None
    return [
        Kpi("pop", "Population totale (RGPH-5)", "groups", "green", tot.get("population"), "int",
           definition="Population recensée, RGPH-5 (2022)."),
        Kpi("mmonly", "Communes MM-only", "location_off", "red", tot.get("mm_only_communes"), "int",
           delta_label=(f"{tot['mm_only_population']:,.0f} hab. ({tot['mm_only_population']/tot['population']*100:.1f} %)"
                        .replace(",", " ") if tot.get("mm_only_population") and tot.get("population") else None),
           definition="Aucun établissement financier formel ; desservies uniquement par des agents Mobile Money."),
        Kpi("prio", "Population P1 + P2", "priority_high", "purple", tot.get("p1p2_population"), "int",
           delta_label=f"{tot.get('p1p2_communes', 0)} communes" if tot.get("p1p2_communes") else None,
           definition="Palier de priorité le plus élevé de l'indice de besoin territorial."),
        Kpi("dist_mmonly", "Distance médiane (MM-only)", "distance", "yellow", dist_mm_only, "dec",
           delta_unit="km", definition="Distance médiane d'un agent Mobile Money au point formel le plus proche, "
                                        "dans les communes MM-only."),
        Kpi("dist_autres", "Distance médiane (ailleurs)", "near_me", "teal", dist_autres, "dec",
           delta_unit="km", definition="Même indicateur, communes disposant d'au moins un établissement formel."),
        Kpi("canton_mmonly", "Cantons MM-only", "location_off", "purple", canton_stats.get("mm_only"), "int",
           delta_label=f"{canton_pct:.0f} % des {canton_stats.get('total')} cantons" if canton_pct is not None else None,
           definition="Cantons sans aucun établissement financier formel, desservis uniquement par des "
                      "agents Mobile Money — lecture plus fine que la commune (aucune donnée de population "
                      "n'est disponible à cet échelon)."),
    ]


# --------------------------------------------------------------------------- #
# Recommandations
# --------------------------------------------------------------------------- #
def recommandations_table(ds: Datasets, f: Filters) -> pd.DataFrame:
    r = ds.get("recommandations")
    r = apply_axe(r, f)
    plan = ds.get("plan_action_consolide")
    budget = ds.get("budget_par_recommandation")
    return r, plan, budget


def match_plan(plan: pd.DataFrame, reco_id: str) -> pd.Series | None:
    if plan.empty:
        return None
    exact = plan[plan["id"] == reco_id]
    if len(exact):
        return exact.iloc[0]
    combo = plan[plan["id"].str.contains(reco_id, regex=False, na=False)]
    if len(combo):
        return combo.iloc[0]
    return None


def match_budget(budget: pd.DataFrame, reco_id: str) -> pd.Series | None:
    if budget.empty:
        return None
    exact = budget[budget["recommandation"] == reco_id]
    if len(exact):
        return exact.iloc[0]
    combo = budget[budget["recommandation"].str.contains(reco_id, regex=False, na=False)]
    if len(combo):
        return combo.iloc[0]
    return None


def scenarios_table(ds: Datasets) -> pd.DataFrame:
    df = ds.get("scenarios_comparaison")
    if df.empty:
        return df
    cols = ["scenario", "territoires", "population", "benef_additionnels_estimes",
           "budget_ferme_central_fcfa", "cout_par_benef_addit_central_fcfa", "calendrier"]
    return df[cols]


def feuille_de_route(ds: Datasets) -> pd.DataFrame:
    return ds.get("recommandations_feuille_de_route")


def priorite_communes(ds: Datasets, f: Filters, n: int = 15) -> pd.DataFrame:
    df = communes_detail(ds, f)
    if df.empty:
        return df
    cols = ["commune", "prefecture", REGION_COL, "population", "palier", "IB", "n_formel", "n_mm", "type_action"]
    cols = [c for c in cols if c in df.columns]
    return df[cols].sort_values("IB", ascending=False).head(n).reset_index(drop=True)
