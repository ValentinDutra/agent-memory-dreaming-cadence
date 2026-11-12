# P3b · Techo, piso y ruido

**Resultado.** Con los stubs actuales (`render_notes` "dominio | clave | valor" y `answer_exam` "<número>: <respuesta>"), sin thinking:

- **Techo:** 70,7 % en weekly/software_engineer y 72,8 % en monthly (3 personas, 1 de cada 4 exámenes).
- **Piso:** 7,3 % y 6,3 %. Solo acierta los gustos que no valen.
- **Ruido:** cambian 47 de 426 respuestas en weekly y 157 de 1.374 en monthly. La precisión total varía como mucho 1,2 pp entre repeticiones.

Casi todo el error del techo es **formato**, no modelo ni examen. Con thinking adaptativo y tres líneas de encabezado que un dream puede escribir, el techo sube a **99,5 %** en weekly y a **99,1 %** en monthly, y el ruido baja a 11 de 426 respuestas. Lo que queda son sumas. Encontré un problema de **examen**: el total de pasos pregunta por un rango que termina en una fecha sin registro todavía. El arreglo es de formato y está probado.

| Rol | Ruta |
| --- | --- |
| Código | `answering/bounds.py` (CLI) |
| Tests | `tests/test_bounds.py` (2, sin API) |
| Respuestas crudas | `results/raw/bounds/<period>/<persona>/` (ignorado por git; se recorrige gratis) |
| Libro de gasto | `results/spend/p3b.jsonl` |

Uso para P3 al integrar (el formato de P3a entra solo, porque `bounds.py` llama a `render_notes` y `answer_exam`):

```bash
uv run python -m answering.bounds weekly software_engineer --budget-name p3 --limit 1.00 --thinking adaptive --effort low --dry-run
uv run python -m answering.bounds weekly software_engineer --budget-name p3 --limit 1.00 --thinking adaptive --effort low
uv run python -m answering.bounds monthly academic_researcher software_engineer startup_founder --every 4 --budget-name p3 --limit 1.00 --thinking adaptive
```

Parámetros del CLI:

- `--measure ceiling floor noise` (por omisión, las tres).
- `--every k`: 1 de cada k exámenes de cada persona.
- `--budget-name` y `--limit`: el presupuesto y su tope.
- `--thinking` y `--effort`.
- `--notes-add closed goals logs totals`: hipótesis de formato que se agregan a `render_notes`.
- `--reversed`: el examen en orden inverso.
- `--errors`: lista cada respuesta incorrecta del techo.
- `--dry-run`.

Antes de pagar, el CLI hace siempre una pasada en seco. Esa pasada cuenta cuántas llamadas ya están en `results/raw/` y acota el costo del resto. Después reporta el costo real de lo que pagó y el costo total de la medición, contando también lo que leyó del caché. Reporta además los tokens y cuántas respuestas se cortaron en `max_tokens`.

## 1. Problema

P3 tiene que separar los errores de memoria (P4, P5) de los errores del examen, del formato y del modelo. Para eso se mide:

- **Techo.** Cuánto acierta el modelo con notas perfectas, `render_notes(timeline.state_after(N))`.
- **Piso.** Cuánto acierta con notas vacías.
- **Ruido.** Cuánto cambia la respuesta si se repite el mismo examen.

Si el techo es bajo, las cadencias de dreaming se comparan dentro de un rango chico, y un error del formato se confunde con un error de memoria.

Ejemplo real, weekly/software_engineer, examen de la s161, notas perfectas con el stub y sin thinking. La pregunta pide el total de gastos de comida del 2025-06-01 al 2025-06-07, que es 258,23. El modelo contestó, todo en la línea de respuesta:

```
food expenses (breakfast, lunch, dinner, grocery, coffee are all food-related; i'm treating all listed categories as food):
9.15+7.35+3.41+3.25+3.91+9.84+13.83+3.45+19.77+7.33+6.8+8.48+9.75+11.79+15.72+4.78+23.03+8.13+7.94+30.01+4.77+10.3+28.5+6.94 = 300.04
```

Esa respuesta muestra tres cosas:

- **El modelo encontró los 24 gastos correctos.** La suma real de esos 24 montos es 258,23 (`truth`), así que las notas y el examen están bien.
- **Sumó mal.** Es un error del modelo.
- **Escribió la cuenta en la línea de respuesta.** Por eso la corrección da `unparseable`, que es un error de formato.

En la misma persona, "Does the user currently like or dislike 'virtual reality' (movie genre)?" (s021) salió "unknown" aunque la nota dice `preference | movies / genres / virtual reality | {'preference': 'like'}`. Era la pregunta número 1 del examen.

## 2. Opciones investigadas

| Fuente | Qué se tomó |
| --- | --- |
| LongMemEval, https://arxiv.org/html/2410.10813v2 §3.4 y §5.5 | El techo como "oracle retrieval setting (answering with only the evidence sessions as the context)". Con evidencia perfecta, "a suboptimal reading strategy results in up to a 10-point absolute performance drop compared to the best approach for GPT-4o": **el formato de lectura mueve el techo**, y Chain-of-Note (extraer y razonar paso a paso) lo sube. Por eso tiene sentido medir el techo con varias variantes de formato y de razonamiento. |
| Anthropic, adaptive thinking y effort: https://platform.claude.com/docs/en/build-with-claude/effort y https://platform.claude.com/docs/en/build-with-claude/thinking-steering-and-cost | "Claude's thinking is adaptive: the model evaluates each request and determines whether to think and how much". `effort` "is a behavioral signal, not a strict token budget". "Thinking counts toward `max_tokens` even when the thinking content isn't returned" (esto explica los cortes de §4.4). |
| Lost in the Middle, https://arxiv.org/abs/2307.03172 | "performance is often highest when relevant information occurs at the beginning or end of the input context". Es el antecedente de los efectos de posición. Acá el efecto aparece en la **primera respuesta**: es posición en la salida, no en el contexto. Lo verifiqué con el examen en orden inverso (§4.2). |
| Quantifying Variance in Evaluation Benchmarks, https://arxiv.org/abs/2406.10229 | Medir la varianza del evaluador antes de comparar modelos. El cambio de formato reduce la varianza ("framing choice tasks … as completion tasks, can often reduce variance"). Acá pasa lo mismo: con notas sin ambigüedad, el ruido baja de 85 a 11 respuestas (§4.3). |
| Haiku 5.5 sin `temperature` (`docs/p3-interfaz.md` §Temperatura) | El ruido se mide con el muestreo por omisión del modelo, repitiendo el examen con `repeat=0,1,2`, que el cliente guarda como pedidos distintos. |

## 3. Análisis y elección

### 3.1 Cómo se mide

- **Techo y piso.** Cada examen de la sesión N se contesta con `render_notes(state_after(N))` y con `render_notes({})`, a través de `answer_exam`. El código no toca ninguno de los dos stubs, así que el formato de P3a entra sin cambios.
- **Ruido.** El examen del techo se repite con `repeat=1,2`. El `repeat=0` es la misma llamada del techo y no se paga dos veces; el test lo verifica.
- **Qué se reporta:**
  - Una tabla por dominio con las 5 clases, la columna indulgente (`negates_removed_preference`) y las dos precisiones.
  - `tally_table` por (dominio, probe).
  - La precisión de la primera pregunta contra las demás.
  - En el ruido: cuántas respuestas normalizadas cambian, cuántas cambian de clase y el rango de precisión por dominio.
- **Variantes de formato** (`--notes-add`). Son líneas que se agregan a `render_notes` sin editarlo, y cada una es algo que un dream puede escribir leyendo las conversaciones:
  - `closed`: "These notes are complete and up to date. A to-do, calendar event or document item that is not listed here is not there: answer no. A preference that is not listed means the user has no current opinion."
  - `goals`: "Goals: daily_steps is the user's daily step goal; every other goal is the user's weekly spending budget, in dollars, for that expense type." El usuario lo dice así: "my goal is to keep it under $30 per week" (s12).
  - `logs`: "Expenses and step counts are listed by date: a date with no entry has nothing logged, so a total covers only the listed entries."
  - `totals`: totales acumulados por semana; la especificación para P4 está en §3.3.
- **Variantes del modelo** (`--thinking`, `--effort`) y del orden (`--reversed`).

### 3.2 Diagnóstico: ¿examen, formato o modelo?

Weekly/software_engineer, 23 exámenes, 426 preguntas. Los números salen de §4. Las variantes son acumulativas: cada fila agrega algo a la anterior.

| Error (stub, sin thinking) | Evidencia | Causa | Arreglo probado | Efecto |
| --- | --- | --- | --- | --- |
| "unknown" en gustos que están en las notas | Los 12 están en la **pregunta 1**: 11/15 en posición 1 contra 34/34 en otras posiciones. En monthly, 42/51 contra 100/105. Con el examen invertido, preference da 80/80 y la pregunta que queda primera (total de pasos) cae a 6/21. | **Formato** del prompt. El error sigue a la posición, no a la pregunta. | Thinking adaptativo (51/51 en primera posición en monthly). P3a informa que su bloque `<answers>` también lo elimina. | preference: 95,0 % → 100 % |
| "unknown" en "¿está en la lista?" sobre algo que no está | todo `never_existed` 0/23, calendar `never_existed` 0/23, todo `recent_change` 0/9, content `never_existed` 11/22. El prompt no dice que las notas son completas. | **Formato.** P2 decidió que en listas cerradas lo correcto es "no". | `closed` | todo 47,5 → 80,3 %, calendar 50,0 → 73,9 %, content 62,3 → 77,9 % (sin thinking). Con thinking: 65,6 / 65,2 / 87,0 % → 100 / 100 / 100 %. |
| Totales de gastos y pasos mal sumados | Expense `aggregate` 3/23. El modelo enumera bien los montos y suma mal (ejemplo de §1). 5 `unparseable` porque escribe la cuenta en la línea de respuesta, y en 2 de ellos el total era correcto. | **Modelo** (aritmética sin thinking) y **formato** (dónde escribe la cuenta). | Thinking adaptativo; `totals` | Sin thinking, `totals`: expense 68,0 → 82,7 %, steps 83,6 → 95,1 %. Con thinking, sin `totals`: 98,7 % y 98,4 %. |
| Metas: "unknown" o el valor de otra meta | `goal \| dinner \| {'value': 210}` no dice qué es. Con thinking y `closed` el modelo se vuelve conservador: 9 "unknown" sobre 26. Sin thinking contestó 210 para el lunch (s084). | **Formato.** El stub pierde lo que dijo el usuario ("$210 per week on dinner"). La pregunta sí lo dice. | `goals` | goal 65,4 → 100 % (con thinking y `closed`) |
| Content: "no" con el ítem en las notas | 5 casos. El stub nombra el documento `meeting_notes_2` y la pregunta lo nombra por su título; el título está en otra línea. | **Modelo** (indirección), agravado por el **formato**. | Thinking adaptativo | 0 casos en weekly; 1 en monthly (startup_founder s119) |
| Total de pasos: "unknown" | Con thinking: 17 de 32 `missing` cuando la última fecha del rango no tiene registro de pasos, contra 1 de 26 cuando sí lo tiene (monthly, 3 personas). El modelo lo dice: "the notes have no step entry for 2025-06-07, so this covers 2025-06-01 to 2025-06-06 only". | **Examen**: el rango termina en la fecha de la sesión, que todavía puede no tener pasos. La verdad (la suma de lo registrado) es defendible, pero la pregunta invita a abstenerse. | `logs` | Monthly, steps 86,3 → 100 % |

**No encontré errores en la verdad.** Los 24 gastos de la s161 suman 258,23. Todos los tipos de gasto son de comida (coffee, dinner, lunch, breakfast y grocery en las 10 personas monthly), así que "food expenses" no es ambiguo. El test `test_running_totals_match_every_weekly_aggregate_of_the_exam` recalcula los 44 totales del examen weekly desde las notas.

### 3.3 Propuestas

Para P3 y P3a (formato de las notas y del prompt):

1. **Thinking adaptativo con effort `low` como configuración oficial.** P3 ya lo decidió. En el stub, el techo weekly pasa de 70,7 % a 82,4 %, y el costo de 23 exámenes de $0,0127 a $0,0222 (≈ +75 %).
   - **Hay que subir `max_tokens`.** `answer_exam` usa 60·n+200, y el thinking cuenta dentro de ese tope. Se cortaron 6 de 69 respuestas en el stub con thinking (weekly) y 3 de 67 en monthly. Las respuestas que siguen al corte salen `missing`, así que es un error de formato que parece memoria.
   - **El costo de subirlo es bajo.** Solo se pagan los tokens que se usan. Lo que crece es la reserva de peor caso del chequeo del tope.
2. **Decir que las listas son cerradas** (`closed`), en las notas o en el prompt. Es el cambio de formato que más pesa: hasta +35 pp en todo y calendar.
3. **Que la nota de una meta diga qué es**, como lo dijo el usuario: "weekly dinner budget: $210", "daily steps: 8000".
4. **Que un día sin registro cuente como cero** (`logs`). Arregla el problema de examen sin tocar `exam/`. **Para P2 (vía P3):** la alternativa es redactar la pregunta como "logged so far" o terminar el rango en el último día con registro.

**Totales precalculados.** P3 pidió reportar el techo con y sin totales (§4.1):

| Corrida | Sin totales | Con totales |
| --- | --: | --: |
| weekly, con thinking, `closed goals` | 99,5 % | 98,6 % |
| monthly cada 8, con thinking, `closed goals` | 97,0 % | 98,9 % (expense 94,9 → 100 %, steps 86,3 → 93,1 %) |
| weekly, sin thinking | 70,7 % | 75,6 % |

- **Recomendación: no exigírselos al dream.** Con thinking y `logs`, sin totales, el techo monthly es 99,1 %, y lo que queda en expense es 5 errores de 118 preguntas (95,8 %).
- **Por qué no:** los totales suman trabajo de mantenimiento a P4 y una fuente de error nueva. Un total sin actualizar sale `stale` aunque los ítems estén bien.
- **Si P3 decide que sí**, la especificación que probé (`weekly_totals`) es:
  - **Qué:** total de gastos y total de pasos.
  - **Rango:** semanas de 7 días contadas desde la fecha de la primera conversación de la persona, igual que las preguntas `aggregate`. No son semanas de domingo a sábado.
  - **Forma:** una línea por cada fecha con registros, con el acumulado desde el inicio de su semana. Por ejemplo, `expense total | from 2025-06-01 to 2025-06-04 | 116.59`.
  - **Actualización:** cuando llega un gasto o un registro de pasos con fecha d, se suma a la línea de d (creándola si no existe) y a las de todas las fechas posteriores de la misma semana.
  - **Ojo con la versión ingenua.** Un único total por semana ("week from 06-01 to 06-07") no sirvió: con la pregunta "from 06-01 to 06-04", el modelo recalcula a mano y se equivoca. Weekly sin thinking, expense: 68,0 % → 69,3 %.

## 4. Prueba

Todas las corridas usan `claude-haiku-5-5`, temperatura por omisión del modelo, `effort low` y el presupuesto `p3b`. Las tablas son salida real del CLI; todas se pueden regenerar gratis desde `results/raw/`.

### 4.1 Techo: weekly/software_engineer, 23 exámenes, 426 preguntas

Cada fila salió de `uv run python -m answering.bounds weekly software_engineer --measure ceiling <variante>` (`all` = precisión total). El costo es el de la medición completa, contando lo que se leyó del caché.

| Variante | correct | stale | missing | invented | unparseable | Precisión | Costo | Cortes en `max_tokens` |
| --- | --: | --: | --: | --: | --: | --: | --: | --: |
| stub (oficial hoy) | 301 | 5 | 89 | 26 | 5 | **70,7 %** | $0,0127 | 0 |
| `--reversed` | 302 | 12 | 76 | 11 | 25 | 70,9 % | $0,0140 | 0 |
| `--notes-add closed` | 339 | 9 | 45 | 25 | 8 | 79,6 % | $0,0130 | 0 |
| `--notes-add totals` | 322 | 6 | 94 | 4 | 0 | 75,6 % | $0,0129 | 0 |
| `--notes-add closed totals` | 353 | 9 | 61 | 2 | 1 | 82,9 % | $0,0130 | 0 |
| `--thinking adaptive` | 351 | 0 | 69 | 6 | 0 | **82,4 %** | $0,0222 | 2 |
| `--thinking adaptive --notes-add closed` | 404 | 0 | 16 | 5 | 1 | 94,8 % | $0,0222 | 1 |
| `--thinking adaptive --notes-add closed totals` | 411 | 0 | 14 | 1 | 0 | 96,5 % | $0,0219 | 1 |
| `--thinking adaptive --notes-add closed goals` | 424 | 0 | 1 | 1 | 0 | **99,5 %** | $0,0204 | 0 |
| `--thinking adaptive --notes-add closed goals totals` | 420 | 0 | 5 | 1 | 0 | 98,6 % | $0,0210 | 0 |

La columna indulgente da 0 en todas las corridas. Con notas perfectas, un gusto borrado no está en las notas y el modelo nunca contesta "dislike". Esa columna va a importar recién con notas viejas (P4 y P5).

Stub, por dominio (`uv run python -m answering.bounds weekly software_engineer --errors`, primera corrida, $0,0420 por las 92 llamadas de techo, piso y ruido):

```
| domain | n | correct | stale | missing | invented | unparseable | lenient | accuracy | lenient accuracy |
| preference | 80 | 76 | 0 | 4 | 0 | 0 | 0 | 95.0% | 95.0% |
| todo | 61 | 29 | 0 | 32 | 0 | 0 | 0 | 47.5% | 47.5% |
| calendar | 46 | 23 | 0 | 23 | 0 | 0 | 0 | 50.0% | 50.0% |
| goal | 26 | 23 | 0 | 2 | 1 | 0 | 0 | 88.5% | 88.5% |
| content | 77 | 48 | 5 | 24 | 0 | 0 | 0 | 62.3% | 62.3% |
| expense | 75 | 51 | 0 | 4 | 17 | 3 | 0 | 68.0% | 68.0% |
| steps | 61 | 51 | 0 | 0 | 8 | 2 | 0 | 83.6% | 83.6% |
| all | 426 | 301 | 5 | 89 | 26 | 5 | 0 | 70.7% | 70.7% |
```

Por probe, lo que mueve el techo del stub: todo `never_existed` 0/23, `recent_change` 0/9; calendar `never_existed` 0/23; expense `aggregate` 3/23 (16 `invented`, 3 `unparseable`); steps `aggregate` 11/21.

### 4.2 Efecto de la primera pregunta

```
$ uv run python -m answering.bounds weekly software_engineer --measure ceiling             # stub
| preference | 11 / 15 | 34 / 34 |          (primera: correct / n | otras: correct / n)
$ uv run python -m answering.bounds weekly software_engineer --measure ceiling --reversed  # $0.0140
| preference | 0 / 0 | 49 / 49 |
| steps | 6 / 21 | 40 / 40 |
```

Con el examen invertido, la pregunta que queda primera es el total de pasos, y 12 de esas respuestas salen `unparseable` porque escriben la cuenta en la línea. En monthly (stub), preference da 42/51 en primera posición y 100/105 en las otras. Con thinking, 51/51 en primera posición.

### 4.3 Piso y ruido

Weekly/software_engineer (23 exámenes, 3 repeticiones del techo):

| Configuración | Piso | Respuestas que cambian (de 426) | Cambian de clase | Rango de precisión total | Mayor rango por dominio | Costo (techo, piso y ruido) |
| --- | --: | --: | --: | --: | --- | --: |
| stub, sin thinking | 7,3 % | 47 | 24 | 1,2 pp | steps 6,6 pp | $0,0420 pagado |
| stub, thinking adaptive | 7,3 % | 85 | 85 | 1,9 pp | goal 19,2 pp | $0,0705 |
| thinking adaptive, `closed goals` | 26,5 % | 11 | 11 | 1,2 pp | steps 4,9 pp | $0,0686 |

Monthly, 3 personas (academic_researcher, software_engineer, startup_founder), 1 de cada 4 exámenes (67 exámenes, 1.374 preguntas):

| Configuración | Techo | Piso | Respuestas que cambian | Rango total | Mayor rango por dominio | Costo |
| --- | --: | --: | --: | --: | --- | --: |
| stub, sin thinking | 72,8 % | 6,3 % | 157 de 1.374 (103 de clase) | 0,8 pp | content 3,3 pp | $0,3450 (268 llamadas) |
| thinking adaptive, `closed goals` | 97,5 % | 24,7 % | 6 de 248 (software_engineer, cada 8: 12 exámenes) | 0,8 pp | steps 8,3 pp (n = 36) | $0,1587 (techo y piso) + $0,0457 (ruido) |

Monthly, stub sin thinking, por dominio (techo):

```
| preference | 243 | 229 | 0 | 14 | 0 | 0 | 0 | 94.2% | 94.2% |
| todo | 222 | 130 | 0 | 92 | 0 | 0 | 0 | 58.6% | 58.6% |
| calendar | 145 | 79 | 0 | 66 | 0 | 0 | 0 | 54.5% | 54.5% |
| goal | 94 | 89 | 0 | 5 | 0 | 0 | 0 | 94.7% | 94.7% |
| content | 240 | 158 | 9 | 73 | 0 | 0 | 0 | 65.8% | 65.8% |
| expense | 231 | 155 | 2 | 6 | 57 | 11 | 0 | 67.1% | 67.1% |
| steps | 199 | 160 | 0 | 3 | 24 | 12 | 0 | 80.4% | 80.4% |
```

Monthly, cada 8 (34 exámenes, 697 preguntas), techo con thinking:

| Notas | preference | todo | calendar | goal | content | expense | steps | Total | Costo |
| --- | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| `closed goals` | 100 | 100 | 100 | 100 | 99,2 | 94,9 | 86,3 | 97,0 % | $0,0680 |
| `closed goals totals` | 100 | 100 | 100 | 100 | 99,2 | 100 | 93,1 | 98,9 % | $0,0695 |
| `closed goals logs` | 100 | 100 | 100 | 100 | 99,2 | 95,8 | 100 | **99,1 %** | $0,0680 |

Errores que quedan con `closed goals logs` (`--errors`):

- 4 totales de gastos mal sumados, por ejemplo academic_researcher s455: 303,46 contra 379,87.
- 1 gasto suelto contestado "unknown".
- 1 content "no" sobre un entregable que está en las notas (startup_founder s119).

Cómo leer el ruido:

- **El ruido depende del formato.** Con thinking sobre el stub ambiguo, el modelo duda entre "unknown" y "no", y cambian 85 respuestas. Con notas que dicen qué significan, cambian 11 en weekly y 6 en monthly, todas en sumas.
- **Una corrida sola alcanza para el total.** La precisión total varía ≤ 1,2 pp entre repeticiones en todas las configuraciones. Una diferencia de 2 pp entre políticas está en el límite del ruido.
- **Los dominios piden más cuidado.** Expense y steps varían hasta 5–8 pp, y goal 19 pp con notas ambiguas. P7 debería comparar dominios con bootstrap o con repeticiones.

### 4.4 Costo

| Concepto | Costo real |
| --- | --: |
| Total gastado por P3b | **$1,0162** de $1,20 (libro `results/spend/p3b.jsonl`, 1.000 llamadas) |
| Costo por examen, weekly | stub $0,00055; thinking $0,00089–0,00097 |
| Costo por examen, monthly (≈ 12k tokens de entrada) | stub $0,00166; thinking con `closed goals` $0,0020 |
| Monthly completo por persona (≈ 88 exámenes), solo techo | ≈ $0,15 (stub) y ≈ $0,18 (thinking) |

La primera versión de la pasada en seco estimaba la entrada como bytes/4, pero estos prompts miden 2,6 bytes por token. Con bytes/4, la cota quedó por debajo del costo real en una corrida: $0,059 contra $0,068 en monthly cada 8 con `closed goals logs`. La versión final usa bytes/2,5. Recalculada sin caché, la cota da $0,0797, $0,5326 y $0,0976 para corridas que costaron $0,0680, $0,3450 y $0,0420: entre 1,2 y 2,3 veces el costo real. El tope duro sigue en `BudgetedClient`, que acota con 1 byte por token.

### 4.5 Tests

```
$ uv run pytest -q
.............................                                            [100%]
29 passed in 8.47s
```

`tests/test_bounds.py`:

- **Techo, piso y ruido.** Con un cliente falso sobre el examen real de la s7: el techo recibe las notas de `state_after(7)` (trail running sí, Bonobo todavía no), el piso recibe notas vacías, y el ruido reusa el techo como repetición 0, sin una cuarta llamada.
- **Totales.** Los totales acumulados de `weekly_totals` reproducen los 44 `aggregate` del examen weekly de software_engineer.

## 5. Opciones descartadas y por qué

| Opción | Por qué no |
| --- | --- |
| Editar `notes.py` o `answer.py` para probar el formato | Son de P3a. Las hipótesis se prueban agregando líneas a `render_notes` (`--notes-add`) o cambiando el orden de las preguntas (`--reversed`), sin tocarlos. |
| Un total único por semana ("week from 06-01 to 06-07") | La pregunta pide "from 06-01 to 06-04", y el modelo recalcula y se equivoca: expense 68,0 → 69,3 %. La versión acumulada por fecha da 82,7 %. |
| Exigir totales precalculados al dream | Con thinking, el arreglo de `logs` solo ya deja el techo monthly en 99,1 %. Los totales le agregan mantenimiento y errores propios a P4 (§3.3). |
| Medir el ruido con más de 3 repeticiones | Con 3, el rango total ya es ≤ 1,2 pp. El presupuesto rinde más en otras personas y variantes. |
| Monthly completo para todas las variantes | Monthly cuesta ≈ 12k tokens de entrada por examen. Muestreé 1 de cada 4 exámenes (y 1 de cada 8 para las variantes) para quedar bajo el tope. |
| Pedir respuesta y cuenta por separado en el prompt (contra los `unparseable`) | Es una decisión de prompt de P3a, que ya la resolvió con `<answers>`. Con thinking, la cuenta va al thinking y no aparece ningún `unparseable` (§4.1). |

## 6. Limitaciones y preguntas abiertas

- **Todo esto es con los stubs.** Cuando P3 integre el formato de P3a, tiene que repetir las mediciones con `--budget-name p3`. El costo esperado es de unos $0,07 en weekly/software_engineer con techo, piso y ruido, y de unos $0,16 por cada corrida de techo y piso con thinking en monthly, 3 personas, cada 4.
  - **Ojo con el caché.** `results/raw/` vive en este worktree y no está en git, así que en el worktree de P3 se paga de nuevo.
- **Muestra chica.** Weekly es 1 persona y monthly son 3 personas muestreadas. Los efectos grandes (`closed`, primera pregunta, `goals`, `logs`) son consistentes entre weekly y monthly. Las diferencias de 1–2 pp no.
- **El techo con `closed` asume notas completas.** Con notas viejas (P4 y P5), "no" sobre algo que el dream no anotó sale `stale`, y no `missing`. Es la clase correcta para un error de memoria, pero cambia la mezcla de clases que va a ver P7.
- **El piso depende del encabezado.** Con notas vacías y `closed`, el piso sube de 6–7 % a 25–27 %, porque "no" es correcto en `never_existed` y en las bajas. Si P3a pone la instrucción de lista cerrada en el prompt, ese es el piso real de una política que nunca soñó.
- **`max_tokens` de `answer_exam` con thinking.** Corta entre 1 y 3 respuestas de cada 23–67 exámenes, y las preguntas que siguen salen `missing`. Es de P3a o de P3.
- **El problema de examen del total de pasos** (rango que termina en una fecha sin registro) está mitigado por formato (`logs`). Si P2 prefiere corregirlo en el examen, hay que regenerar los prompts `aggregate`; eso no cambia los `question_id`.
- **No probé** effort `medium` ni otros valores de thinking. Con `low` el techo ya está en 99 %, y lo que queda son sumas.
