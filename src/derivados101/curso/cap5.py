"""¿Qué es un collar de costo cero?

Cifras de ejemplo (fijas): spot 890, tasas 5,11% CLP / 4,07% USD, plazo 1 año, volatilidad 12%,
nocional US$500.000. Calculadas con ``strategies.PRESETS["collar_importer"]`` (strike de la put
resuelto con ``zero_cost_strike``): call comprada 907,80 y put vendida 890,85, prima neta 0.
Forward 898,89 (``forward.forward_rate``). Call 900 con prima 40,42 (``garman_kohlhagen``).
"""

from .model import Chapter, Concept, Demo, Example, Summary

CHAPTER = Chapter(
    number=8,
    slug="collar-costo-cero",
    title="¿Qué es un collar de costo cero?",
    menu="Collar",
    icon=":material/stacks:",
    goal="Cómo combinar opciones para pagar menos prima, y qué entregas a cambio.",
    minutes=4,
    screens=[
        Concept(
            title="Vender una opción paga parte de la que compras",
            body=(
                "Una opción comprada protege, pero cuesta prima. Si al mismo tiempo vendes otra, "
                "cobras una prima que compensa la primera.\n\n"
                "El costo cambia de forma: pagas menos hoy, pero renuncias a parte del lado bueno. "
                "La estrategia más usada por empresas es el collar de costo cero."
            ),
            terms=[
                ("Collar", "Compras una opción y vendes otra para quedar en una banda de tipo de cambio."),
                ("Costo cero", "La prima cobrada iguala a la pagada: prima neta 0."),
            ],
        ),
        Example(
            title="Con un collar el importador queda entre 890,85 y 907,80",
            setup=(
                "El importador de telas pagará US\\$500.000 en 1 año. Compra una call con strike "
                "907,80 y vende una put con strike 890,85. Las dos primas valen 37,02 por USD y se "
                "anulan. Ejemplo: spot 890, tasas 5,11% CLP y 4,07% USD, volatilidad 12%."
            ),
            steps=[
                "Prima neta hoy: 37,02 − 37,02 = 0.",
                "Si el dólar termina en 950, ejerce la call: paga 907,80 por dólar.",
                "Si termina en 900, ninguna opción paga: compra a 900 en el mercado.",
                "Si termina en 850, el banco ejerce la put: el importador paga 890,85 y pierde la baja.",
            ],
            takeaway="El collar fija un techo sin pagar prima, a cambio de un piso que limita las bajas.",
            lab="app_pages/4_Estrategias.py",
        ),
        Demo(
            title="Mueve el techo y mira dónde queda el piso",
            prompt=(
                "Parte con la call a 907,80: la put de costo cero queda en 890,85. Sube el strike de "
                "la call: la protección es peor, la call es más barata y la put baja. La banda se "
                "ensancha y vuelves a aprovechar más las bajas."
            ),
            demo="collar",
            params={"spot": 890.0, "vol": 0.12, "years": 1.0, "r_dom": 0.0511, "r_for": 0.0407,
                    "call_strike": 907.8},
            takeaway="Un techo más alto te deja un piso más bajo: siempre a prima neta cero.",
        ),
        Example(
            title="Cada alternativa gana en un escenario distinto",
            setup=(
                "Costo en CLP de pagar US\\$500.000 en 1 año según cómo se cubra. Forward 898,89; "
                "call 900 con prima 40,42; collar 890,85–907,80. Cifras de ejemplo."
            ),
            steps=[
                "Dólar en 850: sin cubrir \\$425.000.000; call \\$445.208.703; collar "
                "\\$445.425.182; forward \\$449.447.007.",
                "Dólar en 950: forward \\$449.447.007; collar \\$453.900.000; call "
                "\\$470.208.703; sin cubrir \\$475.000.000.",
                "El forward da certeza total. La call deja la baja abierta, pero cuesta prima. "
                "El collar queda en medio sin pagar prima.",
            ],
            takeaway="Ninguna alternativa gana siempre: eliges cuánta certeza quieres y cuánto pagas por ella.",
            lab="app_pages/4_Estrategias.py",
        ),
        Summary(
            points=[
                "Vender una opción abarata la que compras, a cambio de renunciar a parte del lado bueno.",
                "El collar de costo cero fija una banda: techo para el alza y piso para la baja.",
                "Forward, opción y collar ganan en escenarios distintos; ninguno gana siempre.",
            ],
            next_hint="Siguiente: cuánto y cuándo cubrirse.",
        ),
    ],
)
