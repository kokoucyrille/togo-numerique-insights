"""Menu 5 — Inclusion territoriale : croisements avec la population (RGPH-5, 2022)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from components import charts as ch
from components import territorial_map as tmap
from components.kpi import kpi_row, stat_strip
from components.layout import (
    card_title, context_bar, empty_state, legend, page_header, palier_legend, plot, source_note,
)
from utils import config as C
from utils import metrics as M
from utils.data_loader import Datasets
from utils.filters import Filters
from utils.formatting import fmt_dec, fmt_int, fmt_pct


def render(ds: Datasets, f: Filters) -> None:
    page_header("Inclusion territoriale", "Croisement des données numériques et financières avec la population (RGPH-5, 2022).")
    context_bar([
        ("Région", list(f.region)), ("Préfecture", list(f.prefecture)), ("Commune", list(f.commune)),
        ("Canton", list(f.canton)),
    ])

    kpi_row(M.inclusion_kpis(ds))

    map_col, visual_col = st.columns(2, gap="medium")
    with map_col:
        with st.container(key="card_it_map"):
            card_title("public", "Carte territoriale — palier de priorité par commune",
                      "Couleur = palier · taille = population")
            tmap.render(ds, f, key="it_map", value_col="population", unit="hab.", color_by="palier",
                       height=420)

    with visual_col:
        with st.container(key="card_it_niveau"):
            card_title("layers", "Population par niveau de couverture formelle",
                      "Du désert d'accès (MM-only) au niveau élevé")
            table = M.typologie_niveau_formel(ds)
            if table.empty:
                empty_state(240)
            else:
                df = table.rename(columns={"niv_formel": "label", "population": "valeur"})[["label", "valeur"]]
                colors = ["#D21034", "#F28C28", "#F2B01E", "#5FAF3D", "#0B6B4F"][:len(df)]
                hover_values, hover_lines = _niveau_hover(table, M.niveau_formel_ranges(ds))
                plot(ch.vertical_bars(df, height=320, percent=False, colors=colors,
                                      hover_values=hover_values, hover_extra=hover_lines), "it_niveau")

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        with st.container(key="card_it_dispersion"):
            card_title("scatter_plot", "Dispersion territoriale",
                      "Écart de desserte entre territoires, par échelle — détail au survol")
            table = M.dispersion(ds)
            if table.empty:
                empty_state(230)
            else:
                pivot = M.dispersion_bar(ds)
                colors = {"Établissements formels": C.COLORS["part"], "Agents Mobile Money": C.COLORS["yellow"]}
                hover_extra = _dispersion_hover(table, pivot, M.dispersion_extremes(ds))
                plot(ch.grouped_hbars(pivot, colors, height=200, value_format=lambda v: f"{fmt_dec(v, 2)}×",
                                      hover_extra=hover_extra, hover_suffix="×", hover_decimals=2),
                     "it_dispersion")
    with c2:
        with st.container(key="card_it_region"):
            card_title("public", "Synthèse par région", "Part de communes MM-only — médianes régionales en détail")
            table = M.typologie_regions(ds, f)
            if table.empty:
                empty_state(230)
            else:
                chart_df = table.rename(columns={"region_a": "label", "% MM-only": "valeur"})[["label", "valeur"]]
                chart_df = chart_df.sort_values("valeur", ascending=False).reset_index(drop=True)
                sorted_table = table.set_index("region_a").loc[chart_df["label"]].reset_index()
                colors = [ch.region_color(l) for l in chart_df["label"]]
                plot(ch.radial_bars(chart_df, height=360, colors=colors, value_format=lambda v: fmt_pct(v, 1),
                                    hover_extra=_region_synth_hover(sorted_table)), "it_region_mmonly")

    with st.container(key="card_it_canton"):
        card_title("pin_drop", "Lecture au niveau du canton", "Échelon le plus fin disponible — comptages uniquement, sans polygone ni population")
        cantons_df, stats = M.cantons_stats(ds, f)
        if not stats:
            empty_state(260)
        else:
            bar = M.canton_mm_only_by_region(ds, f)
            g1, g2 = st.columns([1, 1.4], gap="medium")
            with g1:
                pct = stats["scoped_mm_only"] / stats["scoped_total"] * 100 if stats["scoped_total"] else 0
                stat_strip([("Cantons MM-only", f"{stats['scoped_mm_only']} / {stats['scoped_total']} ({fmt_pct(pct)})",
                            "location_off")])
            with g2:
                if not bar.empty:
                    totals = cantons_df.groupby("region_a").size()
                    extra = [f"{int(v)} cantons MM-only sur {int(totals.get(l, 0))} cantons de la région "
                            f"({fmt_pct(v / totals.get(l, 1) * 100, 0)})" for l, v in zip(bar["label"], bar["valeur"])]
                    plot(ch.vertical_bars(bar, height=190, percent=False,
                                          colors=[ch.region_color(l) for l in bar["label"]],
                                          hover_extra=extra), "it_canton_region")

    with st.container(key="card_it_mmonly"):
        card_title("location_off", "Communes MM-only", "Aucun établissement formel — desservies uniquement par des agents Mobile Money")
        table = M.communes_mm_only_table(ds, f)
        if table.empty:
            empty_state(280)
        else:
            bar = table[["commune", "population"]].rename(columns={"commune": "label", "population": "valeur"})
            plot(ch.top_bars(bar, height=max(200, 22 * len(bar)), colors=[C.COLORS["red"]] * len(bar),
                             value_format=fmt_int, hover_extra=_mmonly_hover(table)), "it_mmonly")

    with st.container(key="card_it_prio_pref"):
        card_title("priority_high", "Priorisation par préfecture",
                  "Population en palier P1/P2 · couleur = région · pastille = part de la préfecture concernée")
        table = M.priorisation_prefectures(ds, f)
        if table.empty:
            empty_state(280)
        else:
            bar = table[["prefecture", "population P1/P2", "% de la préfecture en P1/P2", "région"]].rename(
                columns={"prefecture": "label", "population P1/P2": "valeur",
                         "% de la préfecture en P1/P2": "pct", "région": "region"})
            ratio_national = M.hab_par_formel_national(ds)
            g1, g2 = st.columns([3.4, 1], gap="medium")
            with g1:
                plot(ch.priority_bars(bar, height=max(220, 26 * len(bar)),
                                      hover_extra=_prio_pref_hover(table)), "it_prio_pref")
            with g2:
                reg_totals = bar.groupby("region")["valeur"].sum()
                total = reg_totals.sum() or 1
                order = {r: i for i, r in enumerate(C.REGION_ORDER)}
                reg_order = sorted(reg_totals.index, key=lambda r: order.get(r, 99))
                st.markdown(legend([(ch.region_color(r), r, fmt_int(reg_totals[r]),
                                    fmt_pct(reg_totals[r] / total * 100)) for r in reg_order],
                                   cls="lg--region"), unsafe_allow_html=True)
                st.markdown(palier_legend([(C.PALIER_COLORS[p], C.PALIER_LABELS[p], C.PALIER_DETAILS[p])
                                          for p in ("P1", "P2")]), unsafe_allow_html=True)
                ratio_txt = fmt_int(ratio_national) if ratio_national else "n. d."
                st.caption("Besoin indicatif : établissements formels à créer dans les communes P1/P2 pour "
                          f"atteindre le ratio national ({ratio_txt} hab. par établissement).")

    source_note(C.SOURCE_NOTE)


_NIVEAU_PLURAL = {"région": "régions", "préfecture": "préfectures", "commune": "communes"}
_RESEAU_UNITE = {
    "établissements formels (hab./établissement)": ("établissements formels", "hab./établissement"),
    "agents Mobile Money (hab./agent)": ("agents Mobile Money", "hab./agent"),
}


def _niveau_hover(table: pd.DataFrame, ranges: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Info-bulle détaillée du graphique « Population par niveau de couverture formelle » :
    en-tête (population du niveau) + communes, établissements, agents Mobile Money, ratios
    habitants par point de service, densité observée, distance médiane et indice de
    représentation (part des établissements ÷ part de la population)."""
    by_level = ranges.set_index("niv_formel") if not ranges.empty else pd.DataFrame()
    total_communes = table["communes"].sum() or 1
    total_agents = table["agents"].sum() or 1
    heads, lines = [], []
    for _, r in table.iterrows():
        heads.append(f"<b>{fmt_int(r['population'])} hab.</b> ({fmt_pct(r['% de la population'], 1)} de la population)")
        parts = [
            f"Communes : <b>{fmt_int(r['communes'])}</b> sur {fmt_int(total_communes)} "
            f"({fmt_pct(r['communes'] / total_communes * 100, 0)})",
            f"Établissements formels : <b>{fmt_int(r['établissements'])}</b> "
            f"({fmt_pct(r['% des établissements'], 1)} du total)",
            f"Agents Mobile Money : <b>{fmt_int(r['agents'])}</b> "
            f"({fmt_pct(r['agents'] / total_agents * 100, 1)} du total)",
        ]
        if r["établissements"] > 0:
            parts.append(f"Habitants par établissement : <b>{fmt_int(r['population'] / r['établissements'])}</b>")
        else:
            parts.append("Habitants par établissement : <b>aucun établissement</b>")
        if r["agents"] > 0:
            parts.append(f"Habitants par agent MM : <b>{fmt_int(r['population'] / r['agents'])}</b>")
        if r["% de la population"] > 0 and r["établissements"] > 0:
            parts.append(f"Représentation en établissements : <b>×{fmt_dec(r['% des établissements'] / r['% de la population'], 2)}</b> "
                         "(1 = part équitable)")
        if not by_level.empty and r["niv_formel"] in by_level.index:
            g = by_level.loc[r["niv_formel"]]
            if g["dens_max"] > 0:
                parts.append(f"Densité selon les communes : {fmt_dec(g['dens_min'], 2)} à {fmt_dec(g['dens_max'], 2)} "
                             "établ. / 10 000 hab.")
            else:
                parts.append("Densité : 0 établissement formel dans ces communes")
            if "dist_med" in g.index and pd.notna(g["dist_med"]):
                parts.append(f"Distance médiane au point formel : {fmt_dec(g['dist_med'], 1)} km")
        lines.append("<br>".join(parts))
    return heads, lines


def _dispersion_hover(table: pd.DataFrame, pivot: pd.DataFrame, extremes: dict) -> dict[str, list[str]]:
    """Info-bulle détaillée par échelle et par réseau : nombre de territoires comparés, écart entre
    les mieux et les moins bien desservis (lecture en clair), territoires extrêmes et médiane,
    rapport max / min et coefficient de variation."""
    rename_reseau = {
        "établissements formels (hab./établissement)": "Établissements formels",
        "agents Mobile Money (hab./agent)": "Agents Mobile Money",
    }
    hover: dict[str, list[str]] = {}
    for orig, disp in rename_reseau.items():
        label_reseau, unit = _RESEAU_UNITE[orig]
        lines = []
        for niveau in pivot.index:
            row = table[(table["niveau"] == niveau) & (table["réseau"] == orig)]
            if row.empty:
                lines.append("")
                continue
            r = row.iloc[0]
            plural = _NIVEAU_PLURAL.get(niveau, niveau)
            parts = [
                f"Lecture : les 10 % de {plural} les moins bien desservies comptent au moins "
                f"<b>{fmt_dec(r['P90 / P10'], 1)} fois</b> plus d'{unit.replace('hab./', 'habitants par ')} "
                f"que les 10 % les mieux desservies",
                f"Territoires comparés : <b>{fmt_int(r['unités'])}</b> {plural}",
            ]
            ext = extremes.get((niveau, orig))
            if ext:
                parts += [
                    f"Mieux desservi : {ext['min_name'].title()} ({fmt_int(ext['min'])} {unit})",
                    f"Médiane : {fmt_int(ext['med'])} {unit}",
                    f"Moins bien desservi : {ext['max_name'].title()} ({fmt_int(ext['max'])} {unit})",
                ]
            parts += [
                f"Rapport max / min : <b>×{fmt_dec(r['max / min'], 1)}</b>",
                f"Coefficient de variation : <b>{fmt_dec(r['coefficient de variation'], 2)}</b> "
                "(plus il est élevé, plus les écarts sont marqués)",
            ]
            lines.append("<br>".join(parts))
        hover[disp] = lines
    return hover


def _region_synth_hover(table: pd.DataFrame) -> list[str]:
    lines = []
    for _, row in table.iterrows():
        parts = [f"Communes : {fmt_int(row['communes'])}", f"Population : {fmt_int(row['population'])}",
                 f"Communes MM-only : {fmt_int(row['communes MM-only'])}",
                 f"Étab. / 10k hab. (médiane) : {fmt_dec(row['établissements / 10 000 hab. (médiane)'], 2)}",
                 f"Agents MM / 10k hab. (médiane) : {fmt_dec(row['agents MM / 10 000 hab. (médiane)'], 2)}",
                 f"Distance médiane : {fmt_dec(row['distance médiane au point formel (km)'], 1)} km"]
        lines.append("<br>".join(parts))
    return lines


def _mmonly_hover(table: pd.DataFrame) -> list[str]:
    lines = []
    for _, row in table.iterrows():
        parts = [f"Préfecture : {row['préfecture']}", f"Région : {row['région']}",
                 f"Agents MM : {fmt_int(row['agents MM'])}",
                 f"Distance médiane : {fmt_dec(row['distance médiane au point formel (km)'], 1)} km",
                 f"Maillage MM ténu : {'oui' if row['maillage MM ténu (< ½ moyenne nationale)'] else 'non'}"]
        lines.append("<br>".join(parts))
    return lines


def _prio_pref_hover(table: pd.DataFrame) -> list[str]:
    """Info-bulle volontairement courte : trois lignes, sans rappel méthodologique (les paliers
    sont définis dans la légende à droite du graphique, le besoin indicatif juste en dessous)."""
    lines = []
    for _, row in table.iterrows():
        parts = [
            f"Région : <b>{row['région']}</b>",
            f"Communes P1/P2 : <b>{fmt_int(row['communes P1/P2'])}</b> "
            f"(dont {fmt_int(row['communes MM-only'])} MM-only)",
            f"Besoin indicatif : <b>{fmt_int(row['besoin indicatif (points, référence nationale)'])}</b> établissements",
        ]
        lines.append("<br>".join(parts))
    return lines
