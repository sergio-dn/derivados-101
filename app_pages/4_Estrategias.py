"""Estrategias: combinar patas de opciones para acotar costo y riesgo."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from pydantic import ValidationError

from derivados101.forward import forward_rate
from derivados101.options import OptionLeg, garman_kohlhagen
from derivados101.strategies import (
    PRESETS,
    breakevens,
    net_premium,
    spot_grid,
    strategy_pnl,
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
    page_setup,
    section,
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

EXPOSURE_SHORT = {
    "short_usd": "Debo USD",
    "long_usd": "Recibiré USD",
    "none": "Sin exposición",
}

info = next(p for p in PAGES if p.path.endswith("4_Estrategias.py"))
page_setup(
    "Estrategias: combinar opciones",
    info.icon,
    subtitle="Collares, spreads y otras combinaciones, vistas junto con el negocio que cubren.",
)

learn_box(
    "Combinando opciones compradas y vendidas se puede **diseñar** la protección: ponerle techo "
    "al dólar, financiar la prima vendiendo otra opción, o acotar el rango. Vas a ver cómo se "
    "suman las patas, cómo se ve el resultado **junto con el negocio** y por qué el collar del "
    "importador no es igual al del exportador."
)

st.warning(
    "Importador (pasivo en USD): **compra call + vende put**. "
    "Exportador (activo en USD): **compra put + vende call**. Usar el del otro duplica el riesgo "
    "en vez de cubrirlo.",
    title="Ojo con el sentido del collar",
    icon=":material/warning:",
)

# ------------------------------------------------------------------ inputs
PRESET_KEYS = list(PRESETS)
EXP_KEYS = list(EXPOSURE_LABELS)
LEG_COLS = ["kind", "position", "strike", "notional_usd", "premium"]
spot_default, _, _ = example_spot()
r_dom_default, r_for_default, rates_day = example_rates()
st.session_state.setdefault("strat_preset", "collar_importer")
st.session_state.setdefault("strat_notional", 500_000.0)

section("Arma la estrategia", ":material/construction:")
with st.container(border=True):
    c_preset, c_exp = st.columns(2, vertical_alignment="bottom")
    preset_key = c_preset.selectbox(
        "Punto de partida",
        PRESET_KEYS,
        format_func=lambda k: PRESETS[k].name,
        key="strat_preset",
    )
    preset = PRESETS[preset_key]
    # Al cambiar de estrategia se sugiere la exposición para la que fue pensada.
    if st.session_state.get("_strat_last_preset") != preset_key or "strat_exposure" not in st.session_state:
        st.session_state["strat_exposure"] = preset.suggested_exposure
        st.session_state["_strat_last_preset"] = preset_key
    exposure = c_exp.segmented_control(
        "Exposición del negocio",
        EXP_KEYS,
        format_func=EXPOSURE_SHORT.get,
        required=True,
        key="strat_exposure",
        width="stretch",
        help="Por defecto, la exposición para la que fue pensada la estrategia. "
        + " · ".join(EXPOSURE_LABELS.values()),
    )
    st.markdown(f"**{preset.name}**: {preset.description}")
    st.caption(preset.objective)

    c1, c2, c3 = st.columns(3)
    spot = c1.slider("Spot hoy (CLP/USD)", 600.0, 1_300.0, float(round(spot_default)), 1.0,
                     format="%.0f", key="strat_spot")
    vol = c2.slider(
        "Volatilidad anual (%)", 1.0, 40.0, 12.0, 0.5, format="%.1f", key="strat_vol",
        help="Cuánto se espera que se mueva el dólar en un año. Más volatilidad = primas más caras "
        "(hay más chance de que la opción termine sirviendo).",
    ) / 100
    years = c3.slider("Plazo (años)", 0.1, 2.0, 0.5, 0.1, key="strat_years",
                      help="Plazo de las opciones y del forward de comparación.")
    c4, c5, c6, c7 = st.columns(4)
    r_dom = c4.number_input("Tasa CLP (%)", 0.0, 30.0, round(r_dom_default * 100, 2), 0.05,
                            format="%.2f", key="strat_r_dom",
                            help=f"Tasa de referencia en pesos al {rates_day}.") / 100
    r_for = c5.number_input("Tasa USD (%)", 0.0, 30.0, round(r_for_default * 100, 2), 0.05,
                            format="%.2f", key="strat_r_for",
                            help=f"Tasa de referencia en dólares al {rates_day}.") / 100
    notional = c6.number_input("Nocional por pata (USD)", 1_000.0, 50_000_000.0, step=10_000.0,
                               format="%.0f", key="strat_notional")
    # El monto expuesto sigue al nocional salvo que el usuario lo cambie después.
    if st.session_state.get("_strat_last_notional") != notional or "strat_exposure_usd" not in st.session_state:
        st.session_state["strat_exposure_usd"] = float(notional)
        st.session_state["_strat_last_notional"] = notional
    exposure_usd = c7.number_input("Monto expuesto (USD)", 0.0, 50_000_000.0, step=10_000.0,
                                   format="%.0f", key="strat_exposure_usd",
                                   disabled=exposure == "none")
    example_spot_note()
    st.caption(
        ":material/calculate: Las primas se calculan con Garman-Kohlhagen (Black-Scholes para monedas) "
        "con la volatilidad, el plazo y las tasas de arriba. Un banco cotiza con su propio margen."
    )


# ------------------------------------------------------------------ patas (estado)
def _build_legs_df(spot_: float, vol_: float, years_: float, r_dom_: float, r_for_: float,
                   notional_: float) -> pd.DataFrame:
    """Patas del preset con primas teóricas, escaladas al nocional elegido."""
    legs_ = preset.build(spot_, vol_, years_, r_dom_, r_for_)
    return pd.DataFrame(
        {
            "kind": [leg.kind for leg in legs_],
            "position": [leg.position for leg in legs_],
            "strike": [float(leg.strike) for leg in legs_],
            "notional_usd": [float(notional_)] * len(legs_),
            "premium": [float(leg.premium) for leg in legs_],
        },
        columns=LEG_COLS,
    )


def _reprice(df_: pd.DataFrame) -> pd.DataFrame:
    """Recalcula la prima teórica de cada fila (mismo strike) con los parámetros actuales."""
    out = df_.copy()
    for i, row in out.iterrows():
        try:
            out.at[i, "premium"] = garman_kohlhagen(row["kind"], spot, float(row["strike"]),
                                                    years, r_dom, r_for, vol)
        except (ValueError, TypeError, KeyError):
            continue  # fila incompleta: se deja como está
    return out


def _set_base(df_: pd.DataFrame, custom: bool) -> None:
    """Fija la tabla base del editor y fuerza un editor nuevo (key con versión)."""
    st.session_state["_strat_base"] = df_.reset_index(drop=True)
    st.session_state["_strat_edited"] = st.session_state["_strat_base"].copy()
    st.session_state["_strat_custom"] = custom
    st.session_state["_strat_ver"] = st.session_state.get("_strat_ver", 0) + 1


params = (spot, vol, years, r_dom, r_for)
prev_edited = st.session_state.get("_strat_edited")
base = st.session_state.get("_strat_base")
custom = bool(st.session_state.get("_strat_custom")) or (
    prev_edited is not None and base is not None and not prev_edited.equals(base)
)
if base is None or st.session_state.get("_strat_base_preset") != preset_key:
    # Nueva estrategia (o primera vez): patas del preset.
    _set_base(_build_legs_df(*params, notional), custom=False)
    custom = False
elif not custom and (st.session_state.get("_strat_params") != params
                     or st.session_state.get("_strat_base_notional") != notional):
    # Sin ediciones del usuario: las patas siguen a los parámetros.
    _set_base(_build_legs_df(*params, notional), custom=False)
    custom = False
elif custom and st.session_state.get("_strat_base_notional") != notional:
    # Con ediciones: se reescalan los nocionales y se conserva lo demás.
    old_n = st.session_state.get("_strat_base_notional") or notional
    scaled = prev_edited.copy()
    scaled["notional_usd"] = scaled["notional_usd"] * (notional / old_n)
    _set_base(scaled, custom=True)
st.session_state["_strat_custom"] = custom
st.session_state["_strat_base_preset"] = preset_key
st.session_state["_strat_base_notional"] = notional
if not st.session_state["_strat_custom"]:
    st.session_state["_strat_params"] = params

# ------------------------------------------------------------------ editor
section("Patas de la estrategia", ":material/edit_note:")
st.caption(
    f"Cada fila es una opción. Puedes editar, agregar o borrar filas (máximo {MAX_LEGS}); tus cambios "
    "se conservan al mover los parámetros. Prima en CLP por USD de nocional."
)
stale = st.session_state["_strat_custom"] and st.session_state.get("_strat_params") != params
b1, b2 = st.columns(2)
if b1.button("Recalcular primas con los parámetros actuales", icon=":material/refresh:",
             key="strat_reprice", width="stretch", type="primary" if stale else "secondary",
             help="Mantiene tus strikes y nocionales; solo vuelve a calcular la prima teórica de cada pata."):
    _set_base(_reprice(st.session_state["_strat_edited"]), custom=True)
    st.session_state["_strat_params"] = params
    stale = False
if b2.button("Restaurar patas del preset", icon=":material/restart_alt:", key="strat_restore",
             width="stretch", help="Descarta tus ediciones y vuelve a armar la estrategia elegida."):
    _set_base(_build_legs_df(*params, notional), custom=False)
    st.session_state["_strat_params"] = params
    stale = False
if stale:
    st.info(
        "Cambiaste parámetros después de editar las patas: las primas de la tabla todavía son las "
        "anteriores. Usa **Recalcular primas** para actualizarlas.",
        icon=":material/update:",
    )

edited = st.data_editor(
    st.session_state["_strat_base"],
    key=f"strat_legs_{st.session_state['_strat_ver']}",
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
st.session_state["_strat_edited"] = edited.reset_index(drop=True)

legs: list[OptionLeg] = []
skipped = 0
for row in edited.dropna().to_dict("records"):
    try:
        legs.append(OptionLeg(**row))
    except (ValidationError, TypeError):
        skipped += 1
if skipped:
    st.warning(f"Se ignoraron {skipped} fila(s) incompletas o inválidas.", icon=":material/rule:")
if len(legs) > MAX_LEGS:
    st.warning(f"Se usan solo las primeras {MAX_LEGS} patas.", icon=":material/rule:")
    legs = legs[:MAX_LEGS]

# ------------------------------------------------------------------ resultados
grid = spot_grid(spot, 0.20, 401)
res = strategy_pnl(legs, grid, exposure=exposure, spot0=spot, exposure_usd=exposure_usd)
prem = net_premium(legs)
fwd = forward_rate(spot, r_dom, r_for, years)

section("Resultado al vencimiento", ":material/query_stats:")
target = "combined_pnl" if exposure != "none" else "options_pnl"
m1, m2, m3, m4 = st.columns(4)
# Base del %: el nocional cubierto = mayor nocional entre las patas (un collar de US$500.000
# cubre US$500.000 aunque tenga dos patas, por eso no se suman).
covered_usd = max((leg.notional_usd for leg in legs), default=0.0)
zero_tol = 1e-4 * spot * covered_usd  # 0,01% del monto cubierto: redondeos del solver
if abs(prem) <= max(zero_tol, 0.5):
    prem_label, prem_color = "≈ costo cero", "gray"
elif prem > 0:
    prem_label, prem_color = "pagas (débito)", "red"
else:
    prem_label, prem_color = "recibes (crédito)", "green"
m1.metric("Prima neta", fmt_clp(abs(prem)), delta=prem_label, delta_color=prem_color,
          delta_arrow="off", border=True,
          help="Suma de primas pagadas menos primas recibidas, al inicio.")
m2.metric("Prima neta (% del nocional)",
          fmt_pct(prem / (spot * covered_usd)) if covered_usd else "—", border=True,
          help="Prima neta / (spot hoy × nocional cubierto). Nocional cubierto = el mayor nocional "
          "entre las patas: un collar de US\\$500.000 cubre US\\$500.000 aunque tenga dos patas. "
          "Positivo = pagas; negativo = recibes.")
m3.metric("Peor resultado en el rango ±20%", fmt_clp(res[target].min()), border=True,
          help="Negocio + opciones si hay exposición; solo opciones si no la hay.")
m4.metric("Mejor resultado en el rango ±20%", fmt_clp(res[target].max()), border=True,
          help="Negocio + opciones si hay exposición; solo opciones si no la hay.")

if not legs:
    st.info("Agrega al menos una pata para ver el resultado.", icon=":material/add_circle:")

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
fig.update_layout(title="Resultado respecto del spot de hoy")
st.plotly_chart(style_fig(fig, "Spot al vencimiento (CLP/USD)", "CLP", height=540), width="stretch")

be = breakevens(res["spot"].to_numpy(), res[target].to_numpy())
st.markdown(
    ":material/balance: **Puntos de equilibrio** "
    + ("(negocio + opciones): " if exposure != "none" else "(opciones): ")
    + (", ".join(fmt_rate(b) for b in be) if be else "no hay cruces por cero en el rango.")
)

with st.expander("Cómo leer el gráfico", icon=":material/help:"):
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

with st.expander("Ejemplo: collar cero costo del importador", icon=":material/lightbulb:"):
    st.markdown(
        """
Un importador debe pagar US\\$500.000. Compra una **call 2% sobre el spot** (techo) y,
para financiarla, vende una **put** cuyo strike se elige de modo que **su prima pague
exactamente la call**: el costo inicial es **cero** (mira la métrica "Prima neta").

- Si el dólar **sube** sobre el techo: ejerce la call y paga como máximo el strike de la call.
- Si el dólar **baja** bajo el piso: la contraparte ejerce la put y el importador debe comprar
  al strike de la put; **renuncia** a la baja adicional.
- Entre ambos strikes: paga el spot de mercado.

"Costo cero" no significa gratis: se paga renunciando a la baja bajo el piso. Si subes la
volatilidad o el plazo, la banda cambia; si editas un strike, el costo deja de ser cero.

Para el **exportador** es al revés: compra put (piso) y vende call (techo).
"""
    )

with st.expander("Detalle por pata en algunos escenarios", icon=":material/table_chart:"):
    scen = [spot * k for k in (0.85, 0.95, 1.0, 1.05, 1.15)]
    rows = []
    for i, leg in enumerate(legs, start=1):
        r = strategy_pnl([leg], pd.Series(scen).to_numpy(), "none", spot)
        rows.append({"Pata": f"{i}. {POS_LABELS[leg.position]} {KIND_LABELS[leg.kind]} {fmt_rate(leg.strike)}"}
                    | {f"S = {fmt_num(s, 0)}": fmt_clp(v) for s, v in zip(scen, r["options_pnl"], strict=True)})
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

disclaimer(current="4_Estrategias.py")
