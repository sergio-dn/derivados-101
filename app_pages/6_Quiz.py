"""Quiz: 10 preguntas con feedback y explicación."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st

from derivados101.ui import PAGES, disclaimer, learn_box, page_setup, section

page_setup(
    "Quiz: ¿quedó claro?",
    icon=PAGES[-1].icon,
    subtitle="Diez preguntas cortas sobre cómo operan los forwards y las opciones.",
)

learn_box(
    "Diez preguntas para comprobar lo aprendido. La barra avanza a medida que respondes; "
    "al final presiona **Revisar**: cada respuesta trae su explicación."
)

# (pregunta, opciones, índice correcto, explicación)
QUESTIONS: list[tuple[str, list[str], int, str]] = [
    (
        "Un importador chileno debe pagar US\\$1 millón en 6 meses. ¿Qué forward lo cubre?",
        ["Venta de USD a plazo", "Compra de USD a plazo", "Ninguno: el forward es especulación"],
        1,
        "Su riesgo es que el dólar suba (pagará más pesos). Comprar USD a plazo fija el precio.",
    ),
    (
        "Ejemplo fijo: con spot 890 y tasas de 5,11% en pesos y 4,07% en dólares, el forward a 1 año "
        "está…",
        ["Bajo el spot", "Igual al spot", "Sobre el spot (≈ 898,89)"],
        2,
        "Paridad de tasas: 890 × 1,0511 / 1,0407 ≈ 898,89. Los puntos reflejan el diferencial de "
        "tasas, no una predicción del dólar.",
    ),
    (
        "Mismo ejemplo (tasas 5,11% y 4,07%, a 1 año), pero con spot 940 en vez de 890. Los puntos "
        "forward…",
        ["Son los mismos 8,89 puntos", "Se recalculan: ≈ 9,39 puntos", "Pasan a cero"],
        1,
        "Los puntos son proporcionales al spot: 940 × (1,0511/1,0407 − 1) ≈ 9,39. No se heredan de "
        "otro spot.",
    ),
    (
        "Un forward de compra a 948,91 por US\\$500.000 vence con spot 900. Por compensación, la empresa…",
        ["Recibe \\$24.455.000", "Paga \\$24.455.000", "No paga ni recibe nada"],
        1,
        "C = N × (S − K) = 500.000 × (900 − 948,91) = −24.455.000: paga la diferencia. Pero compra "
        "sus dólares más baratos en el mercado, así que su costo total queda fijado en 948,91.",
    ),
    (
        "¿Cuál es la principal diferencia entre una opción comprada y un forward?",
        [
            "La opción es un derecho: la pérdida queda acotada a la prima",
            "La opción no tiene costo",
            "El forward permite no ejercer",
        ],
        0,
        "Asimetría: el comprador de la opción solo ejerce si le conviene; a cambio paga prima. El "
        "forward obliga a ambas partes.",
    ),
    (
        "Si vendes una put, tu ganancia máxima es…",
        ["Ilimitada", "La prima pagada", "La prima recibida"],
        2,
        "Quien vende la opción cobra la prima: esa es su ganancia máxima si la opción no se ejerce. "
        "Su pérdida puede llegar a strike − prima.",
    ),
    (
        "Una call con strike 900 cuando el spot está en 950 está…",
        ["ITM (dentro del dinero)", "ATM", "OTM (fuera del dinero)"],
        0,
        "Ejercerla hoy permitiría comprar a 900 algo que vale 950: tiene valor intrínseco de 50.",
    ),
    (
        "¿Qué pasa con la prima de una opción si sube la volatilidad (todo lo demás igual)?",
        ["Baja", "Sube", "No cambia"],
        1,
        "Más volatilidad = más probabilidad de movimientos grandes. Como quien compra la opción "
        "nunca pierde más que la prima, esos movimientos solo suman valor al derecho: la prima sube.",
    ),
    (
        "Un importador quiere un collar de costo cero. ¿Qué arma?",
        [
            "Compra put + vende call",
            "Compra call + vende put",
            "Compra call + compra put",
        ],
        1,
        "Compra call (techo para el dólar que pagará) y vende put para financiarla (renuncia a "
        "bajas bajo el piso). Compra put + vende call es el collar del exportador.",
    ),
    (
        "Tu forward de compra todavía no vence y su MtM está negativo (el dólar bajó). ¿Qué puede pasar?",
        [
            "Nada: un forward solo importa al vencimiento",
            "El banco puede consumir tu línea de crédito o pedirte garantías",
            "El contrato se cancela automáticamente",
        ],
        1,
        "Mientras el contrato está vivo, un MtM en tu contra es una deuda potencial con el banco. "
        "En Chile lo usual es que el banco la cubra con tu línea de crédito o pida garantías: hay "
        "un efecto de liquidez aunque la cobertura funcione.",
    ),
]

KEYS = [f"q{i}" for i in range(1, len(QUESTIONS) + 1)]


def _mark_checked() -> None:
    """Callback del botón Revisar: activa la corrección en línea de cada tarjeta."""
    st.session_state["quiz_checked"] = True


def _reset_quiz() -> None:
    """Borra respuestas y corrección para volver a empezar."""
    for key in KEYS:
        st.session_state.pop(key, None)
    st.session_state["quiz_checked"] = False


checked = st.session_state.get("quiz_checked", False)

# Los radios van fuera de un form: cada respuesta dispara un rerun y la barra avanza en vivo.
# Se lee session_state antes de dibujar los radios (ya trae el valor recién elegido).
answered = sum(st.session_state.get(k) is not None for k in KEYS)
st.progress(
    answered / len(QUESTIONS),
    text=f"Respondidas: {answered} de {len(QUESTIONS)}",
)

answers: list[str | None] = []
for i, (q, opts, correct, why) in enumerate(QUESTIONS, start=1):
    with st.container(border=True):
        ans = st.radio(f"**{i}. {q}**", opts, index=None, key=f"q{i}")
        answers.append(ans)
        if checked and ans is not None:
            if ans == opts[correct]:
                st.success(why, title="Correcto", icon=":material/check_circle:")
            else:
                st.error(
                    f"Respuesta correcta: *{opts[correct]}*. {why}",
                    title="Incorrecto",
                    icon=":material/cancel:",
                )

# Primer botón de la página (los tests lo usan como at.button[0]).
submitted = st.button(
    "Revisar", type="primary", icon=":material/fact_check:", on_click=_mark_checked, key="quiz_check"
)

if checked:
    section("Resultado", icon=":material/scoreboard:")
    unanswered = [i for i, a in enumerate(answers, start=1) if a is None]
    if unanswered:
        st.warning(
            f"Faltan por responder: {', '.join(map(str, unanswered))}.",
            icon=":material/pending:",
        )
    score = sum(a == opts[c] for (_q, opts, c, _w), a in zip(QUESTIONS, answers, strict=True))
    with st.container(horizontal=True, vertical_alignment="bottom"):
        st.metric("Puntaje", f"{score} / {len(QUESTIONS)}", border=True, width="content")
        st.button("Volver a empezar", icon=":material/restart_alt:", on_click=_reset_quiz, key="quiz_reset")
    if submitted and score == len(QUESTIONS):
        st.balloons()

disclaimer(current="6_Quiz.py")
