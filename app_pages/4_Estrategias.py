"""Estrategias: combinar patas de opciones para acotar costo y riesgo."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from pydantic import ValidationError

from derivados101.forward import forward_rate
from derivados101.options import OptionLeg
from derivados101.strategies import (
    PRESETS,
    breakevens,
    net_premium,
    spot_grid,
    strategy_pnl,
)
from derivados101.ui import (
    PALETTE,
    disclaimer,
    fmt_clp,
    fmt_num,
    fmt_pct,
    fmt_rate,
    learn_box,
    page_setup,
    style_fig,
    vline,
)

MAX_LEGS = 4
EXPOSURE_LABELS = {
    "short_usd": "Debo USD (importador: pasivo en USD)",
    "long_usd": "Recibiré USD (exportador: activo en USD)",
    "none": "Sin exposición (especulación)",
}
KIND_LABELS = {"call": "Call", "put": "Put"}
POS_LABELS = {"long": "Compro (long)", "short": "Vendo (short)"}

page_setup("Estrategias: combinar opciones", "🧩")

learn_box(
    "Combinando opciones compradas y vendidas se puede **diseñar** la protección: ponerle techo "
    "al dólar, financiar la prima vendiendo otra opción, o acotar el rango. Vas a ver cómo se "
    "suman las patas, cómo se ve el resultado **junto con el negocio** y por qué el collar del "
    "importador no es igual al del exportador."
)

st.warning(
    "**Ojo con el sentido del collar.** Importador (pasivo en USD): **compra call + vende put**. "
    "Exportador (activo en USD): **compra put + vende call**. Usar el del otro duplica el riesgo "
    "en vez de cubrirlo.",
    icon="⚠️",
)

# ------------------------------------------------------------------ inputs
with st.sidebar:
    st.header("Estrategia")
    preset_key = st.selectbox(
        "Punto de partida",
        list(PRESETS),
        index=list(PRESETS).index("collar_importer"),
        format_func=lambda k: PRESETS[k].name,
    )
    preset = PRESETS[preset_key]
    spot = st.slider("Spot hoy (CLP/USD)", 700.0, 1_100.0, 890.0, 1.0)
    premium_pct = st.slider(
        "Prima de una opción ATM (% del spot)", 0.0, 6.0, 2.0, 0.1,
        help="Simplificación: las patas fuera del dinero cuestan menos, las dentro del dinero suman su valor intrínseco.",
    ) / 100
    notional = st.number_input("Nocional por pata (USD)", 1_000.0, 50_000_000.0, 500_000.0, 10_000.0, format="%.0f")
    exp_keys = list(EXPOSURE_LABELS)
    exposure = st.radio(
        "Exposición del negocio",
        exp_keys,
        index=exp_keys.index(preset.suggested_exposure),
        format_func=EXPOSURE_LABELS.get,
        help="Por defecto, la exposición para la que fue pensada la estrategia.",
    )
    exposure_usd = st.number_input("Monto expuesto (USD)", 0.0, 50_000_000.0, float(notional), 10_000.0, format="%.0f")
    with st.expander("Forward de comparación"):
        years = st.slider("Plazo (años)", 0.1, 2.0, 0.5, 0.1)
        r_dom = st.number_input("Tasa CLP (%)", 0.0, 30.0, 5.11, 0.05, format="%.2f") / 100
        r_for = st.number_input("Tasa USD (%)", 0.0, 30.0, 4.07, 0.05, format="%.2f") / 100

with st.container(border=True):
    st.markdown(f"**{preset.name}** — {preset.description}")
    st.caption(preset.objective)

# ------------------------------------------------------------------ editor
st.subheader("Patas de la estrategia")
st.caption(f"Puedes editar, agregar o borrar filas (máximo {MAX_LEGS}). Prima en CLP por USD de nocional.")
base_legs = preset.build(spot, premium_pct)
base_df = pd.DataFrame(
    {
        "kind": [leg.kind for leg in base_legs],
        "position": [leg.position for leg in base_legs],
        "strike": [round(leg.strike, 2) for leg in base_legs],
        "notional_usd": [float(notional)] * len(base_legs),
        "premium": [round(leg.premium, 2) for leg in base_legs],
    }
)
edited = st.data_editor(
    base_df,
    key=f"legs_{preset_key}_{spot}_{premium_pct}_{notional}",
    num_rows="dynamic",
    hide_index=True,
    width="stretch",
    column_config={
        "kind": st.column_config.SelectboxColumn("Tipo", options=list(KIND_LABELS), required=True),
        "position": st.column_config.SelectboxColumn("Posición", options=list(POS_LABELS), required=True),
        "strike": st.column_config.NumberColumn("Strike", min_value=1.0, format="%.2f", required=True),
        "notional_usd": st.column_config.NumberColumn("Nocional USD", min_value=1.0, format="%.0f", required=True),
        "premium": st.column_config.NumberColumn("Prima CLP/USD", min_value=0.0, format="%.2f", required=True),
    },
)

legs: list[OptionLeg] = []
skipped = 0
for row in edited.dropna().to_dict("records"):
    try:
        legs.append(OptionLeg(**row))
    except (ValidationError, TypeError):
        skipped += 1
if skipped:
    st.warning(f"Se ignoraron {skipped} fila(s) incompletas o inválidas.")
if len(legs) > MAX_LEGS:
    st.warning(f"Se usan solo las primeras {MAX_LEGS} patas.")
    legs = legs[:MAX_LEGS]

# ------------------------------------------------------------------ resultados
grid = spot_grid(spot, 0.20, 401)
res = strategy_pnl(legs, grid, exposure=exposure, spot0=spot, exposure_usd=exposure_usd)
prem = net_premium(legs)
fwd = forward_rate(spot, r_dom, r_for, years)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Prima neta", fmt_clp(abs(prem)),
          delta="pagas (débito)" if prem > 0.5 else ("recibes (crédito)" if prem < -0.5 else "≈ costo cero"),
          delta_color="off")
m2.metric("Prima neta (% del nocional)", fmt_pct(prem / (spot * notional)) if notional else "—")
target = "combined_pnl" if exposure != "none" else "options_pnl"
m3.metric("Peor resultado en el rango ±20%", fmt_clp(res[target].min()))
m4.metric("Mejor resultado en el rango ±20%", fmt_clp(res[target].max()))

if not legs:
    st.info("Agrega al menos una pata para ver el resultado.")

fig = go.Figure()
fig.add_trace(go.Scatter(x=res["spot"], y=res["options_pnl"], name="Opciones (con primas)",
                         line=dict(color=PALETTE["primary"], dash="dash")))
if exposure != "none":
    fig.add_trace(go.Scatter(x=res["spot"], y=res["underlying_pnl"], name="Negocio sin cubrir",
                             line=dict(color=PALETTE["secondary"], dash="dot")))
    fig.add_trace(go.Scatter(x=res["spot"], y=res["combined_pnl"], name="Negocio + opciones",
                             line=dict(color=PALETTE["accent"], width=3)))
    fwd_sign = 1 if exposure == "short_usd" else -1  # importador compra fwd; exportador vende
    hedged_fwd = res["underlying_pnl"] + fwd_sign * (res["spot"] - fwd) * exposure_usd
    fig.add_trace(go.Scatter(x=res["spot"], y=hedged_fwd, name=f"Negocio + forward a {fmt_rate(fwd)}",
                             line=dict(color=PALETTE["purple"], width=1.5)))
vline(fig, spot, "Spot hoy", color=PALETTE["neutral"], position="top left")
for leg in legs:
    fig.add_vline(x=leg.strike, line_width=0.5, line_dash="dot", line_color=PALETTE["neutral"])
fig.update_layout(title="Resultado al vencimiento (respecto del spot de hoy)")
st.plotly_chart(style_fig(fig, "Spot al vencimiento (CLP/USD)", "CLP", height=460), width="stretch")

be = breakevens(res["spot"].to_numpy(), res[target].to_numpy())
st.markdown(
    "**Puntos de equilibrio** "
    + ("(negocio + opciones): " if exposure != "none" else "(opciones): ")
    + (", ".join(fmt_rate(b) for b in be) if be else "no hay cruces por cero en el rango.")
)

with st.expander("Cómo leer el gráfico"):
    st.markdown(
        f"""
- **Opciones**: suma del resultado de cada pata al vencimiento, descontando primas pagadas y
  sumando primas recibidas.
- **Negocio sin cubrir**: lo que gana o pierde la empresa si el dólar se aleja de
  {fmt_rate(spot)} (para el importador, cada peso que sube el dólar es pérdida).
- **Negocio + opciones**: lo que importa en una cobertura. En un collar se ve una **banda**:
  plana bajo el strike de la put y sobre el strike de la call.
- **Negocio + forward**: línea plana. El forward fija todo; las opciones dejan un rango
  abierto a cambio de prima o de renunciar a parte del movimiento favorable.
- Todo se mide contra el spot de hoy; el forward además incluye los puntos forward del plazo
  elegido. No se considera el valor del dinero en el tiempo de las primas.
"""
    )
    st.latex(r"\text{PnL}_{\text{opciones}}(S_T)=\sum_i s_i N_i\big[\max(\pm(S_T-K_i),0) - \text{prima}_i\big]")
    st.caption("s = +1 si la pata se compra, −1 si se vende.")

with st.expander("Ejemplo: collar cero costo del importador"):
    st.markdown(
        """
Un importador debe pagar US\\$500.000. Compra una **call 2% sobre el spot** (techo) y para
financiarla vende una **put 2% bajo el spot** (piso). Si las primas son iguales, el costo
inicial es **cero**.

- Si el dólar **sube** sobre el techo: ejerce la call y paga como máximo el strike de la call.
- Si el dólar **baja** bajo el piso: la contraparte ejerce la put y el importador debe comprar
  al strike de la put; **renuncia** a la baja adicional.
- Entre ambos strikes: paga el spot de mercado.

Para el **exportador** es al revés: compra put (piso) y vende call (techo).
"""
    )

with st.expander("Detalle por pata en algunos escenarios"):
    scen = [spot * k for k in (0.85, 0.95, 1.0, 1.05, 1.15)]
    rows = []
    for i, leg in enumerate(legs, start=1):
        r = strategy_pnl([leg], pd.Series(scen).to_numpy(), "none", spot)
        rows.append({"Pata": f"{i}. {POS_LABELS[leg.position]} {KIND_LABELS[leg.kind]} {fmt_rate(leg.strike)}"}
                    | {f"S = {fmt_num(s, 0)}": fmt_clp(v) for s, v in zip(scen, r["options_pnl"], strict=True)})
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

disclaimer()
