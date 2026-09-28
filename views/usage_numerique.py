"""Menu 2 — Usage numérique : évolution de l'usage Internet et du marché télécom."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from components import charts as ch
from components.kpi import kpi_row
from components.layout import card_title, context_bar, empty_state, page_header, plot, source_note
from utils import config as C
from utils import metrics as M
from utils.data_loader import Datasets
from utils.filters import Filters, apply_years
from utils.formatting import fmt_dec, fmt_int, fmt_pct, fmt_signed


def render(ds: Datasets, f: Filters) -> None:
    page_header("Usage numérique", "Évolution de l'usage Internet, du marché télécom et de la transition technologique.")
    context_bar([("Période", [f"{f.year_start} – {f.year_end}"]), ("Opérateur GSM", list(f.gsm_operateur))])

    kpi_row(M.usage_kpis(ds, f))

    with st.container(key="card_un_evol"):
        card_title("show_chart", "Usage Internet — série longue", "Individus ayant utilisé Internet, % de la population, 2000-2024")
        series = M.usage_series(ds, f)
        if series.empty:
            empty_state(260)
        else:
            rup_year, _, _ = M.rupture_info(ds)
            plot(ch.evolution_chart(series, height=260, percent=True, rupture_year=rup_year), "un_evol")
        rythme = M.rupture_bar_data(ds)
        if not rythme.empty:
            st.markdown('<p class="section-note">Rythme annuel de progression, avant / après la rupture '
                       "de tendance (points de pourcentage par an) :</p>", unsafe_allow_html=True)
            periods = ds.get("internet_usage_periodes")
            hover_extra = [
                f"{row['rôle']}<br>Début : {fmt_pct(row['début (%)'], 1)} → Fin : {fmt_pct(row['fin (%)'], 1)}"
                f"<br>Gain : {fmt_dec(row['gain (pp)'], 1)} pts"
                f"<br>Croissance annuelle moy. : {fmt_pct(row['croissance annuelle moyenne (%)'], 1)}"
                for _, row in periods.iterrows()
            ]
            plot(ch.vertical_bars(rythme, height=160, percent=False,
                                  colors=[C.COLORS["muted"]] + [C.COLORS["green"]] * (len(rythme) - 1),
                                  hover_extra=hover_extra),
                 "un_rythme")

    with st.container(key="card_un_cmp"):
        card_title("stacked_line_chart", "Usage vs abonnements vs cartes SIM", "Pour 100 habitants — 2013-2019")
        table = M.usage_vs_abon_sim(ds, f)
        if table.empty:
            empty_state(280)
        else:
            plot(ch.multi_line(table, height=280, percent=False), "un_cmp")

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        with st.container(key="card_un_parts"):
            card_title("pie_chart", "Parts de marché GSM",
                      f"{' · '.join(f.gsm_operateur)}, 2013-2019" if f.gsm_operateur else "Togocom vs Moov, 2013-2019")
            table = M.market_share(ds, f)
            if table.empty:
                empty_state(260)
            else:
                colors = {"Part Togocom (%)": C.OPERATEUR_COLORS["Togocom"], "Part Moov (%)": C.OPERATEUR_COLORS["Moov"]}
                plot(ch.stacked_bars(table, height=260, colors=[colors[c] for c in table.columns], percent=True), "un_parts")
    with c2:
        with st.container(key="card_un_hhi"):
            card_title("signal_cellular_alt", "Concentration du marché (HHI)", "Seuil de forte concentration : 2 500")
            m = apply_years(ds.get("marche_gsm_2013_2019"), f, "annee")
            if m.empty:
                empty_state(260)
            else:
                hhi = m.set_index("annee")["HHI"].sort_index()
                plot(ch.evolution_chart(hhi, height=260, percent=False), "un_hhi")

    c3, c4 = st.columns(2, gap="medium")
    with c3:
        with st.container(key="card_un_tech"):
            single_op = f.gsm_operateur[0] if len(f.gsm_operateur) == 1 else None
            card_title("network_cell", "Transition technologique mobile",
                      f"{single_op} — part de la 2G vs de la 3G+4G" if single_op
                      else "Part du trafic Internet mobile par génération")
            table = M.tech_transition(ds, f)
            if table.empty:
                empty_state(280)
            else:
                colors = ["#94A3B8", "#0B6B4F"] if len(table.columns) == 2 else ["#94A3B8", "#2F80ED", "#0B6B4F"]
                plot(ch.stacked_bars(table, height=280, colors=colors, percent=True), "un_tech")
    with c4:
        with st.container(key="card_un_fibre"):
            card_title("cable", "Part de la fibre (FTTH) dans l'Internet fixe", "2013-2019")
            series = M.fibre_share(ds, f)
            if series.empty:
                empty_state(280)
            else:
                plot(ch.evolution_chart(series, height=280, percent=True), "un_fibre")

    with st.container(key="card_un_finance"):
        card_title("payments", "Chiffre d'affaires et investissement du secteur GSM", "Milliards de FCFA, 2013-2019")
        fin = M.market_ca_invest(ds, f)
        if fin.empty:
            empty_state(220)
        else:
            g1, g2 = st.columns(2, gap="medium")
            years = list(fin.index)
            with g1:
                df = pd.DataFrame({"label": [str(y) for y in years], "valeur": fin["Chiffre d'affaires (Mds FCFA)"]})
                st.caption("Chiffre d'affaires")
                heads, lines = _gsm_hover(ds, years, "ca")
                plot(ch.vertical_bars(df, height=200, percent=False, hover_values=heads, hover_extra=lines), "un_ca")
            with g2:
                df = pd.DataFrame({"label": [str(y) for y in years], "valeur": fin["Investissement (Mds FCFA)"]})
                st.caption("Investissement")
                heads, lines = _gsm_hover(ds, years, "invest")
                plot(ch.vertical_bars(df, height=200, percent=False, hover_values=heads, hover_extra=lines), "un_invest")

    source_note(C.SOURCE_NOTE)


def _gsm_hover(ds, years, kind: str) -> tuple[list[str], list[str]]:
    """Info-bulle des graphiques « Chiffre d'affaires » (kind="ca") et « Investissement »
    (kind="invest") : valeur de l'année en en-tête, puis évolution sur un an, ratio
    investissement / CA, CA par abonné, parc d'abonnés, cumul et position dans la série.
    Les évolutions s'appuient sur la série complète 2013-2019, indépendamment du curseur de
    période (l'année précédente reste donc disponible pour la première année affichée)."""
    full = ds.get("marche_gsm_2013_2019").set_index("annee").sort_index()
    ca_col, inv_col = "Chiffre d'affaires (Mds FCFA)", "Investissement (Mds FCFA)"
    col = ca_col if kind == "ca" else inv_col
    top, bottom = full[col].idxmax(), full[col].idxmin()
    what = "chiffre d'affaires" if kind == "ca" else "investissement"
    heads, lines = [], []
    for y in years:
        r = full.loc[y]
        prev = full.loc[y - 1] if (y - 1) in full.index else None
        heads.append(f"<b>{fmt_dec(r[col], 1)} Mds FCFA</b>")
        parts: list[str] = []
        if kind == "ca":
            if pd.notna(r["Croissance du CA (%)"]):
                delta = r[ca_col] - prev[ca_col] if prev is not None else None
                parts.append(f"Évolution sur un an : <b>{fmt_signed(r['Croissance du CA (%)'], 1)}</b>"
                             + (f" ({fmt_signed(delta, 1, ' Mds')})" if delta is not None else ""))
            else:
                parts.append("Première année de la série (pas de point de comparaison)")
            parts.append(f"Investissement de l'année : <b>{fmt_dec(r[inv_col], 1)} Mds FCFA</b> "
                         f"({fmt_pct(r['Investissement / CA (%)'], 1)} du CA)")
            parts.append(f"CA par abonné GSM : <b>{fmt_int(r['CA par abonné GSM (FCFA/an)'])} FCFA/an</b>")
        else:
            parts.append(f"Part du chiffre d'affaires : <b>{fmt_pct(r['Investissement / CA (%)'], 1)}</b> "
                         f"(CA : {fmt_dec(r[ca_col], 1)} Mds FCFA)")
            if prev is not None and prev[inv_col]:
                delta = r[inv_col] - prev[inv_col]
                parts.append(f"Évolution sur un an : <b>{fmt_signed(delta / prev[inv_col] * 100, 1)}</b> "
                             f"({fmt_signed(delta, 1, ' Mds')})")
            else:
                parts.append("Première année de la série (pas de point de comparaison)")
            cumul = full.loc[full.index <= y, inv_col].sum()
            parts.append(f"Cumul depuis {int(full.index.min())} : <b>{fmt_dec(cumul, 1)} Mds FCFA</b>")
        subs = f"Abonnés GSM : {fmt_int(r['Abonnés GSM'])}"
        if pd.notna(r["Croissance des abonnés GSM (%)"]):
            subs += f" ({fmt_signed(r['Croissance des abonnés GSM (%)'], 1)} sur un an)"
        parts.append(subs)
        parts.append(f"Télédensité mobile : {fmt_pct(r['Télédensité mobile (%)'], 1)}")
        if y == top:
            parts.append(f"<i>Point haut de la série en {what}</i>")
        elif y == bottom:
            parts.append(f"<i>Point bas de la série en {what}</i>")
        lines.append("<br>".join(parts))
    return heads, lines
