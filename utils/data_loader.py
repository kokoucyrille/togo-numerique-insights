"""Chargement des tables analytiques réelles et mise en cache.

Toutes les données proviennent de ``data/*.csv``. Aucune valeur n'est
recalculée ni inventée ici : ce module se contente de lire, typer et
mettre en cache. Les seules opérations effectuées plus loin (utils/filters.py,
utils/metrics.py) sont des filtrages, tris et sommes de colonnes déjà présentes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import streamlit as st

from . import config as C

_FILES = [
    "table_analytique_regions", "table_analytique_prefectures", "table_analytique_communes",
    "table_analytique_cantons_presence", "etablissements_detail",
    "etablissements_categorie_region", "agents_mm_operateur_region", "communes_mm_only",
    "gini_desserte", "dispersion_ratios", "typologie_desserte_niveau_formel", "typologie_region",
    "poles_rattachement_mm_only", "mm_only_niveaux", "kpi_catalogue",
    "internet_usage_variations", "internet_usage_periodes", "comparaison_usage_abonnements_sim",
    "marche_gsm_2013_2019", "transition_technologique_mobile", "internet_fixe_fibre",
    "recommandations", "recommandations_feuille_de_route", "matrice_conformite",
    "plan_action_consolide", "budget_par_recommandation", "beneficiaires_par_palier",
    "beneficiaires_communes_detail", "scenarios_comparaison", "suivi_evaluation_par_action",
    "synthese_decisionnelle_finale", "cas_reels_references", "programme_national_en_cours",
    "priorisation_prefectures",
]

_BOOL_COLS = {"mm_only", "desert_recense", "maillage MM ténu (< ½ moyenne nationale)",
              "différence significative", "pôle fragile (≤ 2 établissements)", "apparie_rgph"}


@st.cache_data(show_spinner=False)
def _read(name: str) -> pd.DataFrame:
    path = C.DATA_DIR / f"{name}.csv"
    if not path.is_file():
        return pd.DataFrame()
    df = pd.read_csv(path, encoding="utf-8-sig")
    for col in df.columns:
        if col in _BOOL_COLS and df[col].dtype == object:
            df[col] = df[col].map({"True": True, "False": False, True: True, False: False})
    return df


@st.cache_data(show_spinner=False)
def _load_all() -> dict[str, pd.DataFrame]:
    return {name: _read(name) for name in _FILES}


@dataclass
class Datasets:
    tables: dict[str, pd.DataFrame] = field(default_factory=dict)

    def get(self, name: str) -> pd.DataFrame:
        return self.tables.get(name, pd.DataFrame())

    # ------------------------------------------------------------------ #
    # Hiérarchie géographique (région > préfecture > commune > canton)
    # ------------------------------------------------------------------ #
    @property
    def regions(self) -> list[str]:
        df = self.get("table_analytique_regions")
        if df.empty:
            return []
        order = {r: i for i, r in enumerate(C.REGION_ORDER)}
        return sorted(df["region_a"].dropna().unique().tolist(), key=lambda r: order.get(r, 99))

    def prefectures(self, regions: tuple[str, ...] = ()) -> list[str]:
        df = self.get("table_analytique_prefectures")
        if df.empty:
            return []
        if regions:
            df = df[df["region_a"].isin(regions)]
        return sorted(df["prefecture"].dropna().unique().tolist())

    def prefectures_by_region(self) -> dict[str, list[str]]:
        df = self.get("table_analytique_prefectures")
        if df.empty:
            return {}
        out: dict[str, list[str]] = {}
        for region, group in df.groupby("region_a"):
            out[region] = sorted(group["prefecture"].dropna().unique().tolist())
        return out

    def communes(self, regions: tuple[str, ...] = (), prefectures: tuple[str, ...] = ()) -> list[str]:
        df = self.get("table_analytique_communes")
        if df.empty:
            return []
        if regions:
            df = df[df["region_a"].isin(regions)]
        if prefectures:
            df = df[df["prefecture"].isin(prefectures)]
        return sorted(df["commune"].dropna().unique().tolist())

    def communes_by_prefecture(self) -> dict[str, list[str]]:
        df = self.get("table_analytique_communes")
        if df.empty:
            return {}
        out: dict[str, list[str]] = {}
        for prefecture, group in df.groupby("prefecture"):
            out[prefecture] = sorted(group["commune"].dropna().unique().tolist())
        return out

    def cantons(self, communes: tuple[str, ...] = ()) -> list[str]:
        df = self.get("table_analytique_cantons_presence")
        if df.empty:
            return []
        if communes:
            key = self.get("table_analytique_communes")
            keys = key.loc[key["commune"].isin(communes), "cle_commune"].unique().tolist()
            df = df[df["cle_commune"].isin(keys)]
        return sorted(df["canton_norm"].dropna().unique().tolist())

    def cantons_by_commune(self) -> dict[str, list[str]]:
        cantons = self.get("table_analytique_cantons_presence")
        communes = self.get("table_analytique_communes")
        if cantons.empty or communes.empty:
            return {}
        merged = cantons.merge(communes[["cle_commune", "commune"]], on="cle_commune", how="left")
        out: dict[str, list[str]] = {}
        for commune, group in merged.groupby("commune"):
            out[commune] = sorted(group["canton_norm"].dropna().unique().tolist())
        return out

    @property
    def paliers(self) -> list[str]:
        df = self.get("table_analytique_communes")
        if df.empty or "palier" not in df.columns:
            return []
        present = set(df["palier"].dropna().unique())
        return [p for p in ("P1", "P2", "P3", "P4") if p in present]

    @property
    def axes(self) -> list[str]:
        df = self.get("recommandations")
        if df.empty:
            return []
        return sorted(df["axe"].dropna().unique().tolist())

    @property
    def etab_categories(self) -> list[str]:
        df = self.get("table_analytique_regions")
        if df.empty:
            return []
        return [c for c in C.ETAB_CATEGORIES if C.ETAB_CATEGORY_COLS[c] in df.columns
                and df[C.ETAB_CATEGORY_COLS[c]].sum() > 0]

    @property
    def mm_operateurs(self) -> list[str]:
        df = self.get("table_analytique_regions")
        if df.empty:
            return []
        return [op for op, col in C.MM_OPERATEUR_COLS.items()
                if col in df.columns and df[col].sum() > 0]


def load_datasets() -> Datasets:
    return Datasets(tables=_load_all())
