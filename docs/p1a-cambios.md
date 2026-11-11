# P1a · Extraer los cambios

**Resultado.** `truth/changes.py` convierte cada sesión de Memora en hechos atómicos `(domain, key) → value` en 7 dominios. La extracción reproduce la evidencia de **598 de 600** preguntas de evaluación de Memora (weekly 149/150, monthly 150/150, quarterly 299/300). Las 2 que no coinciden son un defecto de Memora, no de la extracción (sección 6). En las 27.614 sesiones, ningún `update`/`remove` cae sobre un hecho inexistente o con otro valor. Además, reaplicando los hechos se reconstruye exactamente el documento que Memora guarda en cada sesión de contenido largo.

- Código: `truth/changes.py` (extracción), `truth/evidence.py` (validación contra Memora), `tests/test_changes.py`.
- Reproducir: `uv run pytest -q` y `uv run python -m truth.evidence weekly monthly`.

## 1. Problema

Memora publica las conversaciones y, para cada sesión, solo el **cambio** que el simulador le aplicó a la memoria (`session_type`, `operation`, `operation_details`). El estado de la memoria después de cada sesión (`memory_states_by_session.json`) existe en su pipeline pero **no se publica**. La verdad de P1 hay que reconstruirla aplicando esos cambios en orden.

Ejemplo real, `weekly/academic_researcher`, actores de cine:

| sesión | `operation_details` | qué dice el usuario (turno con `share_memory`) | hecho resultante |
|---|---|---|---|
| 5 | add `Joan Crawford`, like | | `(movies, actors, Joan Crawford) = like` |
| 40 | update, `value_update`, `old_item: Joan Crawford` → `Grace Kelly` | "I actually used to prefer Joan Crawford, but I've really come to appreciate Grace Kelly…" | se borra Joan Crawford, se agrega Grace Kelly |
| 50 | update, `value_update`, Grace Kelly → Rita Hayworth | | se borra Grace Kelly, se agrega Rita Hayworth |
| 88 | update, `preference_update`, Rita Hayworth like → dislike | | `(movies, actors, Rita Hayworth) = dislike` |
| 129 / 145 | add / delete `William Holden` | | aparece y desaparece |

La pregunta de Memora `pref_movies_general_158` ("Can you suggest me a movie?") espera Rita Hayworth como *dislike* y The Bridge on the River Kwai en `already_watched_list`. Como olvidados lista Joan Crawford (40), Grace Kelly (50) y William Holden (145). Nuestra extracción produce exactamente ese estado final. El problema es decidir, para cada tipo de operación, **qué es un hecho**, **qué lo identifica** y **qué le hace cada operación**, de forma que el resultado sea verificable.

## 2. Opciones investigadas

Fuentes primarias:

1. **El generador de Memora** (código en `vendor/Memora/data_generation`). Define la semántica real de cada operación:
   - `session_simulator.py`: `add_memory_item`, `remove_memory_item`, `update_memory_item`, `execute_memory_operation`.
   - `question_generation/unified_question_generator.py`: cómo se calculan `memory_evidence` y `forgetting_evidence` a partir del estado final.
2. **Paper de Memora**, https://arxiv.org/abs/2604.20006, §3.2: *"By recording the full memory state before and after each session, Memora produces explicit memory traces … These traces define the ground truth for downstream conversation generation and memory evaluation."* Repo: https://github.com/geniesinc/Memora. El evaluador (`vendor/Memora/evals`) no usa la evidencia para puntuar: la copia al resultado. Puntúa con las subpreguntas sí/no derivadas de ella.
3. **STALE**, https://arxiv.org/abs/2605.06527, repo https://github.com/icedreamc/STALE:
   - El estado del usuario es un conjunto de valores por atributo: *"S_t = {v_t(a) | a ∈ 𝒜}"*.
   - Su baseline CUP-Mem usa ranuras `(dominio, slot)` con cardinalidad *single* o *multi*.
   - Lo obsoleto se archiva como STALE en vez de borrarse. Solo la evidencia posterior puede revisar lo anterior.
4. **MemoryAgentBench**, https://arxiv.org/abs/2507.05257, repo https://github.com/HUST-AI-HYZ/MemoryAgentBench. FactConsolidation numera los hechos y define la verdad como "gana el más nuevo": *"the newer fact has larger serial number. You need to solve the conflicts of facts … by finding the newest fact."*
5. **"Bookkeeping, Composition, or Unreachable Gold?"**, https://arxiv.org/html/2610.09193. Solo leí el resumen del buscador: un resolvedor determinista de última escritura responde el 80% de MemoryAgentBench y encuentra respuestas oro inalcanzables. Es el mismo tipo de chequeo que hacemos acá.

Opciones de diseño que salieron de esas fuentes:

- **A.** Hechos atómicos clave→valor con "gana la última escritura": ranura de STALE/CUP-Mem, número de serie de MemoryAgentBench.
- **B.** Un documento largo = un hecho, con `content_data` entero como valor.
- **C.** Agregados como hechos: total de gasto, promedio de pasos, meta cumplida.
- **D.** Para contenido largo: diferenciar snapshots consecutivos de `content_data` en lugar de leer los deltas.
- **E.** Extraer los hechos de la conversación en lugar de `operation_details`.
- **F.** Identificar preferencias y olvidos solo por el nombre del ítem, como hace el `forgetting_evidence` de Memora.

## 3. Análisis y elección

Se eligió **A** para todo. Las claves y las acciones salen de cómo el simulador identifica y modifica cada elemento:

| dominio | origen | clave | valor | acciones |
|---|---|---|---|---|
| `preference` | `preference` add/delete/update | `(category, subcategory, item)` | `{"preference": "like"\|"dislike"}` | add; update (`preference_update`); remove (`delete` y el `old_item` de `value_update`) |
| `todo` | `todo_list` | `(description,)` | `{"task_type"}` | add, remove |
| `calendar` | `calendar_event` | `(event_name,)` | `{"event_type", "event_date"}` | add, update, remove |
| `expense` | `food_expenses` | `(session_id,)` | `{"date", "expense_type", "amount"}` | add |
| `steps` | `step_tracker` | `(date,)` | `{"activity_type", "step_count"}` | add |
| `goal` | `goal` | `(subcategory,)` | `{"value"}` | add; update con `previous = old_value` |
| `content` | ítems string (`project_proposal_N`…) | `(document_id, field)` para escalares; `(document_id, field, element)` para cada elemento de una lista | `{"value": …}` | add; update (presupuesto); remove (elemento) |

**Cambio de interfaz respecto del stub.** La clave de `preference` pasó de `(subcategory, item)` a `(category, subcategory, item)`. Los demás dominios son nuevos.

### Respuestas a las preguntas concretas

**Gustos.**
- **`delete` borra el ítem entero, no lo pasa a *dislike*.** `remove_memory_item` solo elige entre *likes*, saca el ítem de la lista y lo devuelve al pool, desde donde puede volver a agregarse más tarde. Por eso es `remove`.
- **`value_update`** = remove del `old_item` + add del ítem nuevo, en la misma subcategoría (179 sesiones en weekly+monthly).
- **`preference_update`** = el mismo ítem cambia de like a dislike o al revés (146 sesiones). Es un `update` con `previous`.
- **La categoría no viene en `operation_details`.** Se recupera del arquetipo de la persona, igual que lo hace el simulador (`persona_traits.json` + `preference_metadata.json`). Solo `genres` es ambigua (existe en películas y en música). Para cada persona, los géneros de su arquetipo de cine y los de su arquetipo de música no se solapan. La regla ubica el 100% de los 1.076 casos de `genres` en weekly, monthly y quarterly. Ejemplo: `monthly/software_engineer`, sesión 196, "experimental" → música. En la metadata global "experimental" existe en los dos.
- **Las listas `already_watched/read/listened/visited` no son gustos: son historial de consumo**, con un like/dislike adjunto.
  - Son de solo agregar: el simulador las excluye de delete y update (`_select_random_*_item` filtra `already_*`). En los datos hay 117 adds y 0 updates/deletes en weekly+monthly.
  - Se modelan como `preference` con subcategoría `already_*`. Nunca quedan obsoletas. P2 puede separarlas por el prefijo.

**Pendientes.**
- **La descripción es clave única mientras el pendiente está activo.** Al agregarlo, el simulador la saca del pool, y al borrarlo la devuelve. En los datos: 0 adds sobre una descripción ya activa y 0 deletes sobre una inexistente.
- **Una descripción sí puede repetirse en el tiempo** (add → delete → add → delete). Ejemplo: "Prepare lecture materials" en `weekly/academic_researcher` se borra en las sesiones 92 y 130. Con la clave `(description,)` eso es simplemente un hecho que aparece y desaparece dos veces.
- Ninguna descripción aparece con dos `task_type`.

**Gastos y pasos: hechos atómicos, los agregados se derivan.**
- Memora calcula sus propias respuestas (total, total por tipo, máximo por semana, meta cumplida) sumando la lista atómica del estado final. Nosotros reproducimos esas listas al 100%.
- En los datos no hay ningún `update` ni `delete` de gastos o pasos. Son solo de agregar.
- Hay un registro de pasos por día: 350 de 350 días en weekly+monthly. Por eso la clave es la fecha.
- Los gastos no tienen identificador natural: el par (fecha, tipo) se repite (varios cafés por día). Por eso la clave es el `session_id`.

**Metas.**
- La clave es la subcategoría (`daily_steps`, `coffee`, `breakfast`, `lunch`, `dinner`, `grocery`).
- La sesión es siempre `goal`/`add`, pero `actual_operation` dice si fue un alta o un cambio. En los 66 cambios de weekly+monthly, `old_value` coincide con el valor vigente.
- En monthly, la meta cambia de semana a semana. El `budget_timeline` de Memora sale de esos mismos cambios.

**Eventos de calendario.**
- `event_date = created_at + "+N days"`. Es la regla de Memora, tanto en el simulador (`_is_calendar_event_valid_for_modification`) como en las preguntas (`_filter_future_calendar_events`).
- **Un `update` solo cambia el offset y conserva el `created_at` original**: el desplazamiento se cuenta desde la creación, no desde la sesión del cambio.
- Contra la conversación, con un chequeo heurístico de texto (fecha absoluta, "N days", "N weeks", "tomorrow"):
  - Adds: el texto coincide en **71 de 71** en weekly+monthly. El chequeo automático reconoce 68; los otros 3 los revisé a mano ("six days", "July 08", "July 04").
  - Updates: **0 de 37** coinciden. Ejemplo: `weekly/academic_researcher` sesión 150 dice "next Tuesday" (2025-06-10); Memora guarda "+19 days" desde 2025-06-03 = 2025-06-22. También se confirma la hipótesis de `weekly/software_engineer` sesión 87: "next Tuesday" desde el miércoles 2025-06-04 es el 06-10, y Memora da el 06-11.
- **Que un evento venza no es un cambio**: Memora lo sigue teniendo en memoria y lo filtra al preguntar (`event_date > fecha de la pregunta` = "upcoming"). "Próximo" es un predicado del momento de la consulta, no un hecho que se borra.
- **Los `no_memory` con `delete_to_no_memory`/`update_to_no_memory`** (motivo `all_calendar_events_expired`) no tocan la memoria: el simulador retorna sin modificar nada. Producen 0 cambios.

**Contenido largo.**
- Un documento es un conjunto de hechos atómicos: uno por campo escalar y uno por elemento de cada lista.
  - Es la granularidad con la que Memora evalúa: `forgetting_evidence` lista pares `(field, value)`.
  - Respeta el contrato de "dicts planos".
- Los cambios salen de los deltas de la sesión:
  - `content_data` completo en un `add`.
  - `memory_updates`: `added` → add; `budget_revised` → update.
  - `memory_deletes`: `removed_from_memory` → remove; `budget_reverted` → update.
- **Validación interna**: después de cada sesión de contenido, los hechos reconstruyen exactamente el `content_data` que Memora guarda en esa sesión. Pasa en 178/178 sesiones en weekly y 786/786 en monthly, y también en quarterly (test).
- `session_history`, `pool_status` y `moved_to_completed` no son hechos sobre el usuario. Indican qué documentos están "terminados", y Memora solo pregunta por esos.
- `session_history` se usa para validar: coincide con las sesiones que tocan cada documento.

**Qué pasó realmente en las sesiones con `operation_converted`.** El simulador cambia la operación cuando la pedida no se puede aplicar. El campo `operation` publicado ya es la operación efectiva, y la conversación sigue esa operación efectiva. Ejemplo: en `weekly/sales_manager` sesión 43 (`delete_to_update`), el usuario pide *agregar* dos key points.

| conversión | weekly+monthly | quarterly | qué pasó |
|---|---|---|---|
| `add_to_update` | 101 | 369 | No había documento nuevo disponible: se agregaron elementos a un borrador existente (`memory_updates`). |
| `delete_to_update` | 11 | 24 | Ninguna lista tenía más de un elemento para borrar: se agregaron elementos. |
| `update_to_delete` | 5 | 19 | No quedaban datos para agregar: se borraron elementos (`memory_deletes`). |
| `add_to_no_memory` | 226 | 4.002 | Los pools de contenido estaban agotados: la sesión pasa a `no_memory` y no cambia nada. |
| `delete_/update_to_no_memory` | 16 | 29 | Todos los eventos de calendario estaban vencidos: no cambia nada. |

**Quarterly:** hay 13 sesiones `add_to_update` en las que todas las ediciones son `{"error": …}`. El simulador las trata como fallidas y el documento no cambia, así que producen 0 cambios. La conversación, en cambio, sí pide el cambio. Ejemplo: `quarterly/academic_researcher` sesión 295, "John will now lead the Q3 accessibility review, replacing Sarah".

Las preferencias con `fallback_reason` (81 en weekly+monthly) son adds normales.

## 4. Prueba

```
$ uv run pytest -v
tests/test_changes.py::test_value_update_replaces_the_liked_item PASSED  [ 12%]
tests/test_changes.py::test_genre_category_comes_from_the_persona_archetype PASSED [ 25%]
tests/test_changes.py::test_content_delete_reverts_budget_and_removes_one_element PASSED [ 37%]
tests/test_changes.py::test_rescheduled_event_keeps_memora_anchor_on_creation_date PASSED [ 50%]
tests/test_changes.py::test_failed_content_edit_changes_nothing PASSED   [ 62%]
tests/test_changes.py::test_extraction_reproduces_memora_evidence[weekly] PASSED [ 75%]
tests/test_changes.py::test_extraction_reproduces_memora_evidence[monthly] PASSED [ 87%]
tests/test_changes.py::test_extraction_reproduces_memora_evidence[quarterly] PASSED [100%]
============================== 8 passed in 4.05s ===============================
```

El último test recorre todas las personas y verifica tres cosas:
- 0 precondiciones fallidas: ningún `add` sobre un hecho existente, y ningún `update`/`remove` sobre un hecho inexistente o con otro `previous`.
- Cada snapshot de contenido se reconstruye exactamente.
- Todas las preguntas de Memora coinciden, salvo los 2 defectos conocidos.

Cómo se compara cada familia de preguntas (`truth/evidence.py`) contra el estado final reconstruido:

| familia | `memory_evidence` | `forgetting_evidence` |
|---|---|---|
| todos | igualdad de conjuntos | cada olvidado es un hecho que existió y ya no existe |
| preferencias | igualdad de conjuntos | cada olvidado es un hecho que existió y ya no existe |
| contenido | igualdad de conjuntos, más `session_history` | cada olvidado es un hecho que existió y ya no existe |
| calendario | eventos futuros | cantidad de eventos pasados |
| gastos, pasos, metas | igualdad de multiconjuntos `(session_id, tipo, monto)` / `(session_id, pasos)` | — |
| comparativas por semana o mes | ítems por período y `budget_timeline` | — |

Cambios por dominio como `add/update/remove`:

```
$ uv run python -m truth.evidence weekly monthly
```

**weekly**

| persona | sessions | preference | todo | calendar | expense | steps | goal | content | distinct facts | final facts | precondition failures | questions matching |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| academic_researcher | 158 | 20/3/10 | 13/0/8 | 2/1/1 | 24/0/0 | 7/0/0 | 3/0/0 | 66/4/7 | 134 | 109 | 0 | 15/15 |
| business_executive | 145 | 18/5/7 | 10/0/8 | 2/1/0 | 19/0/0 | 7/0/0 | 2/0/0 | 93/4/6 | 150 | 130 | 0 | 15/15 |
| content_writer | 151 | 19/4/6 | 13/0/9 | 2/1/0 | 20/0/0 | 7/0/0 | 4/0/0 | 80/3/8 | 142 | 122 | 0 | 15/15 |
| creative_designer | 147 | 19/3/10 | 13/0/9 | 2/2/0 | 23/0/0 | 7/0/0 | 3/0/0 | 81/2/14 | 145 | 115 | 0 | 15/15 |
| financial_analyst | 156 | 19/4/9 | 16/0/6 | 3/0/1 | 21/0/0 | 7/0/0 | 2/0/0 | 77/1/6 | 141 | 123 | 0 | 15/15 |
| management_consultant | 157 | 22/4/10 | 12/0/10 | 3/0/0 | 25/0/0 | 7/0/0 | 2/0/0 | 77/3/12 | 146 | 116 | 0 | 15/15 |
| marketing_manager | 156 | 21/3/7 | 12/0/11 | 2/0/1 | 23/0/0 | 7/0/0 | 4/0/0 | 81/0/8 | 148 | 123 | 0 | 15/15 |
| sales_manager | 163 | 19/4/11 | 10/0/10 | 1/2/0 | 22/0/0 | 7/0/0 | 4/0/0 | 83/0/9 | 143 | 116 | 0 | 14/15 |
| software_engineer | 163 | 22/2/9 | 13/0/11 | 2/2/0 | 24/0/0 | 7/0/0 | 4/0/0 | 87/0/9 | 154 | 130 | 0 | 15/15 |
| startup_founder | 155 | 24/2/10 | 10/0/10 | 2/1/0 | 23/0/0 | 7/0/0 | 2/0/0 | 82/1/12 | 149 | 118 | 0 | 15/15 |
| **total** | | 203/34/89 | 122/0/92 | 21/10/3 | 224/0/0 | 70/0/0 | 30/0/0 | 807/18/91 | | | | |

| question family | match | no match |
|---|---|---|
| activity_calendar | 4 | 0 |
| activity_food_total | 10 | 0 |
| activity_food_type | 10 | 0 |
| activity_steps_total | 10 | 0 |
| activity_todos | 8 | 0 |
| content | 38 | 0 |
| goal | 20 | 0 |
| pref_general | 38 | 1 |
| pref_subcategory | 11 | 0 |

```
- sales_manager pref_travel_general_163: memory=True forgetting=False forgotten but not stale: ['Mediterranean']
```

**monthly**

| persona | sessions | preference | todo | calendar | expense | steps | goal | content | distinct facts | final facts | precondition failures | questions matching |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| academic_researcher | 619 | 44/14/26 | 42/0/38 | 7/0/2 | 85/0/0 | 28/0/0 | 5/6/0 | 307/18/40 | 479 | 412 | 0 | 15/15 |
| business_executive | 601 | 46/10/21 | 47/0/42 | 5/4/2 | 91/0/0 | 28/0/0 | 5/8/0 | 334/18/43 | 512 | 448 | 0 | 15/15 |
| content_writer | 628 | 49/12/36 | 39/0/38 | 5/4/0 | 99/0/0 | 28/0/0 | 6/5/0 | 288/21/44 | 472 | 396 | 0 | 15/15 |
| creative_designer | 614 | 44/12/26 | 41/0/40 | 6/2/3 | 97/0/0 | 28/0/0 | 6/6/0 | 321/15/59 | 513 | 415 | 0 | 15/15 |
| financial_analyst | 611 | 44/8/26 | 42/0/39 | 1/1/0 | 94/0/0 | 28/0/0 | 5/7/0 | 302/10/52 | 474 | 399 | 0 | 15/15 |
| management_consultant | 604 | 47/8/30 | 45/0/34 | 4/3/3 | 95/0/0 | 28/0/0 | 6/8/0 | 310/17/55 | 492 | 413 | 0 | 15/15 |
| marketing_manager | 604 | 44/15/26 | 48/0/34 | 4/2/2 | 86/0/0 | 28/0/0 | 6/7/0 | 334/13/61 | 506 | 427 | 0 | 15/15 |
| sales_manager | 635 | 48/9/32 | 51/0/39 | 6/4/0 | 93/0/0 | 28/0/0 | 6/5/0 | 318/14/66 | 502 | 413 | 0 | 15/15 |
| software_engineer | 628 | 46/9/34 | 50/0/43 | 6/4/1 | 88/0/0 | 28/0/0 | 6/9/0 | 310/13/55 | 495 | 401 | 0 | 15/15 |
| startup_founder | 606 | 41/15/27 | 41/0/40 | 6/3/2 | 87/0/0 | 28/0/0 | 5/5/0 | 309/12/43 | 485 | 405 | 0 | 15/15 |
| **total** | | 453/112/284 | 446/0/387 | 50/27/15 | 915/0/0 | 280/0/0 | 56/66/0 | 3133/151/518 | | | | |

| question family | match | no match |
|---|---|---|
| activity_calendar | 6 | 0 |
| activity_food_total | 10 | 0 |
| activity_food_type | 10 | 0 |
| activity_todos | 10 | 0 |
| comparative_goal_met_week | 10 | 0 |
| comparative_max_week | 20 | 0 |
| content | 34 | 0 |
| pref_general | 40 | 0 |
| pref_subcategory | 10 | 0 |

**quarterly** (`uv run python -m truth.evidence quarterly`):
- 0 precondiciones fallidas en las 10 personas.
- Coinciden 299/300 preguntas. La única que no: `creative_designer pref_music_general_1991`, 'Vampire Weekend'.
- Totales `add/update/remove`: preference 2422/517/1636, todo 998/0/873, calendar 111/47/24, expense 2916/0/0, steps 920/0/0, goal 60/360/0, content 5580/370/839.

Cuadre con los conteos de P1 en weekly+monthly. Las 996 sesiones de preferencias (477 add + 194 delete + 325 update) se convierten así:
- 656 adds = 477 + 179 `value_update`.
- 146 updates = los flips.
- 373 removes = 194 deletes + 179 `value_update`.

**Hipótesis heredada "≈26 hechos de gustos y pendientes por persona en weekly": no se confirma tal cual.**
- Hechos distintos de `preference` + `todo` que existieron alguna vez: entre 27 y 33 por persona (media 30,5).
- Vigentes al final de la semana: entre 8 y 20 (media 14,4).

## 5. Opciones descartadas

- **B, documento entero como un hecho.**
  - El valor dejaría de ser plano (tiene listas).
  - Quitar un solo elemento volvería obsoleto todo el documento, cuando Memora evalúa y olvida por elemento: `forgetting_evidence` de contenido trae `(field, value)`.
  - Con A, cada `remove` apunta exactamente al elemento que un dream tiene que corregir.
- **C, agregados como hechos.**
  - Cada gasto nuevo dejaría obsoleto el total, sin que ninguna operación de Memora lo diga. La tasa de "hechos que cambian" quedaría inflada artificialmente.
  - Los agregados se derivan de forma determinista de los hechos atómicos: Memora los calcula así y nosotros los reproducimos en todas las preguntas de gastos, pasos, metas y comparativas.
- **D, diferenciar snapshots de `content_data`.**
  - Da el mismo resultado: lo verificamos, los deltas reconstruyen todos los snapshots.
  - Pero exige recordar el documento entre sesiones, y `extract_changes(session)` es por sesión y sin estado.
  - Quedó como validación en lugar de mecanismo.
- **E, extraer de la conversación.**
  - Cuesta llamadas a un modelo, prohibidas en esta tanda.
  - La conversación contradice la traza en las reprogramaciones de calendario: 0 de 37 coinciden.
  - Trae información sin registrar: `weekly/software_engineer` sesión 30, turno 14 ("upbeat electronic music") con `share_memory=True` pero ausente de `operation_details`; y las 13 sesiones de quarterly que piden un cambio que no se aplicó. En esa misma sesión 30 confirmé que el turno 15 está etiquetado `user_agent` con texto del asistente.
  - La verdad de Memora, la que usa su evaluación, es la traza, no la conversación.
- **F, identidad por nombre.**
  - Es lo que hace el `forgetting_evidence` de Memora, y es la causa de las 2 únicas discrepancias:
    - `weekly/sales_manager`: "Mediterranean" es un clima (dislike, vigente) y una región (like, borrada en la sesión 162).
    - `quarterly/creative_designer`: "Vampire Weekend" es un artista (borrado en la 1668) y está en `already_listened_list` (vigente).
  - En los dos casos Memora pide olvidar algo que también pide recordar.
  - La clave con subcategoría evita esa colisión.
- **Clave del stub `(subcategory, item)`, sin categoría.** Para cada persona no hay solapamiento real entre los géneros de cine y los de música, así que no colisiona. Igual se descartó porque sin categoría el hecho no dice si "thriller" es una película o música, y las preguntas de Memora son por categoría ("suggest me a movie").
- **Anclar las reprogramaciones de calendario en `updated_at`.** Tampoco coincide con la conversación: sesión 150, `updated_at` + 19 = 2025-06-26 contra "next Tuesday" = 06-10. Además se aparta de la regla con la que Memora evalúa.
- **Emitir un `remove` cuando un evento vence.** No es una operación de Memora. Memora conserva el evento y lo trata como "pasado" al preguntar. Si lo emitiéramos, "olvidado" se confundiría con "ya ocurrió".

## 6. Limitaciones y preguntas abiertas

- **Fechas reprogramadas de calendario: no verificables contra la conversación** (37 en weekly+monthly, 47 en quarterly).
  - Nuestra verdad sigue la regla de Memora (`created_at` + offset).
  - P2 no debería preguntar la fecha exacta de un evento reprogramado. La existencia del evento y su borrado sí son verificables.
  - El `update` de calendario va con `previous=None` porque Memora no guarda la fecha anterior.
- **El `forgetting_evidence` de Memora es más débil que nuestra verdad.** No marca como olvidados:
  - Los flips de preferencia (146 en weekly+monthly; ejemplo: "like Rita Hayworth" pasa a dislike en la sesión 88).
  - Los presupuestos viejos de `budget_revised` (109). Sí marca los de `budget_reverted`.
  - Nuestra verdad los marca como valores que dejaron de ser ciertos. Para P2: si se quiere comparar con FAMA, hay que saber que Memora no los evalúa.
- **Defectos de Memora que la validación reproduce en lugar de corregir.** El código de validación los imita. La extracción no se toca.
  - El período comparativo descarta los cambios de meta del último día (`day_offset > total_days`): afecta 15 preguntas de quarterly.
  - Dos gastos idénticos el mismo día comparten el `session_id` del primero (`quarterly/startup_founder`, sesiones 529 y 536).
  - Las 2 colisiones de nombre de la sección 5.
- **La validación externa solo cubre el estado final**: Memora pregunta únicamente al final del período. Los estados intermedios se validan indirectamente por dos vías:
  - 0 precondiciones fallidas en 27.614 sesiones.
  - Los snapshots de contenido, que sí son por sesión.
- **Evidencia por turno.** `evidence_turns` son los turnos con `share_memory=True`, y pueden incluir información no registrada (sesión 30). En weekly+monthly, todas las sesiones con cambios tienen al menos un turno así, y ninguna `no_memory` lo tiene.
- **No modelado.** El estado "terminado" de un documento (`moved_to_completed`) no se modela como hecho. Si P2 quiere preguntar solo por documentos terminados, como hace Memora, lo tiene que leer de `operation_details`.
- **Para P1b.**
  - `truth/evidence.py` incluye un `replay` mínimo, solo para validar. La representación oficial del estado en el tiempo sigue siendo `truth/timeline.py`.
  - El chequeo de precondiciones de P1b debería dar 0 fallas con esta extracción.
