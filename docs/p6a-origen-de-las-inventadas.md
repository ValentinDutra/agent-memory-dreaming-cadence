# P6a · De dónde sale cada inventada

**Resultado.** Las 42 `invented` de `every-5` sobre monthly/academic_researcher entera salen de **11 raíces**. Ninguna es un error del que responde.

- **25 (2 raíces): Memora.** Dos gastos que el usuario fechó "last night", y que Memora fecha el día de la sesión.
- **10 (2 raíces): el sueño.** Una omisión, que arruina 9 totales seguidos, y un "dislike" que la cuenta indulgente ya da por correcto.
- **6: notas atrasadas.** El que responde contesta "0" o "no" donde las reglas piden "unknown".
- **1: Memora.** Un evento que el usuario canceló.

En s1–210, las 56 `invented` de las 11 políticas (`never` 25, `every-50` 17, `every-10` 5, `every-20` 5, `every-5` 2, `triggered-phrases-change` 2) son **todas** del último tipo: la nota no tiene el dato todavía (o no hay nota) y la respuesta es "0" o "no". **Ninguna es una nota falsa.** Con notas perfectas, el examen de la persona entera da 1.809/1.809 `correct` y 0 `invented`.

| Rol | Ruta |
| --- | --- |
| Clasificador y CLI | `diagnosis/causes.py` (`diagnose`, `diagnose_run`, `CAUSES`) |
| Notas perfectas, persona entera | `diagnosis/perfect_notes.py` |
| Criterios alternativos de corrección, medidos aparte | `diagnosis/criteria.py` |
| Marcas nuevas contra una revisión | `diagnosis/marks_diff.py` |
| Arreglo de un bug (dos casos) | `exam/unreachable.py` |
| Tests | `tests/test_causes.py` (1), `tests/test_unreachable.py` (+1) |

## 1. Problema

En P5, `every-5` dio 2 `invented` en s1–210 (0,3 %) y 42 en la persona entera (2,3 % de 1.809 preguntas). Una `invented` debería ser el peor error: el agente afirma algo que nunca fue cierto. Si crece con la vida del agente, P7 sobre s1–210 sería optimista.

Ejemplo real: examen de la s245, `every-5`.

- **Pregunta:** "What is the total of the user's food expenses dated from 2025-06-08 to 2025-06-12, in dollars?"
- **Respuesta:** `154.07`. Lo esperado es `158.18` y la historia no tiene 154.07, así que sale `invented`.
- **Las notas:** las 12 líneas de esa semana suman exactamente 154.07. Les falta un café de $4.11 del 2025-06-11, que Memora registró en la s236 a partir de este turno: *"That's true, even something as simple as grabbing a $4.11 coffee can be a small break in the day."*
- **El sueño:** el de después de la s240 leyó s236–s240 y escribió los otros tres gastos del 11 (`- 2025-06-11 coffee: $4.90`, entre ellos), pero no ese. Ningún sueño posterior lo escribió.

El que responde sumó bien. El total no es inventado: está incompleto. La misma omisión arruina los 9 totales semanales de la s245 a la s301.

## 2. Hipótesis consideradas

| # | Hipótesis | Cómo se prueba |
| --- | --- | --- |
| H1 | El sueño escribe líneas falsas, y más con notas largas | Cada línea de la nota contra la verdad después de N (`truth_entries` contra `note_entries`); el sueño que la escribió con `diagnosis.invented.line_origin` y el turno que la produjo en la transcripción |
| H2 | La nota está bien y el que responde la lee mal (suma mal, confunde ítems) | `from_notes`: la respuesta que dan las notas siguiendo las reglas del prompt al pie de la letra. Además, el examen entero con notas perfectas (§4.3). |
| H3 | La verdad de Memora está mal (fechas "last night", cambios que no registra) | Las marcas de `exam/unreachable.py`, y la transcripción de cada caso |
| H4 | La regla de corrección llama `invented` a lo que es un total incompleto o un "0" sin datos | Recorregir con dos criterios alternativos, sin tocar el conteo oficial (§4.4) |

## 3. Análisis y conclusión

### 3.1 Cómo decide el clasificador

`diagnosis/causes.py` toma cada `WrongAnswer` de `diagnosis.invented` y calcula `from_notes`, lo que contestaría alguien que lee esas notas y aplica las reglas del prompt:

- **Para un total:** suma las líneas del rango.
- **Para un gasto o un registro de pasos:** suma las líneas de esa fecha y ese tipo, y si no hay ninguna da `unknown`.
- **Para un gusto o una fecha:** el valor de la línea, o `unknown` si no hay línea.

Después empareja las entradas de la verdad y de la nota por fecha y monto, y explica cada diferencia:

- `lag`: entró después del último sueño.
- `omitted`: el sueño que leyó esa sesión no la escribió.
- `relative_date`: un gasto "last night" que Memora fecha un día después.
- `merged`: dos gastos en una línea.
- `false_line`: una línea que ningún estado tuvo.
- `dropped_by_user`: un sueño borró el hecho después de un turno del usuario que lo deja.

| Causa | Grupo | Regla |
| --- | --- | --- |
| `dream_false_line` | 1 sueño | La respuesta es la de la nota, y la nota tiene un valor que el hecho nunca tuvo |
| `dream_omission` | 1 sueño | La nota no tiene una entrada que el sueño leyó |
| `reader_misread` | 2 lector | `from_notes` es lo esperado y la respuesta no |
| `reader_nothing_for_absent` | 2 lector | La nota no tiene el gasto, los pasos o el evento, y la respuesta es "0" o "no", donde la regla "A number or date the notes do not contain: answer unknown" pide `unknown` |
| `memora_relative_date` | 3 Memora/examen | Alguna diferencia es un gasto "last night" |
| `memora_kept_removed` | 3 Memora/examen | El usuario dejó el hecho, un sueño lo borró y Memora lo sigue teniendo |
| `grader_empty_total` | 3 Memora/examen | La nota no tiene ninguna entrada del rango todavía (`lag`), así que su total es 0, como dice la regla del prompt. La historia del total empieza en `None`, que se renderiza `unknown`, y por eso el "0" sale `invented` y no `stale`. |
| `unexplained` | 4 otra | Nada de lo anterior. **Quedó en 0.** |

### 3.2 `every-5` sobre la persona entera: causa × tramo

| Causa | Grupo | s1–210 | s211–420 | s421–619 | Total | Raíces distintas | Marcadas por `unreachable` |
| --- | --- | --: | --: | --: | --: | --: | --: |
| `dream_false_line` | 1 sueño | 0 | 1 | 0 | 1 | 1 | 0 |
| `dream_omission` | 1 sueño | 0 | 9 | 0 | 9 | 1 | 0 |
| `reader_misread` | 2 lector | 0 | 0 | 0 | 0 | 0 | 0 |
| `reader_nothing_for_absent` | 2 lector | 1 | 2 | 0 | 3 | 3 | 0 |
| `memora_relative_date` | 3 Memora/examen | 0 | 0 | 25 | 25 | 2 | 25 |
| `memora_kept_removed` | 3 Memora/examen | 0 | 0 | 1 | 1 | 1 | 0 |
| `grader_empty_total` | 3 Memora/examen | 1 | 2 | 0 | 3 | 3 | 0 |
| **total** | | **2** | **14** | **26** | **42** | **11** | **25** |

Una raíz es un gasto o un hecho, que puede arruinar muchos exámenes, o una pregunta suelta cuando la causa es solo el atraso. Ejemplos reales de cada causa (salida completa con el comando de §4.1):

- **`memora_relative_date`, 25 respuestas, 2 gastos:**
  - s470 (2025-06-22): *"Speaking of sophisticated systems, I spent $30.38 on dinner last night."* Memora lo fecha 2025-06-22. El sueño de después de la s470 (leyó s466–s470) escribe `- 2025-06-21 dinner: $30.38`. Los 21 totales de la semana del 22, de la s476 a la s616, dan $30,38 menos de lo esperado; por ejemplo, en la s476 la respuesta es `5.86` y lo esperado `36.24`. Además, "¿cuánto en la cena del 2025-06-21?" en la s595 da `54.39` (24.01 + 30.38), lo que gastó el usuario según él mismo.
  - s429 (2025-06-20): *"like when I treated myself to a $45.81 dinner last night after finishing a big project."* Las notas tienen dos cenas el 2025-06-19 ($45.45 de la s402 y $45.81). "¿cuánto en la cena del 2025-06-19?" da `91.26` en las s441 y s448, lo esperado es `45.45`. La del 2025-06-20 da `0` en la s546, lo esperado es `45.81`.
  - Antes de este informe, `unreachable` marcaba 22 de estas 25. Las 3 de "el día anterior" (s441, s448, s595) no estaban marcadas: era un bug, arreglado en §3.4.
- **`dream_omission`, 9 respuestas, 1 gasto:** el café de $4,11 de la s236 (§1). El turno no dice "gasté": es una frase general sobre los descansos. El sueño cumplió la regla "Food expenses: every one" con los otros tres gastos del día y dejó este. Es una omisión del sueño, pero sobre un turno ambiguo.
- **`dream_false_line`, 1 respuesta:** s420, Thomas Mann. La nota `- Thomas Mann (books / author): dislike` la escribió el sueño de después de la s420 (leyó s416–s420). El usuario dijo en la s416: *"His writing just resonates with me much more than Thomas Mann's ever did… Mann's work always felt a bit too dense for me."* Memora borra el "like" y el sueño escribe "dislike". Es el caso de la decisión del usuario de P2: `invented` en la cuenta estricta y `correct` en la indulgente.
- **`memora_kept_removed`, 1 respuesta:** s602, "On what date is the user's event 'Academic conference' scheduled?". La respuesta es `no` y lo esperado `2025-07-02`. En la s586 el usuario dijo: *"I'm no longer planning to attend the academic conference. You can remove "Plan academic conference attendance" from my work tasks."* Memora borra solo el pendiente y deja el evento. El sueño de después de la s590 borró los dos.
- **`reader_nothing_for_absent`, 3 respuestas:** s49, "How much did the user spend on coffee on 2025-06-03?". La respuesta es `0` y lo esperado `7.75`. El café entró en la s48, después del sueño de la s45, así que la nota no lo tiene y la regla pide `unknown` (que saldría `missing`).
- **`grader_empty_total`, 3 respuestas:** s147, total del 2025-06-08 al 2025-06-08. La respuesta es `0` y lo esperado `5.33`. El único gasto del día entró en la s147, después del sueño de la s145. Con la nota al día de la s145, 0 es el total correcto.

**El que responde no inventa nada.** En las 42, la respuesta es exactamente lo que dan las notas. Las únicas excepciones son las 5 en que las notas no tienen el dato y la respuesta es "0" o "no": las 3 `reader_nothing_for_absent`, la s546 y la s602, y en esas dos últimas "0" y "no" son lo que dijo el usuario. Las 33 `aggregate` son sumas exactas de las líneas de la nota: ningún total está mal sumado.

### 3.3 s1–210, las 11 políticas: causa × política

| Causa | never | every-1 | every-2 | every-3 | every-5 | every-10 | every-20 | every-50 | phrases-change | phrases-any | model-any |
| --- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| `reader_nothing_for_absent` | 3 | 0 | 0 | 0 | 1 | 3 | 2 | 6 | 1 | 0 | 0 |
| `grader_empty_total` | 22 | 0 | 0 | 0 | 1 | 2 | 3 | 11 | 1 | 0 | 0 |
| todas las demás | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **total** | **25** | **0** | **0** | **0** | **2** | **5** | **5** | **17** | **2** | **0** | **0** |

En s1–210, `invented` mide **atraso, no invención**: la nota todavía no tiene el dato. Por eso crece al soñar menos (0 con `every-1`, `every-3` y `triggered-phrases-any`; 25 con `never`) y repite lo que ya mide `missing`. Las 3 de `never` son "Peer review discussion" en las s49, s56 y s77: con notas vacías, la regla de listas cerradas ("if an event is not in the notes … answer no") choca con la de fechas ("A number or date the notes do not contain: answer unknown"). Es un desliz raro. Sobre las 278 preguntas de s1–210 cuya nota no tiene el dato, el que responde dijo `unknown` 262 veces y "0" o "no" 16 (§4.4).

### 3.4 Bugs arreglados en `exam/unreachable.py`

1. **Faltaba el día que quiso decir el usuario.** La regla `relative_date` marcaba la pregunta por el gasto "last night" (fechado por Memora el día de la sesión) y el total que empieza ese día. No marcaba la pregunta por el mismo tipo de gasto el día anterior, una vez registrado el "last night". Para ese día el usuario declaró dos gastos de ese tipo, así que ningún sueño correcto puede contestar el monto único de Memora. Caso: s441, dinner 2025-06-19, esperado `45.45`, notas con $45.45 y $45.81. Arreglo: también se marca esa pregunta desde la sesión del "last night" en adelante. Test: `tests/test_unreachable.py::test_the_day_a_last_night_expense_belongs_to_is_marked_once_it_is_logged`; la s406, anterior a la s429, sigue sin marcar.
2. **Falso positivo con "today".** La regla tomaba cualquier turno con "yesterday". En monthly/creative_designer s132 (2025-06-07) el usuario dice *"I just had a $9.81 lunch today, mostly leftovers from yesterday."* Es un almuerzo de hoy y Memora lo fecha bien. Arreglo: se ignoran los turnos que dicen "today". Es 1 de los 40 gastos que la regla encontraba en weekly + monthly; ningún otro dice "today". Lo encontré porque el arreglo 1 lo propagaba al día anterior. Mismo test.

**Qué resultados anteriores cambian** (`diagnosis.marks_diff`, §4.5):

- **Monthly:** 35 preguntas marcadas más y 4 menos. Pasan de 395 (2,2 %) a 426 (2,3 %), y las de gastos de 223 a 254.
- **Weekly:** sin cambios.
- **P5 en s1–210:** sin cambios en ninguna de las 11 políticas (siguen 585 preguntas alcanzables).
- **P5, `every-5` entera:** "oficial sin marcadas" pasa de 1575/1764 (89,3 %) a 1575/1761 (89,4 %), e "indulgente sin marcadas" de 1576/1764 (89,3 %) a 1576/1761 (89,5 %).
- **P7 en s1–210:** cambian 9 marcas en 4 personas. Se suman 2 en business_executive, 3 en creative_designer (y 1 se quita), 1 en software_engineer y 2 en startup_founder.
- **Lo que no cambia:** el conteo oficial y el caché del examen.
- **P2 a actualizar en la integración:** la tabla de `docs/p2-examen.md` ("Preguntas marcadas") dice 223 y 395.

### 3.5 Conclusión para P7

- **No hay notas que se pudran con la vida del agente.** En 619 sesiones hay 1 línea falsa, que la cuenta indulgente da por buena, y 1 omisión. Con notas perfectas, el que responde no inventa en ningún tramo, ni con las notas más largas (s421–619: 579/579).
- **El salto de 2 (s1–210) a 42 (persona entera) lo explican 3 eventos de esta persona,** no la edad de las notas:
  - dos gastos "last night" (s429 y s470), que dan 25 respuestas, hoy todas marcadas;
  - un café dicho al pasar (s236), que da 9 respuestas.
  
  Sin las marcadas y con la cuenta indulgente quedan 16 de 42, de las que 9 son una sola omisión.
- **Para P7, s1–210 no es optimista en cuanto a notas falsas.** Su `invented` mide atraso: depende de la cadencia, no de la vida.
- **Lo que una persona entera agrega son eventos raros** ("last night", cancelaciones implícitas, gastos dichos al pasar). Eso es varianza entre personas, que P7 tiene que medir con 10 personas y bootstrap. Hay que reportar siempre la columna sin marcadas, que ahora cubre también el día anterior de un "last night".

## 4. Prueba

Todo sale del caché de P5, salvo §4.3. Costo real total: **$0,0987** (88 llamadas, `results/spend/p6a.jsonl`), de un tope de $0,80.

### 4.1 Clasificación, `every-5` entera ($0)

```
$ uv run python -m diagnosis.causes monthly/academic_researcher --policies every-5 --stretches --check-cache
## every-5 on monthly/academic_researcher: 42 invented

### every-5 s49 expense/new: reader_nothing_for_absent
- question: How much did the user spend on coffee on 2025-06-03, in dollars? Answer with a number or unknown.
- answer '0', expected '7.75', the notes give 'unknown'; last dream s45
- lag: 2025-06-03 coffee 7.75 (logged in s48): after the last dream (s45)
...
### every-5 s245 expense/aggregate: dream_omission
- question: What is the total of the user's food expenses dated from 2025-06-08 to 2025-06-12, in dollars? Answer with a number or unknown.
- answer '154.07', expected '158.18', the notes give '154.07'; last dream s245
- omitted: 2025-06-11 coffee 4.11 (logged in s236): the dream after s240 read it and left it out
...
### every-5 s441 expense/stable: memora_relative_date (marked relative_date)
- question: How much did the user spend on dinner on 2025-06-19, in dollars? Answer with a number or unknown.
- answer '91.26', expected '45.45', the notes give '91.26'; last dream s440
- relative_date: `- 2025-06-19 dinner: $45.81` is the day the user meant; Memora dates it a day later; written by the dream after s430, which read s426-s430
...
### every-5 s602 calendar/stable: memora_kept_removed
- question: On what date is the user's event 'Academic conference' scheduled? Answer with a date (YYYY-MM-DD) or unknown.
- answer 'no', expected '2025-07-02', the notes give 'unknown'; last dream s600
- dropped_by_user: the dream after s590 deleted it; s586: "I'm no longer planning to attend the academic conference. You can remove "Plan academic conference attendance" from my work tasks."
...
## By stretch of sessions

| cause | group | every-5 s1-210 | every-5 s211-420 | every-5 s421-619 |
| --- | --- | --: | --: | --: |
| dream_false_line | 1 dream | 0 | 1 | 0 |
| dream_omission | 1 dream | 0 | 9 | 0 |
| reader_misread | 2 reader | 0 | 0 | 0 |
| reader_nothing_for_absent | 2 reader | 1 | 2 | 0 |
| memora_relative_date | 3 Memora/exam | 0 | 0 | 25 |
| memora_kept_removed | 3 Memora/exam | 0 | 0 | 1 |
| grader_empty_total | 3 Memora/exam | 1 | 2 | 0 |
| unexplained | 4 other | 0 | 0 | 0 |
| **total** | | **2** | **14** | **26** |
```

Las tablas de raíces distintas y de marcadas de §3.2 salen del mismo comando. Que ningún sueño escribió nunca el café de $4,11 se ve en la nota de cada sueño de esa corrida: la línea no aparece, y la de después de la s240 tiene los tres gastos del 11 sin ese.

### 4.2 Clasificación, s1–210, 11 políticas ($0)

```
$ uv run python -m diagnosis.causes monthly/academic_researcher:210 --policies never every-1 every-2 every-3 every-5 every-10 every-20 every-50 triggered-phrases-change triggered-phrases-any triggered-model-any --quiet --check-cache
| cause | group | never | every-1 | every-2 | every-3 | every-5 | every-10 | every-20 | every-50 | triggered-phrases-change | triggered-phrases-any | triggered-model-any |
...
| reader_nothing_for_absent | 2 reader | 3 | 0 | 0 | 0 | 1 | 3 | 2 | 6 | 1 | 0 | 0 |
| grader_empty_total | 3 Memora/exam | 22 | 0 | 0 | 0 | 1 | 2 | 3 | 11 | 1 | 0 | 0 |
| unexplained | 4 other | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **total** | | **25** | **0** | **0** | **0** | **2** | **5** | **5** | **17** | **2** | **0** | **0** |
```

Las demás filas dan 0 en todas las políticas.

### 4.3 Notas perfectas, persona entera ($0,0987)

```
$ uv run python -m diagnosis.perfect_notes monthly/academic_researcher --dry-run
88 exams; not cached: worst case $0.3682
$ uv run python -m diagnosis.perfect_notes monthly/academic_researcher --limit 0.40
## Perfect notes on monthly/academic_researcher: 88 exams

| stretch | correct | stale | missing | invented | unparseable |
| --- | --: | --: | --: | --: | --: |
| s1-210 | 593 | 0 | 0 | 0 | 0 |
| s211-420 | 637 | 0 | 0 | 0 | 0 |
| s421-619 | 579 | 0 | 0 | 0 | 0 |

p6a spent: $0.0000 before, $0.0987 after
```

Corrió en el `run` `p6a/perfect/monthly/academic_researcher`, así que no choca con el caché de P5. La cota del dry-run cuenta bytes como tokens; lo pagado fue el 27 % de esa cota.

### 4.4 Criterios alternativos, sin tocar el oficial ($0)

```
$ uv run python -m diagnosis.criteria monthly/academic_researcher:210 --policies never every-1 every-2 every-3 every-5 every-10 every-20 every-50 triggered-phrases-change triggered-phrases-any triggered-model-any --check-cache
$ uv run python -m diagnosis.criteria monthly/academic_researcher --policies every-5 --check-cache
```

| Política | Tramo | `invented` oficial | con `nothing_logged` | con `partial_total` | con los dos | Notas sin el dato: unknown / nothing / other |
| --- | --- | --: | --: | --: | --: | --: |
| never | s1–210 | 25 | 0 | 3 | 0 | 150 / 3 / 0 |
| every-1, -2, -3 | s1–210 | 0 | 0 | 0 | 0 | 0 / 0 / 0; 3 / 0 / 0; 4 / 0 / 0 |
| every-5 | s1–210 | 2 | 0 | 1 | 0 | 8 / 1 / 0 |
| every-10 | s1–210 | 5 | 0 | 3 | 0 | 15 / 3 / 0 |
| every-20 | s1–210 | 5 | 0 | 2 | 0 | 22 / 2 / 0 |
| every-50 | s1–210 | 17 | 0 | 6 | 0 | 52 / 6 / 0 |
| triggered-phrases-change | s1–210 | 2 | 0 | 1 | 0 | 8 / 1 / 0 |
| triggered-phrases-any, triggered-model-any | s1–210 | 0 | 0 | 0 | 0 | 0 / 0 / 0 |
| every-5 | persona entera | 42 | 34 | 9 | 4 | 30 / 5 / 0 |

Los dos criterios:

- **`nothing_logged`:** "0" a un gasto, a unos pasos o a un total, o "no" a la fecha de un evento, cuando el hecho alguna vez no valía (`None` en su historia), sale `stale`, no `invented`. El agente cree que no hay nada registrado, y eso fue cierto antes.
- **`partial_total`:** un total igual a la suma de un subconjunto de las entradas verdaderas de su rango (las que faltan, faltan por atraso u omisión) sale "incompleto".

Ninguno mueve la precisión: solo pasan respuestas de `invented` a `stale` o a incompleto. Con los dos, las 4 `invented` que quedan en `every-5` entera son Thomas Mann (correcta en la cuenta indulgente) y las 3 del día anterior a un "last night" (ahora marcadas).

### 4.5 Marcas de `unreachable` y tests ($0)

```
$ uv run python -m diagnosis.marks_diff 5fc7cc4 weekly monthly
| period/persona | added | added in s1-210 | removed | removed in s1-210 |
| --- | --: | --: | --: | --: |
| monthly/academic_researcher | 3 | 0 | 0 | 0 |
| monthly/business_executive | 6 | 2 | 0 | 0 |
| monthly/creative_designer | 5 | 3 | 4 | 1 |
| monthly/financial_analyst | 5 | 0 | 0 | 0 |
| monthly/management_consultant | 3 | 0 | 0 | 0 |
| monthly/sales_manager | 3 | 0 | 0 | 0 |
| monthly/software_engineer | 7 | 1 | 0 | 0 |
| monthly/startup_founder | 3 | 2 | 0 | 0 |
| **total** | 35 | 8 | 4 | 1 |

$ uv run python -m exam.unreachable weekly monthly
...
| expense | 3024 | 0 | 254 | 0 | 254 (8.4%) | 0 |
| total | 18214 | 171 | 254 | 1 | 426 (2.3%) | 503 |

$ uv run python -m policies.run monthly/academic_researcher --policies every-5 --check-cache
| every-5 | monthly/academic_researcher | 0 | 619 | 123 | 0.1777 | 0.0000 | 0.1076 | 88 | 1577/1809 (87.2%) | 1578/1809 (87.2%) | 1575/1761 (89.4%) | 1576/1761 (89.5%) | 1577 | 123 | 67 | 42 | 0 |

$ uv run pytest -q
................................................                         [100%]
48 passed in 20.46s
```

`5fc7cc4` es la base de esta rama (la interfaz de P6). Weekly no tiene filas porque no cambia.

## 5. Hipótesis descartadas y por qué

| Hipótesis | Por qué no |
| --- | --- |
| H2: el que responde suma mal o confunde ítems | `reader_misread` = 0 en las 11 políticas y en la persona entera. Las 33 `aggregate` son sumas exactas de la nota. Con notas perfectas: 0 `invented` en 1.809 preguntas, también en s421–619, donde las notas son más largas. |
| H1: las notas se llenan de líneas falsas con el tiempo | Hay 1 `dream_false_line` en 619 sesiones, y es el "dislike" que la decisión de P2 ya trata aparte. No hay líneas fusionadas (`merged` = 0): las dos cenas del 2025-06-19 son dos líneas, y la suma la hace el que responde porque la pregunta pide cuánto gastó ese día. |
| "Un total `invented` es un error de suma" (P2 §3.4) | En estos datos, ninguno lo es. Todos son totales de una nota incompleta, por atraso, omisión o "last night". |
| La omisión de $4,11 es un defecto de Memora | El turno es ambiguo ("grabbing a $4.11 coffee can be a small break"), pero nombra un monto y un café el día de la sesión, y la regla del sueño dice "every one". Lo cuento como omisión del sueño y lo dejo señalado. |

## 6. Limitaciones

- **Una sola persona** para la vida entera, y una sola política (`every-5`). Las 11 raíces son demasiado pocas para estimar una tasa de omisión por sesión. Esa tasa la mide P6b con `compare_notes` sobre todos los sueños.
- **Solo `invented`.** No clasifiqué `stale` ni `missing`. `diagnose` sirve para cualquier `WrongAnswer`, pero sus reglas están pensadas para respuestas que no coinciden con ningún estado.
- **`memora_kept_removed`** es una regla de palabras ("no longer", "anymore", "cancel", "remove", "drop") sobre los turnos del usuario que leyó el sueño que borró la línea. Tiene 1 caso real y ningún test propio. No la llevé a `unreachable`: decidir si "ya no voy" cancela un evento es un criterio, no un bug.
- **Preferencias:** `from_notes` busca la línea por nombre exacto (sin mayúsculas). Un gusto escrito con otras palabras daría `unknown`. En estos datos no pasa.
- **Turno ambiguo de la s236:** clasificarlo como omisión del sueño o como defecto de Memora es un juicio, y mueve 9 de las 42.

## Decisiones abiertas

1. **¿Adoptar `nothing_logged` en la corrección oficial?** Un "0" o un "no" cuando el hecho alguna vez no valía pasaría a `stale`. Efecto:
   - en s1–210, `invented` baja a 0 en las 11 políticas (`never` 25 → 0, `every-50` 17 → 0);
   - en `every-5` entera, 42 → 34;
   - la precisión no cambia.
   
   Recomiendo adoptarlo. Así `invented` queda para afirmaciones que nunca fueron ciertas, y deja de duplicar el atraso que ya mide la cadencia. Ejemplos de lo que cambia:
   - s147: total `0` sin gastos en la nota, de `invented` a `stale`.
   - `never` s49: "Peer review discussion" → `no`, de `invented` a `stale`.
2. **¿Adoptar `partial_total` ("incompleto")?** Separa "le falta un gasto" de "inventó un monto": en `every-5` entera, 42 → 9. Es menos limpio que el 1: una suma de subconjunto puede coincidir por azar. No lo recomiendo como oficial; sirve como columna de diagnóstico.
3. **¿Arreglar el prompt de respuesta?** Hoy dice "listas cerradas → no" y "número o fecha que falta → unknown". Unificarlo, o decir explícitamente que un gasto que falta es `unknown`, eliminaría los 16 deslices de §3.3. Pero cambia todos los prompts del examen e invalida el caché de P3 y P5. Con el criterio 1 adoptado no hace falta.
4. **Integración de P6:** el arreglo de `exam/unreachable.py` cambia las cifras de §3.4. Hay que actualizar la tabla de marcadas de `docs/p2-examen.md` y la fila de `every-5` entera de `docs/p5-politicas.md` (§4.2 de P5).
