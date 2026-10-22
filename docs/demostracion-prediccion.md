# Demostración del análisis

La cuenta de prueba Renzo (`renzo@example.com`) tiene 24 sesiones y 44 registros sintéticos distribuidos en ocho semanas, preparados el 21 de octubre de 2026. Sirven para demostrar el recorrido del sistema; no validan la precisión del modelo con deportistas reales.

| Ejercicio | Repeticiones | Caso |
| --- | --- | --- |
| Press de banca | 8 | Ocho semanas con subidas y bajadas; permite una estimación. Meta: 76 kg. |
| Press de banca | 10 | Dos semanas: conserva el historial sin curva futura. |
| Sentadilla | 6 | Ocho semanas comparables. Meta: 96 kg. |
| Curl de bíceps | 12 | Dos semanas: informa que faltan datos. |
| Press militar | 8 | Tendencia no positiva: no inventa un plazo. |

En la cuenta real, elegir ejercicio y repeticiones, revisar las semanas disponibles y pulsar el botón de análisis. La disponibilidad se consulta en `GET /analisis/disponibilidad?ejercicio_id=...`; contar cuatro semanas no garantiza superar los controles del predictor. Las fechas antiguas pueden dejar de cumplir la comprobación de actualidad después de cuatro semanas.

La demo del navegador conserva un ejemplo fijo de banca a ocho repeticiones y meta de 50 kg. Sus sesiones no se envían al backend ni recalculan el ejemplo.
