"""Menu 6 — Recommandations stratégiques : catalogue, chiffrage, scénarios, feuille de route."""
from __future__ import annotations

import re

import pandas as pd
import streamlit as st

from components import charts as ch
from components.layout import (card_title, context_bar, empty_state, legend, page_header, plot,
                               reco_card, source_note, timeline_card)
from utils import config as C
from utils import metrics as M
from utils.data_loader import Datasets
from utils.filters import Filters
from utils.formatting import fmt_dec, fmt_int, fmt_pct, html_escape

AXE_ACCENT = {"Internet": "blue", "Inclusion financière": "green", "Gouvernance des données": "yellow"}

# Libellés en clair pour les codes internes (paliers P1-P4, scénarios S1-S3, indicateurs
# K#.#) : cette page n'affiche que des faits et des formulations en langage naturel,
# jamais les codes de classification utilisés en interne.
PALIER_TEXT = {
    "P1": "Priorité la plus forte",
    "P2": "Priorité forte",
    "P3": "Priorité modérée",
    "P4": "Priorité faible",
}
SCENARIO_TEXT = {"S1": "Minimal", "S2": "Intermédiaire", "S3": "Renforcé"}

_KPI_CODE_RE = re.compile(r"\bK\d+(?:\.\d+)?(?:\s*(?:,|-|et)\s*K\d+(?:\.\d+)?)*\b")
_LEADING_PARENS_RE = re.compile(r"^\(([^)]+)\)\s*")


_PALIER_ADJ = {
    "P1": "très prioritaires", "P2": "prioritaires",
    "P3": "modérément prioritaires", "P4": "peu prioritaires",
}


def _depaliere(text):
    """Remplace les codes de palier (P1 à P4, y compris des combinaisons comme « P1/P2 »)
    par une description en clair, sans jamais afficher le code lui-même."""
    if not isinstance(text, str):
        return text
    text = re.sub(r"\b(en\s+)?palier\s+(?=P[1-4]\b)", "", text, flags=re.IGNORECASE)

    def _combo(m):
        codes = re.findall(r"P[1-4]", m.group(0))
        return "les plus prioritaires" if len(codes) > 1 else _PALIER_ADJ[codes[0]]

    text = re.sub(r"\bP[1-4](?:\s*/\s*P[1-4])+\b", _combo, text)
    return re.sub(r"\bP([1-4])\b", lambda m: _PALIER_ADJ[f"P{m.group(1)}"], text)


def _descenarise(text):
    """Remplace les références aux scénarios codés (S1, S2, S3) par leur nom en clair."""
    if not isinstance(text, str):
        return text
    text = re.sub(r"\bde\s+S1\s*/\s*S2\b", "des scénarios minimal et intermédiaire", text)
    text = re.sub(r"\bS1\s*/\s*S2\b", "les scénarios minimal et intermédiaire", text)
    text = re.sub(r"\bS([1-3])\b", lambda m: f"le scénario {SCENARIO_TEXT['S' + m.group(1)].lower()}", text)
    return text[0].upper() + text[1:] if text else text


def _clean_kpi_text(text) -> str:
    """Retire les codes techniques d'indicateurs (K1.1, K2.11...) et ne garde que leur
    description en clair, telle que déjà rédigée entre parenthèses dans la donnée source."""
    if not isinstance(text, str) or not text.strip():
        return text
    cleaned = []
    for seg in text.split(";"):
        seg = _KPI_CODE_RE.sub("", seg).strip()
        seg = _LEADING_PARENS_RE.sub(r"\1 ", seg).strip()
        seg = re.sub(r"^nouveau\s*:\s*", "Nouvel indicateur : ", seg, flags=re.IGNORECASE)
        seg = seg.strip(" .,-")
        if seg:
            cleaned.append(seg[0].upper() + seg[1:])
    return " ; ".join(cleaned) if cleaned else text.strip()


_DOC_REF_PAREN_RE = re.compile(r"\(\s*(?:cf\.?\s*)?(?:tableau|sections?)\b[^()]*\)", re.IGNORECASE)
_DOC_REF_INLINE_RE = re.compile(
    r"\b(?:cf\.?\s*)?(?:tableau|sections?)\s+n°?\s*\d+(?:\.\d+)?(?:\s*[-–]\s*\d+(?:\.\d+)?)?\b",
    re.IGNORECASE)


def _sans_renvoi_doc(text):
    """Filet de sécurité : retire tout renvoi résiduel à la numérotation d'un document
    externe (« tableau 15.4 », « section 18.1 », « sections 24-25 »...). Cette page ne
    doit jamais laisser deviner qu'elle s'appuie sur un tableau ou une section d'un
    autre document — les libellés doivent se suffire à eux-mêmes."""
    if not isinstance(text, str):
        return text
    text = _DOC_REF_PAREN_RE.sub("", text)
    text = _DOC_REF_INLINE_RE.sub("", text)
    text = re.sub(r",\s*\)", ")", text)
    text = re.sub(r"\(\s*,", "(", text)
    text = re.sub(r"\(\s*\)", "", text)
    text = re.sub(r",\s*([.;])", r"\1", text)
    text = re.sub(r",\s*,", ",", text)
    return text


def _declassify(text):
    """Nettoie un texte libre de tous les codes internes (paliers P1-P4, scénarios S1-S3,
    indicateurs K#.#) et de tout renvoi à un tableau ou une section d'un document externe,
    pour n'afficher que des formulations en langage clair et autoportant."""
    if not isinstance(text, str):
        return text
    text = re.sub(r"\(\s*K\d+(?:\.\d+)?(?:\s*,\s*K\d+(?:\.\d+)?)*\s*\)", "", text)
    text = _KPI_CODE_RE.sub("", text)
    text = _depaliere(text)
    text = _descenarise(text)
    text = _sans_renvoi_doc(text)
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    return text.strip()


def _source_link(text, url) -> str:
    """Transforme un libellé de source en lien cliquable vers l'URL correspondante,
    ouvert dans un nouvel onglet. Si l'URL est absente ou vide, retourne le texte tel
    quel (aucun lien)."""
    text = "" if text is None else str(text)
    if not isinstance(url, str) or not url.strip():
        return html_escape(text)
    return (f'<a href="{html_escape(url.strip())}" target="_blank" '
            f'rel="noopener noreferrer">{html_escape(text)}</a>')


def render(ds: Datasets, f: Filters) -> None:
    page_header("Recommandations stratégiques", "Catalogue de recommandations traçables aux analyses, avec chiffrage et plan d'action.")
    context_bar([("Axe", list(f.axe)),
                ("Niveau de priorité (communes)", [PALIER_TEXT.get(p, p) for p in f.palier])])

    synth = ds.get("synthese_decisionnelle_finale")
    if not synth.empty:
        synth = synth[~synth["question"].isin([
            "Le budget est-il fiable ?",
            "Peut-on chiffrer un effet sur l'emploi ou le PIB togolais ?",
        ])]
    if not synth.empty:
        with st.container(key="card_reco_synth"):
            card_title("quiz", "Synthèse décisionnelle", "Réponses directes aux questions clés de pilotage")
            for _, row in synth.iterrows():
                with st.expander(row["question"]):
                    st.markdown(f"**{_declassify(row['reponse'])}**")
                    st.caption(_declassify(row["condition"]))

    reco, plan, budget = M.recommandations_table(ds, f)
    if reco.empty:
        empty_state(200)
    else:
        with st.container(key="card_reco_list"):
            card_title("flag", "Catalogue des recommandations", f"{len(reco)} recommandation(s) — filtrées par axe si sélectionné")
            for _, row in reco.iterrows():
                plan_row = M.match_plan(plan, row["id"])
                budget_row = M.match_budget(budget, row["id"])
                fields = [
                    ("Constat", _declassify(row["constat"])),
                    ("Territoire", _declassify(row["territoire"])),
                    ("Action", _declassify(row["action"])),
                ]
                if plan_row is not None:
                    fields += [("Population concernée", plan_row.get("population_concernee"))]
                    impact_social = plan_row.get("impact_social")
                    if isinstance(impact_social, str) and impact_social.strip().lower() != "non applicable":
                        fields.append(("Impact social attendu", _declassify(impact_social)))
                    impact_eco = plan_row.get("impact_economique")
                    if isinstance(impact_eco, str) and impact_eco.strip().lower() != "non applicable":
                        fields.append(("Impact économique attendu", _declassify(impact_eco)))
                elif budget_row is not None:
                    fields += [("Budget central (FCFA)", fmt_int(budget_row.get("budget_central_fcfa")))]
                fields += [
                    ("Indicateur de suivi", _clean_kpi_text(row["kpi"])),
                    ("Acteurs", row["acteurs"]),
                ]
                reco_card(f"{row['id']} — {row['axe']}", [row["horizon"]], fields,
                         accent=AXE_ACCENT.get(row["axe"], "green"))

    with st.container(key="card_reco_route"):
        card_title("timeline", "Feuille de route",
                  "Recommandations mobilisées par horizon — détail au survol")
        table = M.feuille_de_route(ds)
        if table.empty:
            empty_state(240)
        else:
            counts = [max(len(re.findall(r"R-[A-Z]+\d+", str(a))), 1) for a in table["actions"]]
            bar = pd.DataFrame({"label": table["horizon"], "valeur": counts})
            palette = [C.COLORS["green"], C.COLORS["yellow"], C.COLORS["part"], C.COLORS["red"]]
            plot(ch.top_bars(bar, height=240, colors=palette[:len(bar)],
                             value_format=lambda v: f"{fmt_int(v)} recommandation(s)",
                             hover_extra=_route_hover(table)), "reco_route")

    with st.container(key="card_reco_communes"):
        card_title("priority_high", "Communes les plus prioritaires",
                  "Indice de besoin (IB) le plus élevé · couleur = niveau de priorité — détail au survol")
        table = M.priorite_communes(ds, f)
        if table.empty:
            empty_state(260)
        else:
            bar = table[["commune", "IB"]].rename(columns={"commune": "label", "IB": "valeur"})
            colors = [C.PALIER_COLORS.get(p, C.COLORS["muted"]) for p in table["palier"]]
            g1, g2 = st.columns([3.4, 1], gap="medium")
            with g1:
                plot(ch.top_bars(bar, height=max(280, 22 * len(bar)), colors=colors,
                                 value_format=lambda v: fmt_dec(v, 1),
                                 hover_extra=_prio_communes_hover(table)), "reco_prio_communes")
            with g2:
                counts = table["palier"].value_counts()
                total = len(table)
                note = (f'<div class="section-note">Pourcentages calculés sur les {fmt_int(total)} '
                        "communes les plus prioritaires affichées ici, et non sur l'ensemble des "
                        "communes du pays.</div>")
                rows = [(C.PALIER_COLORS[p], PALIER_TEXT[p], fmt_int(counts.get(p, 0)),
                        fmt_pct(counts.get(p, 0) / total * 100)) for p in ("P1", "P2", "P3", "P4")
                       if counts.get(p, 0)]
                st.markdown(note + legend(rows), unsafe_allow_html=True)

    with st.container(key="card_reco_suivi"):
        card_title("timeline", "Suivi-évaluation détaillé par action",
                  "Situation initiale puis cibles à 12, 24 et 36 mois, avec indicateurs, "
                  "fréquence et méthode de vérification pour chaque action")
        table = ds.get("suivi_evaluation_par_action")
        if table.empty:
            empty_state(320)
        else:
            ctx = _suivi_context(ds)
            for _, row in table.iterrows():
                ids = [i.strip() for i in str(row["id"]).split("/")]
                axe, titre, _ = ctx.get(ids[0], (None, "Action de suivi-évaluation", None))
                territoires, seen = [], set()
                for rid in ids:
                    entry = ctx.get(rid)
                    if entry and entry[2] and entry[2] not in seen:
                        territoires.append(entry[2])
                        seen.add(entry[2])
                stages = [
                    ("Situation initiale", _declassify(row["situation_initiale"])),
                    ("12 mois", _declassify(row["cible_12m"])),
                    ("24 mois", _declassify(row["cible_24m"])),
                    ("36 mois", _declassify(row["cible_36m"])),
                ]
                meta = [
                    ("Localité(s) concernée(s)", " ; ".join(territoires) if territoires else None),
                    ("Indicateur de réalisation", _declassify(row["indicateur_realisation"])),
                    ("Indicateur social", _declassify(row["indicateur_social"])),
                    ("Fréquence de suivi", _declassify(row["frequence"])),
                    ("Méthode de vérification", _declassify(row["methode_verification"])),
                    ("Source des données", _declassify(row["source_donnees"])),
                ]
                timeline_card(row["id"], titre, stages, meta, accent=AXE_ACCENT.get(axe, "green"))

    with st.container(key="card_reco_cas"):
        card_title("public", "Cas réels de référence et programmes nationaux en cours",
                  "Expériences documentées dans d'autres pays, puis les programmes nationaux "
                  "actuellement déployés au Togo")
        cas = ds.get("cas_reels_references")
        prog = ds.get("programme_national_en_cours")
        if cas.empty and prog.empty:
            empty_state(320)
        if not cas.empty:
            st.markdown('<div class="cas-group-label">Cas réels de référence</div>', unsafe_allow_html=True)
            cg1, cg2 = st.columns(2, gap="medium")
            for i, (_, row) in enumerate(cas.iterrows()):
                with (cg1 if i % 2 == 0 else cg2):
                    fields = [
                        ("Problème initial", _declassify(row["probleme_initial"])),
                        ("Intervention", _declassify(row["intervention"])),
                        ("Coût", _declassify(row["cout"])),
                        ("Échelle", _declassify(row["echelle"])),
                        ("Résultats sociaux", _declassify(row["resultats_sociaux"])),
                        ("Résultats économiques", _declassify(row["resultats_economiques"])),
                        ("Enseignement", _declassify(row["enseignement"])),
                        ("Source", _source_link(row["source"], row.get("source_url"))),
                    ]
                    reco_card(row["pays"], [], fields, accent="red" if "Togo" in row["pays"] else "blue")
        if not prog.empty:
            st.markdown('<div class="cas-group-label">Programme national en cours</div>', unsafe_allow_html=True)
            for _, row in prog.iterrows():
                reco_card(row["programme"], [row["statut"]], [
                    ("Financement", row["montant"]),
                    ("Cible", row["cible"]),
                    ("Articulation avec les recommandations", _declassify(row["articulation"])),
                    ("Source", _source_link(row["source"], row.get("source_url"))),
                ], accent="blue")

    source_note(C.SOURCE_NOTE)


def _route_hover(table) -> list[str]:
    """Détail complet par horizon (actions, territoires, acteurs), intégré à l'info-bulle
    du graphique plutôt qu'affiché dans un tableau séparé. Les codes internes (paliers,
    scénarios, indicateurs) éventuellement présents dans le texte source sont reformulés
    en clair."""
    lines = []
    for _, row in table.iterrows():
        parts = [
            f"Actions : {_declassify(row['actions'])}",
            f"Territoires concernés : {_declassify(row['territoires'])}",
            f"Acteurs (pistes) : {row['acteurs (pistes)']}",
        ]
        lines.append("<br>".join(parts))
    return lines


def _prio_communes_hover(table) -> list[str]:
    lines = []
    for _, row in table.iterrows():
        commune = str(row["commune"])
        m = re.search(r"(\d+)\s*$", commune)
        parts = [f"Préfecture : {row['prefecture']}", f"Région : {row['region_a']}"]
        if m:
            parts.append(
                f"Chiffre après le nom : commune n° {m.group(1)} de la préfecture {row['prefecture']} "
                "— depuis le découpage territorial de 2019, les communes togolaises sont numérotées "
                "au sein de leur préfecture plutôt que dotées d'un nom propre distinct"
            )
        parts += [
            f"Population : {fmt_int(row['population'])}",
            f"Niveau de priorité : {PALIER_TEXT.get(row['palier'], row['palier'])}",
            f"Établissements formels : {fmt_int(row['n_formel'])}",
            f"Agents Mobile Money : {fmt_int(row['n_mm'])}",
            f"Action recommandée : {row['type_action']}",
        ]
        lines.append("<br>".join(parts))
    return lines


def _short_text(text, limit: int = 110) -> str:
    """Tronque un texte sur une limite de mot, avec une ellipse, pour servir de titre court
    (ex. dans l'en-tête d'une carte de suivi-évaluation)."""
    text = str(text).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(",.;:—-") + "…"


def _suivi_context(ds: Datasets) -> dict[str, tuple[str, str, str]]:
    """Associe à chaque identifiant de recommandation son axe, un intitulé court de
    l'action et les localités concernées (texte du champ territoire), à partir du
    catalogue complet (non filtré par axe) afin de couvrir toutes les actions suivies
    même si un filtre est actif ailleurs sur la page."""
    full = ds.get("recommandations")
    ctx: dict[str, tuple[str, str, str]] = {}
    if not full.empty:
        for _, r in full.iterrows():
            ctx[r["id"]] = (r["axe"], _short_text(_declassify(r["action"])), _declassify(r["territoire"]))
    return ctx
