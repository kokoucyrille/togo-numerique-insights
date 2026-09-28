"""TOGO NUMERIQUE INSIGHTS — tableau de bord décisionnel.

Économie numérique et inclusion financière au Togo.
Lancement : streamlit run app.py
"""
from __future__ import annotations

import streamlit as st

from components.layout import inject_css, topbar
from utils import config as C
from utils.data_loader import load_datasets
from utils.filters import render_sidebar
from views import (
    inclusion_territoriale,
    mobile_money,
    recommandations,
    services_financiers,
    usage_numerique,
    vue_ensemble,
)

st.set_page_config(
    page_title=C.APP_TITLE,
    page_icon=str(C.ASSETS_DIR / C.FAVICON_FILES["arms"]),
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()
ds = load_datasets()
page = topbar()
filters = render_sidebar(ds, page)

VIEWS = {
    "vue_ensemble": vue_ensemble.render,
    "usage_numerique": usage_numerique.render,
    "services_financiers": services_financiers.render,
    "mobile_money": mobile_money.render,
    "inclusion_territoriale": inclusion_territoriale.render,
    "recommandations": recommandations.render,
}

VIEWS[page](ds, filters)
