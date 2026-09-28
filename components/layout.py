"""Composants d'interface : barre de navigation, bandeau, cartes, états vides."""
from __future__ import annotations

import base64
import io
from functools import lru_cache
from pathlib import Path

import streamlit as st

from utils import config as C
from utils.formatting import html_escape


# --------------------------------------------------------------------------- #
# Ressources
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=None)
def _data_uri(filename: str, mime: str) -> str:
    raw = (C.ASSETS_DIR / filename).read_bytes()
    return f"data:{mime};base64,{base64.b64encode(raw).decode()}"


@lru_cache(maxsize=None)
def _inline_svg(filename: str) -> str:
    return (C.ASSETS_DIR / filename).read_text(encoding="utf-8")


def banner_path() -> Path | None:
    found = [p for ext in (".jpg", ".jpeg", ".png", ".webp")
             if (p := C.ASSETS_DIR / f"{C.BANNER_STEM}{ext}").is_file()]
    return max(found, key=lambda p: p.stat().st_mtime_ns) if found else None


@lru_cache(maxsize=4)
def _banner_uri(path: str, mtime_ns: int) -> str:
    from PIL import Image, ImageOps
    try:
        with Image.open(path) as raw:
            img = ImageOps.exif_transpose(raw).convert("RGB")
        if img.width > C.BANNER_MAX_WIDTH:
            ratio = C.BANNER_MAX_WIDTH / img.width
            img = img.resize((C.BANNER_MAX_WIDTH, max(1, round(img.height * ratio))), Image.LANCZOS)
        buffer = io.BytesIO()
        img.save(buffer, "JPEG", quality=86, optimize=True)
    except Exception:
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()


def icon(name: str, extra_class: str = "") -> str:
    return f'<span class="msr {extra_class}" aria-hidden="true">{name}</span>'


def inject_css() -> None:
    css = (C.STYLES_DIR / "main.css").read_text(encoding="utf-8")
    photo = banner_path()
    uri = _banner_uri(str(photo), photo.stat().st_mtime_ns) if photo else ""
    banner_var = f'url("{uri}")' if uri else "none"
    css = css.replace("__BANNER_VAR__", banner_var).replace("__BANNER_POS__", C.BANNER_FOCUS)
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def plot(fig, key: str) -> None:
    config = {"displayModeBar": False, "scrollZoom": False, "responsive": True}
    try:
        st.plotly_chart(fig, width="stretch", config=config, key=key)
    except TypeError:
        st.plotly_chart(fig, use_container_width=True, config=config, key=key)


# --------------------------------------------------------------------------- #
# Barre de navigation
# --------------------------------------------------------------------------- #
def _go(page: str) -> None:
    st.session_state["page"] = page


def topbar() -> str:
    page = st.session_state.setdefault("page", C.PAGES[0][0])
    brand = (
        '<div class="brand">'
        f'<span class="brand__logo">{_inline_svg("logo.svg")}</span>'
        '<div class="brand__text">'
        f'<div class="brand__title">{html_escape(C.APP_TITLE)}</div>'
        f'<div class="brand__sub">{html_escape(C.APP_SUBTITLE)}</div>'
        "</div></div>"
    )
    seal = (
        '<div class="seal">'
        f'<img src="{_data_uri("armoiries_togo.svg", "image/svg+xml")}" alt="Armoiries du Togo"/>'
        f'<span>{html_escape(C.MOTTO)}</span></div>'
    )
    n = len(C.PAGES)
    widths = [21] + [11] * n + [11]
    with st.container(key="topbar"):
        cols = st.columns(widths, vertical_alignment="center")
        cols[0].markdown(brand, unsafe_allow_html=True)
        for col, (key, label, mat) in zip(cols[1:1 + n], C.PAGES):
            col.button(
                label, icon=f":material/{mat}:", key=f"nav_{key}",
                type="primary" if key == page else "tertiary",
                on_click=_go, args=(key,),
            )
        cols[-1].markdown(seal, unsafe_allow_html=True)
    return st.session_state["page"]


# --------------------------------------------------------------------------- #
# Bandeau
# --------------------------------------------------------------------------- #
def hero() -> None:
    l1, l2, l3 = C.SLOGAN_LINES
    stripes = (
        '<svg class="hero__stripes" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">'
        '<polygon points="34.6,100 41.6,0 44.2,0 37.2,100" fill="#2E9B57" opacity=".9"/>'
        '<polygon points="37.2,100 44.2,0 47.4,0 40.4,100" fill="#FFCE00"/>'
        '<polygon points="40.4,100 47.4,0 49,0 42,100" fill="#D21034"/>'
        "</svg>"
    )
    st.markdown(
        '<div class="hero"><div class="hero__circuit"></div><div class="hero__photo"></div>'
        f"{stripes}"
        f'<div class="hero__text"><span>{html_escape(l1)}</span><span>{html_escape(l2)}</span>'
        f'<span class="y">{html_escape(l3)}</span></div></div>',
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="page-head"><h1>{html_escape(title)}</h1>'
        f"<p>{html_escape(subtitle)}</p></div>",
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Cartes et états vides
# --------------------------------------------------------------------------- #
def context_bar(chips: list[tuple[str, list[str]]]) -> None:
    """Rappelle les filtres actifs. `chips` : [(libellé du champ, [valeurs])]."""
    groups = [g for g in chips if g[1]]
    if not groups:
        return
    body = "".join(
        f'<span class="ctx__group"><span class="ctx__label">{html_escape(label)}</span>'
        + "".join(f'<span class="ctx__chip">{html_escape(v)}</span>' for v in values)
        + "</span>"
        for label, values in groups
    )
    st.markdown(
        f'<div class="ctx" role="status">{icon("tune")}<span class="ctx__title">Vue active</span>{body}</div>',
        unsafe_allow_html=True,
    )


def source_note(text: str) -> None:
    st.markdown(f'<div class="srcnote">{icon("info")}<span>{html_escape(text)}</span></div>',
               unsafe_allow_html=True)


def card_title(mat_icon: str, title: str, note: str | None = None) -> None:
    right = f'<span class="ct__note">{html_escape(note)}</span>' if note else ""
    st.markdown(
        f'<div class="ct">{icon(mat_icon)}<span title="{html_escape(title)}">{html_escape(title)}</span>'
        f'{right}</div>',
        unsafe_allow_html=True,
    )


def empty_state(height: int, title: str = "Données non disponibles", hint: str = "") -> None:
    hint_html = f"<small>{html_escape(hint)}</small>" if hint else ""
    st.markdown(
        f'<div class="empty" style="min-height:{height}px">{icon("insert_chart")}'
        f"<b>{html_escape(title)}</b>{hint_html}</div>",
        unsafe_allow_html=True,
    )


def notice(message: str) -> None:
    st.markdown(f'<div class="notice">{icon("info")}<span>{message}</span></div>',
               unsafe_allow_html=True)


def palier_legend(rows: list[tuple[str, str, str]]) -> str:
    """Légende statique (couleur, libellé, description) — affiche une définition une seule
    fois pour toute la carte plutôt que de la répéter à chaque survol d'un graphique :
    une info-bulle reste focalisée sur les chiffres de l'élément survolé et sur la formule
    de calcul qui les explique, la méthodologie générale se lit ici, à côté."""
    items = "".join(
        f'<div class="palier-legend__row"><i style="background:{color}"></i>'
        f'<div><b>{html_escape(label)}</b><span>{html_escape(desc)}</span></div></div>'
        for color, label, desc in rows
    )
    return f'<div class="palier-legend">{items}</div>'


def legend(rows: list[tuple[str, str, str, str]], cls: str = "") -> str:
    """Légende HTML : (couleur, libellé, valeur, part)."""
    items = []
    for color, label, value, part in rows:
        items.append(
            f'<div class="lg__row"><i style="background:{color}"></i>'
            f'<span class="lg__name">{html_escape(label)}</span>'
            f'<span class="lg__val">{value}</span><span class="lg__part">{part}</span></div>'
        )
    return f'<div class="lg {cls}">{"".join(items)}</div>'


def show_table(df, height: int | None = None) -> None:
    kwargs = {"hide_index": True}
    if height:
        kwargs["height"] = min(height, 42 + 36 * len(df))
    try:
        st.dataframe(df, width="stretch", **kwargs)
    except TypeError:
        st.dataframe(df, use_container_width=True, **kwargs)


def timeline_card(badge: str, title: str, stages: list[tuple[str, str]],
                  meta: list[tuple[str, str]], accent: str = "green") -> None:
    """Frise de suivi-évaluation textuelle pour une action : un badge + titre, quatre
    étapes (situation initiale puis cibles à échéance) toutes visibles sans survol, et un
    bloc de métadonnées (indicateurs, fréquence, méthode de vérification, source)."""
    steps_html = "".join(
        f'<div class="suivi__step"><div class="suivi__dot"></div>'
        f'<div class="suivi__steplabel">{html_escape(label)}</div>'
        f'<div class="suivi__stepval">{html_escape(value)}</div></div>'
        for label, value in stages
    )
    meta_html = "".join(
        f'<div class="suivi__metarow"><span class="suivi__metak">{html_escape(k)}</span>'
        f'<span class="suivi__metav">{html_escape(v)}</span></div>'
        for k, v in meta if v
    )
    st.markdown(
        f'<div class="suivi suivi--{accent}"><div class="suivi__head">'
        f'<span class="suivi__badge">{html_escape(badge)}</span>'
        f'<span class="suivi__title">{html_escape(title)}</span></div>'
        f'<div class="suivi__track">{steps_html}</div>'
        f'<div class="suivi__meta">{meta_html}</div></div>',
        unsafe_allow_html=True,
    )


def reco_card(title: str, chips: list[str], rows: list[tuple[str, str]], accent: str = "green") -> None:
    """Carte de recommandation : titre, étiquettes, liste champ→valeur."""
    chip_html = "".join(f'<span class="ctx__chip">{html_escape(c)}</span>' for c in chips)
    body = "".join(
        f'<div class="reco__row"><span class="reco__k">{html_escape(k)}</span>'
        f'<span class="reco__v">{v}</span></div>'
        for k, v in rows if v
    )
    st.markdown(
        f'<div class="reco reco--{accent}"><div class="reco__head">'
        f'<span class="reco__title">{html_escape(title)}</span>{chip_html}</div>{body}</div>',
        unsafe_allow_html=True,
    )
