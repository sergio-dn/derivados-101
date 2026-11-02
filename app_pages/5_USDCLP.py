"""USD/CLP: histórico, volatilidad realizada, distribución por horizonte y backtest de cobertura."""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import plotly.graph_objects as go
import streamlit as st

from derivados101.market import (
    fetch_usdclp_live,
    hedge_backtest,
    horizon_changes,
    load_usdclp,
    realized_vol,
    reference_rates,
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
    page_setup,
    style_fig,
)

HORIZON_LABELS = {21: "1 mes", 63: "3 meses", 126: "6 meses", 189: "9 meses", 252: "1 año"}
MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
          "octubre", "noviembre", "diciembre"]
SOURCE_LABELS = {"csv": "CSV incluido", "live": "Actualizar en vivo (mindicador.cl)"}

info = next(p for p in PAGES if p.path.endswith("5_USDCLP.py"))
page_setup(
    "El dólar en Chile: cuánto se mueve",
    info.icon,
    subtitle="Datos reales del dólar observado para dimensionar el riesgo cambiario.",
)

learn_box(
    "Con datos reales del **dólar observado** (Banco Central de Chile) vas a ver cuánto puede "
    "moverse el USD/CLP en uno, tres o doce meses, qué es la volatilidad y qué habría pasado "
    "si un importador se hubiera cubierto con un forward en distintas fechas."
)


@st.cache_data(show_spinner=False)
def _local():
    return load_usdclp()


@st.cache_data(ttl=3600, show_spinner="Descargando desde mindicador.cl…")
def _live(years: tuple[int, ...]):
    # Timeout corto y 2 intentos: si la API no responde, se cae al CSV en menos de ~10 s.
    return fetch_usdclp_live(list(years), timeout=3.0, retries=2)


st.session_state.setdefault("usd_source", "csv")
source = st.segmented_control(
    "Fuente de datos",
    list(SOURCE_LABELS),
    format_func=SOURCE_LABELS.get,
    required=True,
    key="usd_source",
)
if source == "live":
    df = _live(tuple(range(2024, date.today().year + 1)))
    local = _local()
    if df.empty or df.equals(local):
        # fetch_usdclp_live nunca lanza: si falla devuelve el CSV. Si el resultado es idéntico
        # al CSV, no llegó nada nuevo (o la descarga falló): se avisa en vez de fingir "en vivo".
        last_local = f"{local['date'].iloc[-1]:%d-%m-%Y}" if not local.empty else "—"
        st.warning(
            "No se obtuvieron datos nuevos desde mindicador.cl (el servicio no respondió o no hay "
            f"datos posteriores). Se muestran los datos incluidos en la app, hasta el {last_local}.",
            icon=":material/cloud_off:",
        )
        df = local if df.empty else df
    else:
        st.caption(":material/cloud_done: Datos descargados desde mindicador.cl.")
else:
    df = _local()

if df.empty:
    st.error("No hay datos disponibles.", icon=":material/error:")
    st.stop()

last = df.iloc[-1]
first = df.iloc[0]
# Sparkline semanal (cada 5 días hábiles) para no sobrecargar la métrica.
spark = df["usdclp"].iloc[::-5].iloc[::-1].round(2).tolist()
m1, m2, m3, m4 = st.columns(4)
m1.metric(f"Último dato ({last['date']:%d-%m-%Y})", fmt_rate(last["usdclp"]),
          delta=f"{fmt_pct(last['usdclp'] / first['usdclp'] - 1)} desde {first['date']:%m-%Y}",
          delta_color="off", delta_arrow="off", border=True, chart_data=spark, chart_type="area")
m2.metric("Mínimo del período", fmt_rate(df["usdclp"].min()), border=True)
m3.metric("Máximo del período", fmt_rate(df["usdclp"].max()), border=True)
m4.metric("Observaciones", fmt_num(len(df)), border=True, help="Días hábiles con dólar observado publicado.")

tab_hist, tab_vol, tab_hor, tab_bt = st.tabs([
    ":material/show_chart: Histórico",
    ":material/ssid_chart: Volatilidad",
    ":material/date_range: Por plazo",
    ":material/shield: ¿Y si me hubiera cubierto?",
])

# ------------------------------------------------------------------ 1. histórico
with tab_hist:
    fig = go.Figure(go.Scatter(x=df["date"], y=df["usdclp"], name="Dólar observado",
                               line=dict(color=PALETTE["primary"])))
    st.plotly_chart(style_fig(fig, None, "CLP por USD", height=460), width="stretch")
    st.caption("Fuente: Banco Central de Chile, dólar observado, vía mindicador.cl.")

# ------------------------------------------------------------------ 2. volatilidad
with tab_vol:
    st.markdown(
        "La **volatilidad** mide cuán bruscos son los movimientos diarios, expresada en términos "
        "anuales. Es el insumo clave del precio de una opción: más volatilidad, prima más cara."
    )
    window = st.select_slider("Ventana (días hábiles)", options=[10, 21, 63, 126], value=21, key="usd_vol_window")
    vol = realized_vol(df, window=window).dropna()
    fig_v = go.Figure(go.Scatter(x=vol.index, y=vol * 100, name="Vol. realizada",
                                 line=dict(color=PALETTE["secondary"])))
    if not vol.empty:
        fig_v.add_hline(y=float(vol.mean() * 100), line_dash="dot", line_color=PALETTE["neutral"],
                        annotation_text=f"Promedio {fmt_num(vol.mean() * 100, 1)}%")
    st.plotly_chart(style_fig(fig_v, None, "% anual", height=380), width="stretch")
    with st.expander("Cómo se calcula", icon=":material/function:"):
        st.latex(r"r_t=\ln\frac{S_t}{S_{t-1}} \qquad \sigma_{anual}=\text{desv.est.}(r_t)\cdot\sqrt{252}")
        st.markdown(
            "Una vol de 12% anual equivale, groseramente, a que en un año el dólar se mueva "
            "±12% o menos con ~68% de probabilidad (si los retornos fueran normales, que no lo son "
            "del todo: hay más eventos extremos)."
        )

# ------------------------------------------------------------------ 3. horizontes
with tab_hor:
    st.subheader("¿Cuánto puede moverse en un plazo?")
    hc = horizon_changes(df)
    if hc.empty:
        st.info("No hay datos suficientes para calcular variaciones por horizonte.", icon=":material/info:")
    else:
        table = hc.assign(
            Plazo=hc["horizon_days"].map(lambda h: HORIZON_LABELS.get(h, f"{h} días")),
            Ventanas=hc["n"].map(fmt_num),
            **{
                "Mayor baja": hc["min"].map(fmt_pct),
                "P5": hc["p5"].map(fmt_pct),
                "Mediana": hc["p50"].map(fmt_pct),
                "P95": hc["p95"].map(fmt_pct),
                "Mayor alza": hc["max"].map(fmt_pct),
                "Desv. est.": hc["std"].map(fmt_pct),
            },
        )[["Plazo", "Ventanas", "Mayor baja", "P5", "Mediana", "P95", "Mayor alza", "Desv. est."]]
        st.dataframe(table, hide_index=True, width="stretch")
        st.markdown(
            "**Cómo leerlo según tu posición:** para un **importador** (debe USD) el riesgo es la "
            "**mayor alza**: cada punto que sube el dólar encarece lo que paga. Para un **exportador** "
            "(recibe USD) el riesgo es la **mayor baja**: cada punto que cae reduce sus ingresos en pesos."
        )

        fig_h = go.Figure()
        x = table["Plazo"]
        fig_h.add_trace(go.Bar(x=x, y=(hc["p95"] - hc["p5"]) * 100, base=hc["p5"] * 100, name="Rango P5–P95",
                               marker_color="rgba(31,111,139,0.35)"))
        fig_h.add_trace(go.Scatter(x=x, y=hc["p50"] * 100, mode="markers", name="Mediana",
                                   marker=dict(color=PALETTE["primary"], size=10)))
        fig_h.add_trace(go.Scatter(x=x, y=hc["max"] * 100, mode="markers", name="Mayor alza (malo para importador)",
                                   marker=dict(color=PALETTE["negative"], symbol="triangle-up", size=10)))
        fig_h.add_trace(go.Scatter(x=x, y=hc["min"] * 100, mode="markers", name="Mayor baja (malo para exportador)",
                                   marker=dict(color=PALETTE["accent"], symbol="triangle-down", size=10)))
        fig_h.update_layout(hovermode="closest")
        st.plotly_chart(style_fig(fig_h, None, "Variación % del USD/CLP", height=380), width="stretch")
        st.caption(
            "Ventanas traslapadas: las observaciones no son independientes y el período es corto. "
            "Es una ilustración del orden de magnitud, no una estimación de riesgo."
        )

# ------------------------------------------------------------------ 4. backtest
with tab_bt:
    st.markdown(
        "Un importador sabe en una fecha que deberá pagar dólares a cierto plazo. Compara "
        "comprar los dólares al spot del vencimiento contra haber fijado ese día un **forward teórico** "
        "(paridad de tasas con las tasas de referencia de **esa fecha**). No es el forward que cotizó "
        "un banco ese día."
    )
    min_d = first["date"].date()
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        years = c2.select_slider("Plazo", options=[1 / 12, 0.25, 0.5, 0.75, 1.0], value=0.5,
                                 format_func=lambda y: f"{fmt_num(y * 12, 0)} meses", key="usd_bt_years")
        latest_start = max(min_d, (last["date"] - timedelta(days=round(years * 365))).date())
        # Si el plazo crece, la fecha elegida puede quedar fuera de rango: se acota antes del widget.
        prev_start = st.session_state.get("usd_bt_start")
        if prev_start is not None and not (min_d <= prev_start <= latest_start):
            st.session_state["usd_bt_start"] = min(max(prev_start, min_d), latest_start)
        st.session_state.setdefault("usd_bt_start", min_d)
        start = c1.date_input("Fecha de decisión", min_value=min_d, max_value=latest_start,
                              format="DD/MM/YYYY", key="usd_bt_start")
        nominal = c3.number_input("Nocional (USD)", 1_000.0, 50_000_000.0, 500_000.0, 10_000.0, format="%.0f",
                                  key="usd_bt_nominal")
        try:
            ref_dom, ref_for, ref_day = reference_rates(start)
        except Exception:  # noqa: BLE001 - sin tasas de referencia, el usuario las ingresa
            ref_dom, ref_for, ref_day = None, None, None
        own = st.toggle("Usar mis propias tasas", key="usd_bt_own_rates", value=ref_dom is None,
                        disabled=ref_dom is None,
                        help="Por defecto se usan las tasas de referencia vigentes en la fecha de decisión.")
        if own:
            o1, o2 = st.columns(2)
            r_dom = o1.number_input("Tasa CLP (%)", 0.0, 30.0,
                                    round((ref_dom if ref_dom is not None else 0.0511) * 100, 2), 0.05,
                                    format="%.2f", key="usd_bt_r_dom") / 100
            r_for = o2.number_input("Tasa USD (%)", 0.0, 30.0,
                                    round((ref_for if ref_for is not None else 0.0407) * 100, 2), 0.05,
                                    format="%.2f", key="usd_bt_r_for") / 100
        else:
            r_dom = r_for = None

    try:
        bt = hedge_backtest(df, start, years, nominal, r_dom=r_dom, r_for=r_for)
    except ValueError as exc:
        st.warning(f"No se pudo calcular: {exc}", icon=":material/warning:")
    else:
        if own:
            rates_txt = "las tasas que ingresaste"
        else:
            rates_txt = (f"tasas de referencia: promedio de {MONTHS[ref_day.month - 1]} de {ref_day.year}"
                         if ref_day else "tasas de referencia")
        st.caption(
            f":material/percent: Forward calculado con tasa CLP {fmt_pct(bt['r_dom'])} y tasa USD "
            f"{fmt_pct(bt['r_for'])} ({rates_txt})."
        )
        b1, b2, b3, b4 = st.columns(4)
        b1.metric(f"Spot al decidir ({bt['start_date']:%d-%m-%Y})", fmt_rate(bt["spot_start"]), border=True)
        b2.metric("Forward teórico", fmt_rate(bt["fwd_rate"]), border=True,
                  help="Paridad de tasas: spot × (1 + tasa CLP)^plazo / (1 + tasa USD)^plazo. No es el "
                  "forward que cotizó un banco ese día.")
        b3.metric(f"Spot al vencimiento ({bt['end_date']:%d-%m-%Y})", fmt_rate(bt["spot_end"]), border=True)
        comp_pos = bt["compensation"] >= 0
        b4.metric("Compensación del forward", fmt_clp(bt["compensation"]), border=True,
                  delta="recibe" if comp_pos else "paga",
                  delta_color="green" if comp_pos else "red", delta_arrow="up" if comp_pos else "down")
        d1, d2, d3 = st.columns(3)
        d1.metric("Costo sin cobertura", fmt_clp(bt["cost_unhedged"]), border=True)
        d2.metric("Costo con forward teórico", fmt_clp(bt["cost_hedged"]), border=True)
        sav_pos = bt["savings"] >= 0
        d3.metric("Diferencia ex post", fmt_clp(bt["savings"]), border=True,
                  delta="la cobertura convino" if sav_pos else "habría convenido no cubrirse",
                  delta_color="green" if sav_pos else "red", delta_arrow="up" if sav_pos else "down")
        st.caption(
            "Aproximación: las tasas de referencia son tasas interbancarias a 3 meses (en pesos y en "
            "dólares) vigentes en la fecha de decisión. Un banco cotiza el forward con su propio margen, "
            "así que el precio real habría sido algo peor para la empresa. Que la cobertura haya "
            "'perdido' ex post no la hace una mala decisión: su objetivo era eliminar la incertidumbre."
        )

disclaimer(current="5_USDCLP.py")
