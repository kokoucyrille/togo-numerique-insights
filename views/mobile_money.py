"""Menu 4 — Mobile Money : distribution territoriale des agents."""
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
from utils.formatting import fmt_dec, fmt_int, fmt_signed


def render(ds: Datasets, f: Filters) -> None:
    page_header("Mobile Money", "Distribution territoriale des agents Mobile Money — près de 19 800 agents recensés.")
    context_bar([
        ("Région", list(f.region)), ("Préfecture", list(f.prefecture)), ("Commune", list(f.commune)),
        ("Opérateur", list(f.mm_operateur)),
    ])

    kpis = M.mobile_money_kpis(ds, f)
    if kpis:
        kpi_row(kpis)

    map_col, visual_col = st.columns(2, gap="medium")
    with map_col:
        with st.container(key="card_mm_map"):
            note = "Opérateur : " + ", ".join(f.mm_operateur) if f.mm_operateur else \
                "Densité par commune — cliquez une région ou une commune"
            card_title("smartphone", "Carte territoriale — agents Mobile Money", note)
            tmap.render(ds, f, key="mm_map", value_col="n_mm", unit="agents", height=420)

    with visual_col:
        with st.container(key="card_mm_op"):
            card_title("compare_arrows", "Répartition par opérateur, par région", "Moov, Togocom, duo ou non spécifié")
            table = M.mm_operator_by_region(ds, f)
            if table.empty:
                empty_state(300)
            else:
                colors = {c: C.OPERATEUR_COLORS.get(c, C.OTHER_COLOR) for c in table.columns}
                plot(ch.grouped_hbars(table, colors, height=360, stack=True), "mm_op")

    with st.container(key="card_mm_ratio"):
        card_title("insights", "Densité réelle de desserte", "Habitants par agent Mobile Money")
        col_pref, col_reg = st.columns(2, gap="medium")
        with col_pref:
            st.caption("Par préfecture")
            table = M.mm_ratio_table(ds, f, "prefecture").dropna(subset=["hab_par_mm"]) \
                .sort_values("hab_par_mm", ascending=False).head(15).reset_index(drop=True)
            if table.empty:
                empty_state(340)
            else:
                bar = table.rename(columns={"prefecture": "label", "hab_par_mm": "valeur"})[["label", "valeur"]]
                plot(ch.top_bars(bar, height=max(200, 24 * len(bar)), value_format=fmt_int,
                                 hover_extra=_mm_hover(table)), "mm_ratio_pref")
        with col_reg:
            st.caption("Par région")
            table = M.mm_ratio_table(ds, f, "region").dropna(subset=["hab_par_mm"]) \
                .sort_values("hab_par_mm", ascending=False).head(20).reset_index(drop=True)
            if table.empty:
                empty_state(340)
            else:
                bar = table.rename(columns={"region_a": "label", "hab_par_mm": "valeur"})[["label", "valeur"]]
                colors = [ch.region_color(l) for l in bar["label"]]
                plot(ch.radial_bars(bar, height=380, colors=colors, value_format=fmt_int,
                                    hover_extra=_mm_hover(table)), "mm_ratio_region")

    c1, c2 = st.columns([1, 1.2], gap="medium")
    with c1:
        with st.container(key="card_mm_gini"):
            card_title("scatter_plot", "Concentration territoriale (indice de Gini)",
                      "0 = répartition égalitaire, 1 = concentration maximale")
            table = M.gini_comparison(ds)
            if table.empty:
                empty_state(240)
            else:
                colors = {"Gini établissements formels": C.COLORS["part"], "Gini agents MM": C.COLORS["yellow"]}
                plot(ch.grouped_hbars(table, colors, height=240, value_format=lambda v: fmt_dec(v, 2),
                                      hover_decimals=2, hover_extra=_gini_hover(ds, table)), "mm_gini")
    with c2:
        with st.container(key="card_mm_poles"):
            card_title("hub", "Pôles fragiles de rattachement", "Pôles formels desservant des communes MM-only, avec ≤ 2 établissements")
            table = M.poles_fragiles(ds)
            if table.empty:
                empty_state(240)
            else:
                frag_col = "pôle fragile (≤ 2 établissements)"
                chart_df = table.rename(columns={"pole_lbl": "label", "population_dependante": "valeur"})
                chart_df = chart_df.sort_values("valeur", ascending=False).reset_index(drop=True)
                colors = [C.COLORS["red"] if v else C.COLORS["muted"] for v in chart_df[frag_col]]
                extra = []
                for _, row in chart_df.iterrows():
                    parts = [f"Région : {row['region_a']}", f"Communes MM-only rattachées : {fmt_int(row['communes_MM_only'])}",
                             f"Établissements du pôle : {fmt_int(row['établissements du pôle'])}",
                             f"Statut : {'pôle fragile' if row[frag_col] else 'pôle non fragile'}"]
                    extra.append("<br>".join(parts))
                plot(ch.top_bars(chart_df[["label", "valeur"]], height=max(220, 22 * len(chart_df)),
                                 colors=colors, value_format=fmt_int, hover_extra=extra), "mm_poles")
                st.markdown(_poles_legend_html(), unsafe_allow_html=True)

    source_note(C.SOURCE_NOTE)


def _poles_legend_html() -> str:
    items = "".join(
        f'<span style="display:inline-flex;align-items:center;margin-right:16px;font-size:12.5px;color:#334155">'
        f'<i style="background:{color};width:10px;height:10px;border-radius:3px;'
        f'display:inline-block;margin-right:6px"></i>{label}</span>'
        for label, color in [("Pôle fragile (≤ 2 établissements)", C.COLORS["red"]),
                             ("Pôle non fragile", C.COLORS["muted"])]
    )
    return f'<div style="margin-top:6px">{items}</div>'


def _mm_hover(table: pd.DataFrame) -> list[str]:
    """Lignes d'info-bulle (population, agents, taux) — remplace le tableau « Détail complet »."""
    lines = []
    for _, row in table.iterrows():
        parts = []
        if pd.notna(row.get("population")):
            parts.append(f"Population : {fmt_int(row['population'])}")
        if pd.notna(row.get("n_mm")):
            parts.append(f"Agents Mobile Money : {fmt_int(row['n_mm'])}")
        if pd.notna(row.get("mm_10k")):
            parts.append(f"Agents / 10 000 hab. : {fmt_dec(row['mm_10k'], 2)}")
        lines.append("<br>".join(parts))
    return lines


def _fr_interval(text, flip: bool = False) -> str:
    """« [0.044 ; 0.212] » -> « [0,044 ; 0,212] » (virgule décimale, signe moins typographique).
    `flip` : intervalle de l'écart opposé (« [a ; b] » devient « [−b ; −a] »)."""
    try:
        lo, hi = (float(x) for x in str(text).strip("[] ").split(";"))
    except ValueError:
        return str(text).replace(".", ",").replace("-", "−")
    if flip:
        lo, hi = -hi, -lo
    return f"[{fmt_signed(lo, 3, '') if lo < 0 else fmt_dec(lo, 3)} ; {fmt_signed(hi, 3, '') if hi < 0 else fmt_dec(hi, 3)}]"


def _gini_hover(ds: Datasets, table: pd.DataFrame) -> dict[str, list[str]]:
    """Info-bulle de « Concentration territoriale » : pour chaque échelle et chaque réseau, indice de
    Gini, intervalle de confiance à 95 %, nombre de territoires comparés, lecture de l'indice, écart
    avec l'autre réseau et significativité de cet écart (tous issus de la table gini_desserte)."""
    raw = ds.get("gini_desserte")
    if raw.empty:
        return {}
    raw = raw.set_index("niveau")
    # nom de la série -> (réseau, colonne d'intervalle, autre réseau, signe appliqué à « Gini MM − Gini formel »
    # pour obtenir l'écart de CE réseau par rapport à l'autre)
    series = {
        "Gini établissements formels": ("établissements formels", "IC95 formel", "agents Mobile Money", -1),
        "Gini agents MM": ("agents Mobile Money", "IC95 MM", "établissements formels", 1),
    }
    out: dict[str, list[str]] = {}
    for name, (label, ci_col, other, sign) in series.items():
        lines = []
        for niveau in table.index:
            if niveau not in raw.index:
                lines.append("")
                continue
            r = raw.loc[niveau]
            # « région (6) » -> échelle « région », 6 territoires
            echelle, _, count = str(niveau).partition(" (")
            count = count.rstrip(")")
            gap = float(r["Gini MM − Gini formel"]) * sign
            verdict = "plus concentré" if gap > 0 else "moins concentré" if gap < 0 else "aussi concentré"
            significant = str(r["différence significative"]).strip().lower() == "true"
            parts = [
                f"Territoires comparés : <b>{count}</b> ({echelle}s)" if count else f"Échelle : {echelle}",
                f"Intervalle de confiance à 95 % : <b>{_fr_interval(r[ci_col])}</b>",
                "Lecture : 0 = répartition parfaitement égale entre territoires, "
                f"1 = tous les {label} dans un seul territoire",
                f"Écart avec les {other} : <b>{fmt_signed(gap, 2, '')}</b> ({verdict})",
                f"Écart {'statistiquement significatif' if significant else 'non significatif'} "
                f"(IC95 de l'écart : {_fr_interval(r['IC95 de la différence'], flip=sign < 0)})",
            ]
            lines.append("<br>".join(parts))
        out[name] = lines
    return out
