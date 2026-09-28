"""Menu 1 — Vue d'ensemble : synthèse nationale et carte territoriale interactive."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from components import charts as ch
from components import territorial_map as tmap
from components.kpi import insight_cards, kpi_row
from components.layout import card_title, context_bar, empty_state, hero, legend, page_header, plot, source_note
from utils import config as C
from utils import metrics as M
from utils.data_loader import Datasets
from utils.filters import Filters
from utils.formatting import fmt_dec, fmt_int, fmt_pct


def render(ds: Datasets, f: Filters) -> None:
    hero()
    page_header(
        "Vue d'ensemble",
        "Économie numérique et inclusion financière au Togo — synthèse des résultats validés.",
    )
    context_bar([
        ("Région", list(f.region)), ("Préfecture", list(f.prefecture)), ("Commune", list(f.commune)),
        ("Canton", list(f.canton)), ("Type d'établissement", list(f.etab_categorie)),
        ("Opérateur MM", list(f.mm_operateur)),
    ])

    kpi_row(M.overview_kpis(ds))

    map_col, visual_col = st.columns(2, gap="medium")
    with map_col:
        with st.container(key="card_ov_map"):
            card_title("public", "Carte territoriale — points d'accès financiers",
                      "Établissements formels + agents Mobile Money · cliquez une région ou une commune")
            tmap.render(ds, f, key="ov_map", value_col="n_points", unit="points d'accès",
                      value_format=fmt_int, height=420, show_etab=True)

    with visual_col:
        with st.container(key="card_ov_disp"):
            card_title("bar_chart", "Habitants par établissement formel",
                      "Par région — plus haut = moins bien desservi")
            bar = M.accessibility_bar(ds, f, "hab_par_formel")
            if bar.empty:
                empty_state(280)
            else:
                hover_values, hover_lines = _hab_par_formel_hover(bar, M.accessibility_details(ds, f),
                                                                 M.hab_par_formel_national(ds))
                plot(ch.vertical_bars(bar, height=360, percent=False,
                                      colors=[ch.region_color(l) for l in bar["label"]],
                                      hover_values=hover_values, hover_extra=hover_lines), "ov_disp")

    year, usage_val, usage_gain = M.usage_last(ds)
    rup_year, rythme_avant, rythme_apres = M.rupture_info(ds)
    tot = M.national_totals(ds)
    hhi_year, hhi_val = M.hhi_last(ds)
    pop = tot.get("population") or 1
    mm_only_pct = (tot.get("mm_only_population", 0) / pop * 100) if tot.get("mm_only_population") else None

    with st.container(key="card_ov_constats"):
        card_title("insights", "Constats essentiels", "Indicateurs clés, échelle nationale")
        tiles: list[tuple[str, str, str, str]] = []
        if year and usage_gain is not None:
            tiles.append(("Progression de l’usage Internet", f"+{fmt_dec(usage_gain, 1)} point en {year}", "trending_up", "green"))
        if rup_year and rythme_avant is not None and rythme_apres is not None:
            tiles.append((f"Rythme Internet avant / après {rup_year}",
                          f"{fmt_dec(rythme_avant, 2)} → {fmt_dec(rythme_apres, 2)} points/an",
                          "speed", "blue"))
        if tot.get("mm_only_communes") and mm_only_pct is not None:
            tiles.append(("Communes sans établissement formel",
                          f"{fmt_int(tot['mm_only_communes'])} communes · {fmt_pct(mm_only_pct, 1)} de la population",
                          "location_off", "red"))
        if hhi_val:
            niveau = "forte" if hhi_val > 2500 else "modérée"
            tiles.append((f"Concentration marché télécom ({hhi_year})", f"HHI {hhi_val:,.0f} — {niveau}".replace(",", " "), "pie_chart", "purple"))
        if tiles:
            insight_cards(tiles)
        else:
            empty_state(120)

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        with st.container(key="card_ov_formel_cat"):
            card_title("account_balance", "Établissements financiers, par catégorie", "National")
            totals = M.national_category_totals(ds)
            if totals is None:
                empty_state(230)
            else:
                df = pd.DataFrame({"label": totals.index, "valeur": totals.values})
                df = df[df["valeur"] > 0].sort_values("valeur", ascending=False)
                colors = ch.sector_colors(list(df["label"]))
                plot(ch.donut(df, "établissements", height=230, colors=colors), "ov_formel_cat")
                total = df["valeur"].sum()
                st.markdown(legend([(c, l, fmt_int(v), fmt_pct(v / total * 100))
                                    for c, l, v in zip(colors, df["label"], df["valeur"])]),
                           unsafe_allow_html=True)
    with c2:
        with st.container(key="card_ov_mm_op"):
            card_title("smartphone", "Agents Mobile Money, par opérateur", "National")
            totals = M.national_operator_totals(ds)
            if totals is None:
                empty_state(230)
            else:
                df = pd.DataFrame({"label": totals.index, "valeur": totals.values})
                df = df[df["valeur"] > 0].sort_values("valeur", ascending=False)
                colors = [C.OPERATEUR_COLORS.get(l, C.OTHER_COLOR) for l in df["label"]]
                plot(ch.donut(df, "agents MM", height=230, colors=colors), "ov_mm_op")
                total = df["valeur"].sum()
                st.markdown(legend([(c, l, fmt_int(v), fmt_pct(v / total * 100))
                                    for c, l, v in zip(colors, df["label"], df["valeur"])]),
                           unsafe_allow_html=True)

    source_note(C.SOURCE_NOTE)


def _hab_par_formel_hover(bar: pd.DataFrame, details: pd.DataFrame, national: float | None) -> tuple[list[str], list[str]]:
    """Info-bulle du graphique « Habitants par établissement formel » : en-tête (ratio de la région)
    puis population, établissements, densité, comparaison au ratio national, représentation
    (part des établissements ÷ part de la population) et distance médiane au point formel."""
    heads, lines = [], []
    for label, value in zip(bar["label"], bar["valeur"]):
        heads.append(f"<b>{fmt_int(value)} hab.</b> par établissement formel")
        if label not in details.index:
            lines.append("")
            continue
        r = details.loc[label]
        parts = [
            f"Population : <b>{fmt_int(r['population'])}</b> ({fmt_pct(r['part_pop_pct'], 1)} du pays)",
            f"Établissements formels : <b>{fmt_int(r['n_formel'])}</b> ({fmt_pct(r['part_formel_pct'], 1)} du total)",
            f"Densité : <b>{fmt_dec(r['formel_10k'], 2)}</b> établissements pour 10 000 hab.",
        ]
        if national and pd.notna(value):
            ecart = value / national
            verdict = "moins bien" if ecart > 1 else "mieux" if ecart < 1 else "aussi bien"
            parts.append(f"Comparé au ratio national ({fmt_int(national)}) : <b>×{fmt_dec(ecart, 2)}</b> "
                         f"({verdict} desservie)")
        if pd.notna(r.get("ratio_repr_formel")):
            parts.append(f"Représentation en établissements : <b>×{fmt_dec(r['ratio_repr_formel'], 2)}</b> "
                         "(1 = part équitable)")
        if pd.notna(r.get("dist_med_km")):
            parts.append(f"Distance médiane au point formel : <b>{fmt_dec(r['dist_med_km'], 1)} km</b>")
        lines.append("<br>".join(parts))
    return heads, lines
