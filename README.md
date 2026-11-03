# Derivados 101 — forwards y opciones sobre el dólar, explicados con el dólar real

App para entender, en simple, cómo funcionan los **derivados de moneda USD/CLP**:
forwards, opciones y collares. Cada concepto es una pregunta directa ("¿Qué es un forward?")
con pocas pantallas: la idea, un ejemplo con números y una calculadora para ver cómo
funciona en la práctica.

Está pensada para personas con finanzas básicas que alguna vez escucharon "tomamos un
forward" en una reunión y se quedaron con la duda. No es un curso de valorización ni de
contabilidad de coberturas.

> **Material educativo. No es asesoría financiera ni contable.**

**En línea:** [derivados-101.streamlit.app](https://derivados-101.streamlit.app)

![Inicio: la lista de preguntas](docs/inicio.png)

<p align="center"><img src="docs/demo_mtm.png" width="49%" alt="Demo: MtM de un forward y cuándo el banco pide garantías"> <img src="docs/demo_collar.png" width="49%" alt="Demo: collar de costo cero, al subir el techo baja el piso"></p>

<sub>Izquierda: mueves el forward de mercado y ves el MtM, cuánta línea de crédito usa y cuándo sale caja como garantía. Derecha: subes el techo del collar y el piso de costo cero se ajusta solo.</sub>

---

## Cómo abrirla en tu computador (3 pasos)

No necesitas saber programar. Solo tener **Python 3.11 o superior** instalado.

### macOS / Linux

1. **Instala Python** desde [python.org/downloads](https://www.python.org/downloads/)
   (en Mac también sirve `brew install python`). Verifica en la Terminal: `python3 --version`.
2. **Descarga este proyecto**: botón verde *Code → Download ZIP* en GitHub y descomprímelo
   (o `git clone` si usas git).
3. **Abre la Terminal en la carpeta del proyecto y ejecuta:**

   ```bash
   bash scripts/run.sh
   ```

### Windows

1. **Instala Python** desde [python.org/downloads](https://www.python.org/downloads/).
   Durante la instalación marca la casilla **"Add python.exe to PATH"**.
2. **Descarga este proyecto**: *Code → Download ZIP* y descomprímelo.
3. **Abre la carpeta del proyecto y haz doble clic en `scripts\run.bat`**
   (o ejecútalo desde la consola: `scripts\run.bat`).

La primera vez el script crea un entorno aislado (`.venv`) e instala las dependencias;
tarda un par de minutos. Las siguientes veces abre directo. La app se abre sola en tu
navegador en `http://localhost:8501`. Para cerrarla, vuelve a la terminal y presiona
`Ctrl + C`.

<details>
<summary>Instalación manual (si prefieres hacerlo a mano)</summary>

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```
</details>

---

## Qué hay en la app

**Conceptos.** Nueve preguntas, en orden de lectura. Cada una tiene de 3 a 6 pantallas
(concepto, ejemplo, demo interactiva y 3 ideas clave):

1. ¿Qué es el riesgo cambiario?
2. ¿Qué es un derivado?
3. ¿Qué es un forward?
4. ¿Qué tipos de forward hay?
5. ¿Qué es el MtM y por qué piden garantías?
6. ¿Qué es una opción?
7. ¿De qué depende el precio de una opción?
8. ¿Qué es un collar de costo cero?
9. ¿Cuánto y cuándo cubrirse?

**Simuladores.** Para quien quiera jugar con todos los parámetros: Forward (precio,
liquidación, MtM), Opciones (resultado al vencimiento, de qué está hecha la prima),
Estrategias (presets y combinaciones de hasta 4 opciones) y Dólar en Chile (histórico,
cuánto se mueve y qué habría pasado cubriéndose).

**Repasa.** Más preguntas frecuentes y un quiz corto.

Donde la app simplifica, lo dice: en la realidad hay márgenes del banco, curvas de tasas
y contratos de crédito que cambian los números.

Los ejemplos usan casos genéricos (por ejemplo, *"un importador chileno que debe pagar
USD 500.000 en un año"*) con cifras fijas rotuladas como ejemplo: spot 890, tasas de 5,11%
en pesos y 4,07% en dólares, forward a 1 año de 898,89. En los simuladores, el dólar de
partida es el último observado disponible, y también es solo un ejemplo.

---

## Fuente de datos

- **Dólar observado** oficial publicado por el Banco Central de Chile.
- La app trae **un CSV incluido** (`data/usdclp_dolar_observado.csv`, desde enero 2024),
  así que funciona **sin internet**: la app nunca consulta APIs externas al abrirse.
- **Tasas de referencia** (`data/tasas_referencia.csv`): tasas interbancarias a 3 meses de
  Chile y EE.UU. publicadas por la OCDE vía [FRED](https://fred.stlouisfed.org). Son una
  aproximación: un banco cotiza con sus propias tasas y margen.
- Un proceso de GitHub actualiza el CSV cada día hábil desde la **API oficial del Banco Central**
  (si el repositorio tiene configuradas credenciales en sus *Secrets*) o, si no, desde mindicador.cl.
  Las credenciales nunca están en el código ni en la app publicada.
- Las volatilidades de los ejemplos son **valores ilustrativos**, no cotizaciones de mercado. Para operar, consulta precios reales con tu contraparte.

---

## Cómo está organizado el código

Para quien quiera leerlo o reutilizarlo. Python 3.11 o superior, interfaz en [Streamlit](https://streamlit.io),
gráficos en Plotly. El cálculo está separado de la interfaz: toda la matemática vive en
funciones puras, testeadas, que no saben nada de pantallas.

```
derivados-101/
├── app.py                    # Entrada: navegación (st.navigation) con títulos e íconos
├── app_pages/                # Inicio, simuladores, más preguntas y quiz
├── src/derivados101/         # Núcleo de cálculo, sin interfaz
│   ├── curso/                # Las 9 preguntas: textos y demos de cada pantalla (puro)
│   ├── curso_ui.py           # Dibuja las pantallas, las demos y sus gráficos
│   ├── forward.py            # Precio forward, sintético, liquidación, valor de mercado
│   ├── options.py            # Payoff, prima (Garman-Kohlhagen), valor intrínseco y temporal
│   ├── strategies.py         # Estrategias predefinidas, P&L combinado, breakevens
│   ├── market.py             # Dólar observado, tasas de referencia, volatilidad, backtest
│   └── ui.py                 # Formatos ($ 1.234,56), paleta y disclaimer
├── tests/                    # Pruebas automáticas (pytest)
├── data/                     # CSV del dólar observado y de tasas de referencia
├── scripts/                  # run.sh / run.bat y scripts de actualización de datos
├── pyproject.toml            # Metadatos y configuración de pytest y ruff
└── CONTRACT.md               # Especificación: firmas de funciones y convenciones
```

Convenciones: precios en **CLP por USD**, plazos en **años**, tasas como decimales
(`0.0511` = 5,11 %), capitalización compuesta anual. Ejemplo de referencia:
`890 × 1,0511 / 1,0407 = 898,89`.

Para desarrollar:

```bash
pip install -r requirements-dev.txt
pytest -q        # pyproject.toml ya agrega src/ al path
ruff check .     # reglas y versión (0.17.*) fijadas en pyproject.toml / requirements-dev.txt
```

---

## Aviso

**Material educativo. No es asesoría financiera ni contable.** Los modelos están
simplificados a propósito (por ejemplo, no incluyen costos de transacción, spreads
bancarios, riesgo de crédito ni el detalle completo de la norma contable). Antes de
contratar un derivado, consulta con tu banco, tu asesor y tu auditor.

## Licencia

[MIT](LICENSE) © 2026 Sergio Domínguez. Puedes usar, copiar y adaptar este material
citando la fuente.
