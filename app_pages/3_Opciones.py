"""Opciones: payoff, valor intrínseco vs temporal, griegas, sensibilidades y Monte Carlo."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from derivados101.market import simulate_gbm
from derivados101.options import (
    OptionLeg,
    binomial_price,
    garman_kohlhagen,
    greeks,
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

KIND_LABELS = {"call": "Call (comprar USD)", "put": "Put (vender USD)"}
POSITION_LABELS = {"long": "Larga (compro)", "short": "Corta (vendo)"}
PREMIUM_LABELS = {"theoretical": "Teórica (GK)", "manual": "Manual (% spot)"}
MC_PATHS = 1000
MC_SHOWN_PATHS = 25


@st.cache_data(ttl="1h", max_entries=64, show_spinner="Simulando trayectorias…")
def _monte_carlo(
    spot: float, vol: float, years: float, r_dom: float, r_for: float, n_steps: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Simula el GBM y devuelve solo lo que la página dibuja (cacheado: es la parte pesada).

    Retorna (eje de tiempo, percentiles 5/25/50/75/95, primeras trayectorias, spots finales).
    """
    paths = simulate_gbm(spot, vol, years, r_dom, r_for, n_paths=MC_PATHS, n_steps=n_steps, seed=42)
    t_axis = np.linspace(0, years, paths.shape[0])
    pcts = np.percentile(paths, [5, 25, 50, 75, 95], axis=1)
    return t_axis, pcts, paths[:, :MC_SHOWN_PATHS].copy(), paths[-1].copy()


page_setup(
    "Opciones: el derecho, no la obligación",
    PAGE_ICON,
    subtitle="Prima, asimetría frente al forward, valor intrínseco y temporal, y qué mueve el precio.",
)

learn_box(
    "Una opción da el **derecho, pero no la obligación**, de comprar (*call*) o vender (*put*) "
    "dólares a un precio fijado (*strike*). Por ese derecho se paga una **prima**. Vas a ver "
    "por qué la opción es asimétrica frente al forward, qué es el valor intrínseco y el "
    "temporal, y qué mueve la prima."
)

with st.expander("Glosario rápido", icon=":material/menu_book:"):
    st.markdown(
        """
| Término | Significado |
|---|---|
| **Call** | Derecho a **comprar** USD al strike. Protege al que debe pagar USD (importador). |
| **Put** | Derecho a **vender** USD al strike. Protege al que recibirá USD (exportador). |
| **Largo (long)** | Compras la opción: **pagas** la prima y tienes el derecho. |
| **Corto (short)** | Vendes la opción: **recibes** la prima y asumes la obligación si la contraparte ejerce. |
| **Strike** | Precio de ejercicio (CLP por USD). |
| **Nocional** | Cantidad de USD que cubre la opción. |
| **Prima** | Precio de la opción, en CLP por USD de nocional (o en % del spot). |
| **Europea / americana** | La europea solo se ejerce al vencimiento; la americana, en cualquier momento hasta el vencimiento. |
| **ITM / ATM / OTM** | *In / at / out of the money*: valor intrínseco positivo, spot ≈ strike, o valor intrínseco cero. |
"""
    )

# ------------------------------------------------------------------ parámetros
# Panel en el cuerpo (no en la sidebar): los parámetros quedan junto a los gráficos que mueven.
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
        help="Teórica: calculada con Garman-Kohlhagen. Manual: la fijas como % del spot.",
    )

    c1, c2, c3, c4 = st.columns(4)
    spot = c1.slider("Spot hoy (CLP/USD)", 700.0, 1_100.0, 890.0, 1.0, key="opt_spot")
    strike = c2.slider("Strike (CLP/USD)", 700.0, 1_100.0, 900.0, 1.0, key="opt_strike")
    years = c3.slider("Plazo (años)", 0.02, 2.0, 0.5, 0.02, key="opt_years")
    vol = c4.slider("Volatilidad anual (%)", 2.0, 40.0, 12.0, 0.5, key="opt_vol") / 100

    d1, d2, d3, d4 = st.columns(4)
    r_dom = d1.number_input("Tasa CLP (%)", 0.0, 30.0, 5.11, 0.05, format="%.2f", key="opt_r_dom") / 100
    r_for = d2.number_input("Tasa USD (%)", 0.0, 30.0, 4.07, 0.05, format="%.2f", key="opt_r_for") / 100
    notional = d3.number_input(
        "Nocional (USD)", 1_000.0, 50_000_000.0, 500_000.0, 10_000.0, format="%.0f", key="opt_notional"
    )
    if prem_mode == "manual":
        prem_pct = d4.slider("Prima (% del spot)", 0.0, 10.0, 2.0, 0.1, key="opt_prem_pct") / 100
        premium = premium_from_pct(prem_pct, spot)
    else:
        premium = garman_kohlhagen(kind, spot, strike, years, r_dom, r_for, vol)
        d4.caption("Prima calculada con Garman-Kohlhagen. Elige **Manual** para fijarla tú.")

leg = OptionLeg(kind=kind, position=position, strike=strike, notional_usd=notional, premium=premium)
gk = garman_kohlhagen(kind, spot, strike, years, r_dom, r_for, vol)
iv = intrinsic_value(kind, spot, strike)
tv = time_value(kind, spot, strike, years, r_dom, r_for, vol)
mny = moneyness(kind, spot, strike)
sign = 1 if position == "long" else -1
total_prem = premium * notional

# ------------------------------------------------------------------ KPIs
m1, m2, m3, m4 = st.columns(4)
m1.metric("Prima usada (CLP por USD)", fmt_num(premium, 2), delta=f"{fmt_pct(premium / spot)} del spot",
          delta_color="off", delta_arrow="off", border=True)
m2.metric("Prima total", fmt_clp(total_prem), delta="pagas" if position == "long" else "recibes",
          delta_color="off", delta_arrow="off", border=True)
m3.metric("Estado hoy", mny, delta=f"valor intrínseco {fmt_num(iv, 2)}",
          delta_color="off", delta_arrow="off", border=True)
m4.metric("Precio teórico GK", fmt_num(gk, 2),
          delta=("igual a la prima usada" if prem_mode == "theoretical"
                 else f"dif. vs manual {fmt_num(gk - premium, 2)}"),
          delta_color="off", delta_arrow="off", border=True)

tab_exp, tab_val, tab_grk, tab_sim = st.tabs(
    [
        ":material/event: Al vencimiento",
        ":material/hourglass_top: Valor hoy",
        ":material/functions: Griegas",
        ":material/ssid_chart: Simulación",
    ]
)

# ------------------------------------------------------------------ 1. payoff
with tab_exp:
    st.subheader("¿Cuánto gano o pierdo al vencimiento?")
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
    st.plotly_chart(style_fig(fig, "Spot al vencimiento (CLP/USD)", "CLP"), width="stretch")

    if kind == "call" and position == "long":
        max_gain, max_loss = "Ilimitada", fmt_clp(-total_prem)
    elif kind == "call":
        max_gain, max_loss = f"{fmt_clp(total_prem)} (prima recibida)", "Ilimitada"
    elif position == "long":
        max_gain, max_loss = fmt_clp((strike - premium) * notional), fmt_clp(-total_prem)
    else:
        max_gain, max_loss = f"{fmt_clp(total_prem)} (prima recibida)", fmt_clp(-(strike - premium) * notional)
    be = strike + premium if kind == "call" else strike - premium
    e1, e2, e3 = st.columns(3)
    e1.metric("Ganancia máxima", max_gain, border=True)
    e2.metric("Pérdida máxima", max_loss, border=True)
    e3.metric("Punto de equilibrio", fmt_rate(be), border=True)

    with st.expander("La asimetría, explicada", icon=":material/balance:"):
        st.markdown(
            """
- El **forward** gana y pierde en forma simétrica: una línea recta.
- La **opción larga** tiene el lado bueno del forward, pero la pérdida queda **acotada a la
  prima**: si el mercado se mueve en contra, simplemente no la ejerces.
- El **vendedor** de la opción tiene el espejo: su ganancia máxima es la **prima recibida**
  y su pérdida puede ser grande (ilimitada en una call vendida).

| Posición | Ganancia máxima | Pérdida máxima |
|---|---|---|
| Call larga | Ilimitada | Prima pagada |
| Put larga | Strike − prima (si el dólar fuera a cero) | Prima pagada |
| Call corta | **Prima recibida** | Ilimitada |
| Put corta | **Prima recibida** | Strike − prima |
"""
        )
        st.latex(r"\text{Payoff call} = N\max(S_T-K,0) \qquad \text{Payoff put} = N\max(K-S_T,0)")

    with st.expander("Tabla de escenarios al vencimiento", icon=":material/table_chart:"):
        scen = np.array([0.85, 0.9, 0.95, 1.0, 1.05, 1.1, 1.15]) * spot
        df = pd.DataFrame(
            {
                "Spot final": [fmt_rate(s) for s in scen],
                "Payoff": [fmt_clp(v) for v in leg_payoff(leg, scen)],
                "Resultado neto": [fmt_clp(v) for v in leg_pnl(leg, scen)],
                "¿Se ejerce?": ["Sí" if v > 0 else "No" for v in intrinsic_value(kind, scen, strike)],
            }
        )
        st.dataframe(df, hide_index=True, width="stretch")

# ------------------------------------------------------------------ 2. valor
with tab_val:
    st.subheader("Valor intrínseco + valor temporal")
    st.markdown(
        "Antes del vencimiento, la opción vale **más** que lo que daría ejercerla hoy: queda tiempo "
        "para que el dólar se mueva a favor. Esa diferencia es el **valor temporal**, y se va "
        "\"derritiendo\" a medida que se acerca el vencimiento."
    )
    v1, v2, v3 = st.columns(3)
    v1.metric("Valor intrínseco", fmt_num(iv, 2), border=True)
    v2.metric("Valor temporal", fmt_num(tv, 2), border=True)
    v3.metric("Valor total (GK)", fmt_num(gk, 2), border=True)

    vgrid = np.linspace(strike * 0.8, strike * 1.2, 201)
    gk_curve = [garman_kohlhagen(kind, s, strike, years, r_dom, r_for, vol) for s in vgrid]
    iv_curve = intrinsic_value(kind, vgrid, strike)
    fig_v = go.Figure()
    fig_v.add_trace(go.Scatter(x=vgrid, y=iv_curve, name="Valor intrínseco",
                               line=dict(color=PALETTE["neutral"])))
    fig_v.add_trace(go.Scatter(x=vgrid, y=gk_curve, name="Valor total (GK)", fill="tonexty",
                               line=dict(color=PALETTE["primary"], width=3)))
    vline(fig_v, strike, "Strike")
    vline(fig_v, spot, "Spot hoy", color=PALETTE["accent"], dash="dash", position="top left")
    fig_v.update_layout(title="El área sombreada es el valor temporal (precio por USD)")
    st.plotly_chart(style_fig(fig_v, "Spot hoy (CLP/USD)", "CLP por USD"), width="stretch")

    with st.expander("ITM, ATM, OTM y la fórmula de Garman-Kohlhagen", icon=":material/calculate:"):
        st.markdown(
            """
- **ITM** (*in the money*): **valor intrínseco positivo** (call: spot > strike; put: spot < strike).
  Ojo: no implica ganancia neta, porque no descuenta la prima pagada.
- **ATM** (*at the money*): spot ≈ strike. Es donde el valor temporal es máximo.
- **OTM** (*out of the money*): valor intrínseco cero; todo su valor es temporal.

En el mercado de monedas, ATM se define a veces respecto del **forward**, no del spot.
Acá usamos el spot por simplicidad.

**Garman-Kohlhagen** es Black-Scholes adaptado a monedas: la moneda extranjera "rinde" su
tasa de interés, como una acción que paga dividendos.
"""
        )
        st.latex(
            r"C = S e^{-r_f T} N(d_1) - K e^{-r_d T} N(d_2) \qquad "
            r"P = K e^{-r_d T} N(-d_2) - S e^{-r_f T} N(-d_1)"
        )
        st.latex(
            r"d_1 = \frac{\ln(S/K) + (r_d - r_f + \sigma^2/2)T}{\sigma\sqrt{T}} \qquad d_2 = d_1 - \sigma\sqrt{T}"
        )
        st.markdown(
            "Las tasas de la app son compuestas anuales; se convierten a continuas con "
            "$r_c = \\ln(1+r)$. Nota: una **put europea muy ITM** puede tener valor temporal levemente "
            "negativo (no se puede ejercer antes y se pierde el interés del strike). La americana no."
        )

# ------------------------------------------------------------------ 3. griegas
with tab_grk:
    st.subheader("¿Qué mueve la prima? Las griegas")
    g = greeks(kind, spot, strike, years, r_dom, r_for, vol)
    g1, g2, g3, g4, g5 = st.columns(5)
    g1.metric("Delta", fmt_num(g["delta"], 3), help="Cambio de la prima por +1 peso en el spot.", border=True)
    g2.metric("Gamma", fmt_num(g["gamma"], 4), help="Cambio de la delta por +1 peso en el spot.", border=True)
    g3.metric("Vega", fmt_num(g["vega"], 2), help="Cambio de la prima por +1 punto de volatilidad.",
              border=True)
    g4.metric("Theta (día)", fmt_num(g["theta"], 3), help="Cambio de la prima por el paso de un día.",
              border=True)
    g5.metric("Rho", fmt_num(g["rho"], 2), help="Cambio de la prima por +1 punto en la tasa CLP.", border=True)
    pos_n = sign * notional  # la posición corta invierte el signo de todas las griegas
    st.caption(
        "Las métricas son por USD de opción **comprada**. "
        + ("Como tu posición es **corta**, para tu nocional los signos se invierten: " if sign < 0
           else "Para tu nocional: ")
        + f"delta ≈ {fmt_num(g['delta'] * pos_n, 0)} USD de exposición; vega "
        f"{md_clp(g['vega'] * pos_n)} por punto de vol; theta {md_clp(g['theta'] * pos_n)} por día."
    )

    s1, s2 = st.columns(2)
    vols = np.linspace(0.02, 0.40, 60)
    fig_s1 = go.Figure(go.Scatter(x=vols * 100, y=[garman_kohlhagen(kind, spot, strike, years, r_dom, r_for, v)
                                                    for v in vols], line=dict(color=PALETTE["primary"])))
    fig_s1.add_vline(x=vol * 100, line_dash="dot", line_color=PALETTE["neutral"])
    fig_s1.update_layout(title="Más volatilidad → prima más cara")
    s1.plotly_chart(style_fig(fig_s1, "Volatilidad (%)", "Prima (CLP por USD)", height=340), width="stretch")
    terms = np.linspace(0.01, 2.0, 60)
    fig_s2 = go.Figure(go.Scatter(x=terms, y=[garman_kohlhagen(kind, spot, strike, t, r_dom, r_for, vol)
                                              for t in terms], line=dict(color=PALETTE["secondary"])))
    fig_s2.add_vline(x=years, line_dash="dot", line_color=PALETTE["neutral"])
    fig_s2.update_layout(title="Más plazo → más valor temporal (en general)")
    s2.plotly_chart(style_fig(fig_s2, "Plazo (años)", "Prima (CLP por USD)", height=340), width="stretch")

    with st.expander("Otro método: árbol binomial (europea vs americana)", icon=":material/account_tree:"):
        eu = binomial_price(kind, spot, strike, years, r_dom, r_for, vol, steps=200, american=False)
        am = binomial_price(kind, spot, strike, years, r_dom, r_for, vol, steps=200, american=True)
        b1, b2, b3 = st.columns(3)
        b1.metric("Garman-Kohlhagen", fmt_num(gk, 4), border=True)
        b2.metric("Binomial europea (200 pasos)", fmt_num(eu, 4), border=True)
        b3.metric("Binomial americana", fmt_num(am, 4), border=True)
        st.caption(f"Diferencia americana − europea: {fmt_num(am - eu, 4)} por ejercicio anticipado.")
        st.markdown(
            "El árbol binomial (Cox-Ross-Rubinstein) divide el plazo en pasos donde el dólar sube o "
            "baja. Con muchos pasos converge a Garman-Kohlhagen para la europea; su ventaja es que "
            "permite valorar la **americana**, revisando en cada nodo si conviene ejercer antes."
        )

# ------------------------------------------------------------------ 4. Monte Carlo
with tab_sim:
    st.subheader("¿Por qué el tiempo vale? Mil futuros posibles")
    st.markdown(
        "Simulamos trayectorias aleatorias del dólar con la volatilidad elegida. La prima es, en "
        "esencia, el **promedio (descontado) de lo que pagaría la opción** en todos esos futuros: "
        "más plazo o más volatilidad abren el abanico y suben ese promedio."
    )
    n_steps = max(10, int(round(years * 252)))
    t_axis, pcts, shown_paths, final = _monte_carlo(spot, vol, years, r_dom, r_for, n_steps)
    fig_mc = go.Figure()
    for j in range(shown_paths.shape[1]):
        fig_mc.add_trace(go.Scatter(x=t_axis, y=shown_paths[:, j], mode="lines", showlegend=False,
                                    hoverinfo="skip", line=dict(width=0.6, color="rgba(138,150,163,0.35)")))
    fig_mc.add_trace(go.Scatter(x=t_axis, y=pcts[0], line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig_mc.add_trace(go.Scatter(x=t_axis, y=pcts[4], fill="tonexty", name="Rango 5%–95%",
                                fillcolor="rgba(31,111,139,0.15)", line=dict(width=0)))
    fig_mc.add_trace(go.Scatter(x=t_axis, y=pcts[1], line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig_mc.add_trace(go.Scatter(x=t_axis, y=pcts[3], fill="tonexty", name="Rango 25%–75%",
                                fillcolor="rgba(31,111,139,0.30)", line=dict(width=0)))
    fig_mc.add_trace(go.Scatter(x=t_axis, y=pcts[2], name="Mediana", line=dict(color=PALETTE["primary"], width=2)))
    fig_mc.add_hline(y=strike, line_dash="dot", line_color=PALETTE["negative"],
                     annotation_text=f"Strike {fmt_rate(strike, 0)}")
    st.plotly_chart(style_fig(fig_mc, "Años", "CLP/USD"), width="stretch")

    payoffs = intrinsic_value(kind, final, strike)
    mc_price = float(np.mean(payoffs)) / (1 + r_dom) ** years
    prob_itm = float(np.mean(payoffs > 0))
    k1, k2, k3 = st.columns(3)
    k1.metric("Prob. de terminar ITM (neutral al riesgo)", fmt_pct(prob_itm, 1), border=True,
              help="Probabilidad bajo la medida neutral al riesgo usada para valorizar. No es una predicción.")
    k2.metric("Prima por Monte Carlo", fmt_num(mc_price, 2), border=True)
    k3.metric("Prima GK (fórmula)", fmt_num(gk, 2), border=True)
    st.caption(
        "Simulación neutral al riesgo (deriva = r_CLP − r_USD), 1.000 trayectorias, semilla fija. "
        "La probabilidad es neutral al riesgo (no es una predicción) y la diferencia con la fórmula "
        f"({fmt_num(mc_price - gk, 2)}) es ruido de muestreo. No es un pronóstico del dólar."
    )

disclaimer(current=PAGE_FILE)
