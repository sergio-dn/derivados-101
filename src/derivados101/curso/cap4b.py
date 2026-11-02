"""¿De qué depende el precio de una opción?

Cifras de ejemplo (fijas): spot 890, tasas 5,11% CLP / 4,07% USD, plazo 1 año, volatilidad 12%.
Primas calculadas con ``options.garman_kohlhagen``: call 850 = 67,30 (intrínseco 40, temporal 27,30);
call 900 = 40,42; call 900 con vol 20% = 67,64; call 900 a 6 meses = 26,98; call 950 = 22,15.
"""

from .model import Chapter, Concept, Demo, Summary

CHAPTER = Chapter(
    number=7,
    slug="precio-de-una-opcion",
    title="¿De qué depende el precio de una opción?",
    menu="Precio opción",
    icon=":material/price_change:",
    goal="Por qué la misma opción puede costar el doble según el plazo y la volatilidad.",
    minutes=4,
    screens=[
        Concept(
            title="La prima suma valor intrínseco y valor temporal",
            body=(
                "El valor intrínseco es lo que pagaría la opción si venciera hoy. En una call es "
                "spot − strike si es positivo; si no, cero.\n\n"
                "El valor temporal es el resto de la prima. Paga la posibilidad de que el dólar se "
                "mueva a favor antes del vencimiento. Al vencimiento llega a cero.\n\n"
                "Ejemplo con spot 890: una call con strike 850 vale 67,30 por USD. Su intrínseco es 40 "
                "y su valor temporal, 27,30."
            ),
            terms=[
                ("ITM (in the money)", "Ejercerla hoy pagaría algo."),
                ("ATM (at the money)", "Strike igual o muy cerca del spot."),
                ("OTM (out of the money)", "Ejercerla hoy no pagaría nada: solo tiene valor temporal."),
            ],
            callout=(
                "Ojo: las primas de aquí salen de un modelo (Garman-Kohlhagen) con volatilidad fija. "
                "En la realidad el banco cotiza con su propia volatilidad, que cambia según strike y "
                "plazo, y agrega su margen. Compara más de una cotización."
            ),
        ),
        Demo(
            title="Sube la volatilidad o alarga el plazo y mira la prima",
            prompt=(
                "La call 900 a 1 año con volatilidad 12% vale 40,42. Sube la volatilidad a 20%: pasa "
                "a 67,64. Acorta el plazo a 6 meses: baja a 26,98. Aleja el strike a 950: baja a 22,15."
            ),
            demo="option_price",
            params={"kind": "call", "spot": 890.0, "strike": 900.0, "vol": 0.12, "years": 1.0,
                    "r_dom": 0.0511, "r_for": 0.0407},
            takeaway="Más volatilidad y más plazo suben el valor temporal; el intrínseco no cambia.",
        ),
        Summary(
            points=[
                "La prima suma valor intrínseco (lo que paga hoy) y valor temporal (lo que podría pagar).",
                "Más volatilidad y más plazo suben la prima; un strike más lejano la baja.",
                "Las primas de aquí salen de un modelo; un banco cotiza con su volatilidad y margen.",
            ],
            next_hint="Siguiente: cómo combinar opciones para no pagar prima.",
        ),
    ],
)
