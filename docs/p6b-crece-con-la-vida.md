# P6b · ¿Crecen las respuestas inventadas con la vida del agente?

**Resultado.** Medí 5 políticas sobre monthly/academic_researcher entera (619 sesiones) y 3 sobre monthly/startup_founder entera (606 sesiones), por tramo de 210 sesiones y por (dominio, probe).

- **El orden de las políticas no cambia entre tramos** en ninguna de las dos personas, con el conteo oficial ni sin las preguntas marcadas.
- **`invented` no crece con la vida del agente.** Sigue a la semana del mes en la que cae un gasto "last night", que es el defecto de fechas de Memora ya marcado por la decisión (c), `relative_date`:
  - En academic_researcher es la última semana: 22 de las 42 `invented` de every-5 son preguntas marcadas, todas en s421-619.
  - En startup_founder es la primera: s1-210 es el tramo con más `invented`, 4,5 % contra 0,3–0,5 % después.
  - Sin las marcadas, every-5 da 0,3 % → 2,2 % → 0,7 % en academic_researcher y 0,6 % → 0,0 % → 0,2 % en startup_founder.
- **Lo que sí cae con el tiempo,** solo en academic_researcher, es la precisión de las políticas que sueñan seguido, por errores `stale`/`missing`. Sin marcadas, every-1 pasa de 98,5 % a 95,4 % y a 92,2 %, y la ventaja de every-1 sobre every-5 se reduce de 8,1 a 4,1 puntos.
- **Las notas no se degradan:** el 89–96 % de los hechos vivos está bien en todos los tramos, y las líneas falsas no se acumulan.
- **Para P7:** s1-210 alcanza para ordenar las políticas, no para el valor absoluto.

| Rol | Ruta |
| --- | --- |
| Script (CLI, todo desde el caché salvo `estimate`, que no llama a nada) | `diagnosis/growth.py` |
| Test | `tests/test_growth.py` (1: la tasa con la mezcla del primer tramo separa la mezcla de la tasa) |
| Salidas | `results/p6b/*.txt` (ignorado por git, se regenera con los comandos de §4) |
| Caché | `results/raw/p5/r0/` de este worktree (el de P5, más lo que pagó P6b) |

## 1. Problema

En P5, every-5 sobre monthly/academic_researcher dio 2 `invented` en s1-210 (0,3 %) y 42 sobre la persona entera. La precisión bajó de 89,2 % a 87,2 %. Si eso crece con la vida del agente, P7 sobre s1-210 sería optimista.

Ejemplo real, every-5, academic_researcher, s595:

> What is the total of the user's food expenses dated from 2025-06-22 to 2025-06-27, in dollars?
> respuesta 260.82 → `invented` (esperado 291.2)

El mismo total de la misma semana se vuelve a preguntar en s602, s609 y s616, y las cuatro respuestas quedan cortas por exactamente $30,38. En las notas está `- 2025-06-21 dinner: $30.38`. Memora lo fecha el 22: el usuario dijo "last night" en una sesión del 22. La pregunta está marcada `relative_date` (decisión (c) de P5).

Este ejemplo junta tres cosas que hay que separar antes de hablar de "crecer":

- la mezcla del examen;
- la tasa real;
- los errores que se repiten de un examen al siguiente.

## 2. Hipótesis consideradas

| # | Hipótesis | Cómo se prueba |
| --- | --- | --- |
| H1 | Crece porque cambia la mezcla del examen (más totales, semanas más largas, más hechos vivos), no la tasa | Tasa por (dominio, probe) y por tramo; tasa recalculada con la mezcla del primer tramo (`standardized`) |
| H2 | Las notas acumulan líneas falsas, viejas o duplicadas | `compare_notes` (P4b) sobre cada sueño, promedio por tramo |
| H3 | Un total largo (más gastos en la semana, más líneas de gastos en las notas) se suma mal | Totales por semana: ítems, líneas de gastos en las notas, si las notas tenían todos los gastos, `invented` |
| H4 | Las `invented` se concentran en las semanas con un gasto "last night" (`relative_date`) | Conteo con y sin las preguntas marcadas, marcadas por semana |
| H5 | Los errores no son independientes: el examen vuelve a preguntar el mismo hecho y el mismo total semanal | Hechos distintos detrás de los errores; faltantes distintos de los totales `invented` |
| H6 | Las políticas que sueñan seguido empeoran más tarde por errores que no son `invented` | Error por tramo separado en "la nota no tiene el hecho" y "la nota lo tiene bien y el examen igual falla" |
| H7 | El orden de las políticas cambia entre tramos | Ranking por tramo, oficial y sin marcadas |

## 3. Análisis y conclusión

### 3.1 Un monthly es un solo mes

Las 619 sesiones de academic_researcher son junio de 2025, unas 20 por día. Cada tramo de 210 sesiones cubre un poco más de una semana de calendario. El total semanal de gastos se pregunta unas 20 veces seguidas por semana, con un ítem más cada vez (`exam-academic.txt`, tabla por semana):

| semana desde | exámenes | academic_researcher: totales marcados | startup_founder: totales marcados |
| --- | --- | --: | --: |
| 2025-06-01 | s7–s140 | 0 de 20 | 19 de 20 |
| 2025-06-08 | s147–s301 | 0 de 23 | 0 de 22 |
| 2025-06-15 | s308–s462 | 0 de 23 | 0 de 22 |
| 2025-06-22 | s476–s616 | **21 de 21** | 0 de 21 |

### 3.2 `invented` sigue a la semana marcada, no al tiempo (H4 confirmada, H1 descartada)

academic_researcher, persona entera (`exam-academic.txt`):

| política | tramo | correcto oficial | `invented` oficial | marcadas | correcto sin marcadas | `invented` sin marcadas | errores sin marcadas (hechos distintos) |
| --- | --- | --: | --: | --: | --: | --: | --: |
| every-1 | s1-210 | 97,1 % | 0 (0,0 %) | 8 | 98,5 % | 0 (0,0 %) | 9 (8) |
| every-1 | s211-420 | 94,7 % | 11 (1,7 %) | 6 | 95,4 % | 11 (1,7 %) | 29 (11) |
| every-1 | s421-619 | 87,4 % | 25 (4,3 %) | 31 | 92,2 % | 3 (0,5 %) | 43 (19) |
| phrases-any | s1-210 | 96,1 % | 0 (0,0 %) | 8 | 97,4 % | 0 (0,0 %) | 15 (12) |
| phrases-any | s211-420 | 92,8 % | 11 (1,7 %) | 6 | 93,5 % | 11 (1,7 %) | 41 (16) |
| phrases-any | s421-619 | 86,9 % | 26 (4,5 %) | 31 | 91,6 % | 5 (0,9 %) | 46 (22) |
| every-5 | s1-210 | 89,2 % | 2 (0,3 %) | 8 | 90,4 % | 2 (0,3 %) | 56 (39) |
| every-5 | s211-420 | 88,7 % | 14 (2,2 %) | 6 | 89,2 % | 14 (2,2 %) | 68 (42) |
| every-5 | s421-619 | 83,4 % | 26 (4,5 %) | 31 | 88,1 % | 4 (0,7 %) | 65 (38) |
| every-20 | s1-210 | 76,1 % | 5 (0,8 %) | 8 | 77,1 % | 5 (0,9 %) | 134 (77) |
| every-20 | s211-420 | 73,0 % | 13 (2,0 %) | 6 | 73,2 % | 13 (2,1 %) | 169 (94) |
| every-20 | s421-619 | 72,4 % | 24 (4,1 %) | 31 | 76,1 % | 3 (0,5 %) | 131 (74) |
| never | s1-210 | 23,9 % | 25 (4,2 %) | 8 | 24,3 % | 25 (4,3 %) | 443 (113) |
| never | s211-420 | 24,0 % | 23 (3,6 %) | 6 | 24,2 % | 23 (3,6 %) | 477 (157) |
| never | s421-619 | 24,5 % | 17 (2,9 %) | 31 | 25,9 % | 10 (1,8 %) | 406 (151) |

startup_founder, persona entera (`exam-startup.txt`), y every-1 en s1-210 (`exam-startup-210.txt`, caché de P5):

| política | tramo | correcto oficial | `invented` oficial | marcadas | correcto sin marcadas | `invented` sin marcadas |
| --- | --- | --: | --: | --: | --: | --: |
| every-1 | s1-210 | 89,7 % | 25 (4,3 %) | 40 | 95,6 % | 3 (0,6 %) |
| every-5 | s1-210 | 84,7 % | 26 (4,5 %) | 40 | 90,6 % | 3 (0,6 %) |
| every-5 | s211-420 | 85,4 % | 2 (0,3 %) | 14 | 86,9 % | 0 (0,0 %) |
| every-5 | s421-606 | 89,5 % | 3 (0,5 %) | 10 | 90,7 % | 1 (0,2 %) |
| every-20 | s1-210 | 70,7 % | 8 (1,4 %) | 40 | 73,9 % | 4 (0,7 %) |
| every-20 | s211-420 | 75,7 % | 6 (0,9 %) | 14 | 77,0 % | 3 (0,5 %) |
| every-20 | s421-606 | 77,5 % | 1 (0,2 %) | 10 | 78,5 % | 0 (0,0 %) |
| never | s1-210 | 24,8 % | 12 (2,1 %) | 40 | 26,6 % | 8 (1,5 %) |
| never | s211-420 | 23,9 % | 28 (4,1 %) | 14 | 24,4 % | 28 (4,2 %) |
| never | s421-606 | 23,4 % | 18 (3,2 %) | 10 | 23,8 % | 18 (3,3 %) |

- **Concentración por semana:**
  - academic_researcher: el pico de `invented` es la última semana. De las 26 `invented` de every-5 en s421-619, 22 son marcadas.
  - startup_founder: el pico es la primera. every-1 y every-5 sacan 18 de 20 totales `invented` en la semana del 2025-06-01, y 19 de esos 20 totales están marcados.
  - Sin las marcadas, `invented` no crece en ninguna de las dos personas.
- **Mezcla contra tasa (H1).** Con la mezcla de (dominio, probe) del primer tramo, el `invented` oficial de every-5 en academic_researcher queda en 0,3 % → 2,3 % → 4,7 %: casi lo mismo que el observado (0,3 → 2,2 → 4,5 %). Con las tasas del primer tramo y la mezcla de cada tramo daría 0,3 % → 0,3 % → 0,3 %. La suba oficial es de tasa, no de mezcla, y esa tasa es la del total semanal marcado. Lo mismo pasa en las otras cuatro políticas que sueñan (`exam-academic.txt`, tabla "Invented and all errors per stretch").
- **La semana marcada pega igual a todas las cadenas.** every-1, every-5, every-20 y phrases-any son cadenas de sueños distintas, y las cuatro sacan 21 de 21 totales `invented` en la semana del 2025-06-22. Lo que falla es la fecha de la clave, no el sueño. En las notas el gasto está el 21, el día que dijo el usuario.

### 3.3 Las notas no acumulan errores (H2 descartada)

Promedio por sueño de cada tramo (`notes-academic.txt`, `notes-startup.txt`). La columna "líneas sin hecho" suma `unmatched_supported` y `unmatched_unsupported`; la de apoyadas es casi todo.

| persona | política | tramo | caracteres | líneas | hechos vivos | correctos | faltantes | líneas stale | líneas invented | duplicadas | líneas sin hecho |
| --- | --- | --- | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| academic | every-1 | s1-210 | 7.098 | 103 | 98 | 91,4 % | 8,6 % | 0,8 | 0,0 | 0,0 | 8,3 |
| academic | every-1 | s211-420 | 17.812 | 254 | 236 | 93,0 % | 7,0 % | 1,0 | 0,0 | 0,3 | 22,6 |
| academic | every-1 | s421-619 | 21.300 | 335 | 307 | 92,3 % | 7,7 % | 1,3 | 1,0 | 1,0 | 36,3 |
| academic | every-5 | s1-210 | 6.923 | 106 | 100 | 91,1 % | 8,9 % | 0,0 | 0,0 | 0,0 | 8,5 |
| academic | every-5 | s421-619 | 20.313 | 327 | 307 | 93,3 % | 6,7 % | 0,9 | 1,0 | 1,0 | 25,6 |
| academic | every-20 | s421-619 | 19.376 | 311 | 307 | 88,7 % | 10,9 % | 3,9 | 1,0 | 0,0 | 20,9 |
| academic | phrases-any | s421-619 | 20.828 | 325 | 307 | 91,7 % | 8,3 % | 0,0 | 1,4 | 1,0 | 40,8 |
| startup | every-5 | s1-210 | 7.115 | 102 | 97 | 95,8 % | 3,4 % | 0,8 | 0,0 | 0,6 | 7,2 |
| startup | every-5 | s421-606 | 20.639 | 322 | 311 | 94,1 % | 5,3 % | 4,9 | 0,0 | 1,7 | 20,2 |

- **Las notas se triplican** (7 mil → 20 mil caracteres, ~100 → ~330 líneas), al ritmo de los hechos vivos (~100 → ~307). Los gastos no expiran: pasan de 16 a 73 hechos vivos por sueño.
- **Exactitud estable.** La parte de los hechos vivos que la nota tiene bien no baja: 89–96 % en todos los tramos. Las líneas stale, invented y duplicadas llegan como mucho a 5 por sueño sobre ~320 (≤ 1,5 %).
- **Excepción, las líneas sin hecho en la verdad** de every-1 y phrases-any: pasan de 8 a 36–41, del 8 % al 11–13 % de las líneas. Casi todas son `unmatched_supported`: al menos el 75 % de sus raíces aparece en las transcripciones (0,0–0,4 por sueño no lo cumplen). No las clasifiqué más, y no se ven como `invented` en el examen (§3.2, sin marcadas).
- **Preferencias en las notas de every-1:** faltan el 0 % → 6 % → 12 %. Vuelve en §3.5.

### 3.4 Los totales largos no se suman peor (H3 descartada como mecanismo general)

- **startup_founder, semana del 2025-06-22,** con every-5: 15 gastos por total y 73 líneas de gastos en las notas, y 0 de 21 totales `invented` (`exam-startup.txt`).
- **academic_researcher, semana del 2025-06-08:** every-1 saca 10 de 23 totales `invented`.
  - En los 10, a las notas les falta el mismo gasto: 1 solo faltante distinto. Es una omisión del sueño que se repite 10 exámenes, no un error de suma.
  - every-5 y phrases-any caen en la misma semana; every-5 con 4 faltantes distintos.
- **Las notas "completas" de la semana marcada no lo son** (§1). `compare_notes` empareja `2025-06-21 dinner` con `2025-06-22 dinner` (similitud 0,75), así que la columna "complete notes" sale engañosa en esa semana. Está aclarado en el docstring de `aggregate_table`.

### 3.5 Lo que sí crece: errores de every-1 y phrases-any en academic_researcher (H6, confirmada a medias)

Sin marcadas, los errores de every-1 pasan de 1,5 % a 4,6 % y a 7,8 %. Con la mezcla del primer tramo dan 1,5 → 4,8 → 7,6 %, así que es tasa, no mezcla. Casi todo es `stale` o `missing`.

Separé dos causas para las preguntas sobre un hecho vivo (`exam-academic.txt`, tabla "Questions about a fact that holds"):

| política | tramo | hecho bien en la nota | error con la nota bien | hecho ausente de la nota |
| --- | --- | --: | --: | --: |
| every-1 | s1-210 | 381 | 3 (0,8 %) | 5 |
| every-1 | s211-420 | 407 | 5 (1,2 %) | 13 |
| every-1 | s421-619 | 343 | 11 (3,2 %) | 31 |
| phrases-any | s1-210 | 375 | 4 (1,1 %) | 11 |
| phrases-any | s421-619 | 341 | 12 (3,5 %) | 33 |
| every-5 | s1-210 | 350 | 5 (1,4 %) | 32 |
| every-5 | s421-619 | 331 | 7 (2,1 %) | 40 |
| every-20 | s1-210 | 299 | 1 (0,3 %) | 78 |
| every-20 | s421-619 | 287 | 9 (3,1 %) | 76 |

- **Crecen las dos causas,** con números chicos.
  - Las notas pierden más hechos preguntados: 5 → 31 en every-1. Las preferencias son las que más faltan: 0 % → 6 % → 12 % en la tabla por dominio de `notes-academic.txt`. Por ejemplo, el dislike de 'Marlon Brando' en s427 y el de 'romantic comedy' en s434 y s455 (`diagnosis.invented ... --outcomes missing`).
  - Leer notas de 21 mil caracteres falla más con la nota bien: 0,8 % → 3,2 %.
- **Hechos distintos.** Los 43 errores de every-1 en s421-619 caen sobre 19 hechos distintos: el examen vuelve a preguntar una preferencia estable en varios exámenes (H5).
- **startup_founder no muestra esto.** El error con la nota bien en every-5 va de 1,2 % a 1,5 % y a 0,6 %, con notas del mismo tamaño. Con dos personas no se puede atribuir a la longitud de las notas.
- **Corresponde a P6a.** Por qué la nota pierde preferencias y por qué el examen falla con la nota bien son causas.

### 3.6 El orden no cambia; las distancias sí (H7 descartada)

Sin marcadas (`exam-academic.txt`, `exam-startup.txt`):

| tramo | academic_researcher | startup_founder |
| --- | --- | --- |
| s1-210 | every-1 98,5 > phrases-any 97,4 > every-5 90,4 > every-20 77,1 > never 24,3 | every-5 90,6 > every-20 73,9 > never 26,6 |
| s211-420 | every-1 95,4 > phrases-any 93,5 > every-5 89,2 > every-20 73,2 > never 24,2 | every-5 86,9 > every-20 77,0 > never 24,4 |
| s421-end | every-1 92,2 > phrases-any 91,6 > every-5 88,1 > every-20 76,1 > never 25,9 | every-5 90,7 > every-20 78,5 > never 23,8 |

El orden oficial es el mismo en todos los tramos. Las distancias cambian en academic_researcher:

| distancia (puntos, sin marcadas) | s1-210 | s211-420 | s421-619 |
| --- | --: | --: | --: |
| every-1 − every-5 | 8,1 | 6,2 | 4,1 |
| every-1 − phrases-any | 1,1 | 1,9 | 0,6 |
| every-5 − every-20 | 13,3 | 16,0 | 12,0 |

Sobre la persona entera, el conteo oficial da:

- every-1 93,1 %, phrases-any 92,0 %, every-5 87,2 %, every-20 73,8 %, never 24,2 %;
- contra 97,1 / 96,1 / 89,2 / 76,1 / 23,9 % en s1-210.

### 3.7 Conclusión para P7

- **s1-210 sirve para ordenar las políticas.** El orden se mantuvo en los 3 tramos de las 2 personas, con los dos conteos.
- **No sirve para el valor absoluto ni para el tamaño de las ventajas,** por dos razones:
  1. **El conteo oficial depende de en qué semana cae un gasto "last night".** Eso es de la persona, no del tiempo, y puede hacer s1-210 optimista (academic_researcher) o pesimista (startup_founder). P7 debería reportar siempre "sin marcadas" al lado del oficial; las marcadas de `relative_date` explican la mayor parte de las `invented`.
  2. **En academic_researcher la ventaja de soñar seguido se achica a la mitad** hacia el final del mes (every-1 sobre every-5: 8,1 → 4,1 puntos). No hay datos de every-1 tardío en una segunda persona para saber si es general.
- **Un tramo tardío cuesta la persona entera.** La cadena de sueños depende de todo lo anterior. Medir s421-end obliga a pagar s1-420, así que "tramo tardío" y "persona entera" cuestan lo mismo.
- **Recomendación:** P7 en s1-210, reportando sin marcadas, y declarando que las distancias entre políticas que sueñan seguido pueden ser hasta 2 veces más chicas en el resto del mes. Si sobra presupuesto, la medición más útil es every-1 y every-5 enteras en 1–2 personas más: verifica la compresión, que es lo único que s1-210 no puede ver.

## 4. Prueba

Todo con `claude-haiku-5-5`, motor de P5 sin cambios. Los comandos de lectura usan `PYTHONHASHSEED=0` (ver §6).

### 4.1 Estimación antes de correr

```
$ uv run python -m diagnosis.growth estimate monthly/academic_researcher monthly/startup_founder --policies never every-1 every-5 every-20 triggered-phrases-any
| period/persona | policy | dreams after cache | dream $ | exams after cache | exam $ | total $ |
| monthly/academic_researcher | never | 0 | 0.0000 | 58 | 0.0263 | 0.0263 |
| monthly/academic_researcher | every-1 | 409 | 0.4532 | 58 | 0.1000 | 0.5532 |
| monthly/academic_researcher | every-5 | 81 | 0.1328 | 58 | 0.0998 | 0.2326 |
| monthly/academic_researcher | every-20 | 20 | 0.0725 | 58 | 0.0994 | 0.1719 |
| monthly/academic_researcher | triggered-phrases-any | 282 | 0.3290 | 58 | 0.1000 | 0.4290 |
| monthly/startup_founder | never | 0 | 0.0000 | 56 | 0.0254 | 0.0254 |
| monthly/startup_founder | every-1 | 396 | 0.4295 | 56 | 0.0942 | 0.5237 |
| monthly/startup_founder | every-5 | 79 | 0.1277 | 56 | 0.0941 | 0.2219 |
| monthly/startup_founder | every-20 | 20 | 0.0720 | 56 | 0.0933 | 0.1653 |
| monthly/startup_founder | triggered-phrases-any | 294 | 0.3322 | 56 | 0.0942 | 0.4264 |
```

Las 10 corridas sumaban $2,78 contra un tope de $1,60. Decidí:

- **academic_researcher entera con las 5 políticas,** porque every-5 entera ya estaba pagada. Es la única persona donde se puede ver si el orden cambia entre las políticas cercanas (every-1, phrases-any, every-5).
- **startup_founder entera con never, every-5 y every-20,** las más baratas, para ver si la suba de `invented` se repite en otra persona.

startup_founder every-1 y phrases-any ($0,95) no entraban. every-20 de startup_founder la corrí al final, cuando el gasto real confirmó que entraba.

### 4.2 Corridas pagadas (cada política una sola vez)

```
$ uv run python -m policies.run monthly/academic_researcher --policies never every-20 --budget-name p6b --limit 1.60
p6b spent: $0.0000 before, $0.1686 after
$ uv run python -m policies.run monthly/startup_founder --policies never every-5 --budget-name p6b --limit 1.60
p6b spent: $0.1686 before, $0.3961 after
$ uv run python -m policies.run monthly/academic_researcher --policies every-1 --budget-name p6b --limit 1.60
p6b spent: $0.3961 before, $0.9108 after
$ uv run python -m policies.run monthly/academic_researcher --policies triggered-phrases-any --budget-name p6b --limit 1.60
p6b spent: $0.9108 before, $1.3008 after
$ uv run python -m policies.run monthly/startup_founder --policies every-20 --budget-name p6b --limit 1.60
p6b spent: $1.3008 before, $1.4447 after
```

| Corrida | Proyectado | Pagado |
| --- | --: | --: |
| academic_researcher never + every-20 | 0,1982 | 0,1686 |
| startup_founder never + every-5 | 0,2473 | 0,2275 |
| academic_researcher every-1 | 0,5532 | 0,5147 |
| academic_researcher triggered-phrases-any | 0,4290 | 0,3900 |
| startup_founder every-20 | 0,1653 | 0,1439 |
| **Total** | **1,5930** | **1,4447** (tope 1,60; libro `results/spend/p6b.jsonl`) |

La proyección de P5 sobrestimó el costo entre un 7 % y un 15 % en cada corrida, del lado seguro.

### 4.3 Todo vuelve a salir del caché con tope $0

```
$ uv run python -m policies.run monthly/academic_researcher --policies never every-1 every-5 every-20 triggered-phrases-any --check-cache
| never | monthly/academic_researcher | 0 | 619 | 0 | 0.0000 | 0.0000 | 0.0340 | 88 | 437/1809 (24.2%) | ... | 437 | 329 | 977 | 65 | 1 |
| every-1 | monthly/academic_researcher | 0 | 619 | 619 | 0.5557 | 0.0000 | 0.1096 | 88 | 1685/1809 (93.1%) | ... | 1685 | 50 | 38 | 36 | 0 |
| every-5 | monthly/academic_researcher | 0 | 619 | 123 | 0.1777 | 0.0000 | 0.1076 | 88 | 1577/1809 (87.2%) | ... | 1577 | 123 | 67 | 42 | 0 |
| every-20 | monthly/academic_researcher | 0 | 619 | 30 | 0.0989 | 0.0000 | 0.1045 | 88 | 1335/1809 (73.8%) | ... | 1335 | 291 | 141 | 42 | 0 |
| triggered-phrases-any | monthly/academic_researcher | 0 | 619 | 441 | 0.4078 | 0.0000 | 0.1065 | 88 | 1664/1809 (92.0%) | ... | 1664 | 61 | 47 | 37 | 0 |
$ uv run python -m policies.run monthly/startup_founder --policies never every-5 every-20 --check-cache
| never | monthly/startup_founder | 0 | 606 | 0 | ... | 86 | 437/1819 (24.0%) | ... | 437 | 394 | 930 | 58 | 0 |
| every-5 | monthly/startup_founder | 0 | 606 | 121 | ... | 86 | 1572/1819 (86.4%) | ... | 1572 | 121 | 95 | 31 | 0 |
| every-20 | monthly/startup_founder | 0 | 606 | 30 | ... | 86 | 1358/1819 (74.7%) | ... | 1358 | 302 | 144 | 15 | 0 |
```

### 4.4 Las tablas de este informe

```bash
PYTHONHASHSEED=0 uv run python -m diagnosis.growth exam monthly/academic_researcher --policies never every-1 every-5 every-20 triggered-phrases-any
PYTHONHASHSEED=0 uv run python -m diagnosis.growth exam monthly/startup_founder --policies never every-5 every-20
PYTHONHASHSEED=0 uv run python -m diagnosis.growth exam monthly/startup_founder:210 --policies never every-1 every-5 every-20
PYTHONHASHSEED=0 uv run python -m diagnosis.growth notes monthly/academic_researcher --policies every-1 every-5 every-20 triggered-phrases-any
PYTHONHASHSEED=0 uv run python -m diagnosis.growth notes monthly/startup_founder --policies every-5 every-20
uv run pytest -q    # 47 passed
```

`exam` imprime, por persona:

- por tramo: correcto, stale, missing, invented, marcadas y lo mismo sin marcadas, con los hechos distintos detrás de los errores;
- el ranking por tramo, la tasa con la mezcla del primer tramo y las tablas por (dominio, probe), con el conteo oficial y sin marcadas;
- "nota mal contra lectura mal" y los totales por semana de calendario.

`notes` corre `compare_notes` sobre cada sueño: 1.213 en academic_researcher, 151 en startup_founder.

## 5. Hipótesis descartadas y por qué

| Hipótesis | Por qué no | Dónde |
| --- | --- | --- |
| H1, crece por la mezcla | Con la mezcla del primer tramo, la suba es igual a la observada; con las tasas del primer tramo, sería nula | §3.2 |
| H2, las notas acumulan líneas falsas | La parte de hechos vivos bien queda en 89–96 %; stale, invented y duplicadas ≤ 1,5 % de las líneas | §3.3 |
| H3, los totales largos se suman mal | startup_founder suma bien totales de 15 gastos con 73 líneas de gastos en la nota; los totales malos de academic_researcher son una omisión repetida o la semana marcada | §3.4 |
| H7, el orden cambia entre tramos | Mismo orden en los 3 tramos de las 2 personas, con los dos conteos | §3.6 |
| `invented` crece con la vida del agente | Sin marcadas no crece en ninguna persona; con marcadas, en startup_founder baja | §3.2 |

## 6. Limitaciones

- **Dos personas, una repetición.** every-1 y phrases-any tardíos solo están en academic_researcher, así que la compresión de §3.5 y §3.6 podría ser de esa persona. Las diferencias entre vecinas, de 1–4 puntos, son del tamaño del ruido de P5 (1,1–2,8).
- **Muestra efectiva chica.** Los errores no son independientes:
  - el mismo total semanal se pregunta ~20 veces;
  - el mismo hecho estable, varias veces;
  - los 29 errores de every-1 en s211-420 son 11 hechos distintos.
  Por eso no doy intervalos de confianza: contar exámenes como independientes los achicaría de más.
- **`compare_notes` (P4b) no es determinista entre procesos.** `match_documents` elige con `max(set(...), key=score)` (`dreaming/quality.py:325`), y con empates gana el orden de hash.
  - Efecto medido sobre every-1 s421-619 con 3 semillas: 92,1–92,3 % de hechos bien, 1,0–1,8 duplicadas por sueño. El error con la nota bien en s421-619 pasó de 13 a 11 al fijar la semilla.
  - No lo cambié (es de P4b): fijé `PYTHONHASHSEED=0`. Las tablas de examen que no usan `compare_notes` no dependen de la semilla.
- **"complete notes" se engaña en las semanas marcadas** por el emparejamiento difuso de fechas (§3.4).
- **La causa de cada error es de P6a.** Por qué every-1 pierde preferencias, y por qué el examen falla con la nota bien en academic_researcher y no en startup_founder. Acá solo están las tasas.

### Decisión abierta (cambio de criterio, no aplicado)

El conteo oficial pesa cada examen igual. Un total semanal con un gasto mal fechado cuenta ~20 veces. En academic_researcher s421-619, las preguntas marcadas son el 81–88 % de las `invented` de cada política que sueña: every-1 22 de 25, phrases-any 21 de 26, every-5 22 de 26, every-20 21 de 24 (§3.2).

- **(a) Dejarlo así** y reportar siempre "sin marcadas" al lado. Es lo que ya hace `score`.
- **(b) Contar también por hecho distinto:** un total semanal o un hecho estable mal respondido cuenta una vez por racha. Daría un número menos ruidoso para comparar políticas, pero cambia el criterio de P2.

Recomiendo (a) para P7, que no cuesta nada, y decidir (b) solo si las distancias entre políticas resultan del tamaño del ruido.
