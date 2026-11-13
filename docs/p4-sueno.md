# P4 · Un sueño

**Resultado.** Un sueño lee las notas y las transcripciones completas desde el último sueño, y devuelve **solo ediciones** (`<append section>` y `<replace><old><new>`, al estilo del `str_replace` del memory tool). El código las aplica y entrega notas completas en el formato de P3. Usa thinking adaptativo con effort `medium` y hace una llamada por sueño.

Con un sueño cada 7 sesiones sobre las sesiones 1–210 de 3 personas monthly (90 sueños, $0,132):

- **Hechos de las notas contra la verdad:** 96,2 % correctos.
- **Examen:** 95,7 %, con un techo de 100 % y un piso de 23,9–27,8 %.
- **Valores viejos o falsos sobre hechos vivos:** 0, salvo 24 fechas de gastos ("last night"), que son un artefacto de Memora (§3.3).
- **Líneas de más:** 20 de hechos que ya no valen, casi todas "Co-founder's birthday", que sigue en el calendario después de "I missed the co-founder's birthday event" (s93). Además, 29 gustos retirados que quedaron como `dislike`, todos `invented` solo en la cuenta estricta.
- **Notas:** miden 0,91–1,00 veces las perfectas. No hay mapa de Borges.
- **Degradación por editar muchas veces:** no aparece. Entre 2 y 3 hechos por cadena de 30 sueños se pierden después de haber estado bien.

| Medición, sueño elegido (P4a), cadencia 7 | weekly/software_engineer s1–161 | monthly/software_engineer s1–210 | monthly/academic_researcher s1–210 | monthly/startup_founder s1–210 |
| --- | --: | --: | --: | --: |
| Sueños / costo de los sueños | 23 / $0,0313 | 30 / $0,0434 | 30 / $0,0446 | 30 / $0,0438 |
| Hechos correctos (comparación línea por línea) | 98,5 % (1.410/1.431) | 98,4 % (2.412/2.451) | 93,6 % (2.805/2.997) | 97,0 % (2.857/2.944) |
| Examen | 93,4 % (398/426) | 96,6 % (542/561) | 97,3 % (577/593) | 93,3 % (542/581) |
| Examen sin totales de gastos | 96,3 % | 96,4 % | 97,2 % | 92,9 % |
| Techo / piso del examen | 98,4 % / 27,5 % | 100 % / 27,8 % | 100 % / 23,9 % | 100 % / 25,0 % |
| Perdidos después de estar bien | 0 | 2 | 3 | 2 |
| Caracteres de las notas / perfectas | 1,06 | 1,00 | 0,91 | 0,97 |

**Al integrar encontré y arreglé un bug del sueño de P4a.** El modelo a veces cierra `</edits>` y sigue escribiendo ediciones afuera, y el parser las tiraba. Lo vi en una sola respuesta, pero esa respuesta perdió 4 hechos para el resto de su cadena: el examen de monthly/academic_researcher daba **82,6 %** y pasó a **97,3 %**, y los hechos correctos de 87,9 % a 93,6 %. El arreglo solo cambia el parser, así que todo el caché sigue valiendo. Tiene un test con la respuesta real.

| Rol | Ruta |
| --- | --- |
| Tag | `p4` |
| Interfaz | `docs/p4-interfaz.md` |
| Informe de P4a (qué entra y qué sale) | `docs/p4a-entrada-y-salida.md` |
| Informe de P4b (calidad del sueño) | `docs/p4b-calidad-del-sueno.md` |
| Lo que lee un sueño, sin hoja de respuestas (P4) | `dreaming/transcripts.py` (`Session`, `load_transcripts`, `sessions_between`) |
| Sueño (P4a, con el arreglo de P4) | `dreaming/dream.py` (`dream`, `dream_with_failures`) |
| Variante descartada (reescritura, P4a) | `dreaming/dream_rewrite.py` |
| Medición de costo y variantes (P4a) | `dreaming/dream_compare.py` |
| Medición de calidad (P4b): comparación con la verdad y CLI | `dreaming/quality.py`, `dreaming/quality_run.py`, `dreaming/quality_calibrate.py` |
| Cliente con streaming (P3, cambiado por P4) | `answering/client.py` |
| Tests (8 de P4; 39 en total) | `tests/test_transcripts.py` (1), `tests/test_dream.py` (3), `tests/test_quality.py` (4) |

Uso para P5–P7:

```python
from answering.client import BudgetedClient
from dreaming.dream import dream
from dreaming.transcripts import load_transcripts, sessions_between

client = BudgetedClient("p5", limit_dollars=2.00)     # thinking adaptativo, effort medium: obligatorio
sessions = load_transcripts("monthly", "software_engineer")
notes, last_dream = "", 0
for now in (20, 40, 60):                              # una política de cadencia 20
    result = dream(notes, sessions_between(sessions, last_dream, now), client, run=f"p5/c20/monthly/software_engineer/{now}")
    notes, last_dream = result.notes, now             # result.cost, result.input_tokens, result.output_tokens
```

Para medir una política con los dos instrumentos:

```bash
uv run python -m dreaming.quality_run monthly <persona> chain --cadence 7 --through 210 \
  --dream dreaming.dream:dream --budget-name <nombre> --limit <dólares> --run-prefix <prefijo> --errors --dry-run
```

## 1. Problema

Las notas solo cambian cuando sueña el agente. Un sueño tiene que hacer tres cosas:

- **Corregir lo que cambió:** borrar, actualizar, agregar.
- **No inventar.**
- **No perder lo que estaba bien.**

Y tiene que hacerlo a un costo que P5 pueda multiplicar por cientos de sueños.

Ejemplo real, weekly/software_engineer. Así quedan las notas de la cadena de cadencia 7 (`--watch Bonobo "deep house"`):

| Sesión | Lo que dice el usuario | Notas del sueño en el examen siguiente |
| --: | --- | --- |
| 17 | le gusta Bonobo | s21 y s28: `- Bonobo (music / artists): like` |
| 30 | "I used to really like Bonobo, but I'm just not into his music anymore" | s35 en adelante: sin Bonobo (correcto: el gusto se borró) |
| 129 | no le gusta el deep house | — (el sueño de s127–133 lee las dos sesiones juntas) |
| 132 | ahora le gusta el deep house | s133 en adelante: `- Deep house music (music / genres): like` |

Las dos preguntas abiertas eran estas:

- **Qué lee y qué devuelve el sueño** (P4a).
- **Cómo se mide si las notas que deja son buenas, y cómo cambia eso con las sesiones que lee** (P4b).

## 2. Opciones investigadas

El detalle, con las secciones citadas, está en P4a §2 y P4b §2.

| Fuente | Qué se tomó |
| --- | --- |
| Dreams de Managed Agents, https://platform.claude.com/docs/en/managed-agents/dreams | El sueño de Anthropic es una síntesis que reescribe ("not an editor applied to the text of the store"), lee de 1 a 100 sesiones, y su costo crece lineal con las sesiones. Corrige "duplicates, contradictions, and stale entries" → las categorías `duplicate` y `stale` de la comparación. |
| Cookbook de dreaming, https://platform.claude.com/cookbook/managed-agents-cma-dreaming-with-a-dynamic-workflow | Leer la transcripción entera con hablantes; "add your entries with a targeted edit; don't rewrite the whole file" → editar en lugar de reescribir. |
| Memory tool, https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool | `str_replace`: texto exacto, único, `new_str` vacío borra → la semántica de `<replace>`. |
| Sleep-time compute, https://arxiv.org/abs/2504.13171 | Razonar más en el paso offline sube la precisión (§5.2) → thinking en el sueño. |
| Auto-Dreamer, https://arxiv.org/html/2605.20616 | Reescribir solo la región que cambia (§4.1). "Information missed by the writer cannot generally be recovered" (App. A). Barrido de k sesiones por consolidación (§5.4). |
| RecMem, https://aclanthology.org/2026.findings-acl.1619.pdf | Actualizar incremental cuesta 87 % menos tokens que Mem0 (Tabla 1); los lotes grandes omiten detalles (App. C.1). |
| Useful Memories Become Faulty, https://arxiv.org/html/2605.12978v2 | "In-place rewriting is the most damaging single step" (§6.4). Static vs. Stream (Fig. 2). Separar el *initial compression error* de lo que se pierde después. |
| The components of agent memory, https://www.anthropic.com/engineering/components-of-agent-memory | El mapa de Borges: notas más grandes que lo que resumen → el tamaño contra las notas perfectas. |

Ninguna fuente mide hechos uno por uno contra una verdad: todas miden utilidad en la tarea, a veces con un juez LLM. Acá la verdad existe (P1), y P4b la usa directamente.

## 3. Análisis y elección

### 3.1 El sueño (P4a)

| Pieza | Elección | Por qué (número) |
| --- | --- | --- |
| Entrada | Notas + todas las transcripciones, sin filtrar. Turnos `User` / `Assistant`; cada sesión con número, fecha y día de la semana. | Leer solo al usuario ahorra ≈ $0,000038 por sesión, y Taylor Swift (defecto 4 de P1) solo la nombra el asistente: sin sus turnos no se borra nunca. El día de la semana resuelve "next Tuesday". |
| Salida | Ediciones aplicadas por código; `dream()` devuelve las notas completas en el formato de P3. | Misma calidad que reescribir (93,7 contra 93,0 % weekly; 95,5 contra 96,1 % monthly s1–210) por 1,5–4,6× menos. En monthly, la reescritura cambió 4 líneas sin motivo. |
| Thinking | Adaptativo, effort `medium` (lo que `BudgetedClient` usa por omisión). | Sin thinking: 70,4 %. `low`: 91,5 %, y pierde pendientes. `high`: +1 pregunta por 15 % más. |
| Llamadas | Una por sueño. Sin reintentos. | En monthly hubo 1 edición fallida en 106 sueños, y fue inofensiva. |
| Regla anti-trampa | El sueño recibe `Session(session_id, date, turns=(speaker, message))`, armada desde una lista permitida. | `tests/test_transcripts.py` cambia `share_memory`, `operation`, `operation_details` y `session_type` en la s30 real y exige el mismo prompt. |

**Arreglo de P4 al integrar.** `parse_edits` leía solo el último bloque `<edits>…</edits>`. Ahora lee desde el último `<edits>` hasta el final de la respuesta. Caso real: el sueño de monthly/academic_researcher sobre s15–21 escribió un `<replace>` dentro del bloque, cerró `</edits>` y siguió con 4 `<append>` afuera. Se perdieron el presupuesto de almuerzo ($115), el primer registro de pasos (8.381), el primer gasto y un pendiente, y como cada sueño solo lee las sesiones nuevas, no se recuperaron nunca: 28 exámenes seguidos. Test: `tests/test_dream.py::test_edits_written_after_the_closing_tag_are_applied`.

### 3.2 Cómo se mide (P4b)

- **Dos instrumentos, siempre juntos:**
  - **El examen de P2/P3** sobre las notas del sueño.
  - **La comparación línea por línea** contra `state_after(N)` (`dreaming/quality.py`), que clasifica cada hecho en correcto, viejo, equivocado o faltante, y cada línea sobrante en vieja, inventada (cuenta estricta e indulgente), duplicada, sin emparejar con o sin apoyo en las transcripciones, o prosa.
- **Calibración:** sobre 3.951 notas perfectas de los 3 períodos, la comparación da 0 errores.
- **Cómo empareja:** por dominio y por las palabras del ítem, nunca por la etiqueta, porque el sueño escribe sus propias categorías y títulos de documento.
- **Por qué hacen falta las dos:**
  - La comparación es 4 veces más densa (456 hechos contra 122 preguntas en el mismo barrido) y ve pérdidas de documentos enteros que el examen casi no registra. Con el stub: 68,6 % de hechos y 90,6 % en el examen.
  - El examen ve paráfrasis que la comparación da por buenas (§3.3).
- **Ventanas desde notas perfectas:** P4b preguntó si se pueden usar para medir. Respuesta de P4: sí. El sueño sigue viendo solo `Session` y notas, y arrancar de notas perfectas aísla el error de un solo sueño. Es un instrumento, no una política.

### 3.3 Errores que no son del sueño

Hay tres clases de error que ningún sueño puede arreglar, porque la verdad de Memora no dice lo que dijo el usuario. P7 no tiene que cargárselos a la cadencia.

| Clase | Ejemplo real (verificado en la transcripción) | Peso en las cadenas monthly |
| --- | --- | --- |
| **Ítems de documento con el texto de Memora y no con el del usuario** | academic_researcher s44: el usuario dice "The attendees included Ms. Anya Sharma, Dr. Sofia Ramirez, Mr. David Kim, and Dr. Aris Thorne". Memora guarda "Ms. Anya Sharma (Data Scientist, Predictive Analytics Unit)". El sueño copia lo que oyó. | La mayor parte de los 182 hechos de content que faltan en academic_researcher (cada ítem cuenta una vez por examen). En el examen: 29 de los 74 errores de las 3 cadenas son `stale` en content. |
| **Fechas de gastos relativas** | startup_founder s112 (2025-06-06): "I spent $27.04 on dinner last night". El sueño anota 2025-06-05; Memora lo fecha el 06-06. | Los 24 `wrong` de expense de startup_founder: son 2 gastos por 12 exámenes. |
| **El que responde no reconoce una paráfrasis en una lista cerrada** | academic_researcher s28: la pregunta es si "Coordinate with research team" está en la lista. La nota dice "Coordinate with the research team this week" y la respuesta es "no". | Parte de los `stale` de todo: 3, 5 y 7 por persona. |

**Errores que sí son del sueño:**

- **Gustos dichos y nunca anotados:** startup_founder, Mark Hamill dislike (s159) y el flip del food scene (s200).
- **Un pendiente cumplido que no se borra:** "Fix critical bug" (s114; P4a).
- **"Ya no me gusta" anotado como dislike** cuando la verdad lo borra (Sandra Bullock; P4a). La regla del prompt es borrar, porque la verdad tiene 373 borrados contra 64 cambios a dislike.

## 4. Prueba

Todo corrió con `claude-haiku-5-5`, temperatura por omisión del modelo, thinking `{"type": "adaptive"}`, effort `medium` y presupuesto `p4`. Las respuestas crudas están en `results/raw/p4/`, y cada comando se vuelve a correr gratis desde ahí. Las salidas completas quedaron en `results/p4/*.txt` (ignorado por git; los comandos de abajo las regeneran).

```
$ uv run pytest -q
.......................................                                  [100%]
39 passed
```

### 4.1 Monthly, 3 personas: cadena de cadencia 7 hasta la s210

```
$ D="--dream dreaming.dream:dream --budget-name p4 --limit 0.80 --run-prefix p4/p4a"
$ uv run python -m dreaming.quality_run monthly <software_engineer|academic_researcher|startup_founder> chain --cadence 7 --through 210 $D --errors
```

La tabla del encabezado sale de estas corridas y de la weekly de §4.2. Por dominio:

| Dominio (suma de las 3 personas) | hechos correctos | faltantes | equivocados | examen: correct | examen: stale | examen: missing | examen: invented |
| --- | --: | --: | --: | --: | --: | --: | --: |
| preference | 503 | 17 | 0 | 295 | 1 | 11 | 2 |
| todo | 339 | 11 | 0 | 263 | 15 | 0 | 0 |
| calendar | 61 | 0 | 0 | 147 | 1 | 0 | 0 |
| goal | 278 | 0 | 0 | 124 | 0 | 0 | 0 |
| content | 5.040 | 266 | 0 | 301 | 29 | 1 | 0 |
| expense | 1.407 | 0 | 24 | 277 | 0 | 6 | 8 |
| steps | 446 | 0 | 0 | 254 | 0 | 0 | 0 |
| **total** | **8.074** | **294** | **24** | **1.661** | **46** | **18** | **10** |

Los 14 errores de expense en el examen son preguntas por un gasto (fecha y tipo), no totales; en monthly el error de 1 centavo no apareció.

- **9 de los 11 de startup_founder** son los dos gastos con fecha "last night" (§3.3).
- **Los otros 5** (3 de software_engineer y 2 de startup_founder) no los revisé.

Antes del arreglo del parser, academic_researcher daba:

```
| chain-c7 | 30 | 0.0438 | 2635/2997 (87.9%) | 362 | 0 | 0 | 0 (0) | 242 | 144 | 8 | 0.86 | 490/593 (82.6%) | 478/563 (84.9%) | 100.0% | 23.9% |
```

y después:

```
| chain-c7 | 30 | 0.0446 | 2805/2997 (93.6%) | 192 | 0 | 0 | 0 (0) | 242 | 190 | 3 | 0.91 | 577/593 (97.3%) | 547/563 (97.2%) | 100.0% | 23.9% |
```

Las cadenas de software_engineer y startup_founder no cambiaron: se volvieron a correr desde el caché y costaron $0,0000.

### 4.2 Casos de control y cadena weekly

```
$ uv run python -m dreaming.quality_run weekly software_engineer chain --cadence 7 --through 161 $D --watch Bonobo "deep house" --errors
| chain-c7 | 23 | 0.0313 | 1410/1431 (98.5%) | 21 | 0 | 17 | 0 (0) | 179 | 18 | 0 | 1.06 | 398/426 (93.4%) | 388/403 (96.3%) | 98.4% | 27.5% |
- chain-c7 N=28 'Bonobo': ['- Bonobo (music / artists): like']
- chain-c7 N=35 'Bonobo': absent
- chain-c7 N=126 'deep house': absent
- chain-c7 N=133 'deep house': ['- Deep house music (music / genres): like']
```

Las 17 líneas `+stale` son una sola: "Ann Leckie's earlier books: like", del s49 al s161. Los 13 `invented` del examen en expense son el error de 1 centavo del que responde, que decidí dejar.

### 4.3 ¿Se degrada al editar muchas veces? 56 sueños de 1 sesión, 8 de 7 y 1 sobre todo

```
$ uv run python -m dreaming.quality_run weekly software_engineer chain --cadence 1 7 --through 56 $D --watch Bonobo --errors
$ uv run python -m dreaming.quality_run weekly software_engineer chain --cadence 1 7 --through 56 --dream dreaming.dream:dream --budget-name p4 --limit 0.80 --run-prefix p4/p4a-r1 --errors
$ uv run python -m dreaming.quality_run weekly software_engineer single --at 7 14 21 28 35 42 49 56 $D --errors
```

| weekly/software_engineer s1–56, 8 exámenes | sueños | costo de los sueños r0 / r1 | hechos correctos r0 / r1 | examen sin totales r0 / r1 | stub de P4b: hechos r0 / r1 |
| --- | --: | --: | --: | --: | --: |
| Cadena c1 (56 sueños de 1 sesión) | 56 | $0,0222 / $0,0215 | 100 % / 99,6 % | 96,2 % / 94,3 % | 86,5 % / 92,8 % |
| Cadena c7 (8 sueños de 7 sesiones) | 8 | $0,0095 / $0,0093 | 100 % / 99,1 % | 96,2 % / 94,3 % | 99,1 % / **68,6 %** |
| Sueño único sobre 1..N | 1 por N | $0,0296 (los 8) | 99,6 % | 94,3 % | 100 % / 98,2 % |

- **Editando no hay degradación.** La gran varianza del stub, que perdía documentos enteros al reescribir, desaparece: r0 y r1 quedan a menos de 1 punto.
- **Sobre el mismo tramo, soñar cada sesión cuesta 2,3 veces más que cada 7** ($0,0222 contra $0,0095) **y no es mejor.** Con el stub la diferencia era 3,3–4,3 veces, porque cada sueño pagaba las notas enteras como salida.

### 4.4 Calidad y costo según cuántas sesiones lee un sueño (para P5)

Cada sueño arranca de las notas perfectas de N−k, así que sus errores son solo suyos.

```
$ uv run python -m dreaming.quality_run weekly software_engineer window --sizes 1 5 20 50 --at 56 77 98 119 133 161 $D --errors
$ uv run python -m dreaming.quality_run monthly software_engineer window --sizes 1 5 20 50 --at 210 420 609 $D --errors
```

| k (sesiones leídas) | weekly: faltantes (de 456) | weekly: examen sin totales (de 116) | weekly: $ por sueño | monthly: faltantes (de 772) | monthly: examen sin totales (de 59) | monthly: $ por sueño | stub: $ por sueño weekly / monthly |
| --: | --: | --: | --: | --: | --: | --: | --: |
| 1 | 1 (0,2 %) | 115 (99,1 %) | $0,00055 | 0 | 59 | $0,00097 | $0,0014 / $0,0041 |
| 5 | 1 (0,2 %) | 115 (99,1 %) | $0,00105 | 2 (0,3 %) | 59 | $0,00173 | $0,0018 / $0,0046 |
| 20 | 4 (0,9 %) | 112 (96,6 %) | $0,00308 | 5 (0,6 %) | 59 | $0,00373 | $0,0035 / $0,0061 |
| 50 | 10 (2,2 %) | 112 (96,6 %) | $0,00645 | 5 (0,6 %) | 57 (96,6 %) | $0,00763 | $0,0065 / $0,0092 |

El costo por sueño es el costo de los sueños de la tabla dividido por 6 (weekly) o por 3 (monthly).

- **Lo que se pierde crece con k, pero poco.** Un sueño que lee 50 sesiones deja afuera el 0,6–2,2 % de los hechos; uno de 1 sesión, el 0–0,2 %.
- **El costo crece casi lineal con k:** P4a lo modela como ≈ $0,00047 + $0,00004 por cada 1.000 caracteres de notas + $0,0001 por sesión leída.
- **Editar abarata sobre todo los sueños cortos con notas grandes:** monthly k=1 cuesta 4,2 veces menos que con el stub, y k=50, 1,2 veces menos.

### 4.5 Costo real

| Proceso | Tope | Gastado | Libro |
| --- | --: | --: | --- |
| P4a | $1,00 | $0,5669 | `results/spend/p4a.jsonl` (worktree de P4a) |
| P4b | $1,20 | $0,6345 | `results/spend/p4b.jsonl` (worktree de P4b) |
| P4 (integración) | $0,80 | $0,6886 | `results/spend/p4.jsonl` |
| **Total** | **$3,00** | **$1,8900** | |

Desglose de P4:

| Corrida | Pagado |
| --- | --: |
| Prueba del stub (s1–35) | $0,0038 |
| weekly/software_engineer chain c7 hasta s161 (incluye techo y piso de referencia) | $0,0715 |
| monthly chain c7 hasta s210: software_engineer / academic_researcher / startup_founder | $0,0978 / $0,1026 / $0,1022 |
| academic_researcher otra vez, tras el arreglo del parser | $0,0675 |
| weekly chain c1+c7 hasta s56 (r0; c7 ya estaba en caché) / r1 | $0,0266 / $0,0395 |
| weekly single s7…s56 | $0,0342 |
| weekly window k = 1/5/20/50 | $0,0842 |
| monthly window k = 1/5/20/50 | $0,0587 |

La estimación de `--dry-run` está calibrada con el stub y queda arriba de lo real: $0,1709 estimado contra $0,0978 pagado en la primera cadena monthly.

## 5. Opciones descartadas y por qué

| Opción | Por qué no | Dónde |
| --- | --- | --- |
| Reescribir las notas enteras (el stub, y el pipeline de Dreams) | Misma calidad. Paga las notas enteras como salida en cada sueño (1,5–4,6× más), y con el stub una cadena perdió 3 documentos para siempre (68,6 % de hechos). | P4a §4.1, P4b §4.4, §4.3 |
| Leer solo los turnos del usuario | Ahorra ≈ $0,000038 por sesión, y pierde los ítems viejos que solo nombra el asistente | P4a §3.1 |
| Filtrar la charla trivial | Hace falta un modelo o una heurística, y solo ahorra en la entrada, que es la parte barata | P4a §3.1 |
| Sin thinking, o con effort `low` | 70,4 % y 91,5 % en el examen | P4a §4.3 |
| Effort `high` | +1 pregunta, dentro del ruido, por 15 % más | P4a §4.3 |
| El memory tool real, con varios turnos | Reenvía las transcripciones en cada turno, y `BudgetedClient` no maneja herramientas | P4a §2 |
| Reintentar las ediciones fallidas | 1 en 106 sueños, inofensiva | P4a §3.2 |
| Juez LLM para comparar notas con la verdad | Cuesta en cada medición y agrega ruido. Un emparejador determinista calibrado da 0 errores en 3.951 notas perfectas. | P4b §5 |
| Medir solo con el examen | Con el stub no vio la pérdida de 3 documentos (68,6 % de hechos, 90,6 % en el examen) | P4b §4.7 |
| Sueño único sobre todo el período | Es el más estable, pero 161 sesiones weekly ya son ~109k tokens: pasa a precio largo. No es una política desplegable para monthly. | P4b §4.4 |
| Cambiar el prompt del sueño al integrar (p. ej. "nunca reemplaces `- (none)`, usá append") | Invalidaría todo el caché de P4a y P4b. El arreglo del parser alcanza para el error medido. | §3.1 |

## 6. Limitaciones y preguntas abiertas

- **Muestra.** Monthly: 3 personas hasta la s210 (un tercio del período), una sola corrida. Weekly: software_engineer con 2 corridas en s1–56. Quarterly no se midió. P5 necesita ≥ 2 repeticiones y ≥ 2 personas por política: las corridas r0/r1 de §4.3 difieren en hasta 1,9 puntos de examen.
- **Decisión abierta: ¿los errores del §3.3 se aceptan como límite medido?** Son ítems de documento con el texto de Memora, fechas de gastos relativas y paráfrasis en listas cerradas. Hay dos opciones:
  - **(a) Aceptarlos como límite medido, igual que el centavo de los totales.** P7 reporta siempre el examen y la comparación línea por línea, y compara cadencias por diferencia con la misma persona: estos errores dependen de cómo escribe el sueño, no de cuándo sueña. Ejemplo: "Ms. Anya Sharma" sale `missing` con cualquier cadencia.
  - **(b) Cambiar P2 para que no pregunte ítems de documento cuyo texto no aparece en la transcripción.** Hoy hay que medir cuántos son. Ejemplo: la pregunta "¿Ms. Anya Sharma (Data Scientist, Predictive Analytics Unit) es una de las attendees?" desaparece del examen.

  **Recomiendo (a):** no toca P2 y el sesgo es el mismo para todas las cadencias. Falta probar con números que es igual para todas; P7 puede verlo comparando por dominio.
- **El sueño no reporta las ediciones fallidas** por respetar el contrato; `dream_with_failures` sí. Con el arreglo del parser, las que quedan son `<replace>` ambiguos (p. ej. `- (none)` cuando pendientes y calendario están vacíos a la vez).
- **Las omisiones son permanentes.** Un sueño solo relee las sesiones nuevas: lo que no anota la primera vez no vuelve (Auto-Dreamer App. A; Mark Hamill en s159). Esto es justo lo que hace que la cadencia importe en P5: menos sueños son menos oportunidades de omitir, pero cada uno lee más (§4.4).
- **Las proyecciones de costo por cadencia** (P4a: monthly completo ≈ $0,61 con cadencia 1 y ≈ $0,07 con cadencia 50) son aritmética sobre el modelo de costo, no mediciones: las mide P6.
- **La estimación de `--dry-run` sigue calibrada con el stub.** Sobreestima entre 1,5 y 2 veces con el sueño de ediciones; para los topes es el lado seguro.
- **El caché no viaja entre worktrees.** Las respuestas de P4a y P4b están en sus worktrees; las de P4, en este (`results/raw/p4/`).
