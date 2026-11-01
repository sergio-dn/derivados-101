"""Quiz: 10 preguntas con feedback y explicación."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st

from derivados101.ui import disclaimer, learn_box, page_setup

page_setup("Quiz: ¿quedó claro?", "✅")

learn_box(
    "Diez preguntas para comprobar lo aprendido. Responde todas y presiona **Revisar**: "
    "cada respuesta trae su explicación."
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
        "Con tasa en pesos 5,11% y en dólares 4,07%, el forward a 1 año con spot 890 está…",
        ["Bajo el spot", "Igual al spot", "Sobre el spot (≈ 898,89)"],
        2,
        "Paridad de tasas: 890 × 1,0511 / 1,0407 ≈ 898,89. Los puntos reflejan el diferencial de "
        "tasas, no una predicción del dólar.",
    ),
    (
        "Si el spot fuera 940 en vez de 890 (mismas tasas y plazo), los puntos forward…",
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
        "Más volatilidad amplía el abanico de escenarios; como la pérdida del comprador está "
        "acotada, más dispersión aumenta el valor esperado del derecho (vega positiva).",
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
        "Bajo IFRS 9, sin contabilidad de coberturas, la variación del MtM de un derivado va a…",
        ["Resultados del período", "Patrimonio (OCI)", "No se registra hasta el vencimiento"],
        0,
        "Todo derivado va al balance a valor razonable; sin hedge accounting, sus cambios van a "
        "resultados. Con hedge accounting de flujo de caja, la porción efectiva va a OCI.",
    ),
]

with st.form("quiz"):
    answers: list[str | None] = []
    for i, (q, opts, _, _) in enumerate(QUESTIONS, start=1):
        answers.append(st.radio(f"**{i}. {q}**", opts, index=None, key=f"q{i}"))
    submitted = st.form_submit_button("Revisar", type="primary")

if submitted:
    unanswered = [i for i, a in enumerate(answers, start=1) if a is None]
    if unanswered:
        st.warning(f"Faltan por responder: {', '.join(map(str, unanswered))}.")
    score = 0
    for i, ((_q, opts, correct, why), ans) in enumerate(zip(QUESTIONS, answers, strict=True), start=1):
        if ans is None:
            continue
        ok = ans == opts[correct]
        score += ok
        if ok:
            st.success(f"**{i}.** Correcto. {why}")
        else:
            st.error(f"**{i}.** Respuesta correcta: *{opts[correct]}*. {why}")
    st.metric("Puntaje", f"{score} / {len(QUESTIONS)}")
    if score == len(QUESTIONS):
        st.balloons()

disclaimer()
