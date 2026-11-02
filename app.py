"""Derivados 101 — punto de entrada y navegación.

Ejecutar con: streamlit run app.py
Menú en tres secciones (``ui.SECTIONS``): "Conceptos" (Inicio + un tema por pregunta, páginas
generadas por ``curso_ui.chapter_pages()``, no archivos), "Simuladores" y "Repasa".
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import streamlit as st

from derivados101.curso_ui import chapter_pages
from derivados101.ui import PAGES, SECTIONS

ROOT = Path(__file__).resolve().parent

sections: dict[str, list] = {name: [] for name in SECTIONS}
for i, p in enumerate(PAGES):
    sections[p.section].append(st.Page(ROOT / p.path, title=p.title, icon=p.icon, default=(i == 0)))
    if i == 0:
        sections[p.section].extend(chapter_pages())  # los temas van justo después de Inicio

nav = st.navigation(sections, expanded=True)  # 9 temas + simuladores: sin "View more"
nav.run()
