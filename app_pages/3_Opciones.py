"""Opciones: payoff al vencimiento vs forward, prima, valor intrínseco y temporal."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from derivados101.options import (
    OptionLeg,
    garman_kohlhagen,
    intrinsic_value,
    leg_payoff,
    leg_pnl,
    moneyness,
    premium_from_pct,
    time_value,
)
from derivados101.ui import (
    PAGES,
    PALETTE,
    disclaimer,
    example_rates,
    example_spot,
    example_spot_note,
    fmt_clp,
    fmt_num,
    fmt_pct,
    fmt_rate,
    learn_box,
    md_clp,
    page_setup,
    style_fig,
    vline,
)

PAGE_FILE = "3_Opciones.py"
PAGE_ICON = next(p.icon for p in PAGES if p.path.endswith(PAGE_FILE))
ADVANCED_URL = "https://github.com/sergio-dn/derivados-101/tree/opciones-avanzado"

KIND_LABELS = {"call": "Call (comprar USD)", "put": "Put (vender USD)"}
POSITION_LABELS = {"long": "Larga (compro)", "short": "Corta (vendo)"}
PREMIUM_LABELS = {"theoretical": "Teórica", "manual": "Manual (% spot)"}

page_setup(
    "Opciones: el derecho, no la obligación",
    PAGE_ICON,
    subtitle="Prima, resultado al vencimiento frente al forward y de qué está hecho el precio.",
)

learn_box(
    "Una opción da el **derecho, pero no la obligación**, de comprar (*call*) o vender (*put*) "
    "dólares a un precio fijado (*strike*). Ese derecho se paga por adelantado: es la **prima**. "
    "Vas a ver cuánto ganas o pierdes al vencimiento comparado con un forward, y de qué está "
    "hecha la prima."
)

with st.expander("Glosario rápido", icon=":material/menu_book:"):
    st.markdown(
        """
| Término | Significado |
|---|---|
| **Call** | Derecho a **comprar** USD al strike. Protege al que debe pagar USD (importador). |
| **Put** | Derecho a **vender** USD al strike. Protege al que recibirá USD (exportador). |
| **Larga (long)** | Compras la opción: **pagas** la prima y tienes el derecho. |
| **Corta (short)** | Vendes la opción: **recibes** la prima y te obligas a cumplir si la contraparte ejerce. |
| **Strike** | Precio de ejercicio (CLP por USD). |
| **Nocional** | Cantidad de USD que cubre la opción. |
| **Prima** | Precio de la opción, en CLP por USD de nocional (o en % del spot). |
| **ITM / ATM / OTM** | *In / at / out of the money*: hoy convendría ejercerla, spot ≈ strike, o hoy no convendría. |
"""
    )

# ------------------------------------------------------------------ parámetros
EX_SPOT = float(round(example_spot()[0]))
EX_STRIKE = float(math.ceil(EX_SPOT / 10) * 10)  # strike por defecto: spot redondeado a la decena superior
EX_R_CLP, EX_R_USD, EX_RATES_DAY = example_rates()
LO, HI = float(round(EX_SPOT * 0.7)), float(round(EX_SPOT * 1.3))  # rango de sliders: ±30% del spot

with st.container(border=True):
    st.markdown("**:material/tune: Parámetros de la opción**")
    p1, p2, p3 = st.columns(3)
    kind = p1.segmented_control(
        "Tipo", list(KIND_LABELS), default="call", required=True, format_func=KIND_LABELS.get,
        key="opt_kind", width="stretch",
        help="Call: derecho a comprar USD al strike. Put: derecho a vender USD al strike.",
    )
    position = p2.segmented_control(
        "Posición", list(POSITION_LABELS), default="long", required=True, format_func=POSITION_LABELS.get,
        key="opt_position", width="stretch",
        help="Larga: compras la opción y pagas la prima. Corta: la vendes y recibes la prima.",
    )
    prem_mode = p3.segmented_control(
        "Prima", list(PREMIUM_LABELS), default="theoretical", required=True, format_func=PREMIUM_LABELS.get,
        key="opt_prem_mode", width="stretch",
        help="Teórica: calculada con un modelo (Garman-Kohlhagen). Manual: la fijas como % del spot.",
    )

    c1, c2, c3, c4 = st.columns(4)
    spot = c1.slider("Spot hoy (CLP/USD)", LO, HI, EX_SPOT, 1.0, format="%.0f", key="opt_spot")
    strike = c2.slider("Strike (CLP/USD)", LO, HI, EX_STRIKE, 1.0, format="%.0f", key="opt_strike")
    years = c3.slider("Plazo (años)", 0.02, 2.0, 0.5, 0.02, key="opt_years")
    vol = c4.slider(
        "Volatilidad anual (%)", 2.0, 40.0, 12.0, 0.5, key="opt_vol",
        help="Cuánto se espera que se mueva el dólar. Más volatilidad, prima más cara.",
    ) / 100

    d1, d2, d3, d4 = st.columns(4)
    r_dom = d1.number_input(
        "Tasa CLP (%)", 0.0, 30.0, round(EX_R_CLP * 100, 2), 0.05, format="%.2f", key="opt_r_dom"
    ) / 100
    r_for = d2.number_input(
        "Tasa USD (%)", 0.0, 30.0, round(EX_R_USD * 100, 2), 0.05, format="%.2f", key="opt_r_for"
    ) / 100
    notional = d3.number_input(
        "Nocional (USD)", 1_000.0, 50_000_000.0, 500_000.0, 10_000.0, format="%.0f", key="opt_notional"
    )
    if prem_mode == "manual":
        prem_pct = d4.slider("Prima (% del spot)", 0.0, 10.0, 2.0, 0.1, key="opt_prem_pct") / 100
        premium = premium_from_pct(prem_pct, spot)
    else:
        premium = garman_kohlhagen(kind, spot, strike, years, r_dom, r_for, vol)
        d4.caption("Prima calculada con el modelo. Elige **Manual** para fijarla tú.")

    example_spot_note()
    rates_origin = (
        "las del ejemplo de la planilla original" if EX_RATES_DAY == "planilla"
        else f"tasas de referencia al {EX_RATES_DAY}"
    )
    st.caption(f":material/percent: Tasas por defecto: {rates_origin}. Son un ejemplo, no una cotización.")

leg = OptionLeg(kind=kind, position=position, strike=strike, notional_usd=notional, premium=premium)
gk = garman_kohlhagen(kind, spot, strike, years, r_dom, r_for, vol)
iv = intrinsic_value(kind, spot, strike)
tv = time_value(kind, spot, strike, years, r_dom, r_for, vol)
mny = moneyness(kind, spot, strike)
sign = 1 if position == "long" else -1
total_prem = premium * notional
be = strike + premium if kind == "call" else strike - premium

# ------------------------------------------------------------------ KPIs
with st.container(horizontal=True):
    st.metric("Prima (CLP por USD)", fmt_num(premium, 2), delta=f"{fmt_pct(premium / spot)} del spot",
              delta_color="off", delta_arrow="off", border=True, height="stretch")
    st.metric("Prima total", fmt_clp(total_prem), delta="pagas hoy" if position == "long" else "recibes hoy",
              delta_color="off", delta_arrow="off", border=True, height="stretch")
    st.metric("Estado hoy", mny, delta=f"valor intrínseco {fmt_num(iv, 2)}",
              delta_color="off", delta_arrow="off", border=True, height="stretch")
    st.metric("Punto de equilibrio", fmt_rate(be), delta="strike ± prima",
              delta_color="off", delta_arrow="off", border=True, height="stretch")

tab_exp, tab_val = st.tabs(
    [
        ":material/event: 1. Al vencimiento",
        ":material/hourglass_top: 2. De qué está hecha la prima",
    ]
)

# ------------------------------------------------------------------ 1. payoff
with tab_exp:
    st.subheader("Al vencimiento: la opción acota la pérdida a la prima")
    grid = np.linspace(min(spot, strike) * 0.8, max(spot, strike) * 1.2, 401)
    payoff = leg_payoff(leg, grid)
    pnl = leg_pnl(leg, grid)
    direction = 1 if kind == "call" else -1  # call ~ comprar forward, put ~ vender forward
    fwd_like = sign * direction * (grid - strike) * notional

    show_fwd = st.toggle("Comparar con un forward al mismo precio (strike)", value=True, key="opt_show_fwd")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=grid, y=payoff, name="Payoff (sin prima)",
                             line=dict(color=PALETTE["neutral"], dash="dash")))
    fig.add_trace(go.Scatter(x=grid, y=pnl, name="Resultado neto (con prima)",
                             line=dict(color=PALETTE["primary"], width=3)))
    if show_fwd:
        fig.add_trace(go.Scatter(x=grid, y=fwd_like, name="Forward equivalente",
                                 line=dict(color=PALETTE["secondary"], dash="dot")))
    vline(fig, strike, f"Strike {fmt_rate(strike, 0)}")
    vline(fig, spot, "Spot hoy", color=PALETTE["accent"], dash="dash", position="top left")
    with st.container(border=True):
        st.plotly_chart(style_fig(fig, "Spot al vencimiento (CLP/USD)", "CLP"), width="stretch")

    if kind == "call" and position == "long":
        max_gain, max_loss = "Ilimitada", fmt_clp(-total_prem)
    elif kind == "call":
        max_gain, max_loss = f"{fmt_clp(total_prem)} (prima recibida)", "Ilimitada"
    elif position == "long":
        max_gain, max_loss = fmt_clp((strike - premium) * notional), fmt_clp(-total_prem)
    else:
        max_gain, max_loss = f"{fmt_clp(total_prem)} (prima recibida)", fmt_clp(-(strike - premium) * notional)
    with st.container(horizontal=True):
        st.metric("Ganancia máxima", max_gain, border=True, height="stretch")
        st.metric("Pérdida máxima", max_loss, border=True, height="stretch")
        st.metric("Punto de equilibrio", fmt_rate(be), border=True, height="stretch")

    st.markdown(
        """
El **forward** gana y pierde lo mismo hacia ambos lados: es una línea recta. La **opción
comprada** se queda con el lado bueno del forward. Si el dólar se mueve en contra, no la ejerces
y pierdes solo la prima. El **vendedor** tiene el espejo: gana como máximo la prima y su pérdida
puede ser grande (sin tope en una call vendida).
"""
    )

    st.markdown("**:material/table_chart: Escenarios al vencimiento**")
    scen = np.array([0.85, 0.9, 0.95, 1.0, 1.05, 1.1, 1.15]) * spot
    exercised = intrinsic_value(kind, scen, strike) > 0
    df = pd.DataFrame(
        {
            "Spot final": [fmt_rate(s) for s in scen],
            "¿Se ejerce?": ["Sí" if e else "No" for e in exercised],
            "Payoff (sin prima)": [fmt_clp(v) for v in leg_payoff(leg, scen)],
            "Resultado neto (con prima)": [fmt_clp(v) for v in leg_pnl(leg, scen)],
        }
    )
    st.dataframe(df, hide_index=True, width="stretch")
    st.caption(
        "Payoff: lo que paga la opción al vencimiento. Resultado neto: payoff menos la prima pagada "
        "(o más la prima recibida, si la vendiste)."
    )

    with st.expander("Ganancia y pérdida máxima por posición", icon=":material/balance:"):
        st.markdown(
            """
| Posición | Ganancia máxima | Pérdida máxima |
|---|---|---|
| Call larga | Sin tope | Prima pagada |
| Put larga | Strike − prima (si el dólar fuera a cero) | Prima pagada |
| Call corta | Prima recibida | Sin tope |
| Put corta | Prima recibida | Strike − prima |
"""
        )
        st.latex(r"\text{Payoff call} = N\max(S_T-K,0) \qquad \text{Payoff put} = N\max(K-S_T,0)")

# ------------------------------------------------------------------ 2. valor
with tab_val:
    st.subheader("Prima = valor intrínseco + valor temporal")
    st.markdown(
        "La prima tiene 2 partes. El **valor intrínseco** es lo que ganarías si ejercieras hoy. "
        "El **valor temporal** es lo que pagas extra porque queda tiempo para que el dólar se mueva "
        "a tu favor. Ese extra se va perdiendo a medida que se acerca el vencimiento, y el día que "
        "vence solo queda el intrínseco."
    )
    with st.container(horizontal=True):
        st.metric("Valor intrínseco (CLP por USD)", fmt_num(iv, 2), border=True, height="stretch")
        st.metric("Valor temporal (CLP por USD)", fmt_num(tv, 2), border=True, height="stretch")
        st.metric("Prima teórica (CLP por USD)", fmt_num(gk, 2), border=True, height="stretch")
    st.caption(
        f"Para tu nocional: prima teórica total {md_clp(gk * notional)}, de la cual "
        f"{md_clp(tv * notional)} es valor temporal."
    )

    vgrid = np.linspace(strike * 0.8, strike * 1.2, 201)
    gk_curve = [garman_kohlhagen(kind, s, strike, years, r_dom, r_for, vol) for s in vgrid]
    iv_curve = intrinsic_value(kind, vgrid, strike)
    fig_v = go.Figure()
    fig_v.add_trace(go.Scatter(x=vgrid, y=iv_curve, name="Valor intrínseco",
                               line=dict(color=PALETTE["neutral"])))
    fig_v.add_trace(go.Scatter(x=vgrid, y=gk_curve, name="Prima teórica", fill="tonexty",
                               line=dict(color=PALETTE["primary"], width=3)))
    vline(fig_v, strike, "Strike")
    vline(fig_v, spot, "Spot hoy", color=PALETTE["accent"], dash="dash", position="top left")
    fig_v.update_layout(title="El área sombreada es el valor temporal (CLP por USD)")
    with st.container(border=True):
        st.plotly_chart(style_fig(fig_v, "Spot hoy (CLP/USD)", "CLP por USD"), width="stretch")

    st.markdown(
        """
Según dónde está el spot respecto del strike, la opción está en uno de 3 estados:

1. **ITM** (*in the money*): hoy convendría ejercerla, así que tiene valor intrínseco. Ojo: eso no
   significa ganancia neta, porque falta descontar la prima.
2. **ATM** (*at the money*): spot ≈ strike. El valor temporal es máximo, porque el resultado
   depende por completo de hacia dónde se mueva el dólar.
3. **OTM** (*out of the money*): hoy no convendría ejercerla. Toda la prima es valor temporal.
"""
    )

    with st.expander("Cómo se calcula la prima", icon=":material/calculate:"):
        st.markdown(
            """
El banco calcula la prima con un modelo. Para monedas, el estándar es **Garman-Kohlhagen**
(Black-Scholes adaptado a monedas). La prima sube cuando:

1. El strike te favorece más (una call con strike bajo, o una put con strike alto).
2. Hay más plazo: más tiempo para que el dólar se mueva.
3. Hay más volatilidad: más movimiento posible, más valor del derecho.

Las tasas en pesos y en dólares también influyen, por la misma razón que mueven el forward.
En la práctica, el banco agrega su margen sobre la prima teórica.
"""
        )
        st.latex(
            r"C = S e^{-r_f T} N(d_1) - K e^{-r_d T} N(d_2) \qquad "
            r"P = K e^{-r_d T} N(-d_2) - S e^{-r_f T} N(-d_1)"
        )
        st.caption(
            "Las tasas de la app son compuestas anuales y el modelo las convierte a continuas. "
            "En una put muy ITM el valor temporal puede salir levemente negativo: es una "
            "particularidad de las opciones europeas, que solo se ejercen al vencimiento."
        )

st.caption(
    ":material/school: Existe una versión de esta página con más detalle técnico (griegas, árbol "
    f"binomial y simulación Monte Carlo) en la rama [opciones-avanzado]({ADVANCED_URL}) del repositorio."
)

disclaimer(current=PAGE_FILE)
