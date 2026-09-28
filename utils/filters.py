"""Filtres : état (session), rendu de la barre latérale, application aux tables.

Les tables analytiques sont déjà agrégées (une ligne = une région / une
préfecture / une commune). Filtrer consiste donc à restreindre les lignes,
ou à recombiner des colonnes déjà présentes (ex. n_banque + n_mf pour un
sous-ensemble de catégories) — jamais à recalculer un ratio ou une part.
Sélectionner deux valeurs dans un même champ (ex. 2 régions) affiche
naturellement les deux côte à côte dans les graphiques et tableaux (comparaison).
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import streamlit as st

from . import config as C
from .data_loader import Datasets

# Clés de session partagées avec la carte territoriale interactive
# (components/territorial_map.py) : un clic sur la carte écrit directement
# dans ces clés puis déclenche un st.rerun(), exactement comme la barre latérale.
F_REGION, F_PREFECTURE, F_COMMUNE, F_CANTON = "f_region", "f_prefecture", "f_commune", "f_canton"
F_ETAB, F_MM, F_PALIER, F_AXE, F_YEARS = "f_etab_categorie", "f_mm_operateur", "f_palier", "f_axe", "f_years"
F_GSM = "f_gsm_operateur"
_ALL_KEYS = (F_REGION, F_PREFECTURE, F_COMMUNE, F_CANTON, F_ETAB, F_MM, F_PALIER, F_AXE, F_YEARS, F_GSM)

# Compteur incrémenté à chaque réinitialisation géographique (barre latérale ou bouton
# « Vue nationale » de la carte). La carte territoriale (components/territorial_map.py)
# l'intègre à la clé de son widget st.plotly_chart : Streamlit conserve la sélection d'un
# widget à clé identique d'un rerun à l'autre (survole/clic sur la carte), donc un simple
# pop des clés F_REGION/... ne suffit pas à effacer la sélection déjà faite sur la carte —
# changer la clé force son remontage complet, sans quoi la carte reste visuellement
# « sélectionnée » après un clic sur Réinitialiser.
F_GEO_NONCE = "f_geo_nonce"


@dataclass(frozen=True)
class Filters:
    region: tuple[str, ...] = ()
    prefecture: tuple[str, ...] = ()
    commune: tuple[str, ...] = ()
    canton: tuple[str, ...] = ()
    etab_categorie: tuple[str, ...] = ()
    mm_operateur: tuple[str, ...] = ()
    palier: tuple[str, ...] = ()
    axe: tuple[str, ...] = ()
    year_start: int = C.USAGE_YEAR_MIN
    year_end: int = C.USAGE_YEAR_MAX
    gsm_operateur: tuple[str, ...] = ()

    @property
    def compare_regions(self) -> bool:
        return len(self.region) == 2

    @property
    def has_geo(self) -> bool:
        return bool(self.region or self.prefecture or self.commune or self.canton)


# --------------------------------------------------------------------------- #
# Application aux tables (lignes)
# --------------------------------------------------------------------------- #
def apply_region(df: pd.DataFrame, f: Filters, col: str = "region_a") -> pd.DataFrame:
    if not f.region or col not in df.columns:
        return df
    return df[df[col].isin(f.region)]


def apply_prefecture(df: pd.DataFrame, f: Filters, col: str = "prefecture") -> pd.DataFrame:
    if not f.prefecture or col not in df.columns:
        return df
    return df[df[col].isin(f.prefecture)]


def apply_commune(df: pd.DataFrame, f: Filters, col: str = "commune") -> pd.DataFrame:
    if not f.commune or col not in df.columns:
        return df
    return df[df[col].isin(f.commune)]


def apply_geo(df: pd.DataFrame, f: Filters, region_col: str = "region_a",
              prefecture_col: str = "prefecture", commune_col: str = "commune") -> pd.DataFrame:
    df = apply_region(df, f, region_col)
    df = apply_prefecture(df, f, prefecture_col)
    df = apply_commune(df, f, commune_col)
    return df


def apply_canton(df: pd.DataFrame, f: Filters, col: str = "canton_norm") -> pd.DataFrame:
    if not f.canton or col not in df.columns:
        return df
    return df[df[col].isin(f.canton)]


def apply_etab_categorie(df: pd.DataFrame, f: Filters, col: str = "activite_categorie") -> pd.DataFrame:
    """Pour les tables au grain « un établissement = une ligne » (etablissements_detail)."""
    if not f.etab_categorie or col not in df.columns:
        return df
    return df[df[col].isin(f.etab_categorie)]


def apply_palier(df: pd.DataFrame, f: Filters, col: str = "palier") -> pd.DataFrame:
    if not f.palier or col not in df.columns:
        return df
    return df[df[col].isin(f.palier)]


def apply_axe(df: pd.DataFrame, f: Filters, col: str = "axe") -> pd.DataFrame:
    if not f.axe or col not in df.columns:
        return df
    return df[df[col].isin(f.axe)]


def apply_years(df: pd.DataFrame, f: Filters, col: str = "année") -> pd.DataFrame:
    if col not in df.columns:
        return df
    return df[(df[col] >= f.year_start) & (df[col] <= f.year_end)]


# --------------------------------------------------------------------------- #
# Colonnes déjà agrégées par catégorie / opérateur — recombinaison sans recalcul
# --------------------------------------------------------------------------- #
def effective_formel(df: pd.DataFrame, f: Filters) -> pd.Series:
    """Nombre d'établissements formels, restreint aux catégories sélectionnées.

    Simple somme des colonnes déjà présentes (n_banque, n_mf, n_assurance,
    n_mutuelle) — aucune estimation. Sans sélection, renvoie n_formel tel quel.
    """
    if not f.etab_categorie:
        return df["n_formel"] if "n_formel" in df.columns else pd.Series(0, index=df.index)
    cols = [C.ETAB_CATEGORY_COLS[c] for c in f.etab_categorie if C.ETAB_CATEGORY_COLS[c] in df.columns]
    if not cols:
        return df["n_formel"] if "n_formel" in df.columns else pd.Series(0, index=df.index)
    return df[cols].sum(axis=1)


def effective_mm(df: pd.DataFrame, f: Filters) -> pd.Series:
    """Nombre d'agents Mobile Money, restreint aux opérateurs sélectionnés (même principe)."""
    if not f.mm_operateur:
        return df["n_mm"] if "n_mm" in df.columns else pd.Series(0, index=df.index)
    cols = [C.MM_OPERATEUR_COLS[o] for o in f.mm_operateur if C.MM_OPERATEUR_COLS[o] in df.columns]
    if not cols:
        return df["n_mm"] if "n_mm" in df.columns else pd.Series(0, index=df.index)
    return df[cols].sum(axis=1)


def with_effective_counts(df: pd.DataFrame, f: Filters) -> pd.DataFrame:
    """Copie de `df` avec n_formel/n_mm/n_points — et les ratios qui en dérivent
    (hab_par_formel, formel_10k, hab_par_mm, mm_10k, hab_par_point, pts_10k) —
    recalculés selon les filtres financiers actifs, avec la même formule que celle
    déjà utilisée pour produire ces colonnes (division par la population réelle).
    Sans filtre de catégorie / opérateur actif, la table est renvoyée inchangée.
    """
    if df.empty or not (f.etab_categorie or f.mm_operateur):
        return df
    out = df.copy()
    pop = out["population"].replace(0, pd.NA) if "population" in out.columns else None
    if "n_formel" in out.columns:
        out["n_formel"] = effective_formel(out, f)
        n_formel = out["n_formel"].replace(0, pd.NA)
        if pop is not None:
            if "hab_par_formel" in out.columns:
                out["hab_par_formel"] = pop / n_formel
            if "formel_10k" in out.columns:
                out["formel_10k"] = out["n_formel"] / pop * 10_000
    if "n_mm" in out.columns:
        out["n_mm"] = effective_mm(out, f)
        n_mm = out["n_mm"].replace(0, pd.NA)
        if pop is not None:
            if "hab_par_mm" in out.columns:
                out["hab_par_mm"] = pop / n_mm
            if "mm_10k" in out.columns:
                out["mm_10k"] = out["n_mm"] / pop * 10_000
    if {"n_formel", "n_mm"} <= set(out.columns):
        out["n_points"] = out["n_formel"] + out["n_mm"]
        n_points = out["n_points"].replace(0, pd.NA)
        if pop is not None:
            if "hab_par_point" in out.columns:
                out["hab_par_point"] = pop / n_points
            if "pts_10k" in out.columns:
                out["pts_10k"] = out["n_points"] / pop * 10_000
    return out


# --------------------------------------------------------------------------- #
# Barre latérale
# --------------------------------------------------------------------------- #
def _reset() -> None:
    for key in _ALL_KEYS:
        st.session_state.pop(key, None)
    st.session_state[F_GEO_NONCE] = st.session_state.get(F_GEO_NONCE, 0) + 1


def _multi(key: str, label: str, options: list[str], placeholder: str, *,
           icon: str | None = None, disabled: bool = False, max_sel: int | None = None,
           format_func=str) -> tuple[str, ...]:
    """Multisélection dont la valeur est systématiquement recalée sur `options`
    (corrige toute sélection devenue invalide après un changement de filtre parent
    — ex. préfecture choisie puis région changée — pour éviter toute perte d'état
    incohérente entre la carte et les filtres). `format_func` permet d'afficher un
    libellé plus parlant qu'un simple code (ex. paliers P1-P4 → priorité en toutes lettres).

    Le widget est rendu sous une clé physique suffixée par le compteur de
    réinitialisation (F_GEO_NONCE) : un simple `st.session_state.pop(key)` met bien
    à jour l'état côté serveur, mais Streamlit ne redessine pas toujours les
    pastilles déjà affichées d'un `st.multiselect` dont la clé ne change pas (bug
    connu) — d'où le bouton « Réinitialiser » qui semblait ne rien faire à l'écran.
    Changer la clé force un remontage complet du widget, qui repart alors vide.
    `key` reste la clé « logique » utilisée partout ailleurs dans l'app (carte
    territoriale incluse) ; elle est toujours resynchronisée avec la valeur
    réellement affichée par le widget."""
    nonce = st.session_state.get(F_GEO_NONCE, 0)
    widget_key = f"{key}__{nonce}"
    if widget_key not in st.session_state:
        seed = [v for v in st.session_state.get(key, ()) if v in options]
        if max_sel:
            seed = seed[:max_sel]
        st.session_state[widget_key] = seed
    shown = f":material/{icon}: {label}" if icon else label
    picked = st.multiselect(shown, options, key=widget_key, max_selections=max_sel,
                            placeholder=placeholder, disabled=disabled, format_func=format_func)
    st.session_state[key] = tuple(picked)
    return tuple(picked)


def render_sidebar(ds: Datasets, page: str) -> Filters:
    """Filtres cohérents avec la page active : jamais de filtre décoratif.

    Organisés par catégorie (territoire / finance / temporel). Tous les filtres,
    y compris les sous-filtres (commune, canton, type d'établissement, opérateur),
    sont affichés directement, sans section repliable.
    """
    with st.sidebar:
        with st.container(key="sb_head"):
            st.markdown('<div class="sb-title"><span class="msr">filter_alt</span>Filtres</div>',
                       unsafe_allow_html=True)
            st.button("Réinitialiser", icon=":material/restart_alt:", key="btn_reset",
                      on_click=_reset, type="tertiary")

        chosen: dict[str, tuple] = {"region": (), "prefecture": (), "commune": (), "canton": (),
                                    "etab_categorie": (), "mm_operateur": (), "palier": (), "axe": (),
                                    "gsm_operateur": ()}
        year_start, year_end = C.USAGE_YEAR_MIN, C.USAGE_YEAR_MAX

        geo_pages = {"vue_ensemble", "services_financiers", "mobile_money", "inclusion_territoriale"}
        finance_pages = {"vue_ensemble", "services_financiers", "mobile_money"}

        if page in geo_pages:
            st.markdown('<div class="sb-section">Territoire</div>', unsafe_allow_html=True)
            regions = ds.regions
            chosen["region"] = _multi(F_REGION, "Région", regions, C.ALL_LABELS["region"],
                                      icon="location_on", disabled=not regions, max_sel=C.MAX_COMPARE)

            by_region = ds.prefectures_by_region()
            scoped_pref = sorted({p for r in chosen["region"] for p in by_region.get(r, ())}) \
                if chosen["region"] else ds.prefectures()
            chosen["prefecture"] = _multi(F_PREFECTURE, "Préfecture", scoped_pref,
                                          C.ALL_LABELS["prefecture"], icon="account_balance",
                                          disabled=not scoped_pref)

            by_pref = ds.communes_by_prefecture()
            scoped_com = sorted({c for p in chosen["prefecture"] for c in by_pref.get(p, ())}) \
                if chosen["prefecture"] else ds.communes(regions=chosen["region"])
            chosen["commune"] = _multi(F_COMMUNE, "Commune", scoped_com, C.ALL_LABELS["commune"],
                                       icon="location_city", disabled=not scoped_com)
            by_commune = ds.cantons_by_commune()
            scoped_canton = sorted({ct for c in chosen["commune"] for ct in by_commune.get(c, ())}) \
                if chosen["commune"] else ds.cantons()
            chosen["canton"] = _multi(F_CANTON, "Canton", scoped_canton, C.ALL_LABELS["canton"],
                                      icon="pin_drop", disabled=not scoped_canton)

            if chosen["region"]:
                st.caption("2 régions sélectionnées : comparaison activée."
                          if len(chosen["region"]) == 2 else
                          f"{len(chosen['region'])} région sélectionnée.")

        if page in finance_pages:
            st.markdown('<div class="sb-section">Finance</div>', unsafe_allow_html=True)
            # Deux filtres indépendants, affichés directement (aucun sous-menu repliable). Chaque
            # page ne propose que celui qui a un sens pour elle : le type d'établissement n'agit
            # pas sur la page Mobile Money (agents), et l'opérateur Mobile Money n'agit pas sur
            # la page Services financiers (établissements formels). La Vue d'ensemble garde les deux.
            if page in {"vue_ensemble", "services_financiers"}:
                categories = ds.etab_categories
                chosen["etab_categorie"] = _multi(F_ETAB, "Type d'établissement", categories,
                                                  C.ALL_LABELS["etab_categorie"], icon="category",
                                                  disabled=not categories)
            if page in {"vue_ensemble", "mobile_money"}:
                operateurs = ds.mm_operateurs
                chosen["mm_operateur"] = _multi(F_MM, "Opérateur Mobile Money", operateurs,
                                                C.ALL_LABELS["mm_operateur"], icon="sim_card",
                                                disabled=not operateurs)

        # Le filtre « Palier de priorité » n'existe plus que sur la page Recommandations :
        # la page Inclusion territoriale présente déjà tous les paliers (carte, légende).
        if page == "recommandations":
            st.markdown('<div class="sb-section">Priorisation</div>', unsafe_allow_html=True)
            paliers = ds.paliers
            chosen["palier"] = _multi(F_PALIER, "Palier de priorité", paliers,
                                      C.ALL_LABELS["palier"], icon="flag", disabled=not paliers,
                                      format_func=lambda p: C.PALIER_LABELS.get(p, p))

        if page == "recommandations":
            axes = ds.axes
            chosen["axe"] = _multi(F_AXE, "Axe de recommandation", axes, C.ALL_LABELS["axe"],
                                   icon="alt_route", disabled=not axes)

        if page == "usage_numerique":
            st.markdown('<div class="sb-section">Période</div>', unsafe_allow_html=True)
            years = list(range(C.USAGE_YEAR_MIN, C.USAGE_YEAR_MAX + 1))
            # Même correctif que _multi() ci-dessus : clé physique suffixée par le
            # compteur de réinitialisation, pour que « Réinitialiser » force bien le
            # curseur à revenir visuellement à la plage complète.
            years_nonce = st.session_state.get(F_GEO_NONCE, 0)
            years_widget_key = f"{F_YEARS}__{years_nonce}"
            years_default = st.session_state.get(
                years_widget_key, st.session_state.get(F_YEARS, (C.USAGE_YEAR_MIN, C.USAGE_YEAR_MAX)))
            # `value` reste nécessaire en plus de `key` : sans lui, select_slider ne
            # sait pas qu'il doit fonctionner en mode plage (bug Streamlit reproduit
            # même hors réinitialisation — la 2e interaction lève sinon une
            # TypeError côté widget).
            year_start, year_end = st.select_slider(
                ":material/calendar_month: Usage Internet (2000-2024)", options=years,
                value=years_default, key=years_widget_key,
            )
            st.session_state[F_YEARS] = (year_start, year_end)

            st.markdown('<div class="sb-section">Marché GSM</div>', unsafe_allow_html=True)
            chosen["gsm_operateur"] = _multi(F_GSM, "Opérateur GSM", list(C.GSM_OPERATEURS),
                                             C.ALL_LABELS["gsm_operateur"], icon="signal_cellular_alt")

        st.markdown(_sidebar_decoration(), unsafe_allow_html=True)

    return Filters(region=chosen["region"], prefecture=chosen["prefecture"], commune=chosen["commune"],
                   canton=chosen["canton"], etab_categorie=chosen["etab_categorie"],
                   mm_operateur=chosen["mm_operateur"], palier=chosen["palier"], axe=chosen["axe"],
                   year_start=year_start, year_end=year_end, gsm_operateur=chosen["gsm_operateur"])


def _sidebar_decoration() -> str:
    return (
        '<div class="sb-deco" aria-hidden="true">'
        '<svg viewBox="0 0 248 90" preserveAspectRatio="none">'
        '<path d="M0 54 C70 44 150 26 248 0 L248 12 C150 38 70 58 0 66 Z" fill="#0E9F6E"/>'
        '<path d="M0 64 C70 56 150 38 248 10 L248 22 C150 48 70 68 0 76 Z" fill="#FFCE00"/>'
        '<path d="M0 74 C70 68 150 50 248 20 L248 28 C150 58 70 78 0 84 Z" fill="#D21034"/>'
        "</svg>"
        '<div class="sb-tag"><span>Économie numérique</span>'
        "<span>Territoire du Togo</span><b>plus inclusif</b></div></div>"
    )
