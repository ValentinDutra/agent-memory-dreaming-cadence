# P3 · Responder leyendo solo las notas

**Resultado.** Con notas perfectas, en el formato elegido y con thinking adaptativo (effort `medium`), Haiku 5.5 contesta bien el **97,7–100 %** del examen. Todo error que queda es aritmética de los totales semanales de gastos. Con notas vacías acierta el **24,8–27,5 %**. Repetir el mismo examen cambia 0–12 respuestas de cada 1.374 o 426, todas en sumas. El techo de todo el experimento queda prácticamente en 100 % fuera de los totales de gastos. Por eso, desde P4 en adelante, casi todo error se puede atribuir a la memoria.

| Medición (configuración final) | weekly/software_engineer, 23 exámenes, 426 preguntas | monthly, 3 personas, 1 de cada 4 exámenes (67), 1.374 preguntas |
| --- | --: | --: |
| Techo, sin totales precalculados (oficial) | **97,7 %** (expense 86,7 %, el resto 100 %) | **100 %** |
| Techo, con totales precalculados | 100 % | 100 % |
| Piso (notas vacías) | **27,5 %** | **24,8 %** |
| Ruido: respuestas que cambian entre 3 repeticiones | 12 / 426 (todas totales de gastos) | 0 / 1.374 |
| Ruido: rango de la precisión total | 0,7 pp (expense 4,0 pp) | 0,0 pp |
| `unparseable` | 0 | 0 |
| Cuenta indulgente − cuenta estricta | 0 | 0 |

Monthly cubre academic_researcher, software_engineer y startup_founder.

| Rol | Ruta |
| --- | --- |
| Tag | `p3` |
| Interfaz y lo que hereda P4 | `docs/p3-interfaz.md` |
| Informe de P3a (formato) | `docs/p3a-formato.md` |
| Informe de P3b (techo, piso y ruido) | `docs/p3b-techo-piso-ruido.md` |
| Cliente con tope de gasto (P3) | `answering/client.py` (`BudgetedClient`, `MODEL`, `THINKING`, `EFFORT`) |
| Notas (P3a) | `answering/notes.py` (`render_notes`) |
| Prompt y parseo (P3a, con un cambio de P3) | `answering/answer.py` (`answer_exam`, `parse_answers`, `RULES`) |
| Totales precalculados, no oficiales (P3a) | `answering/format_totals.py` |
| Medición (P3b) | `answering/bounds.py` (CLI) |
| Comparación de formatos (P3a) | `answering/format_compare.py`, `answering/format_*.py` |
| Tests (6 de P3; 31 con los de P1 y P2) | `tests/test_client.py` (2), `tests/test_answer.py` (2), `tests/test_bounds.py` (2) |

Uso para P4–P7:

```python
from answering.answer import answer_exam
from answering.client import BudgetedClient
from answering.notes import render_notes
from exam.grading import grade

client = BudgetedClient("p5", limit_dollars=2.00)   # thinking adaptive + effort medium por omisión
answers = answer_exam(notes, exam_at_350, client, run="p5/cadence-20/monthly/software_engineer")
grades = [grade(question, answer) for question, answer in zip(exam_at_350, answers)]
```

Para medir otra persona, desde la CLI:

```bash
uv run python -m answering.bounds monthly <persona> --every 4 --budget-name <nombre> --limit <dólares> --dry-run
```

## 1. Problema

P4–P7 van a atribuir cada error del examen a la memoria: una nota vieja, que falta o que es inventada. Eso vale solo si un modelo con notas perfectas contesta bien. Hay otras tres fuentes de error que no son de memoria:

- **El examen:** una pregunta ambigua.
- **El formato:** cómo se le muestran las notas y cómo se le pide la respuesta.
- **El modelo:** no sabe hacerlo, por ejemplo sumar.

Ejemplo real, weekly/software_engineer, examen de la s147, con las notas perfectas en el stub de la interfaz, sin thinking. Acertó 16 de 21:

| Pregunta | Esperado | Contestó | Causa (se supo después) |
| --- | --- | --- | --- |
| like/dislike de un gusto que está en las notas (pregunta n.º 1) | like | unknown | Formato: efecto de la primera pregunta |
| ¿Está un pendiente distractor en la lista? | no | unknown | Formato: el prompt no decía que las listas son cerradas |
| Total de gastos de la semana | 258.23 | 503 | Modelo: suma sin pensar |

Con el stub, el techo era 70,7 % en weekly y 72,8 % en monthly. Un techo así habría hundido las diferencias entre cadencias en el error de formato.

## 2. Opciones investigadas

El detalle, con las secciones citadas, está en P3a §2 y P3b §2.

| Fuente | Qué se tomó |
| --- | --- |
| Memory tool de Anthropic, https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool | Memoria como archivos de texto que el modelo edita con `str_replace` → un hecho por línea. `view` trunca archivos de más de 16.000 caracteres. |
| `MEMORY.md` de Claude Code, https://code.claude.com/docs/en/memory | Markdown con encabezados y viñetas. Límite de carga de 200 líneas / 25 KB. |
| Dreams de Managed Agents, https://platform.claude.com/docs/en/managed-agents/dreams | El dream reemplaza entradas viejas por el último valor y sigue "output conventions": el formato es una convención que P4 le da al dream. |
| Letta, memory blocks, https://docs.letta.com/guides/agents/memory-blocks | Bloques etiquetados con una descripción que dice cómo leerlos → `<notes>` y un encabezado por sección. |
| Structured outputs, https://platform.claude.com/docs/en/build-with-claude/structured-outputs | Disponible en Haiku 5.5. No hizo falta: el bloque `<answers>` da 0 `unparseable`. |
| LongMemEval, https://arxiv.org/html/2410.10813v2 §3.4 y §5.5 | El techo como "oracle retrieval". Con evidencia perfecta, la estrategia de lectura mueve el techo hasta 10 puntos, y razonar antes de responder lo sube. |
| Effort y thinking adaptativo, https://platform.claude.com/docs/en/build-with-claude/effort | El effort es una señal de comportamiento; los tokens de thinking cuentan dentro de `max_tokens`. |
| Guía de migración de Haiku 5.5, https://platform.claude.com/docs/en/models/haiku-5-5/migration-guide | Sin `temperature`, `top_p` ni `top_k`; thinking adaptativo encendido por omisión. |
| Quantifying Variance in Evaluation Benchmarks, https://arxiv.org/abs/2406.10229 | Medir la varianza del evaluador antes de comparar. |

## 3. Análisis y elección

### 3.1 Qué se eligió

| Pieza | Elección | Por qué (número) |
| --- | --- | --- |
| Notas | Markdown, una sección por dominio y un hecho por línea. Todo nombrado como lo nombra el usuario: documento por título, gasto por fecha y tipo, metas con su significado ("Weekly budget for dinner expenses: $210"). Listas cerradas vacías escritas como `- (none)`. Sin la prosa larga de los documentos. | Stub → Markdown: 69–70 % → 85–86 % sin thinking (P3a §4.1). Sin prosa: −7 % de tokens en weekly, −14–19 % en monthly. |
| Prompt | Notas en `<notes>`. Reglas: las listas son cerradas; "unknown" solo para un gusto sin opinión actual o un dato que falta; fechas ISO y dígitos; los días sin registro no suman. Respuestas dentro de `<answers>`, una por línea. | Bloque `<answers>`: la pregunta 1 pasa de 14/23 a 23/23, y 0 `unparseable` en todas las corridas. |
| Thinking | Adaptativo, effort `medium`. Es el valor por omisión de `BudgetedClient` desde la integración. | weekly: sin thinking 85–86 %; `low` 95–97 %; `medium` 98,6 % (P3a §3.3). Con `low` no piensa en 18 de 69 exámenes, y ahí caen los errores repetidos. |
| Totales semanales precalculados | **No.** El dream de P4 no los mantiene. | Con el prompt final ganan 2,3 pp en weekly (97,7 → 100 %) y 0 en monthly (100 → 100 %). Si el dream sumara, su aritmética se mezclaría con la memoria en las `aggregate`. Sin totales, ese error queda en el que responde y está medido acá. |
| Llamadas | Una por examen; un examen monthly cuesta $0,00107 de media (§4.4) | — |

### 3.2 Diagnóstico de los errores del techo: examen, formato o modelo

| Error | Causa | Arreglo | Efecto |
| --- | --- | --- | --- |
| "unknown" en la pregunta n.º 1 | **Formato** (posición en la salida; con el examen invertido el error sigue a la posición) | `<answers>` + thinking | preference 95 % → 100 % |
| "unknown" en "¿está en la lista?" sobre algo que no está | **Formato** (el prompt no decía que las listas son cerradas) | Regla de listas cerradas + `- (none)` | todo 47,5 % → 100 %, calendar 50 % → 100 % |
| Metas: "unknown" o el valor de otra meta | **Formato** (el stub no decía qué es `{'value': 210}`) | La línea dice "Weekly budget for … expenses" | goal 65–88 % → 100 % |
| Content: "no" con el ítem en las notas | **Formato** (el stub nombraba `meeting_notes_2`; la pregunta, el título) | Documento por su título | content 62 % → 100 % |
| Total de pasos: "unknown" | **Examen** (el rango termina en la fecha de la sesión, que puede no tener registro) | Regla en el prompt: "a date with no entry has nothing logged" (P3 al integrar; P3b lo encontró) | monthly steps 95,0 % → 100 % |
| Total de gastos: un centavo menos | **Modelo** (aritmética) | Ninguno sin cambiar las notas o la corrección | weekly expense 86,7–92,0 % |

**Total de pasos.** Antes del arreglo, los 10 errores del techo monthly eran todos totales de pasos contestados "unknown". Los 10 caen en preguntas cuyo rango termina en una fecha sin registro de pasos. Fallaron 10 de 32 preguntas con la fecha final sin registro, y 0 de 26 con registro (script en §4.2). Agregué una frase a la regla de totales en `answering/answer.py` (`RULES`). Es la misma idea que la línea `logs` de P3b, pero en el prompt y no en las notas, porque es una regla de lectura y no un hecho.

**Total de gastos.** Los errores que quedan en weekly son siempre de 1 centavo hacia abajo, por ejemplo 258.22 contra 258.23. Solo hay una excepción: s049 da 78.24 contra 79.24. Los montos de Memora tienen como máximo 2 decimales y los 44 totales del examen weekly salen exactos de las notas (test `test_weekly_totals_match_every_weekly_aggregate_of_the_exam`). El error es de la suma: en una respuesta con razonamiento visible, el modelo escribe "3.25 + 3.91 + 9.84 = 16.99" (P3a §4.1). Esos tres montos son de la primera semana de software_engineer, y por eso el error se repite en todos los exámenes de esa semana desde la s049. En las 3 personas monthly no apareció ninguno (231/231).

## 4. Prueba

Todo corrió con `claude-haiku-5-5`, temperatura por omisión del modelo (no se puede fijar), thinking `{"type": "adaptive"}` y effort `medium`, presupuesto `p3`. Las respuestas crudas están en `results/raw/bounds/` y cada comando se vuelve a correr gratis desde ahí.

```
$ uv run pytest -q
...............................                                          [100%]
31 passed
```

### 4.1 Techo, piso y ruido con el prompt final

```
$ uv run python -m answering.bounds weekly software_engineer --budget-name p3 --limit 1.00 --errors
estimate: 0 calls cached, 92 to pay, up to $0.2310 (output priced at max_tokens). Budget p3: spent $0.5285 of $1.00
cost: $0.0531 paid now in 92 calls; ... 233343 input and 59506 output tokens; 0 responses cut at max_tokens.
```

| weekly, por dominio | techo: correct / n | techo: invented | piso: correct | piso: stale | piso: missing | piso: invented | ruido: cambian | ruido: rango (pp) |
| --- | --: | --: | --: | --: | --: | --: | --: | --: |
| preference | 80 / 80 | 0 | 31 / 80 | 0 | 49 | 0 | 0 | 0,0 |
| todo | 61 / 61 | 0 | 32 / 61 | 29 | 0 | 0 | 0 | 0,0 |
| calendar | 46 / 46 | 0 | 23 / 46 | 8 | 15 | 0 | 0 | 0,0 |
| goal | 26 / 26 | 0 | 0 / 26 | 0 | 26 | 0 | 0 | 0,0 |
| content | 77 / 77 | 0 | 31 / 77 | 46 | 0 | 0 | 0 | 0,0 |
| expense | 65 / 75 | 10 | 0 / 75 | 0 | 63 | 12 | 12 | 4,0 |
| steps | 61 / 61 | 0 | 0 / 61 | 0 | 51 | 10 | 0 | 0,0 |
| **total** | **416 / 426 (97,7 %)** | 10 | **117 / 426 (27,5 %)** | 83 | 204 | 22 | **12** | **0,7** |

```
$ uv run python -m answering.bounds monthly academic_researcher software_engineer startup_founder --every 4 --budget-name p3 --limit 1.00 --errors
estimate: 0 calls cached, 268 to pay, up to $0.7609 (output priced at max_tokens). Budget p3: spent $0.2886 of $1.00
cost: $0.2400 paid now in 268 calls; ... 1480770 input and 183833 output tokens; 0 responses cut at max_tokens.
```

| monthly, por dominio | techo: correct / n | piso: correct | piso: stale | piso: missing | piso: invented | ruido: cambian |
| --- | --: | --: | --: | --: | --: | --: |
| preference | 243 / 243 | 87 / 243 | 0 | 156 | 0 | 0 |
| todo | 222 / 222 | 101 / 222 | 121 | 0 | 0 | 0 |
| calendar | 145 / 145 | 68 / 145 | 14 | 61 | 2 | 0 |
| goal | 94 / 94 | 0 / 94 | 0 | 94 | 0 | 0 |
| content | 240 / 240 | 85 / 240 | 136 | 19 | 0 | 0 |
| expense | 231 / 231 | 0 / 231 | 0 | 212 | 19 | 0 |
| steps | 199 / 199 | 0 / 199 | 0 | 184 | 15 | 0 |
| **total** | **1.374 / 1.374 (100 %)** | **341 / 1.374 (24,8 %)** | 271 | 726 | 36 | **0** |

En el techo, `stale`, `missing`, `unparseable` y la columna indulgente dan 0 en las dos corridas. La primera pregunta del examen quedó bien en 15/15 (weekly) y 51/51 (monthly). La tabla por (dominio, probe) es la salida completa del mismo comando.

**Cómo leer el piso.** Es lo que logra una política que nunca soñó:

- Acierta los gustos que no valen ("unknown" es correcto), los distractores y las bajas ("no" en una lista cerrada).
- Los `stale` del piso son "no" sobre pendientes, eventos o ítems que sí existen.
- Los `invented` en expense y steps son "0" como total: con las notas vacías, el modelo aplica la regla "a date with no entry has nothing logged".

### 4.2 Antes del arreglo del total de pasos

La misma corrida monthly, con el prompt de P3a sin la frase sobre días sin registro ($0.2374): techo 99,3 %. Los 10 errores fueron todos `missing` en steps `aggregate`, y el ruido dio 9 de 1.374, todos en steps. Weekly con el mismo prompt ($0.0503): techo 98,4 %, piso 27,0 %, ruido 9/426.

Verificación de la causa, con un script inline sobre `build_exam` y `state_after`:

```
(end date has a step entry, failed): {(True, False): 26, (False, False): 22, (False, True): 10}
```

### 4.3 Techo con y sin totales precalculados 

```
$ uv run python -m answering.bounds weekly software_engineer --measure ceiling --notes-add totals --budget-name p3 --limit 1.00 --errors
cost: $0.0162 paid now in 23 calls
$ uv run python -m answering.bounds monthly academic_researcher software_engineer startup_founder --every 4 --measure ceiling --notes-add totals --budget-name p3 --limit 1.00 --errors
cost: $0.0726 paid now in 67 calls
```

| Configuración | weekly sin totales | weekly con totales | monthly sin totales | monthly con totales |
| --- | --: | --: | --: | --: |
| Stub de la interfaz, sin thinking (P3b) | 70,7 % | 75,6 % | 72,8 % | — |
| Formato elegido, sin thinking (P3a) | 84,7–85,9 % | — | — | — |
| Formato elegido, thinking `low` (P3a) | 95,3–96,9 % | 97,7–98,4 % | 260/260 (2 personas, 12 exámenes) | 258/260 |
| **Formato elegido + regla de días sin registro, thinking `medium` (P3)** | **97,7 %** | **100 %** | **100 %** | **100 %** |

`--notes-add totals` usa los totales de P3a (`answering/format_totals.py`). Al integrar, cambié `bounds.py` para que use esa única implementación en lugar de la de P3b. Las semanas de P3a (domingo a sábado) y las de P3b (bloques de 7 días desde la primera sesión) coinciden: los tres períodos empiezan el domingo 2025-06-01, verificado en las 30 personas.

### 4.4 Costo

| Proceso | Tope | Gastado | Llamadas |
| --- | --: | --: | --: |
| P3a | $0,80 | $0,7224 | 1.315 |
| P3b | $1,20 | $1,0162 | 1.000 |
| P3 (integración) | $1,00 | $0,6704 | 812 |
| **Total** | **$3,00** | **$2,4090** | **3.127** |

Lo de P3a y P3b sale de sus informes (libros `results/spend/p3a.jsonl` y `results/spend/p3b.jsonl`, en sus worktrees). Lo de P3 sale de `results/spend/p3.jsonl` en este worktree. Las medias por examen salen de las respuestas crudas en `results/raw/bounds/`. Desglose de P3:

| Corrida | Costo |
| --- | --: |
| Prueba del stub | $0,0008 |
| weekly, prompt de P3a | $0,0503 |
| monthly, prompt de P3a | $0,2374 |
| monthly, prompt final | $0,2400 |
| weekly, prompt final | $0,0531 |
| Techo con totales: weekly | $0,0162 |
| Techo con totales: monthly | $0,0726 |

Costo por examen con la configuración final, solo techo:

| Período | Por examen | Detalle |
| --- | --: | --- |
| weekly | $0,00064 | 2.945 tokens de entrada, 687 de salida (media de 69 llamadas) |
| monthly | $0,00107 | 6.901 tokens de entrada, 761 de salida (media de 201 llamadas) |

Proyección para P6 y P7 (no medida):

- **Por política, monthly completo:** 873 exámenes ≈ $0,93.
- **Por política, weekly completo:** 218 exámenes ≈ $0,14.

Los prompts quedan lejos de los 100k tokens: el más grande de los 812 pedidos de P3 tuvo 10.203 tokens de entrada.

## 5. Opciones descartadas y por qué

| Opción | Por qué no | Dónde |
| --- | --- | --- |
| Stub `dominio \| clave \| valor` | Claves internas que el modelo nunca ve; 69–73 % de techo | P3a §5, P3b §4.1 |
| Notas en JSON | Empatan con Markdown sin thinking, pesan 6 % más, y una edición puntual del dream rompe el archivo más fácil | P3a §5 |
| Prosa larga de los documentos | Nunca se pregunta ni cambia; +7–19 % de tokens | P3a §3.1 |
| Respuestas en líneas sueltas | Efecto de la primera pregunta (14/23); una cuenta escrita se lee como respuesta | P3a §3.2, P3b §3.2 |
| Structured outputs | El bloque `<answers>` ya da 0 `unparseable`; hubiera hecho falta cambiar `client.py` | P3a §2 |
| Sin thinking | Techo 85–86 %: los errores de lectura se mezclarían con los de memoria | P3a §3.3 |
| Thinking con effort `low` | No piensa en 26 % de los exámenes y ahí se repiten los errores; `medium` cuesta ≈ 7 % más por examen | P3a §3.3 |
| Totales precalculados que mantiene el dream | +2,3 pp solo en weekly expense; suman mantenimiento y la aritmética del dream a la memoria | §3.1 |
| Totales acumulados por fecha (versión de P3b) | Una sola implementación de totales alcanza (YAGNI). Los totales por semana de P3a dan 100 % con thinking. | §4.3 |
| Encabezados `closed`/`goals` de P3b en las notas | El formato de P3a ya lo dice: listas cerradas en el prompt, metas con su significado en cada línea | P3b §3.1 |
| La regla de días sin registro en las notas (`logs` de P3b) | Es una regla de lectura, no un hecho: va en el prompt y el dream no la tiene que escribir | §3.2 |
| Más de 3 repeticiones para el ruido | Con el prompt final el ruido ya es 0–12 respuestas y ≤ 0,7 pp | P3b §5 |

## 6. Limitaciones y preguntas abiertas

- **Muestra.** El techo final está medido en 1 persona weekly completa y en 3 personas monthly con 1 de cada 4 exámenes (67 de 263). La semana de software_engineer en weekly muestra que el error aritmético depende de los montos concretos de una persona. Otras personas pueden tener semanas así. Quarterly no se midió.
- **Error de 1 centavo en totales (decisión abierta).** Es el único error de techo que queda, y es del modelo. Hay dos arreglos posibles:
  - **Tolerancia absoluta de ±$0,01 en las `aggregate`.** Se hace en `exam/grading.py`, que es de P2. No confunde un total viejo con uno correcto: un total anterior difiere en al menos un gasto, y el gasto más chico de weekly y monthly es $3,02.
  - **Dejarlo como está.** Es un piso de error conocido, ≤ 2,3 pp en weekly expense y 0 en monthly.

  Recomiendo dejarlo: es chico, está medido y no toca P2.
- **Problema de examen del total de pasos.** Está resuelto en el prompt (regla de días sin registro). La alternativa es que P2 redacte la pregunta como "logged so far". No hace falta mientras el prompt mantenga la regla.
- **El piso depende de la regla de listas cerradas.** Con ella, "no" es correcto en distractores y bajas, y el piso es 25–27 %, no 6–7 %. Es el piso correcto según la decisión de P2 (listas cerradas).
- **Con notas viejas, la regla de listas cerradas cambia la mezcla de clases.** Un hecho nuevo que el dream no anotó sale `stale` ("no") y no `missing`. Para la cadencia, P7 tiene que leer `stale + missing` juntos en los `new` por existencia (P2 §6).
- **La cuenta indulgente da 0 con notas perfectas:** un gusto borrado no está en las notas. Va a importar con notas de un dream (P4), que puede escribir "ya no le gusta".
- **Las notas perfectas usan las etiquetas de Memora** ("music / genres", "work tasks"). Un dream va a usar sus propias palabras; si se aparta mucho, P4 lo va a ver como error de memoria.
- **Tamaño de las notas monthly:** 20–24 KB y 451–491 líneas. Pasan los 16.000 caracteres de `view` del memory tool y las 200 líneas de `MEMORY.md`. Si P4 usa el memory tool, conviene un archivo por sección.
- **El caché de respuestas no viaja entre worktrees.** `results/` está ignorado por git, así que las respuestas de P3a y P3b quedaron en sus worktrees. Las de P3 están en este.
