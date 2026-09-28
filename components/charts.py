"""Figures Plotly au style institutionnel (fond transparent, sobres, lisibles)."""
from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go

from utils import config as C
from utils.formatting import fmt_dec, fmt_int, fmt_pct
from utils.geo import load_regions_geojson

FONT = "Inter, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Liberation Sans', sans-serif"
NAVY, SLATE, MUTED, GRID = (C.COLORS[k] for k in ("navy", "slate", "muted", "grid"))
PALETTE = C.SECTOR_COLORS + C.EXTRA_COLORS


def _layout(height: int, **extra) -> dict:
    base = dict(
        height=height,
        margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=12, color=SLATE),
        separators=", ",
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=GRID,
                        font=dict(family=FONT, size=12, color=NAVY)),
        dragmode=False,
    )
    base.update(extra)
    return base


def _text_color(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#FFFFFF" if (0.299 * r + 0.587 * g + 0.114 * b) < 150 else NAVY


def region_color(name: str, index: int = 0) -> str:
    return C.REGION_COLORS.get(name, C.FALLBACK_COLORS[index % len(C.FALLBACK_COLORS)])


def sector_colors(labels: list[str]) -> list[str]:
    colors, i = [], 0
    for label in labels:
        if label == "Autres":
            colors.append(C.OTHER_COLOR)
        else:
            colors.append(PALETTE[i % len(PALETTE)])
            i += 1
    return colors


# --------------------------------------------------------------------------- #
# Carte régionale (polygones, sans dépendance réseau)
# --------------------------------------------------------------------------- #
def _polygon_xy(geometry: dict) -> tuple[list, list]:
    polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
    xs: list = []
    ys: list = []
    for polygon in polygons:
        for ring in polygon:
            xs += [pt[0] for pt in ring] + [None]
            ys += [pt[1] for pt in ring] + [None]
    return xs, ys


def region_map(regions: pd.DataFrame | None, height: int = 420, unit: str = "",
               value_format=fmt_int, highlight=None,
               colors: dict[str, str] | None = None) -> go.Figure:
    """Carte des 6 régions (5 polygones + Grand Lomé en pastille) ; `regions` : colonnes label/valeur."""
    geo = load_regions_geojson()
    values = {} if regions is None or regions.empty else dict(zip(regions["label"], regions["valeur"]))
    parts = {} if regions is None or regions.empty or "part" not in regions else \
        dict(zip(regions["label"], regions["part"]))
    colors = colors or {}
    highlighted = {highlight} if isinstance(highlight, str) else set(highlight or ())
    fig = go.Figure()
    polygon_names: set[str] = set()
    lons: list[float] = []
    lats: list[float] = []

    points = [C.GEO_POINTS[n] for n in values if n in C.GEO_POINTS]
    for i, feature in enumerate(geo["features"]):
        props = feature["properties"]
        geo_name = props["region"]
        data_name = C.REGION_GEO_ALIAS.get(geo_name, geo_name)
        polygon_names.add(data_name)
        has = data_name in values
        selected = not values and data_name in highlighted
        color = colors.get(data_name) or region_color(data_name, i) if (has or selected) else C.COLORS["empty"]
        hover = (f"<b>{data_name}</b><br>{value_format(values[data_name])} {unit}"
                 + (f" ({fmt_pct(parts[data_name])})" if data_name in parts else "")
                 if has else f"<b>{data_name}</b><br>"
                 + ("Région sélectionnée" if selected else "Donnée non disponible"))
        xs, ys = _polygon_xy(feature["geometry"])
        lons += [x for x in xs if x is not None]
        lats += [y for y in ys if y is not None]
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", fill="toself", fillcolor=color, name=data_name,
            line=dict(color="#FFFFFF", width=1.6), hoveron="fills", text=hover, hoverinfo="text",
            showlegend=False,
        ))
        label = f"{data_name}<br><b>{value_format(values[data_name])}</b>" if has else data_name
        near = any(abs(props["cy"] - lat) < 0.5 and abs(props["cx"] - lon) < 0.6 for lat, lon in points)
        fig.add_trace(go.Scatter(
            x=[props["cx"]], y=[props["cy"] + (0.2 if near else 0)], mode="text", text=[label],
            hoverinfo="skip", showlegend=False,
            textfont=dict(family=FONT, size=11,
                          color=_text_color(color) if (has or selected) else MUTED),
        ))

    extra = [(n, v) for n, v in values.items() if n not in polygon_names and n in C.GEO_POINTS]
    if extra:
        vmax = max(v for _, v in extra) or 1
        for i, (name, value) in enumerate(extra):
            lat, lon = C.GEO_POINTS[name]
            fig.add_trace(go.Scatter(
                x=[lon], y=[lat], mode="markers+text", showlegend=False,
                marker=dict(size=12 + 16 * math.sqrt(value / vmax), color=colors.get(name) or region_color(name, i),
                            line=dict(color="#FFFFFF", width=1.5)),
                text=[f"{name}<br><b>{value_format(value)}</b>"], textposition="bottom center",
                textfont=dict(family=FONT, size=11, color=NAVY),
                hovertemplate=f"<b>{name}</b><br>{value_format(value)} {unit}"
                              + (f" ({fmt_pct(parts[name])})" if name in parts else "")
                              + "<extra></extra>",
            ))

    x0, x1 = min(lons) - 0.55, max(lons) + 0.55
    y0, y1 = min(lats) - 0.7, max(lats) + 0.15
    fig.update_layout(**_layout(height, margin=dict(l=0, r=0, t=0, b=0), showlegend=False))
    fig.update_xaxes(visible=False, range=[x0, x1], constrain="domain", fixedrange=True)
    fig.update_yaxes(visible=False, range=[y0, y1], scaleanchor="x", scaleratio=1,
                     constrain="domain", fixedrange=True)
    return fig


# --------------------------------------------------------------------------- #
# Séries temporelles
# --------------------------------------------------------------------------- #
def evolution_chart(series: pd.Series, height: int = 230, name: str = "", percent: bool = False,
                    rupture_year: int | None = None) -> go.Figure:
    years = [int(y) for y in series.index]
    values = [float(v) for v in series.values]
    fmt = (lambda v: fmt_pct(v, 1)) if percent else fmt_int
    fig = go.Figure(go.Scatter(
        x=years, y=values, mode="lines+markers+text", name=name,
        line=dict(color="#0A8F5A", width=2.6),
        fill="tozeroy", fillcolor="rgba(14,159,110,0.12)",
        marker=dict(size=7, color="#FFFFFF", line=dict(color="#0A8F5A", width=2.2)),
        text=[fmt(v) if i % max(1, len(values) // 8) == 0 or i == len(values) - 1 else ""
              for i, v in enumerate(values)],
        textposition="top center", textfont=dict(size=10.5, color=NAVY),
        hovertemplate="%{x} : <b>%{y:,.2f}" + ("%" if percent else "") + "</b><extra></extra>",
        cliponaxis=False,
    ))
    top = max(values) if values else 1
    if rupture_year is not None and rupture_year in years:
        fig.add_vline(x=rupture_year, line=dict(color=C.COLORS["red"], width=1.4, dash="dot"))
        fig.add_annotation(x=rupture_year, y=top * 1.18, text=f"Rupture {rupture_year}",
                           showarrow=False, font=dict(size=10.5, color=C.COLORS["red"]))
    fig.update_layout(**_layout(height, margin=dict(l=46, r=18, t=26, b=26), showlegend=False))
    step = max(1, len(years) // 12)
    fig.update_xaxes(tickmode="array", tickvals=years[::step] + ([years[-1]] if years[-1] not in years[::step] else []),
                     showgrid=False, linecolor=GRID, tickfont=dict(size=10.5, color=MUTED), fixedrange=True)
    fig.update_yaxes(range=[0, top * 1.28], gridcolor=GRID, zeroline=False,
                     tickformat=",d" if not percent else ",.0f", ticksuffix="%" if percent else "",
                     tickfont=dict(size=11, color=MUTED), fixedrange=True, nticks=6)
    return fig


def multi_line(table: pd.DataFrame, height: int = 300, percent: bool = False,
              colors: list[str] | None = None) -> go.Figure:
    fig = go.Figure()
    palette = colors or PALETTE
    for i, column in enumerate(table.columns):
        fig.add_trace(go.Scatter(
            x=[int(y) for y in table.index], y=table[column], mode="lines+markers", name=str(column),
            line=dict(color=palette[i % len(palette)], width=2.2), marker=dict(size=6),
            hovertemplate="%{x} · " + str(column) + " : <b>%{y:,.1f}" + ("%" if percent else "")
                          + "</b><extra></extra>",
        ))
    fig.update_layout(**_layout(height, margin=dict(l=44, r=10, t=8, b=34),
                                legend=dict(orientation="h", y=-0.22, x=0, font=dict(size=11))))
    years = [int(y) for y in table.index]
    fig.update_xaxes(tickmode="array", tickvals=years, showgrid=False,
                     linecolor=GRID, fixedrange=True, tickfont=dict(size=11, color=MUTED))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, tickformat=",d" if not percent else ",.0f",
                     ticksuffix="%" if percent else "", fixedrange=True, tickfont=dict(size=11, color=MUTED))
    return fig


# --------------------------------------------------------------------------- #
# Répartitions
# --------------------------------------------------------------------------- #
def donut(df: pd.DataFrame, center_label: str = "", height: int = 210,
          colors: list[str] | None = None) -> go.Figure:
    colors = colors or sector_colors(list(df["label"]))
    total = df["valeur"].sum()
    fig = go.Figure(go.Pie(
        labels=df["label"], values=df["valeur"], hole=0.68, sort=False, direction="clockwise",
        marker=dict(colors=colors, line=dict(color="#FFFFFF", width=2)), textinfo="none",
        hovertemplate="<b>%{label}</b><br>%{value:,.0f} (%{percent:.1%})<extra></extra>",
        showlegend=False,
    ))
    fig.add_annotation(
        text=f"<b>{fmt_int(total)}</b><br><span style='font-size:12px;color:{SLATE}'>{center_label}</span>",
        showarrow=False, font=dict(size=20, color=NAVY, family=FONT),
    )
    fig.update_layout(**_layout(height, margin=dict(l=4, r=4, t=4, b=4)))
    return fig


def top_bars(df: pd.DataFrame, height: int = 170, colors: list[str] | None = None,
             value_format=fmt_int, hover_extra: list[str] | None = None) -> go.Figure:
    if "valeur" in df.columns and df["valeur"].isna().any():
        mask = df["valeur"].notna()
        df = df[mask].reset_index(drop=True)
        if colors is not None:
            colors = [c for c, keep in zip(colors, mask) if keep]
        if hover_extra is not None:
            hover_extra = [c for c, keep in zip(hover_extra, mask) if keep]
    n = len(df)
    if n == 0:
        fig = go.Figure()
        fig.update_layout(**_layout(height, showlegend=False))
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
        return fig
    palette = colors or (C.BAR_GRADIENT if n <= len(C.BAR_GRADIENT) else
                         [C.BAR_GRADIENT[min(i * len(C.BAR_GRADIENT) // n, 4)] for i in range(n)])
    vmax = float(df["valeur"].max()) or 1.0
    fig = go.Figure()
    fig.add_trace(go.Bar(y=df["label"], x=[vmax] * n, orientation="h",
                         marker=dict(color="#EEF2F6"), hoverinfo="skip", width=0.56))
    extra = hover_extra if hover_extra is not None else [""] * n
    customdata = [[value_format(v), (f"<br>{e}" if e else "")] for v, e in zip(df["valeur"], extra)]
    fig.add_trace(go.Bar(
        y=df["label"], x=df["valeur"], orientation="h", marker=dict(color=palette[:n]),
        width=0.56, customdata=customdata,
        hovertemplate="<b>%{y}</b> : %{customdata[0]}%{customdata[1]}<extra></extra>",
    ))
    for label, value in zip(df["label"], df["valeur"]):
        fig.add_annotation(x=vmax * 1.03, y=label, text=value_format(value), showarrow=False,
                           xanchor="left", font=dict(size=11.5, color=NAVY))
    fig.update_layout(**_layout(height, barmode="overlay", showlegend=False,
                                margin=dict(l=4, r=54, t=2, b=2)))
    fig.update_xaxes(visible=False, range=[0, vmax * 1.2], fixedrange=True)
    fig.update_yaxes(autorange="reversed", showgrid=False, tickfont=dict(size=11.5, color=NAVY),
                     fixedrange=True, automargin=True)
    return fig


def _severity_color(pct: float) -> str:
    """Couleur de sévérité alignée sur les paliers de priorité déjà utilisés sur cette
    page (carte, palier P1-P4) : plus la part du territoire en P1/P2 est élevée, plus la
    pastille se rapproche du rouge (P1), même palette que C.PALIER_COLORS."""
    if pct >= 55:
        return C.PALIER_COLORS["P1"]
    if pct >= 30:
        return C.PALIER_COLORS["P2"]
    return C.PALIER_COLORS["P3"]


def priority_bars(df: pd.DataFrame, height: int = 320, hover_extra: list[str] | None = None) -> go.Figure:
    """Classement de priorisation territoriale : longueur de barre = valeur principale
    (ex. population en palier P1/P2), couleur de barre = région (mêmes teintes que la
    carte et la synthèse régionale de la page), pastille = part (%) du territoire concerné,
    colorée selon la même échelle de sévérité que les paliers P1-P4. Deux dimensions du
    même triage lisibles d'un coup d'œil, sans rien ajouter aux données déjà calculées
    (`df` : colonnes label / valeur / pct / region)."""
    if "valeur" in df.columns and df["valeur"].isna().any():
        mask = df["valeur"].notna()
        df = df[mask].reset_index(drop=True)
        if hover_extra is not None:
            hover_extra = [c for c, keep in zip(hover_extra, mask) if keep]
    n = len(df)
    if n == 0:
        fig = go.Figure()
        fig.update_layout(**_layout(height, showlegend=False))
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
        return fig

    labels = [str(l) for l in df["label"]]
    values = [float(v) for v in df["valeur"]]
    pct = [float(v) for v in df["pct"]]
    colors = [region_color(r, i) for i, r in enumerate(df["region"])]
    vmax = max(values) or 1.0
    extra = hover_extra if hover_extra is not None else [""] * n
    customdata = [[fmt_int(v), fmt_pct(p, 0), (f"<br>{e}" if e else "")]
                  for v, p, e in zip(values, pct, extra)]

    fig = go.Figure()
    fig.add_trace(go.Bar(y=labels, x=[vmax] * n, orientation="h",
                         marker=dict(color="#EEF2F6"), hoverinfo="skip", width=0.6))
    fig.add_trace(go.Bar(
        y=labels, x=values, orientation="h", marker=dict(color=colors, line=dict(width=0)),
        width=0.6, customdata=customdata,
        hovertemplate="<b>%{y}</b> : %{customdata[0]} hab. en P1/P2 "
                      "(%{customdata[1]} du territoire)%{customdata[2]}<extra></extra>",
    ))
    for label, value, p in zip(labels, values, pct):
        sev = _severity_color(p)
        fig.add_annotation(x=vmax * 1.05, y=label, text=f"<b>{fmt_int(value)}</b>", showarrow=False,
                           xanchor="left", font=dict(size=11.5, color=NAVY))
        fig.add_annotation(x=vmax * 1.34, y=label, text=fmt_pct(p, 0), showarrow=False,
                           xanchor="left", align="center", font=dict(size=10, color=_text_color(sev)),
                           bgcolor=sev, bordercolor=sev, borderwidth=0, borderpad=3)
    fig.update_layout(**_layout(height, barmode="overlay", showlegend=False,
                                margin=dict(l=4, r=88, t=2, b=2)))
    fig.update_xaxes(visible=False, range=[0, vmax * 1.58], fixedrange=True)
    fig.update_yaxes(autorange="reversed", showgrid=False, tickfont=dict(size=11.5, color=NAVY),
                     fixedrange=True, automargin=True)
    return fig


def radial_bars(df: pd.DataFrame, height: int = 360, colors: list[str] | None = None,
                value_format=fmt_int, hover_extra: list[str] | None = None) -> go.Figure:
    """Barres circulaires (Barpolar) : un territoire (typiquement une région) = un secteur
    autour du cercle, la longueur du rayon portant la valeur. Toutes les informations
    complémentaires (celles qui figuraient auparavant dans un tableau « Détail complet »)
    sont intégrées à l'info-bulle via `hover_extra`, une ligne HTML déjà formatée par secteur."""
    n = len(df)
    if n == 0:
        fig = go.Figure()
        fig.update_layout(**_layout(height))
        return fig
    labels = [str(l) for l in df["label"]]
    values = [float(v) for v in df["valeur"]]
    palette = colors or [region_color(l, i) for i, l in enumerate(labels)]
    extra = hover_extra if hover_extra is not None else [""] * n
    customdata = [[value_format(v), (f"<br>{e}" if e else "")] for v, e in zip(values, extra)]
    vmax = max(values) or 1.0
    fig = go.Figure(go.Barpolar(
        r=values, theta=labels, marker=dict(color=palette, line=dict(color="#FFFFFF", width=1.5)),
        customdata=customdata, opacity=0.92,
        hovertemplate="<b>%{theta}</b><br>%{customdata[0]}%{customdata[1]}<extra></extra>",
    ))
    fig.update_layout(**_layout(
        height, showlegend=False, margin=dict(l=36, r=36, t=30, b=30),
        polar=dict(
            bgcolor="rgba(0,0,0,0)", hole=0.12,
            radialaxis=dict(visible=True, range=[0, vmax * 1.18], showticklabels=False,
                            gridcolor=GRID, linecolor=GRID, ticksuffix=""),
            angularaxis=dict(tickfont=dict(size=12, color=NAVY), gridcolor=GRID, linecolor=GRID),
        ),
    ))
    return fig


def vertical_bars(df: pd.DataFrame, height: int = 190, colors: list[str] | None = None,
                  percent: bool = True, hover_extra: list[str] | None = None,
                  hover_values: list[str] | None = None) -> go.Figure:
    """`hover_values` : texte déjà formaté de la valeur affichée en tête de l'info-bulle
    (ex. « 759 599 hab. ») ; sans lui, la valeur brute est affichée avec une décimale."""
    colors = colors or [region_color(l, i) for i, l in enumerate(df["label"])]
    texts = [fmt_pct(v, 1) if percent else fmt_int(v) for v in df["valeur"]]
    extra = hover_extra if hover_extra is not None else [""] * len(df)
    extra = [f"<br>{e}" if e else "" for e in extra]
    if hover_values is not None:
        customdata = [[hv, e] for hv, e in zip(hover_values, extra)]
        hovertemplate = "<b>%{x}</b><br>%{customdata[0]}%{customdata[1]}<extra></extra>"
    else:
        customdata = [[None, e] for e in extra]
        hovertemplate = ("<b>%{x}</b> : %{y:,.1f}" + ("%" if percent else "")
                         + "%{customdata[1]}<extra></extra>")
    fig = go.Figure(go.Bar(
        x=df["label"], y=df["valeur"], marker=dict(color=colors), text=texts,
        textposition="outside", textfont=dict(size=11, color=NAVY), cliponaxis=False,
        customdata=customdata, hovertemplate=hovertemplate,
        width=0.62,
    ))
    top = max(100.0, float(df["valeur"].max())) if percent else float(df["valeur"].max()) * 1.18
    fig.update_layout(**_layout(height, margin=dict(l=40, r=6, t=22, b=22), showlegend=False))
    fig.update_xaxes(showgrid=False, linecolor=GRID, tickfont=dict(size=11, color=MUTED),
                     fixedrange=True, tickmode="array", tickvals=list(df["label"]),
                     ticktext=[str(l).replace(" ", "<br>") for l in df["label"]], tickangle=0)
    fig.update_yaxes(range=[0, top * (1.02 if percent else 1)], gridcolor=GRID, zeroline=False,
                     tickfont=dict(size=11, color=MUTED), fixedrange=True,
                     ticksuffix="%" if percent else "", tickformat=",d", nticks=6)
    return fig


def stacked_bars(table: pd.DataFrame, height: int = 300, colors: list[str] | None = None,
                 percent: bool = False) -> go.Figure:
    fig = go.Figure()
    palette = colors or PALETTE
    for i, column in enumerate(table.columns):
        fig.add_trace(go.Bar(x=[str(x) for x in table.index], y=table[column], name=str(column),
                             marker=dict(color=palette[i % len(palette)]),
                             hovertemplate="<b>%{x}</b> · " + str(column) + " : %{y:,.1f}"
                                           + ("%" if percent else "") + "<extra></extra>"))
    fig.update_layout(**_layout(height, barmode="stack", margin=dict(l=44, r=10, t=10, b=30),
                                legend=dict(orientation="h", y=-0.22, x=0, font=dict(size=11))))
    fig.update_xaxes(showgrid=False, linecolor=GRID, fixedrange=True, tickfont=dict(size=11, color=MUTED))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, tickformat=",d" if not percent else ",.0f",
                     ticksuffix="%" if percent else "", fixedrange=True, tickfont=dict(size=11, color=MUTED))
    return fig


def heatmap(table: pd.DataFrame, height: int = 300) -> go.Figure:
    fig = go.Figure(go.Heatmap(
        z=table.values, x=[str(c) for c in table.columns], y=[str(i) for i in table.index],
        colorscale=[[0, "#F1F6F4"], [0.5, "#7CC29B"], [1, "#006A4E"]], showscale=False,
        xgap=2, ygap=2, hovertemplate="<b>%{y}</b> × %{x}<br>%{z:,.0f}<extra></extra>",
        text=[[fmt_int(v) if v else "" for v in row] for row in table.values],
        texttemplate="%{text}", textfont=dict(size=11),
    ))
    fig.update_layout(**_layout(height, margin=dict(l=8, r=8, t=8, b=8)))
    fig.update_xaxes(side="top", tickfont=dict(size=11, color=SLATE), fixedrange=True)
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=11, color=SLATE), fixedrange=True,
                     automargin=True)
    return fig


def grouped_hbars(table: pd.DataFrame, colors: dict[str, str], height: int = 200,
                  stack: bool = False, percent: bool = False, value_format=None,
                  hover_extra: dict[str, list[str]] | None = None,
                  hover_suffix: str = "", hover_decimals: int = 1) -> go.Figure:
    """Barres horizontales par libellé (`table` : index = libellés, colonnes = séries nommées).
    `hover_extra` : {nom_série: [ligne HTML par libellé]} pour intégrer dans l'info-bulle des
    informations complémentaires (auparavant dans un tableau « Détail complet »)."""
    fmt = value_format or ((lambda v: fmt_pct(v, 1)) if percent else fmt_int)
    labels = [str(i) for i in table.index]
    fig = go.Figure()
    for name in table.columns:
        vals = [float(v) for v in table[name]]
        extra = (hover_extra or {}).get(name, [""] * len(vals))
        extra = [f"<br>{e}" if e else "" for e in extra]
        fig.add_trace(go.Bar(
            y=labels, x=vals, name=str(name), orientation="h",
            marker=dict(color=colors.get(name, C.COLORS["green"])),
            text=[fmt(v) if (v and not stack) else "" for v in vals],
            textposition="outside", textfont=dict(size=11, color=NAVY), cliponaxis=False,
            customdata=extra,
            hovertemplate=f"<b>%{{y}}</b> · {name} : %{{x:,.{hover_decimals}f}}" + ("%" if percent else "")
                          + hover_suffix + "%{customdata}<extra></extra>",
        ))
    xmax = float(table.sum(axis=1).max() if stack else table.values.max()) or 1.0
    if stack:
        for label, total in zip(labels, table.sum(axis=1)):
            fig.add_annotation(x=xmax * 1.03, y=label, text=fmt(total), showarrow=False,
                               xanchor="left", font=dict(size=11, color=NAVY))
    fig.update_layout(**_layout(
        height, barmode="stack" if stack else "group", bargap=0.28,
        margin=dict(l=4, r=44, t=34, b=2),
        legend=dict(orientation="h", x=0, y=1.0, yanchor="bottom", traceorder="normal",
                    font=dict(size=11.5)),
    ))
    fig.update_xaxes(visible=False, range=[0, xmax * 1.3], fixedrange=True)
    fig.update_yaxes(autorange="reversed", showgrid=False, tickfont=dict(size=11, color=NAVY),
                     fixedrange=True, automargin=True)
    return fig


def scatter_xy(df: pd.DataFrame, x: str, y: str, label: str, height: int = 280,
               x_title: str = "", y_title: str = "", color: str | None = None) -> go.Figure:
    """Nuage de points (ex. population × ratio) avec étiquette au survol."""
    fig = go.Figure(go.Scatter(
        x=df[x], y=df[y], mode="markers", marker=dict(size=9, color=color or C.COLORS["green"],
                                                       opacity=0.75, line=dict(color="#FFFFFF", width=1)),
        text=df[label], hovertemplate="<b>%{text}</b><br>%{x:,.0f} · %{y:,.2f}<extra></extra>",
    ))
    fig.update_layout(**_layout(height, margin=dict(l=48, r=14, t=10, b=36), showlegend=False))
    fig.update_xaxes(title=dict(text=x_title, font=dict(size=11, color=MUTED)), gridcolor=GRID,
                     tickfont=dict(size=10.5, color=MUTED), fixedrange=True)
    fig.update_yaxes(title=dict(text=y_title, font=dict(size=11, color=MUTED)), gridcolor=GRID,
                     tickfont=dict(size=10.5, color=MUTED), fixedrange=True)
    return fig


def lorenz_curve(shares_pop: list[float], shares_net: list[float], height: int = 260,
                 name: str = "Réseau") -> go.Figure:
    """Courbe de Lorenz : part cumulée de population (x) vs part cumulée du réseau (y)."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[0, 100], y=[0, 100], mode="lines", line=dict(color=GRID, width=1.6, dash="dash"),
                             name="Égalité parfaite", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=shares_pop, y=shares_net, mode="lines", fill="tonexty",
                             fillcolor="rgba(14,159,110,0.12)", line=dict(color=C.COLORS["green"], width=2.4),
                             name=name, hovertemplate="%{x:.0f}% pop. · %{y:.0f}% " + name + "<extra></extra>"))
    fig.update_layout(**_layout(height, margin=dict(l=42, r=14, t=10, b=30),
                                legend=dict(orientation="h", y=-0.2, x=0, font=dict(size=11))))
    fig.update_xaxes(title=dict(text="Part cumulée de la population (%)", font=dict(size=10.5, color=MUTED)),
                     range=[0, 100], gridcolor=GRID, fixedrange=True, tickfont=dict(size=10.5, color=MUTED))
    fig.update_yaxes(title=dict(text="Part cumulée du réseau (%)", font=dict(size=10.5, color=MUTED)),
                     range=[0, 100], gridcolor=GRID, fixedrange=True, tickfont=dict(size=10.5, color=MUTED))
    return fig



