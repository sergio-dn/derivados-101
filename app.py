"""Derivados 101 — punto de entrada y navegación.

Ejecutar con: streamlit run app.py
Las páginas viven en app_pages/; títulos, íconos y secciones salen de ``ui.PAGES``.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import streamlit as st

from derivados101.ui import PAGES

ROOT = Path(__file__).resolve().parent

sections: dict[str, list] = {}
for i, p in enumerate(PAGES):
    sections.setdefault(p.section, []).append(
        st.Page(ROOT / p.path, title=p.title, icon=p.icon, default=(i == 0))
    )

nav = st.navigation(sections)
nav.run()
