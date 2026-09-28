"""Menu 3 — Accès aux services financiers : couverture territoriale des établissements formels."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from components import charts as ch
from components import territorial_map as tmap
from components.kpi import kpi_row
from components.layout import card_title, context_bar, empty_state, page_header, plot, source_note
from utils import config as C
from utils import metrics as M
from utils.data_loader import Datasets
from utils.filters import Filters
from utils.formatting import fmt_dec, fmt_int

_CLASSE_COLORS = {"Correct": C.COLORS["green"], "Faible": C.OPERATEUR_COLORS["Moov"], "MM-only": C.COLORS["red"]}


def render(ds: Datasets, f: Filters) -> None:
    page_header("Accès aux services financiers", "Couverture territoriale des banques, IMF, assurances et mutuelles.")
    context_bar([
        ("Région", list(f.region)), ("Préfecture", list(f.prefecture)), ("Commune", list(f.commune)),
        ("Type d'établissement", list(f.etab_categorie)),
    ])

    kpis = M.financial_kpis(ds, f)
    if kpis:
        kpi_row(kpis)

    map_col, visual_col = st.columns(2, gap="medium")
    with map_col:
        with st.container(key="card_sf_map"):
            note = "Type d'établissement : " + ", ".join(f.etab_categorie) if f.etab_categorie else \
                "Banques, IMF, assurances, mutuelles — cliquez une région ou une commune"
            card_title("account_balance", "Carte territoriale — établissements financiers formels", note)
            tmap.render(ds, f, key="sf_map", value_col="n_formel", unit="établissements", height=420, show_etab=True,
                      )

    with visual_col:
        with st.container(key="card_sf_cat"):
            card_title("category", "Répartition par catégorie, par région", "Banque · Micro-Finance · Assurance · Mutuelle")
            table = M.formel_category_by_region(ds, f)
            if table.empty:
                empty_state(300)
            else:
                colors = {c: C.ETAB_CATEGORY_COLORS[c] for c in table.columns}
                plot(ch.grouped_hbars(table, colors, height=360, stack=True), "sf_cat")

    with st.container(key="card_sf_ratio"):
        card_title("insights", "Accessibilité réelle", "Habitants par établissement — plus la barre est longue, moins le territoire est desservi")
        col_pref, col_reg = st.columns(2, gap="medium")
        with col_pref:
            st.caption("Par préfecture")
            table = M.formel_ratio_table(ds, f, "prefecture").dropna(subset=["hab_par_formel"]) \
                .sort_values("hab_par_formel", ascending=False).head(15).reset_index(drop=True)
            if table.empty:
                empty_state(340)
            else:
                bar = table.rename(columns={"prefecture": "label", "hab_par_formel": "valeur"})[["label", "valeur"]]
                colors = [_CLASSE_COLORS.get(c, C.COLORS["muted"]) for c in table["classe"]]
                plot(ch.top_bars(bar, height=max(200, 24 * len(bar)), colors=colors, value_format=fmt_int,
                                 hover_extra=_ratio_hover(table, "prefecture")), "sf_ratio_pref")
                st.markdown(_legend_html(), unsafe_allow_html=True)
        with col_reg:
            st.caption("Par région")
            table = M.formel_ratio_table(ds, f, "region").dropna(subset=["hab_par_formel"]) \
                .sort_values("hab_par_formel", ascending=False).head(20).reset_index(drop=True)
            if table.empty:
                empty_state(340)
            else:
                bar = table.rename(columns={"region_a": "label", "hab_par_formel": "valeur"})[["label", "valeur"]]
                colors = [ch.region_color(l) for l in bar["label"]]
                plot(ch.radial_bars(bar, height=380, colors=colors, value_format=fmt_int,
                                    hover_extra=_ratio_hover(table, "region")), "sf_ratio_region")

    with st.container(key="card_sf_faible"):
        card_title("warning", "Territoires à plus faible présence formelle",
                   "Rayon = habitants par établissement · plus long = moins bien desservi")
        bar = M.weakest_prefectures(ds, f)
        if bar.empty:
            empty_state(300)
        else:
            chart_df = bar.rename(columns={"prefecture": "label", "hab_par_formel": "valeur"})[["label", "valeur", "classe"]]
            chart_df = chart_df.dropna(subset=["valeur"])
            if chart_df.empty:
                empty_state(300)
            else:
                colors = [_CLASSE_COLORS.get(c, C.COLORS["muted"]) for c in chart_df["classe"]]
                plot(ch.radial_bars(chart_df[["label", "valeur"]], height=420, colors=colors,
                                    value_format=fmt_int,
                                    hover_extra=_ratio_hover(bar.dropna(subset=["hab_par_formel"]), "prefecture")),
                     "sf_faible")
                st.markdown(_legend_html(), unsafe_allow_html=True)

    source_note(C.SOURCE_NOTE)


def _legend_html() -> str:
    items = "".join(
        f'<span style="display:inline-flex;align-items:center;margin-right:16px;font-size:12.5px;color:#334155">'
        f'<i style="background:{color};width:10px;height:10px;border-radius:3px;'
        f'display:inline-block;margin-right:6px"></i>{label}</span>'
        for label, color in _CLASSE_COLORS.items()
    )
    return f'<div style="margin-top:8px">{items}</div>'


def _ratio_hover(table: pd.DataFrame, level: str) -> list[str]:
    """Lignes d'info-bulle (population, établissements, taux, classe) — remplace le tableau
    « Détail complet » en intégrant directement ces informations aux graphiques."""
    lines = []
    for _, row in table.iterrows():
        parts = []
        if pd.notna(row.get("population")):
            parts.append(f"Population : {fmt_int(row['population'])}")
        if pd.notna(row.get("n_formel")):
            parts.append(f"Établissements : {fmt_int(row['n_formel'])}")
        if pd.notna(row.get("formel_10k")):
            parts.append(f"Étab. / 10 000 hab. : {fmt_dec(row['formel_10k'], 2)}")
        if level == "prefecture" and pd.notna(row.get("classe")):
            parts.append(f"Classe : {row['classe']}")
        lines.append("<br>".join(parts))
    return lines
