"""Derivados 101 — punto de entrada y navegación.

Ejecutar con: streamlit run app.py
Las páginas viven en app_pages/; acá se declaran con título e ícono explícitos.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import streamlit as st

PAGES_DIR = Path(__file__).resolve().parent / "app_pages"

nav = st.navigation(
    [
        st.Page(PAGES_DIR / "0_Inicio.py", title="Inicio", icon="🧭", default=True),
        st.Page(PAGES_DIR / "1_Conceptos.py", title="Conceptos", icon="📚"),
        st.Page(PAGES_DIR / "2_Forward.py", title="Forward", icon="📈"),
        st.Page(PAGES_DIR / "3_Opciones.py", title="Opciones", icon="🎛️"),
        st.Page(PAGES_DIR / "4_Estrategias.py", title="Estrategias", icon="🧩"),
        st.Page(PAGES_DIR / "5_USDCLP.py", title="USD/CLP", icon="💵"),
        st.Page(PAGES_DIR / "6_Quiz.py", title="Quiz", icon="✅"),
    ]
)
nav.run()
