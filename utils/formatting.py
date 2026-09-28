"""Formatage à la française (espace fine pour les milliers, virgule décimale)."""
from __future__ import annotations

import math
import re
import unicodedata

THIN = "\u202f"  # espace fine insécable


def _valid(x) -> bool:
    try:
        return x is not None and not (isinstance(x, float) and math.isnan(x))
    except TypeError:
        return False


def fmt_int(x) -> str:
    if not _valid(x):
        return "—"
    return f"{int(round(float(x))):,}".replace(",", THIN)


def fmt_dec(x, decimals: int = 1) -> str:
    if not _valid(x):
        return "—"
    s = f"{float(x):,.{decimals}f}"
    return s.replace(",", THIN).replace(".", ",")


def fmt_pct(x, decimals: int = 1) -> str:
    if not _valid(x):
        return "—"
    return f"{fmt_dec(x, decimals)}%"


def fmt_signed(x, decimals: int = 1, unit: str = "%") -> str:
    if not _valid(x):
        return "—"
    sign = "+" if x > 0 else ("−" if x < 0 else "")
    sep = "\u00a0" if unit == "pts" else ""
    return f"{sign}{fmt_dec(abs(x), decimals)}{sep}{unit}"


def norm_key(value) -> str:
    """Clé normalisée : minuscules, sans accents, séparateurs -> « _ »."""
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^0-9a-zA-Z]+", "_", text.lower())
    return text.strip("_")


def html_escape(text) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
