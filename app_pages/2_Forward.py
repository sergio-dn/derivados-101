"""Forward de moneda: sintético paso a paso, liquidación y MtM."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from derivados101.forward import (
    forward_mtm,
    forward_points,
    forward_rate,
    settle_forward,
    synthetic_forward,
)
from derivados101.ui import (
    PAGES,
    PALETTE,
    disclaimer,
    fmt_clp,
    fmt_num,
    fmt_pct,
    fmt_rate,
    fmt_usd,
    learn_box,
    md_clp,
    md_usd,
    page_setup,
    style_fig,
    vline,
)

PAGE_ICON = next(p.icon for p in PAGES if p.path.endswith("2_Forward.py"))
page_setup(
    "Forward: fijar hoy el dólar de mañana",
    PAGE_ICON,
    subtitle="Precio forward, liquidación al vencimiento y valor antes de vencer.",
)

learn_box(
    "Un forward es la **obligación** de comprar (o vender) dólares en una fecha futura a un "
    "precio fijado hoy. Vas a ver de dónde sale ese precio (los *puntos forward* no son una "
    "apuesta del banco: salen del diferencial de tasas), cómo se liquida al vencimiento y "
    "por qué su valor (MtM) se mueve antes de vencer."
)

# ------------------------------------------------------------------ inputs
SIDE_LABELS = {
    "buy": ":material/shopping_cart: Comprar USD (importador, tiene deuda en USD)",
    "sell": ":material/sell: Vender USD (exportador, tiene cobros en USD)",
}

with st.container(border=True):
    st.subheader("Parámetros del contrato", icon=":material/tune:")
    st.caption("Por defecto, el ejemplo de la planilla. Cambia cualquier valor y todo se recalcula.")
    c1, c2, c3, c4, c5 = st.columns(5)
    nominal = c1.number_input(
        "Nocional (USD)", 1_000.0, 100_000_000.0, 500_000.0, 10_000.0, format="%.0f", key="fwd_nominal"
    )
    spot = c2.number_input("Spot hoy (CLP/USD)", 300.0, 2_000.0, 890.0, 1.0, format="%.2f", key="fwd_spot")
    r_dom = c3.number_input("Tasa CLP anual (%)", 0.0, 30.0, 5.11, 0.05, format="%.2f", key="fwd_r_dom") / 100
    r_for = c4.number_input("Tasa USD anual (%)", 0.0, 30.0, 4.07, 0.05, format="%.2f", key="fwd_r_for") / 100
    years = c5.number_input("Plazo (años)", 0.05, 5.0, 1.0, 0.05, format="%.2f", key="fwd_years")
    side = st.segmented_control(
        "¿Qué necesita la empresa?",
        options=list(SIDE_LABELS),
        format_func=SIDE_LABELS.get,
        default="buy",
        required=True,
        key="fwd_side",
    )

fwd = forward_rate(spot, r_dom, r_for, years)
pts = forward_points(spot, fwd)

with st.container(horizontal=True):
    st.metric("Spot hoy", fmt_rate(spot), border=True, height="stretch")
    st.metric("Forward a plazo", fmt_rate(fwd), delta=f"{fmt_num(pts, 2)} pts", border=True, height="stretch")
    st.metric("Diferencial de tasas", fmt_pct(r_dom - r_for), border=True, height="stretch")
    st.metric("Monto fijado", fmt_clp(nominal * fwd), border=True, height="stretch")

tab_price, tab_settle, tab_mtm = st.tabs(
    [
        ":material/calculate: 1. De dónde sale el precio",
        ":material/event_available: 2. Al vencimiento",
        ":material/query_stats: 3. Antes de vencer (MtM)",
    ]
)

# ------------------------------------------------------------------ 1. sintético
with tab_price:
    st.subheader("¿De dónde sale el precio forward?")
    st.markdown(
        "El banco no adivina el dólar futuro. Puede **replicar** el forward con operaciones de hoy, "
        "y cobrar lo que le cuesta esa réplica. Esa es la *paridad de tasas de interés*."
    )
    syn = synthetic_forward(nominal, spot, r_dom, r_for, years)

    steps = pd.DataFrame(
        [
            ("a", "Pide prestados pesos hoy para comprar los USD al spot", fmt_clp(syn.debt_clp_today)),
            ("b", f"Esa deuda en CLP crece a {fmt_pct(r_dom)} anual hasta el vencimiento",
             fmt_clp(syn.debt_clp_maturity)),
            ("c", f"Los USD comprados se depositan a {fmt_pct(r_for)} anual", fmt_usd(syn.usd_maturity, 2)),
            ("d", "Precio implícito = CLP que se deben ÷ USD que se tienen (b ÷ c)", fmt_rate(syn.implied_rate, 4)),
            ("e", "Puntos forward = precio implícito − spot", fmt_num(syn.implied_points, 4)),
        ],
        columns=["Paso", "Qué hace el banco", "Resultado"],
    )
    st.dataframe(steps, hide_index=True, width="stretch")

    with st.expander("Fórmula y explicación", icon=":material/functions:"):
        st.latex(r"F = S \cdot \frac{(1+r_{CLP})^{T}}{(1+r_{USD})^{T}} \qquad \text{Puntos} = F - S")
        st.markdown(
            f"""
- Con $S$ = {fmt_rate(spot)}, $r_{{CLP}}$ = {fmt_pct(r_dom)}, $r_{{USD}}$ = {fmt_pct(r_for)} y
  $T$ = {fmt_num(years, 2)} año(s): $F$ = **{fmt_rate(fwd, 4)}**.
- Los puntos **reflejan el diferencial de tasas** entre pesos y dólares. Si la tasa en pesos es
  **mayor**, el forward queda **sobre** el spot (puntos positivos); si la tasa en dólares es
  mayor, queda **bajo** el spot (puntos negativos). No es una predicción del dólar ni un cargo
  del banco (el margen del banco es aparte).
- Los puntos son proporcionales al spot: si el spot cambia, **los puntos cambian**. No se
  pueden reciclar los puntos calculados con otro spot.
- Capitalización compuesta anual. Bancos usan convenciones de días (act/360, act/365) que
  generan diferencias menores.
"""
        )
        alt_spots = [spot * k for k in (0.95, 1.0, 1.0562, 1.10)]
        tbl = pd.DataFrame(
            {
                "Spot": [fmt_rate(s) for s in alt_spots],
                "Forward": [fmt_rate(forward_rate(s, r_dom, r_for, years)) for s in alt_spots],
                "Puntos": [
                    fmt_num(forward_points(s, forward_rate(s, r_dom, r_for, years)), 2) for s in alt_spots
                ],
            }
        )
        st.caption("Mismas tasas y plazo, distintos spots: los puntos se recalculan siempre.")
        st.dataframe(tbl, hide_index=True)

# ------------------------------------------------------------------ 2. liquidación
with tab_settle:
    st.subheader("Al vencimiento: entrega física vs compensación")
    st.markdown(
        "Mueve el dólar del día de vencimiento. Fíjate que el **resultado económico es el mismo** en "
        "ambas modalidades; lo que cambia es qué flujo de caja se mueve."
    )
    spot_T = st.slider(
        "Spot al vencimiento (CLP/USD)",
        min_value=float(round(spot * 0.75)),
        max_value=float(round(spot * 1.25)),
        value=float(round(spot * 1.0)),
        step=1.0,
        format="%.0f",
        key="fwd_spot_T",
    )
    stl = settle_forward(nominal, fwd, spot_T, side)

    cards = st.container(horizontal=True)
    with cards, st.container(border=True, height="stretch"):
        st.markdown("**:material/local_shipping: Entrega física (full delivery)**")
        verb = "paga" if side == "buy" else "recibe"
        usd_verb = "recibe" if side == "buy" else "entrega"
        st.markdown(
            f"La empresa **{verb} {md_clp(stl.full_delivery_clp)}** y **{usd_verb} "
            f"{md_usd(nominal)}**, a {fmt_rate(fwd)} sin importar el spot."
        )
        k1, k2 = st.columns(2)
        k1.metric("CLP intercambiados", fmt_clp(stl.full_delivery_clp))
        k2.metric("Valor de esos USD a mercado", fmt_clp(stl.market_value_clp))
    with cards, st.container(border=True, height="stretch"):
        st.markdown("**:material/swap_horiz: Compensación (non delivery)**")
        st.markdown(
            "No se intercambian dólares: solo se paga la **diferencia** entre el precio pactado y el "
            "spot del día. La empresa compra o vende sus USD en el mercado como siempre."
        )
        comp = stl.compensation_clp
        st.metric(
            "Compensación",
            fmt_clp(comp),
            delta="la empresa recibe" if comp > 0 else ("la empresa paga" if comp < 0 else "sin flujo"),
            delta_color="green" if comp > 0 else ("red" if comp < 0 else "gray"),
            delta_arrow="up" if comp > 0 else ("down" if comp < 0 else "off"),
        )
        st.caption("Positivo = la empresa recibe; negativo = paga al banco.")

    with st.expander("Fórmula de compensación", icon=":material/functions:"):
        st.latex(r"\text{Compra USD: } C = N\,(S_T - K) \qquad \text{Venta USD: } C = N\,(K - S_T)")
        sgn = "S_T − K" if side == "buy" else "K − S_T"
        diff = (spot_T - fwd) if side == "buy" else (fwd - spot_T)
        st.markdown(
            f"**Tu escenario:** forward calculado arriba $K$ = {fmt_rate(fwd)}, spot final "
            f"$S_T$ = {fmt_rate(spot_T)} → C = {fmt_num(nominal)} × ({sgn}) = "
            f"{fmt_num(nominal)} × {fmt_num(diff, 2)} = **{md_clp(stl.compensation_clp)}**."
        )
        st.markdown(
            "**Segundo ejemplo (caso de la planilla original):** compra de US\\$500.000 a un forward "
            "de 948,91 y spot final 900 → C = 500.000 × (900 − 948,91) = "
            f"**{md_clp(500_000 * (900 - 948.91))}** (la empresa paga). Ese 948,91 corresponde a "
            "otro spot inicial; sus puntos deben recalcularse con la fórmula, no heredarse."
        )

    # gráfico costo cubierto vs no cubierto
    grid = np.linspace(spot * 0.75, spot * 1.25, 201)
    unhedged = nominal * grid
    hedged = np.full_like(grid, nominal * fwd)
    fig = go.Figure()
    label_unh = "Sin cobertura (spot al vencimiento)"
    label_h = "Con forward (precio fijado)"
    fig.add_trace(go.Scatter(x=grid, y=unhedged, name=label_unh, line=dict(color=PALETTE["secondary"])))
    fig.add_trace(go.Scatter(x=grid, y=hedged, name=label_h, line=dict(color=PALETTE["primary"], width=3)))
    vline(fig, fwd, f"Forward {fmt_rate(fwd)}")
    vline(fig, spot_T, "Spot final", color=PALETTE["accent"], dash="dash", position="top left")
    title = "CLP que paga el importador" if side == "buy" else "CLP que recibe el exportador"
    fig.update_layout(title=title)
    with st.container(border=True):
        st.plotly_chart(style_fig(fig, "Spot al vencimiento (CLP/USD)", "CLP"), width="stretch")
        if side == "buy":
            st.caption(
                "Sobre el forward, la cobertura ahorra dinero; bajo el forward, se paga más que sin "
                "cubrirse. Ese es el trato: certeza a cambio de renunciar a la ganancia."
            )
        else:
            st.caption(
                "Bajo el forward, la cobertura protege el ingreso; sobre el forward, se deja de ganar. "
                "Certeza a cambio de renunciar a la ganancia."
            )

# ------------------------------------------------------------------ 3. MtM
with tab_mtm:
    st.subheader("Antes de vencer: Mark-to-Market")
    st.markdown(
        "Entre hoy y el vencimiento el contrato tiene un **valor de mercado**: lo que costaría o "
        "rendiría cerrarlo hoy."
    )
    st.warning(
        "Si es negativo para la empresa, el banco puede pedir **garantías** o usar la **línea de "
        "crédito** de la empresa, aunque el flujo cubierto todavía no ocurra.",
        title="Un MtM negativo puede exigir caja o línea",
        icon=":material/account_balance:",
    )

    left, right = st.columns([1, 2], gap="medium")
    months_total = max(1, int(round(years * 12)))
    with left, st.container(border=True):
        elapsed = st.slider(
            "Meses transcurridos", 0, months_total, min(months_total // 2, months_total), 1, key="fwd_elapsed"
        )
        spot_t = st.slider(
            "Spot en esa fecha (CLP/USD)",
            min_value=float(round(spot * 0.8)),
            max_value=float(round(spot * 1.2)),
            value=float(round(spot * 1.03)),
            step=1.0,
            format="%.0f",
            key="fwd_spot_t",
        )
    tau = max(years - elapsed / 12, 0.0)
    mtm = forward_mtm(nominal, fwd, spot_t, r_dom, r_for, tau, side)
    f_t = forward_rate(spot_t, r_dom, r_for, tau)
    with left:
        st.metric("Plazo remanente", f"{fmt_num(tau, 2)} años", border=True)
        st.metric("Forward de mercado para esa fecha", fmt_rate(f_t), border=True)
        st.metric("MtM para la empresa", fmt_clp(mtm), delta="a favor" if mtm >= 0 else "en contra",
                  delta_color="green" if mtm >= 0 else "red", delta_arrow="up" if mtm >= 0 else "down",
                  border=True)

    spot_grid = np.linspace(spot * 0.8, spot * 1.2, 121)
    fig2 = go.Figure()
    for m in sorted({0, months_total // 2, max(months_total - 1, 0), months_total}):
        t_rem = max(years - m / 12, 0.0)
        vals = [forward_mtm(nominal, fwd, s, r_dom, r_for, t_rem, side) for s in spot_grid]
        fig2.add_trace(go.Scatter(x=spot_grid, y=vals, name=f"Mes {m}"))
    fig2.add_trace(
        go.Scatter(x=[spot_t], y=[mtm], mode="markers", name="Tu escenario",
                   marker=dict(size=12, color=PALETTE["negative"], symbol="diamond"))
    )
    fig2.update_layout(title="MtM según spot y tiempo transcurrido")
    with right, st.container(border=True):
        st.plotly_chart(style_fig(fig2, "Spot (CLP/USD)", "MtM (CLP)"), width="stretch")
        st.caption(
            "En el mes 0, con el spot de hoy, el MtM es cero: un forward a precio de mercado no cuesta "
            "nada al firmarlo (sin contar el margen del banco). Al vencimiento, el MtM es igual a la "
            "compensación."
        )

    with st.expander("Fórmula del MtM", icon=":material/functions:"):
        st.latex(r"\text{MtM} = \pm\, N \cdot \frac{F_t - K}{(1+r_{CLP})^{\tau}}")
        st.markdown(
            "Se compara el precio pactado $K$ con el forward que hoy se obtendría para la misma fecha "
            "($F_t$, calculado con el spot y el plazo remanente $\\tau$) y se trae a valor presente. "
            "Signo + para quien compra USD, − para quien vende."
        )

disclaimer(current="2_Forward.py")
