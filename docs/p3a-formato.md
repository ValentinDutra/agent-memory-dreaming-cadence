# P3a · Formato de las notas y del prompt de respuesta

**Resultado.** Las notas son Markdown con una sección por dominio y un hecho por línea. Todo se nombra como lo nombra el usuario: un documento por su título y un gasto por fecha y tipo. Los documentos guardan título, presupuesto e ítems de lista, sin la prosa larga. El prompt pide las respuestas dentro de `<answers>…</answers>`, una línea por pregunta. Lo que más sube el techo no es el formato de las notas: es que el modelo **piense antes de responder** (thinking adaptativo).

Techo con notas perfectas, weekly/software_engineer, 23 exámenes, 426 preguntas, Haiku 5.5:

| Configuración | Sin totales precalculados | Con totales precalculados |
| --- | --: | --: |
| Stub de P3 (sin thinking) | 69,2–70,2% (3 rep.) | — |
| Notas elegidas, sin thinking | 84,7–85,9% (3 rep.) | — |
| Notas elegidas, thinking adaptativo, effort `low` | 95,3–96,9% (3 rep.) | 97,7–98,4% (3 rep.) |
| Notas elegidas, thinking adaptativo, effort `medium` | **98,6%** (1 rep.) | **100%** (1 rep.) |

- En monthly (2 personas, 6 exámenes cada una, 260 preguntas), con thinking y effort `low`: 260/260 sin totales y 258/260 con totales.
- `unparseable` es 0 en todas las corridas con el bloque `<answers>`.
- La cuenta indulgente coincide con la estricta en todas las corridas: ninguna respuesta fue "dislike" después de un "like" borrado.
- Costo real total: **$0.7224** de $0.80, en 1.315 llamadas.

| Rol | Ruta |
| --- | --- |
| Notas elegidas | `answering/notes.py` (`render_notes`; `render_markdown` y `without_prose` son las piezas) |
| Prompt elegido | `answering/answer.py` (`answer_exam`, `parse_answers`) |
| Variantes comparadas | `answering/format_stub.py`, `format_json.py`, `format_line_answers.py`, `format_json_answers.py`, `format_work_answers.py`, `format_totals.py` |
| Comparación (CLI) | `answering/format_compare.py` |
| Tests | `tests/test_answer.py` (2, sin API) |

## 1. Problema

Con notas dadas, el modelo tiene que contestar un examen de unas 18 preguntas (weekly) o 21 (monthly) en una sola llamada. La respuesta tiene que poder corregirse con `exam.grading.grade`. Además, las notas tienen que ser algo que un dream (P4) pueda escribir leyendo conversaciones.

Ejemplo real: el stub, weekly/software_engineer, examen de la s147.

- **Claves internas.** El stub escribía `content | meeting_notes_2 / key_decisions / … | {'value': …}` y `expense | 147 | {…}`. Ninguna de esas claves (`meeting_notes_2`, `147`) aparece en las conversaciones ni en las preguntas. La pregunta nombra el documento por su título: "the user's meeting notes 'Accessibility Compliance Review for VR Navigation Module'".
- **Prompt.** No decía que las notas estaban completas, así que el modelo contestaba "unknown" sobre un pendiente que no figuraba.
- **Efecto de la primera pregunta** (también lo encontró P3b). Con el formato de salida `<n>: <respuesta>` sin nada antes, la pregunta 1 falla mucho más que el resto. Con Markdown, la pregunta 1 estuvo bien en 14 de 23 exámenes: el modelo contestó "unknown" sobre "deep house", que figuraba en las notas como "like".

## 2. Opciones investigadas

| Fuente | Qué dice (sección) | Qué tomé |
| --- | --- | --- |
| Memory tool de Anthropic, https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool | "How it works": la memoria es un directorio `/memories` de archivos de texto que Claude crea y edita (el ejemplo usa `.xml` y `.txt`). "Prompting guidance": *"keep its content up-to-date, coherent and organized"*. "Tool commands › view": la descripción de la herramienta trunca la vista de archivos de más de 16.000 caracteres. | Texto plano organizado, editable línea por línea con `str_replace`. Un hecho por línea permite cambiar un hecho sin reescribir el archivo. |
| `MEMORY.md` de Claude Code, https://code.claude.com/docs/en/memory | "Auto memory › How it works": se cargan las primeras 200 líneas o 25 KB de `MEMORY.md`; Claude mueve el detalle a archivos por tema. "Write effective instructions": *"group related instructions under markdown headers and bullets. Organized sections are easier for Claude to follow than dense paragraphs."* | Markdown con encabezados por dominio y viñetas. |
| Dreams de Managed Agents, https://platform.claude.com/docs/en/managed-agents/dreams | Introducción: un dream lee el memory store y las transcripciones y produce uno nuevo con *"duplicates merged, stale or contradicted entries replaced with the latest value"*. "Steer with instructions": las `instructions` fijan foco, qué preservar y *"output conventions you want applied across the store"*. | El formato es una convención de salida que el dream puede seguir. Cada hecho tiene que tener un valor actual reemplazable (like/dislike, fecha, monto), no una narración. |
| Letta, memory blocks, https://docs.letta.com/guides/agents/memory-blocks | "What are memory blocks?": los bloques se anteponen al prompt en un formato tipo XML (`<memory_blocks><human>…<value>…</value>…`), con `label`, `description`, `value` (texto libre) y `limit` en caracteres. "The importance of the description field": la descripción es lo que usa el agente para saber cómo leer y escribir el bloque. | Las notas van entre etiquetas (`<notes>`), y un encabezado describe cada sección. El bloque de Letta es texto libre, sin esquema. |
| Structured outputs, https://platform.claude.com/docs/en/build-with-claude/structured-outputs | Haiku 5.5 está en la lista de modelos soportados. Se activa con `output_config.format` (`type: "json_schema"`). "Schema complexity limits": como máximo 24 parámetros opcionales y 16 uniones. "Invalid outputs": un `enum` puede salir con otra capitalización. | No lo usé: `client.py` (de P3) arma `output_config={"effort": …}` y no deja pasar `format`. Con el bloque `<answers>` el `unparseable` ya es 0, así que no hace falta pedirle el cambio a P3. |

## 3. Análisis y elección

### 3.1 Notas: Markdown por dominio, sin prosa

Ejemplo real (weekly/software_engineer después de la s147, recortado):

```markdown
## Likes and dislikes
- genetic engineering (books / topics): dislike
- deep house (music / genres): like

## To-do list
- Optimize database queries (work tasks)

## Calendar
- Sprint planning meeting: 2025-06-04 (work meetings)
- Mechanic visit: 2025-06-08 (personal appointments)

## Goals
- Weekly budget for coffee expenses: $30
- Daily step goal: 8000 steps

## Documents

### Project proposal: Real-Time Order Orchestration Engine with Intelligent Routing
- budget: $575000
- deliverables:
  - Automated CI/CD pipeline with testing and deployment workflows

## Food expenses
- 2025-06-01 breakfast: $9.15

## Steps
- 2025-06-01: 14096 steps
```

Decisiones, cada una con su medición en §4:

- **Markdown frente a JSON.** Sin thinking empatan: 84,7–85,9% contra 84,5–85,2% con el mismo prompt. Con thinking en monthly, Markdown sin prosa da 259/260 y JSON (con prosa) da 256/260. Elegí Markdown por las fuentes: Claude Code lo recomienda, y el memory tool edita con `str_replace` por línea. Un hecho por línea se corrige sin reescribir el documento ni romper comas y llaves. Además, JSON pesa 6% más que Markdown con el mismo contenido, y 34–35% más que las notas elegidas (§4.3).
- **Sin claves internas.** Un gasto se identifica por fecha y tipo; un documento, por su tipo y su título completo; las preferencias, por ítem con su categoría. El stub con el prompt nuevo (79,8–81,2%) queda 4–5 puntos debajo de Markdown con el mismo prompt (84,7–85,2% sin prosa). La pérdida viene de content: 55–61/77 contra 62/77, porque el stub nombra los documentos `meeting_notes_2`.
- **Prosa larga afuera.** `project_description`, `timeline`, `call_to_action`, `project_lead`, `platform`… Nunca se preguntan y nunca cambian (P2a §3.2). Medido:
  - Weekly: −7% de tokens de entrada (3.111 → 2.885 por examen).
  - Monthly: −14% y −19% (8.232 → 7.073 y 8.988 → 7.278).
  - Sin thinking, la precisión sube de 81,9–83,8% a 84,7–85,9%. Con thinking no cambia más allá del ruido.
  - Lo que queda: el título (identifica el documento), el presupuesto y los ítems de lista, que son lo que cambia y lo que se pregunta.
- **Listas cerradas vacías se escriben.** Si no hay pendientes o eventos, la sección dice `- (none)`; si no, el modelo no distingue "lista vacía" de "esto no lo anoto".
  - Antes del arreglo, los 5 `missing` de calendario que se repetían (s14, s21, s28, s35, s42) eran justo los exámenes sin sección Calendar.
  - Con el arreglo, calendar pasó de 42–44/46 a 45/46 en las 3 repeticiones, y las preguntas que no son totales quedaron en 377/382 en las 3.
- **`render_notes({})` devuelve `""`**, como pide el contrato para el piso.

### 3.2 Prompt de respuesta

```
system: You are the user's personal assistant, starting a new session. Everything you know about the user is in your notes.
        The notes are complete and up to date: they were rewritten from all your past conversations with the user.
user:   <notes>…</notes>
        Answer each question using only the notes.
        - To-do list, calendar, and documents are complete lists: if a task, event, or document item is not in the notes,
          it is not there, so answer "no", not "unknown".
        - Likes and dislikes: answer like or dislike only as the notes record it; if the notes record no opinion about it, answer "unknown".
        - A number or date the notes do not contain: answer "unknown".
        - Dates as YYYY-MM-DD. Numbers in digits only, without currency signs, units, or words (for example 1234.5).
        - A total: add up every matching entry in the notes.
        Reply with the answers inside <answers> tags, exactly one line per question, "<number>: <answer>", with only the answer after the colon.
        <questions>1. … 2. …</questions>
```

- **Listas cerradas.** La regla "complete lists" corrige el "unknown" en todo y calendar: con las mismas notas del stub, todo pasa de 29/61 a 51–53/61 y calendar de 23/46 a 35–36/46.
- **Gustos.** La regla repite la redacción de P2: "unknown" es "sin opinión actual".
- **Formato de los valores.** Pide ISO y dígitos, porque la normalización de P2 no acepta "06/11/2025" ni números en palabras (P2 §6).
- **El bloque `<answers>`** resuelve dos problemas:
  - **Efecto de la primera pregunta.** Con Markdown, la pregunta 1 queda bien en 14/23 con líneas sueltas y en 22/23 dentro del bloque. Con thinking, en 23/23 en todas las corridas.
  - **Separa el razonamiento.** `parse_answers` lee solo el último bloque `<answers>`, así que una cuenta escrita antes ("9.15 + 3.41 …", "13.83") nunca se lee como respuesta (test con un caso real). P3b había visto 5 `unparseable` del stub por cuentas escritas en la línea de respuesta. Con el bloque: 0 `unparseable` en las 51 corridas con `<answers>`.
- **Una llamada por examen.** `max_tokens` es 15 por pregunta + 200, más 4.000 si el cliente tiene thinking. La salida más larga observada con thinking fue de 1.335 tokens, y ninguna respuesta terminó por `max_tokens`.

### 3.3 Thinking: recomendación para P3

Thinking es una propiedad del `BudgetedClient`, no de `answer_exam`. P3 ya decidió poner thinking adaptativo por omisión en `client.py`. Los números indican además **effort `medium`**:

| weekly/software_engineer, notas elegidas | correctas | sin las preguntas de totales | tokens de salida por examen | costo por examen |
| --- | --: | --: | --: | --: |
| sin thinking (`block`, effort low) | 361–366/426 | — | 114–125 | $0.00035 |
| `<work>` visible, sin thinking | 407–409/426 | — | 702–712 | $0.00065 |
| thinking adaptativo, effort `low` | 406–413/426 | 377/382 (las 3 rep.) | 552–571 | $0.00058 |
| thinking adaptativo, effort `medium` | 420/426 | 382/382 | 658 | $0.00062 |

- **Con effort `low`, el thinking adaptativo no piensa en 18 de 69 exámenes** (salida de menos de 300 tokens). Los errores que se repiten caen ahí. Ejemplos:
  - s084: 140 tokens de salida. "Configure development environment", "Plan weekend activities" y "1:1 with tech lead" salen "unknown" en lugar de "no".
  - s035: 96 tokens. "virtual reality" y la meta de cena de $210 salen "unknown", aunque las dos están en las notas.
- **Con `medium`, solo 1 de 23 exámenes salió sin pensar.** Lo único que queda mal son 6 totales de gastos errados por 1 centavo (el análisis de las sumas es de P3b).
- **Pensar mejora todo, no solo las sumas.** Sin thinking, las preguntas que no son totales también fallan: con las mismas notas sin prosa, content 64–66/77 y todo 54–56/61. Con thinking `medium`: 77/77 y 61/61.

### 3.4 Totales semanales precalculados: propuesta para P4

P3 pidió que, si se proponen, quede escrito qué son. **Propuesta:**

- **Qué totales.** El total de gastos de comida (en dólares) y el total de pasos de cada semana.
- **Rango.** Semanas de **domingo a sábado**. Los tres períodos de Memora empiezan el domingo 2025-06-01 (verificado en las 30 personas de weekly y monthly), así que son las mismas semanas por las que pregunta el examen ("dated from 2025-06-01 to 2025-06-05").
- **Forma.** Una línea por semana, al final de las notas:
  ```markdown
  ## Weekly totals (Sunday to Saturday)
  - Week 2025-06-01 to 2025-06-07 (so far): food expenses $258.23, 46312 steps
  ```
- **Cómo se actualizan.** Cada gasto o registro de pasos nuevo se suma al total de la semana en la que cae su fecha.
  - En Memora los gastos y pasos solo se agregan: nunca se editan ni se borran (P1 §4: 0 viejos), así que nunca hay que restar.
  - El total es "so far": la pregunta termina en la fecha de hoy y no hay registros con fechas futuras.
- **Efecto medido:**

  | Configuración | Gastos sin totales | Gastos con totales | Total sin totales | Total con totales |
  | --- | --: | --: | --: | --: |
  | weekly, thinking `low` | 62–67/75 | 72–74/75 | 406–413/426 | 416–419/426 |
  | weekly, thinking `medium` | 69/75 | 75/75 | 420/426 | 426/426 |
  | monthly, thinking `low` | 43/43 | 42/43 | 260/260 | 258/260 |

- **Sin thinking, los totales casi no sirven si el prompt pide hacer la cuenta.** Con `<work>` sin thinking, el modelo vuelve a sumar los ítems aunque el total esté en las notas: gastos 64/75 con totales contra 60–63/75 sin ellos. Con thinking, el modelo sí lee el total.
- **Decisión pendiente (P3/P4).** Si el dream de P4 mantiene los totales, se usa `answering/format_totals.render_notes`, que agrega la sección a `notes.render_notes`. Hoy `notes.py` queda **sin** totales.

## 4. Prueba

Notas perfectas (`render_notes(timeline.state_after(N))`), el mismo subconjunto para todos los formatos:

- **Weekly:** software_engineer, sus 23 exámenes (s7 a s161), 426 preguntas.
- **Monthly:** software_engineer y business_executive, exámenes s98, s196, s294, s392, s490 y s588 (130 preguntas por persona).

Antes de cada corrida estimé el costo con `--estimate`, que suma la cota de peor caso del cliente (bytes del prompt + `max_tokens`). El costo real fue entre un tercio y un quinto de esa cota. Todas las salidas se regeneran gratis desde `results/raw/p3a/` con los mismos comandos: verifiqué "0 paid now" en todas las corridas de este informe después del último cambio de código.

```
$ uv run python -m answering.format_compare weekly software_engineer --formats stub+stub,stub+lines,markdown+lines,markdown_without_prose+lines,json+lines,markdown+json,markdown+block,markdown_without_prose+block,json+block,markdown_with_totals+block,markdown+work --repeats 0,1,2
$ uv run python -m answering.format_compare weekly software_engineer --formats markdown_without_prose+work,markdown_with_totals+work --repeats 0,1
$ uv run python -m answering.format_compare weekly software_engineer --formats markdown+block_thinking,markdown_with_totals+block_thinking
$ uv run python -m answering.format_compare weekly software_engineer --formats notes+block_thinking,notes_with_totals+block_thinking --repeats 0,1,2
$ uv run python -m answering.format_compare weekly software_engineer --formats notes+block_thinking_medium,notes_with_totals+block_thinking_medium
$ uv run python -m answering.format_compare monthly software_engineer,business_executive --formats markdown+block,markdown+block_thinking,markdown_without_prose+block_thinking,markdown_with_totals+block_thinking,json+block_thinking,notes+block_thinking,notes_with_totals+block_thinking --sessions 98,196,294,392,490,588
```

Los nombres son `<notas>+<respuesta>`:

- **Notas:**
  - `stub`: el stub de P3.
  - `markdown`: con prosa.
  - `markdown_without_prose`.
  - `json`: con prosa.
  - `*_with_totals`: con totales semanales.
  - `notes`: la versión final, sin prosa y con las listas vacías escritas.
- **Respuesta:**
  - `stub`: el prompt del stub.
  - `lines`: las reglas nuevas, líneas sueltas.
  - `json`: las reglas nuevas, objeto JSON en texto.
  - `block`: las reglas nuevas dentro de `<answers>`, sin thinking.
  - `work`: `<work>` visible y después `<answers>`.
  - `block_thinking`: thinking adaptativo, effort `low`.
  - `block_thinking_medium`: thinking adaptativo, effort `medium`.

### 4.1 Weekly, software_engineer (426 preguntas por repetición)

Salida real, una línea por repetición (`correct`/426; entre paréntesis, la primera pregunta bien de 23):

| Configuración | rep. 0 | rep. 1 | rep. 2 | stale / missing / invented / unparseable (rep. 0) | tokens entrada / salida por examen |
| --- | --: | --: | --: | --- | --- |
| stub+stub | 295 (20) | 299 | 298 | 5 / 88 / 31 / 7 | 4.868 / 126–148 |
| stub+lines | 340 (19) | 346 | 340 | 5 / 42 / 38 / 1 | 5.105 / 105–128 |
| markdown+lines | 346 (14) | 350 | 352 | 11 / 31 / 38 / 0 | 3.111 / 104–118 |
| markdown_without_prose+lines | 361 (18) | 363 | 353 | 9 / 18 / 38 / 0 | 2.885 / 103–110 |
| json+lines | 359 (20) | 357 | 357 | 12 / 22 / 33 / 0 | 3.234 / 104–110 |
| markdown+json | 358 (21) | 357 | 358 | 11 / 35 / 22 / 0 | 3.130 / 137 |
| markdown+block | 355 (22) | 357 | 349 | 10 / 27 / 34 / 0 | 3.127 / 120–122 |
| markdown_without_prose+block | 361 (22) | 366 | 361 | 7 / 26 / 32 / 0 | 2.901 / 114–125 |
| json+block | 360 (22) | 362 | 363 | 6 / 29 / 31 / 0 | 3.250 / 115 |
| markdown_with_totals+block | 385 (21) | 389 | 383 | 3 / 27 / 11 / 0 | 3.186 / 114–115 |
| markdown+work | 411 (23) | 414 | 411 | 1 / 0 / 14 / 0 | 3.157 / 731–748 |
| markdown_without_prose+work | 409 (23) | 407 | — | 1 / 3 / 13 / 0 | 2.931 / 702–712 |
| markdown_with_totals+work | 411 (23) | 411 | — | 1 / 3 / 11 / 0 | 3.216 / 695–713 |
| markdown+block_thinking | 415 (23) | — | — | 1 / 1 / 9 / 0 | 3.128 / 602 |
| markdown_with_totals+block_thinking | 418 (23) | — | — | 2 / 5 / 1 / 0 | 3.187 / 628 |
| markdown_without_prose+block_thinking | 415 (23) | 404 | 412 | 0 / 3 / 8 / 0 | 2.902 / 538–590 |
| markdown_without_prose_with_totals+block_thinking | 414 (23) | 416 | 415 | 1 / 7 / 4 / 0 | 2.960 / 646–655 |
| **notes+block_thinking** | 412 (23) | 413 | 406 | 0 / 5 / 9 / 0 | 2.907 / 552–571 |
| **notes_with_totals+block_thinking** | 418 (23) | 416 | 419 | 1 / 5 / 2 / 0 | 2.966 / 633–644 |
| **notes+block_thinking_medium** | 420 (23) | — | — | 0 / 0 / 6 / 0 | 2.907 / 658 |
| **notes_with_totals+block_thinking_medium** | 426 (23) | — | — | 0 / 0 / 0 / 0 | 2.966 / 761 |

Por dominio, rep. 0 (correctas / preguntas):

| Configuración | preference /80 | todo /61 | calendar /46 | goal /26 | content /77 | expense /75 | steps /61 |
| --- | --: | --: | --: | --: | --: | --: | --: |
| stub+stub | 77 | 29 | 23 | 24 | 46 | 50 | 46 |
| stub+lines | 76 | 51 | 35 | 23 | 59 | 49 | 47 |
| markdown_without_prose+block | 76 | 56 | 38 | 25 | 64 | 53 | 49 |
| json+block | 79 | 54 | 39 | 26 | 58 | 55 | 49 |
| markdown+work | 80 | 61 | 46 | 26 | 76 | 61 | 61 |
| notes+block_thinking | 79 | 59 | 45 | 26 | 76 | 66 | 61 |
| notes_with_totals+block_thinking | 79 | 59 | 45 | 25 | 76 | 73 | 61 |
| notes+block_thinking_medium | 80 | 61 | 46 | 26 | 77 | 69 | 61 |
| notes_with_totals+block_thinking_medium | 80 | 61 | 46 | 26 | 77 | 75 | 61 |

Errores que quedan con la configuración elegida, `notes+block_thinking_medium` (salida real con `--errors`):

```
- invented    weekly/software_engineer/s063/expense/total expected '109.79' given '109.78'
- invented    weekly/software_engineer/s091/expense/total expected '134.82' given '134.81'
- invented    weekly/software_engineer/s119/expense/total expected '197.08' given '197.07'
- invented    weekly/software_engineer/s133/expense/total expected '243.16' given '243.15'
- invented    weekly/software_engineer/s147/expense/total expected '258.23' given '258.22'
- invented    weekly/software_engineer/s161/expense/total expected '258.23' given '258.22'
```

Los montos de Memora tienen como máximo 2 decimales (lo verifiqué en weekly y monthly), así que el error es de la suma. En una respuesta con `<work>` se ve dónde está: el modelo escribe "3.25 + 3.91 + 9.84 = 16.99" (es 17.00).

### 4.2 Monthly (2 personas × 6 exámenes, 130 preguntas por persona)

| Configuración | software_engineer | business_executive | tokens de entrada por examen (SE / BE) | salida (SE / BE) |
| --- | --: | --: | --- | --- |
| markdown+block | 115 | 115 | 8.231 / 8.987 | 131 / 131 |
| markdown+block_thinking | 130 | 127 | 8.232 / 8.988 | 796 / 773 |
| markdown_without_prose+block_thinking | 130 | 129 | 7.073 / 7.278 | 795 / 826 |
| markdown_with_totals+block_thinking | 130 | 128 | 8.357 / 9.113 | 775 / 717 |
| json+block_thinking | 128 | 128 | 8.554 / 9.262 | 777 / 866 |
| **notes+block_thinking** | **130** | **130** | 7.077 / 7.278 | 798 / 885 |
| **notes_with_totals+block_thinking** | **130** | **128** | 7.203 / 7.404 | 782 / 765 |

En monthly, sin thinking, las preguntas que no son totales dan 111/118 y 113/118. Con thinking, 117–118/118.

### 4.3 Tamaño de las notas perfectas al final del período (caracteres, las 10 personas)

| Formato | weekly mín / media / máx | monthly mín / media / máx |
| --- | --- | --- |
| stub | 15.226 / 16.639 / 19.941 | 52.504 / 58.495 / 66.693 |
| Markdown con prosa | 7.358 / 8.347 / 10.087 | 23.651 / 27.603 / 32.606 |
| JSON con prosa | 7.794 / 8.816 / 10.530 | 25.363 / 29.181 / 34.200 |
| **Notas elegidas** | **5.884 / 6.507 / 7.496** (132–159 líneas) | **19.857 / 21.694 / 24.178** (451–491 líneas) |

### 4.4 Costo

- **Real:** $0.7224, 1.315 llamadas, 4.757.483 tokens de entrada y 493.256 de salida (libro `results/spend/p3a.jsonl`).
- **Por examen, con la configuración elegida:** $0.00058 (`low`) o $0.00062 (`medium`) en weekly; unos $0.0011 en monthly.
- **Proyección a escala, techo de una política** (no lo corrí; es de P3b): 218 exámenes weekly ≈ $0.14 y 873 monthly ≈ $1.0. En monthly, el thinking agrega unos 750 tokens de salida (≈ $0.0004) a unos 7.100 de entrada (≈ $0.0007).

### 4.5 Tests

```
$ uv run pytest -q
.............................                                            [100%]
29 passed
```

`tests/test_answer.py` tiene 2 tests:

- Una respuesta real con `<work>` se parsea solo desde `<answers>`, en orden, con `None` para el número que falta.
- Las notas reales de la s14 escriben el calendario vacío como `- (none)`, contienen el título y el ítem de cada pregunta de content que vale, y no contienen claves internas.

## 5. Opciones descartadas y por qué

| Opción | Por qué no | Evidencia |
| --- | --- | --- |
| Stub `dominio \| clave \| valor` | Claves internas que el modelo nunca ve. Documentos sin título y metas sin decir que son presupuestos semanales. El doble de caracteres. | 69,2–70,2%; content 46/77 |
| JSON como notas | Empata con Markdown sin thinking. Pesa 6% más que Markdown con el mismo contenido, y una edición puntual de un dream rompe más fácil el archivo entero. | 84,5–85,2% contra 84,7–85,9%; monthly 256/260 contra 259–260/260 |
| Prosa larga de documentos | Nunca se pregunta ni cambia. Cuesta 7% (weekly) y 14–19% (monthly) de tokens de entrada, y sin thinking resta 2–3 puntos. | §3.1 |
| Respuestas en líneas sueltas | Efecto de la primera pregunta (14/23), y una cuenta escrita antes se lee como respuesta | §3.2 |
| Respuestas como objeto JSON en texto | Arregla la primera pregunta (21/23), pero contesta más "unknown" en listas cerradas: missing 33–35 contra 27–32 con el bloque y las mismas notas | markdown+json |
| Structured outputs (`output_config.format`) | Hay que cambiar `client.py` (de P3), y el bloque ya da 0 `unparseable` | §2 |
| `<work>` visible sin thinking | 95,5–97,2%, pero gasta más salida que el thinking (700–750 tokens contra 550–660) y fuerza a volver a sumar aunque las notas traigan el total | §3.3, §3.4 |
| Thinking adaptativo con effort `low` | No piensa en 26% de los exámenes, y ahí se concentran los errores que se repiten | §3.3 |
| Totales diarios o por tipo de gasto | No se probaron: la pregunta es por semana, y con thinking `medium` los totales semanales ya dan 75/75 (YAGNI) | — |

## 6. Limitaciones y preguntas abiertas

- **Subconjunto chico.**
  - Weekly es 1 persona; monthly son 2 personas con 6 exámenes cada una.
  - Effort `medium` se midió con 1 repetición y solo en weekly. Monthly con `medium` no se midió.
  - Entre repeticiones, la configuración `low` varió 7 preguntas de 426 (406–413). El ruido a escala y el techo completo son de P3b.
- **Thinking y effort los fija el cliente, no `answer_exam`.**
  - Recomiendo `{"type": "adaptive"}` con effort `medium`. P3 ya anunció adaptive con `low`; los números de §3.3 indican `medium`.
  - Si P3b mide con thinking desactivado, el techo baja a ~85% y mezcla errores de lectura con errores de memoria.
- **Totales precalculados: decisión de P3/P4** (§3.4). `notes.py` queda sin ellos. Si P4 los mantiene, se usa `format_totals.render_notes`.
- **El tamaño de monthly choca con límites de las fuentes.**
  - Las notas finales tienen 20–24 KB y 451–491 líneas: entran en los 25 KB de `MEMORY.md`, pero pasan su límite de 200 líneas y los 16.000 caracteres de `view` del memory tool.
  - Si P4 usa el memory tool, conviene un archivo por sección o leer por rangos. El texto que ve el examen es el mismo.
- **Las notas perfectas usan las etiquetas de Memora** ("music / genres", "work tasks"). Un dream va a escribir sus propias palabras; si se aparta mucho, P4 lo va a ver como error de memoria, no de formato.
- **Las preguntas truncan títulos largos a 12 palabras** ("…"). Con notas perfectas eso no causó errores con thinking: content 76–77/77.
- **Los resultados de la primera fase (stub, lines, json) usaron nombres de corrida viejos** (`stub_notes`, `markdown_json_answers`). Renombré los directorios en `results/raw/p3a/`; el libro de gasto conserva los nombres viejos en el campo `run`.
