"""Cartes KPI épurées (style Power BI) et blocs de statistiques compacts."""
from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from utils.formatting import fmt_dec, fmt_int, fmt_pct, fmt_signed, html_escape

from .layout import icon


@dataclass
class Kpi:
    key: str
    label: str
    icon: str
    tone: str                    # green | blue | yellow | purple | teal
    value: float | None
    kind: str                    # int | pct | dec
    delta: float | None = None
    delta_unit: str = "%"
    delta_label: str | None = None
    definition: str = ""


def format_kpi_value(kpi: Kpi) -> str:
    if kpi.value is None:
        return "—"
    if kpi.kind == "pct":
        return fmt_pct(kpi.value, 1)
    if kpi.kind == "dec":
        return fmt_dec(kpi.value, 0 if float(kpi.value).is_integer() else 1)
    return fmt_int(kpi.value)


def _cmp_row(k: Kpi | None, color: str) -> str:
    if k is None or k.value is None:
        return f'<div class="kpi__cmp"><i style="background:{color}"></i><span class="kpi__cv">—</span></div>'
    delta = ""
    if k.delta is not None:
        direction = "up" if k.delta >= 0 else "down"
        arrow = "trending_up" if k.delta >= 0 else "trending_down"
        delta = (f'<span class="kpi__cd kpi__cd--{direction}">{icon(arrow)}'
                 f"{fmt_signed(k.delta, 1, k.delta_unit)}</span>")
    return (f'<div class="kpi__cmp"><i style="background:{color}"></i>'
            f'<span class="kpi__cv">{format_kpi_value(k)}</span>{delta}</div>')


def kpi_row(kpis: list[Kpi], compare: list[list[Kpi | None]] | None = None,
            compare_colors: list[str] | None = None) -> None:
    """Rangée de cartes KPI ; en comparaison, chaque carte porte une ligne par région."""
    cards = []
    for idx, k in enumerate(kpis):
        if compare:
            body = "".join(_cmp_row(series[idx], (compare_colors or [])[i % len(compare_colors or [1])])
                          for i, series in enumerate(compare))
            cards.append(
                f'<div class="kpi kpi--{k.tone} kpi--compare" title="{html_escape(k.definition)}">'
                f'<div class="kpi__icon">{icon(k.icon)}</div>'
                f'<div class="kpi__body"><div class="kpi__label">{html_escape(k.label)}</div>{body}</div></div>'
            )
            continue
        if k.value is None:
            delta = '<div class="kpi__delta kpi__delta--na">Donnée non disponible</div>'
        elif k.delta is not None:
            direction = "up" if k.delta >= 0 else "down"
            arrow = "trending_up" if k.delta >= 0 else "trending_down"
            delta = (
                f'<div class="kpi__delta kpi__delta--{direction}">{icon(arrow)}'
                f"<b>{fmt_signed(k.delta, 1, k.delta_unit)}</b></div>"
                f'<div class="kpi__ref">{html_escape(k.delta_label or "")}</div>'
            )
        else:
            delta = ""
        cards.append(
            f'<div class="kpi kpi--{k.tone}" title="{html_escape(k.definition)}">'
            f'<div class="kpi__icon">{icon(k.icon)}</div>'
            '<div class="kpi__body">'
            f'<div class="kpi__label">{html_escape(k.label)}</div>'
            f'<div class="kpi__value">{format_kpi_value(k)}</div>'
            f"{delta}</div></div>"
        )
    cols = max(1, min(len(kpis), 6))
    st.markdown(f'<div class="kpi-grid" style="--cols:{cols}">{"".join(cards)}</div>',
               unsafe_allow_html=True)


def insight_cards(tiles: list[tuple[str, str, str, str]], notes: dict[int, str] | None = None) -> None:
    """Grille sur quatre colonnes maximum : [(libellé, valeur, icône, ton)].

    Ton parmi green | blue | yellow | red | purple — un accent par nature de constat
    (progression, rythme, lacune, priorité, structure de marché), pour une lecture
    rapide par un décideur. `notes` associe l'index d'une carte à une courte précision
    affichée sous sa valeur (jamais un bloc de texte partagé sous toute la grille).
    """
    notes = notes or {}
    cards = []
    for i, (label, text, mat, tone) in enumerate(tiles):
        note_html = f'<div class="insight__note">{html_escape(notes[i])}</div>' if i in notes else ""
        cards.append(
            f'<div class="insight insight--{tone}">'
            f'<div class="insight__top"><span class="insight__icon">{icon(mat)}</span>'
            f'<span class="insight__label">{html_escape(label)}</span></div>'
            f'<div class="insight__value">{text}</div>'
            f"{note_html}</div>"
        )
    st.markdown(f'<div class="insight-grid" style="--cols:{max(1, min(4, len(cards)))}">{"".join(cards)}</div>',
               unsafe_allow_html=True)


def stat_strip(tiles: list[tuple[str, str, str]]) -> None:
    """Bloc de statistiques compactes : [(libellé, valeur déjà formatée, icône)]."""
    items = []
    for label, text, mat in tiles:
        items.append(
            '<div class="tile tile--ind">'
            f'<div class="tile__head"><span class="tile__icon">{icon(mat)}</span>'
            f'<span class="tile__label">{html_escape(label)}</span></div>'
            f'<div class="tile__value tile__value--green">{text}</div></div>'
        )
    st.markdown(f'<div class="strip strip--ind" style="--cols:{max(1, len(items))}">{"".join(items)}</div>',
               unsafe_allow_html=True)
