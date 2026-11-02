"""Inicio: una línea de qué es esto y la lista de preguntas."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st

from derivados101.curso import CHAPTERS
from derivados101.curso_ui import chapter_page
from derivados101.ui import PAGES, disclaimer

st.set_page_config(page_title="Derivados 101", page_icon=PAGES[0].icon, layout="centered")

st.title("Derivados 101", anchor=False)
st.markdown(
    "Forwards y opciones de dólar explicados en simple, con ejemplos en pesos chilenos. "
    "Elige una pregunta o parte por la primera."
)

for ch in CHAPTERS:
    with st.container(border=True):
        st.page_link(chapter_page(ch), label=f"**{ch.title}**", icon=ch.icon, width="stretch")
        if ch.goal:
            st.caption(ch.goal)

if st.button("Empezar por la primera", icon=":material/arrow_forward:", icon_position="right", type="primary",
             key="start"):
    st.switch_page(chapter_page(CHAPTERS[0]))

st.caption("Para mover los números tú mismo, usa los **Simuladores** del menú.")

disclaimer()
