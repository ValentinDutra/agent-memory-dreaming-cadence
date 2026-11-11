# P1b · Representar y validar el estado

Tag: `p1`. Código: `truth/timeline.py`. Tests: `tests/test_timeline.py`.

Todos los números de este informe salen del stub actual de `truth/changes.py`, que cubre los dominios `preference` y `todo`. `timeline.py` no menciona ningún dominio: cuando P1a agregue dominios, el mismo comando recalcula todo.

## 1. Problema

P1a convierte cada sesión de Memora en una lista de `Change` (add, update o remove de un hecho `(domain, key)`). Con eso hay que resolver dos cosas:

1. **Representar** la verdad en el tiempo, de modo que P2 pueda preguntar barato "¿qué es cierto después de la sesión N?" y "¿qué hecho cambió entre la sesión A y la B?". Esa segunda pregunta es la que necesita un dream que corre cada K sesiones para saber qué notas quedaron viejas.
2. **Validar** que esa verdad es confiable. Hay tres frentes: que los cambios no se contradigan entre sí, que lo que dice la conversación coincida con `operation_details`, y catalogar los defectos del dataset.

Ejemplo real: `weekly/academic_researcher`, el actor favorito.

| Sesión | Fecha | `operation_details` | Turno `share_memory=True` |
| --: | --- | --- | --- |
| 5 | 2025-06-01 | add `actors/Joan Crawford` like | — |
| 40 | 2025-06-02 | `value_update`: Joan Crawford → Grace Kelly | t16 |
| 50 | 2025-06-03 | `value_update`: Grace Kelly → Rita Hayworth | t11 "I used to really like Grace Kelly, but I've found myself much more drawn to Rita Hayworth lately" |
| 88 | 2025-06-04 | `preference_update`: Rita Hayworth like → dislike | t16 "I actually used to really like Rita Hayworth, but I've gone off her movies lately" |

Después de la sesión 39 la verdad es "le gusta Joan Crawford". Después de la 88 es "no le gusta Rita Hayworth". Entre la 39 y la 50, el cambio neto es: Joan Crawford sale y Rita Hayworth entra. Grace Kelly entró y salió en el medio, así que una nota escrita en la sesión 39 no la necesita.

Otro detalle que importa: `date` no sirve como reloj. Weekly tiene unas 150 sesiones en 7 fechas, así que muchas sesiones comparten fecha. El reloj es `session_id`.

## 2. Opciones investigadas

| Opción | Quién la usa | Fuente |
| --- | --- | --- |
| Estado latente S_t, una sola pareja viejo→nuevo por instancia; en el prototipo CUPMem, estados ACTIVE/STALE/UNKNOWN decididos por un LLM | STALE (2026) | https://arxiv.org/abs/2605.06527, §3.1, §3.4, App. F; repo https://github.com/icedreamc/STALE |
| Intervalos de validez bitemporales en cada arista: `valid_at`/`invalid_at` (tiempo del mundo) y `created_at`/`expired_at` (tiempo del sistema); la información nueva invalida la vieja sin borrarla | Zep / Graphiti | https://arxiv.org/html/2501.13956, §2.2.3; https://www.getzep.com/blog/beyond-static-knowledge-graphs/ |
| Lista numerada de hechos, append-only; gana el número más alto (last-write-wins) | MemoryAgentBench, FactConsolidation | https://arxiv.org/html/2507.05257v4, §3.1, App. B.4.2 |
| Auditoría de MemoryAgentBench con un resolvedor last-write-wins por `(sujeto, relación)`: 67 preguntas tienen un gold que apunta a un valor ya sobrescrito | Auditoría externa (2026) | https://arxiv.org/html/2610.09193, §3.3 |
| Historia de sesiones con fecha (registro de eventos); la respuesta es un string y `answer_session_ids` marca las sesiones de evidencia | LongMemEval, tipo `knowledge-update` | https://github.com/xiaowu0162/LongMemEval |
| Estado completo después de cada sesión (snapshot) | Opción trivial; ninguno de los benchmarks la publica | — |

El propio Memora define la verdad con un simulador con estado (`vendor/Memora/data_generation/session_simulator.py`: `add_memory_item`, `remove_memory_item`, `update_memory_item`), que elige qué borrar o actualizar entre los ítems activos. Por eso cabía esperar pocas violaciones de precondición, y así fue.

## 3. Análisis y elección

**Representación: intervalos de validez sobre un solo eje de tiempo (`session_id`), construidos con una sola pasada sobre los cambios.** Es la mitad "valid time" de Graphiti. Cada valor que tuvo un hecho es una `Version(domain, key, value, valid_from, valid_until)` y vale para las sesiones `valid_from <= N < valid_until`.

```python
from truth.changes import persona_changes
from truth.timeline import build_timeline, state_after

timeline = build_timeline(persona_changes("monthly", "software_engineer"))
timeline.state_after(300)              # {(domain, key): value}
timeline.changed_between(300, 350)     # {(domain, key): (antes, después)}, solo cambios netos
timeline.inconsistencies               # [Inconsistency(kind, change, found)]
state_after(changes, 300)              # la firma de la interfaz; reconstruye en cada llamada
```

Por qué esta y no otra:

- **Responde las dos consultas de P2.** `state_after(N)` filtra versiones. `changed_between(A, B)` compara dos estados y devuelve solo el cambio neto: si un hecho cambió y volvió a su valor anterior, la nota sigue bien y no aparece. Para el dream es la semántica correcta.
- **Ocupa O(cambios), no O(sesiones × hechos).** Quarterly entero (stub): 3.937 versiones, 0,32 MB en JSON, contra 970.655 entradas y 76 MB si se guardara un snapshot por sesión. Construir el timeline tarda 6 ms en total. No hace falta persistir nada en disco: se recalcula en milisegundos.
- **Guarda desde cuándo vale cada valor.** El registro de eventos crudo obliga a repetir la pasada para saberlo.
- **Es simple:** unas 60 líneas, sin dependencias, sin conocer ningún dominio.
- **Un solo eje alcanza.** El segundo eje de Graphiti (cuándo se enteró el sistema) acá coincide con el primero: el usuario dice el hecho en la sesión N y vale desde la sesión N. Ningún cambio corrige el pasado de forma retroactiva.

**Validación de consistencia, hecha durante la misma pasada.** Cada cambio se compara con el valor vigente:

| Tipo | Cuándo | Qué hace la verdad | Por qué |
| --- | --- | --- | --- |
| `add_existing` | add de un hecho que ya existe | aplica el valor nuevo; si es igual, no hace nada | Lo último que dijo el usuario es la mejor evidencia del presente: es la regla de MemoryAgentBench y de Graphiti. Cubre, por ejemplo, las sesiones `goal` con `operation: "add"` y `actual_operation: "update"` si P1a las extrae como add. |
| `update_missing` | update de un hecho que no existe | lo crea con el valor nuevo | El valor nuevo está afirmado; lo que falló fue el registro del pasado, no el presente. |
| `remove_missing` | remove de un hecho que no existe | nada (el hecho sigue sin existir) | No hay nada que borrar. |
| `previous_mismatch` | `previous` no coincide con el valor vigente | aplica el cambio | Lo nuevo gana. |

En los cuatro casos el cambio queda en `timeline.inconsistencies` con el valor que tenía la verdad (`found`), para que P2 pueda excluir esos hechos del examen si quiere. **No agregué un estado "dudoso"**: con los datos actuales no hay ninguna inconsistencia, así que sería código sin uso. Si P1a trae dominios con inconsistencias reales, P2 puede filtrar por la lista sin que haya que cambiar la representación.

**Validación contra el texto, sin modelos.** Para cada cambio, `change_text_support` busca el nombre del hecho (el último componente de `key`) en los turnos `share_memory=True`. Compara por raíz de 4 letras, de modo que "buy" calza con "buying" y "symphony" con "symphonies", y normaliza las décadas ("1980s" → "80s"). Clasifica en `full`, `partial` (al menos la mitad de las palabras) o `absent`. `session_defects` agrega controles estructurales por sesión.

**Validación contra la evidencia del propio Memora.** Es la más fuerte. Las `evaluation_questions` traen, en el momento de la pregunta, qué hechos deben recordarse (`memory_evidence`) y cuáles olvidarse (`forgetting_evidence`). `evidence_check` reproduce esa evidencia con `state_after` en la sesión de la pregunta (el número del `question_id`). Además, cada `session_id` de la evidencia se compara con el `valid_from` del hecho.

## 4. Prueba

### Tests

```
$ uv run pytest -q
.......                                                                  [100%]
7 passed in 0.02s
```

Los tests cubren: el límite de `state_after` (los cambios de la sesión N cuentan en N), el cambio neto de `changed_between`, las cuatro inconsistencias con la política "lo nuevo gana", el matching de texto (paráfrasis sí, omisión no) y la evidencia de Memora sobre un caso real. Probé que fallan: si cambio `session_id < valid_until` por `<=`, fallan 2 de los 7.

### Informe completo por período

```
$ uv run python -m truth.timeline weekly
== weekly: facts alive after the last session, by persona
  academic_researcher        15  {'preference': 10, 'todo': 5}
  business_executive         13  {'preference': 11, 'todo': 2}
  content_writer             17  {'preference': 13, 'todo': 4}
  creative_designer          13  {'preference': 9, 'todo': 4}
  financial_analyst          20  {'preference': 10, 'todo': 10}
  management_consultant      14  {'preference': 12, 'todo': 2}
  marketing_manager          15  {'preference': 14, 'todo': 1}
  sales_manager               8  {'preference': 8}
  software_engineer          15  {'preference': 13, 'todo': 2}
  startup_founder            14  {'preference': 14}
== weekly: inconsistencies none
== weekly: does a share_memory turn mention the changed fact?
  ('preference', 'add', 'full') 203
  ('preference', 'remove', 'absent') 1
  ('preference', 'remove', 'full') 88
  ('preference', 'update', 'full') 34
  ('todo', 'add', 'full') 119
  ('todo', 'add', 'partial') 3
  ('todo', 'remove', 'full') 87
  ('todo', 'remove', 'partial') 5
== weekly: session defects
  user_turn_after_user_turn                  233  e.g. ('academic_researcher', 7, 9)
  share_turn_mentions_no_changed_fact        118  e.g. ('academic_researcher', 10, 12)
== weekly: Memora evaluation evidence reproduced by the truth
  ('activity_calendar', 'remembered', 'missing') 4
  ('activity_todos', 'forgotten', 'removed') 64
  ('activity_todos', 'remembered', 'in_truth') 30
  ('content_email', 'forgotten', 'never_in_truth') 24
  ('content_email', 'remembered', 'missing') 68
  ('content_meeting', 'forgotten', 'never_in_truth') 28
  ('content_meeting', 'remembered', 'missing') 69
  ('content_project', 'forgotten', 'never_in_truth') 26
  ('content_project', 'remembered', 'missing') 184
  ('pref_books', 'forgotten', 'removed') 28
  ('pref_books', 'remembered', 'in_truth') 37
  ('pref_books', 'remembered', 'in_truth_since_earlier_version') 7
  ('pref_movies', 'forgotten', 'removed') 32
  ('pref_movies', 'remembered', 'in_truth') 34
  ('pref_movies', 'remembered', 'in_truth_since_earlier_version') 6
  ('pref_music', 'forgotten', 'removed') 25
  ('pref_music', 'remembered', 'in_truth') 27
  ('pref_music', 'remembered', 'in_truth_since_earlier_version') 4
  ('pref_travel', 'forgotten', 'removed') 20
  ('pref_travel', 'forgotten', 'still_in_truth') 1
  ('pref_travel', 'remembered', 'in_truth') 22
  ('pref_travel', 'remembered', 'in_truth_since_earlier_version') 4
```

`uv run python -m truth.timeline monthly` (extracto):

```
== monthly: facts alive after the last session, by persona
  academic_researcher        22  {'preference': 18, 'todo': 4}
  business_executive         30  {'preference': 25, 'todo': 5}
  content_writer             14  {'preference': 13, 'todo': 1}
  creative_designer          19  {'preference': 18, 'todo': 1}
  financial_analyst          21  {'preference': 18, 'todo': 3}
  management_consultant      28  {'preference': 17, 'todo': 11}
  marketing_manager          32  {'preference': 18, 'todo': 14}
  sales_manager              28  {'preference': 16, 'todo': 12}
  software_engineer          19  {'preference': 12, 'todo': 7}
  startup_founder            15  {'preference': 14, 'todo': 1}
== monthly: inconsistencies none
== monthly: does a share_memory turn mention the changed fact?
  ('preference', 'add', 'full') 452
  ('preference', 'add', 'partial') 1
  ('preference', 'remove', 'absent') 3
  ('preference', 'remove', 'full') 280
  ('preference', 'remove', 'partial') 1
  ('preference', 'update', 'full') 112
  ('todo', 'add', 'full') 442
  ('todo', 'add', 'partial') 4
  ('todo', 'remove', 'full') 378
  ('todo', 'remove', 'partial') 9
== monthly: session defects
  user_turn_after_user_turn                  962  e.g. ('academic_researcher', 6, 7)
  share_turn_mentions_no_changed_fact        237  e.g. ('academic_researcher', 1, 14)
```

Quarterly, procesado persona por persona: `/usr/bin/time -l uv run python -m truth.timeline quarterly` tarda 3,50 s y usa 62 MB de RSS como máximo. Da 0 inconsistencias. Los hechos vivos al final van de 75 a 113 por persona (911 en total).

### Resumen de números

| | weekly | monthly | quarterly |
| --- | --: | --: | --: |
| Cambios (stub) | 540 | 1.682 | 6.446 |
| Hechos vivos al final, por persona (mín–máx) | 8–20 | 14–32 | 75–113 |
| Hechos vivos al final, promedio por persona | 14,4 | 22,8 | 91,1 |
| Inconsistencias de cualquier tipo | 0 | 0 | 0 |
| Cambios con texto `full` / `partial` / `absent` | 531 / 8 / 1 | 1.664 / 15 / 3 | 6.395 / 40 / 11 |
| Evidencia "recordar" de pref+todo reproducida | 171/171 | 259/259 | 1.238/1.238 |
| Evidencia "olvidar" de pref+todo con el hecho borrado | 169/170 | 592/592 | 1.988/1.995 |

Las 8 evidencias de "olvidar" que siguen vivas (1 en weekly, 7 en quarterly) son **colisiones de nombre, no errores de la verdad**: el mismo string vive en otra subcategoría. Por ejemplo, en `quarterly/creative_designer` "Vampire Weekend" se borró de `artists` en la sesión 1668, pero sigue en `already_listened_list` desde la 1640. En `weekly/sales_manager` "Mediterranean" se borró de `regions` y sigue en `climates`. Revisé las 8 una por una.

Los `in_truth_since_earlier_version` (21 en weekly, 38 en monthly, 148 en quarterly) **también están bien**. Memora guarda la sesión en que el ítem entró por primera vez; nuestro `valid_from` arranca de nuevo con cada cambio de valor. Ejemplo: Rita Hayworth entra en la sesión 50 y pasa a dislike en la 88; Memora dice 50 y `valid_from` dice 88. En weekly y monthly verifiqué con un script aparte que las 59 discrepancias son exactamente este caso: la cadena de versiones contiguas del mismo hecho llega a la sesión de Memora.

### Chequeo inverso: ¿la verdad tiene preferencias que Memora no lista?

Las preguntas `pref_*_general_*` listan todas las preferencias vivas de cada subcategoría. Las comparo contra `state_after` en esa sesión, en las dos direcciones:

```
$ uv run python - <<'EOF'
import json
from truth.changes import MEMORA_DATA, persona_changes, personas
from truth.timeline import build_timeline, question_session

for period in ("weekly", "monthly", "quarterly"):
    in_both = only_truth = only_memora = 0
    for persona in personas(period):
        timeline = build_timeline(persona_changes(period, persona))
        questions = json.loads((MEMORA_DATA / period / persona / f"evaluation_questions_{persona}.json").read_text())["questions"]
        general = [q for task in questions.values() for q in task if "_general_" in q["question_id"]]
        assert len({question_session(q["question_id"]) for q in general}) == 1
        memora = {(sub, item["item"], side[:-1]) for q in general for sub, sides in q["memory_evidence"]["memory_items"].items() for side, items in sides.items() for item in items}
        state = timeline.state_after(question_session(general[0]["question_id"]))
        truth = {(key[0], key[1], value["preference"]) for (domain, key), value in state.items() if domain == "preference"}
        in_both += len(memora & truth); only_truth += len(truth - memora); only_memora += len(memora - truth)
    print(f"{period}: in_both={in_both} only_truth={only_truth} only_memora={only_memora}")
EOF
weekly: in_both=114 only_truth=0 only_memora=0
monthly: in_both=169 only_truth=0 only_memora=0
quarterly: in_both=786 only_truth=0 only_memora=0
```

La verdad de preferencias coincide exactamente con la de Memora en los tres períodos: 1.069 hechos, ninguno de más y ninguno de menos.

### Tamaño de la representación

```
$ uv run python - <<'EOF'
import json
from truth.changes import load_sessions, persona_changes, personas
from truth.timeline import build_timeline

for period in ("weekly", "monthly", "quarterly"):
    changes = versions = snapshot_entries = interval_bytes = snapshot_bytes = 0
    for persona in personas(period):
        persona_change_list = persona_changes(period, persona)
        timeline = build_timeline(persona_change_list)
        changes += len(persona_change_list)
        versions += len(timeline.versions)
        interval_bytes += len(json.dumps([[v.domain, v.key, v.value, v.valid_from, v.valid_until] for v in timeline.versions]))
        for session in load_sessions(period, persona):
            state = timeline.state_after(session["session_id"])
            snapshot_entries += len(state)
            snapshot_bytes += len(json.dumps([[domain, key, value] for (domain, key), value in state.items()]))
    print(f"{period}: changes={changes} versions={versions} snapshot_entries={snapshot_entries} "
          f"intervals_json={interval_bytes / 1e6:.2f}MB snapshots_json={snapshot_bytes / 1e6:.2f}MB")
EOF
weekly: changes=540 versions=359 snapshot_entries=14273 intervals_json=0.03MB snapshots_json=1.07MB
monthly: changes=1682 versions=1011 snapshot_entries=97205 intervals_json=0.08MB snapshots_json=7.29MB
quarterly: changes=6446 versions=3937 snapshot_entries=970655 intervals_json=0.32MB snapshots_json=76.01MB
```

### Defectos del dataset

Encontrados con búsqueda de strings y revisión manual. Los ejemplos están en formato persona, sesión, turno.

| # | Defecto | Cuántos | Ejemplo real | Qué hace la verdad |
| -- | --- | --: | --- | --- |
| D1 | `value_update` en el que los turnos `share_memory` nunca nombran el ítem reemplazado; aparece solo en otros turnos, casi siempre en la pregunta del asistente, que "filtra" la memoria (en 12 de 13 casos, solo el asistente lo nombra) | weekly 1, monthly 3, quarterly 9 | `weekly/marketing_manager`, s86. t8 (asistente): "maybe from Taylor Swift to someone like SZA?"; t9 (usuario): "I'm really into SZA these days" | Aplica el remove: es lo que dice `operation_details`, y el evaluador de Memora pregunta por Taylor Swift como olvidado (`pref_music_general_156`). |
| D2 | Igual que D1, pero el ítem viejo no aparece en ningún turno | quarterly 1 | `quarterly/content_writer`, s1341: 1990s → 2000s; "1990s" no figura en la conversación | Igual que D1. |
| D3 | Un turno `share_memory=True` dice un hecho nuevo que `operation_details` no registra | 3 vistos a mano; de los 118 turnos weekly "sin mención", 2 en la muestra de 10 | `weekly/software_engineer`, s30, t14: "I'm leaning more towards upbeat electronic music now" (solo se registra el delete de Bonobo). `weekly/management_consultant`, s35, t15: "more into instrumental jazz lately". `weekly/academic_researcher`, s26, t12: "more drawn to places with ancient history and ruins, like Italy or Greece" | No es un hecho de la verdad. Un agente que lo recuerde no está equivocado, pero el examen no lo pregunta. |
| D4 | Texto del asistente etiquetado `user_agent` | 2–3 de 8 en una muestra de dos turnos de usuario seguidos (233 en weekly, 962 en monthly, 3.659 en quarterly son candidatos, no defectos confirmados) | `weekly/software_engineer`, s30, t15: "That sounds like a fun shift in taste!"; `weekly/financial_analyst`, s116, t9: "Yes, those are very popular. Some other widely used programs include CorelDRAW..." | No afecta a la verdad (ninguno tiene `share_memory=True`), pero sí a P3/P4 si leen la transcripción como "lo que dijo el usuario". |
| D5 | Turno de usuario duplicado, o dos turnos `share_memory` que se contradicen | 11 turnos `share_memory=True` justo después de otro turno de usuario (weekly 2, monthly 9) | `weekly/academic_researcher`, s104, t9/t10 repiten la misma frase. `weekly/software_engineer`, s138: t17 dice "I used to be all about action movies" y t18 "I used to be really into post-apocalyptic movies" (el `old_item` es post-apocalyptic) | La verdad sigue a `operation_details` (post-apocalyptic). |
| D6 | Fecha relativa del calendario que no coincide con el texto | 1 verificado; no lo conté de forma sistemática (calendario es dominio de P1a) | `weekly/software_engineer`, s87 (miércoles 2025-06-04): "next Tuesday at 10 AM" es +6 días, pero se guarda `"+7 days"` | Para P1a: decidir si la verdad usa `operation_details` o la fecha del texto. |
| D7 | `operation: "add"` con `actual_operation: "update"` en goals | weekly 0, monthly 66, quarterly 360 | `monthly/academic_researcher`, s156: `daily_steps` 7500 → 6000 | Si P1a lo extrae como add, sale `add_existing` y gana el valor nuevo, que es lo correcto. |
| D8 | Update de goal al mismo valor | monthly 4, quarterly 17 | `monthly/academic_researcher`, s326: `lunch` 115 → 115 | No abre una versión nueva (no-op). |
| D9 | Hueco en `session_id` | monthly 1 | `monthly/management_consultant`: falta la 579 (salta de 578 a 580) | `state_after(579)` devuelve lo mismo que `state_after(578)`. |
| D10 | `genres` existe en movies y en music, y `operation_details` no dice cuál | Sin colisiones en los tres períodos (0 `add_existing`) | `quarterly/software_engineer`, `("genres", "cyberpunk")` | La clave `(subcategory, item)` es ambigua. Para P1a: hoy no rompe nada, pero un mismo género en las dos categorías se fundiría en un solo hecho. |

Lo que **no** encontré en ningún período: `share_memory=True` en turnos del asistente, `share_memory=True` en sesiones `no_memory`, ni sesiones con memoria sin turnos `share_memory` (0 en los tres casos). Las 28 preferencias "add" que vienen de un update fallido (`fallback_reason`) en weekly no son defecto: revisé a mano las 4 cuyo texto sonaba a cambio ("lately"), y las 4 se leen como un add.

### Revisión manual de la muestra (weekly, `random.seed(2026)`)

- **10 cambios al azar con soporte `full`:** 10 de 10 coinciden en acción y en like/dislike con lo que dice el usuario. Por ejemplo, `startup_founder` s147 "I actually disliked the movie 'The Martian'" corresponde a add dislike; `software_engineer` s37 "Please remove that activity" corresponde a remove del todo.
- **Todos los `absent` y `partial`:**
  - Los `partial` son paráfrasis correctas: "Call family" frente a "I just got off the phone with my family"; "Plan literary event attendance" frente a "attendance at a literary event".
  - Los `absent` son D1/D2 (13 + 1), más 1 paráfrasis (`quarterly/content_writer` s107: "Exercise/walk for inspiration" frente a "go for a walk to clear my head and get some fresh ideas").
- **10 turnos `share_memory` que no mencionan el hecho:** 8 son el usuario explicando por qué (`academic_researcher` s10 t12: "the outback to the Great Barrier Reef", sobre Australia). 2 son hechos nuevos no registrados (D3).
- **10 turnos de usuario tras otro turno de usuario:** los 2 con `share_memory` son D5. De los 8 al azar, 2 son claramente texto del asistente (D4) y 1 es dudoso (`creative_designer` s136 t15: "I can understand that. Perhaps we can chat again sometime").

## 5. Opciones descartadas

- **Snapshot completo por sesión.** Con los dominios del stub ocupa 970.655 entradas (76 MB en JSON) en quarterly, contra 3.937 versiones (0,32 MB). Crece como sesiones × hechos vivos, y los hechos vivos crecen con el período (de 14 a 91 por persona). No responde mejor ninguna consulta: `state_after` sobre intervalos ya es instantáneo.
- **Registro de eventos sin derivar nada (reproducir `list[Change]` en cada consulta).** Es lo que hace `state_after(changes, N)` por compatibilidad con la interfaz, y anda bien. Como representación principal pierde `valid_from`, que es lo que permitió verificar las sesiones contra la evidencia de Memora. Además obliga a repetir la detección de inconsistencias en cada consulta.
- **Bitemporal completo (Graphiti).** El segundo eje (`created_at`/`expired_at`, cuándo se enteró el sistema) es idéntico al primero en Memora: nada se corrige hacia atrás. Sería un campo que siempre vale lo mismo.
- **Estados ACTIVE/STALE/UNKNOWN decididos por un modelo (CUPMem, de STALE).** Necesita un LLM (costo distinto de $0), y resuelve conflictos implícitos. En Memora los conflictos son explícitos: `operation_details` dice qué se agrega, cambia o borra, y la verdad coincide 1.069/1.069 con la evidencia del evaluador.
- **Estado "dudoso" para hechos inconsistentes.** No hay inconsistencias con los datos actuales. La lista `inconsistencies` ya identifica el hecho, así que P2 puede excluirlo sin que haga falta un tercer estado.
- **Usar `date` como reloj.** Muchas sesiones comparten fecha (unas 150 en 7 días en weekly), así que no ordena. Se usa `session_id`.

## 6. Limitaciones y preguntas abiertas

- **Todo lo medido cubre `preference` y `todo` (el stub).** La evidencia de calendario y de contenido sale `missing` / `never_in_truth` porque esos dominios todavía no se extraen. `evidence_check` ya queda listo como prueba de aceptación para P1a: cuando extienda el stub, `uv run python -m truth.timeline weekly` debería pasar esas familias a `in_truth` / `removed`.
- **Hipótesis "unos 26 hechos por persona en weekly": no se confirma con el stub.** Mido entre 8 y 20 (promedio 14,4) de preferencias y pendientes. Puede que el 26 contara otros dominios o ítems borrados; no lo pude reconstruir.
- **El matching de texto es heurístico** (raíz de 4 letras). Puede dar `full` por coincidencia ("plan" calza con "planet"). La muestra manual de 10 no encontró ningún falso `full`, pero la muestra es chica.
- **`evidence_check` compara strings**, así que confunde subcategorías cuando el mismo ítem aparece en dos (las 8 colisiones de arriba). Para preferencias, el chequeo inverso por `(subcategoría, ítem, like/dislike)` no tiene ese problema.
- **D4 (etiquetas de hablante) se detecta solo como candidato.** Separar texto de usuario de texto de asistente sin un modelo no es confiable; los conteos de `user_turn_after_user_turn` son una cota superior.
- **Para P2:** `changed_between` devuelve el cambio neto. Si el examen también quiere los valores intermedios (lo que entró y salió entre A y B), están en `timeline.versions` filtrando por `A < valid_from <= B` o `A < valid_until <= B`.
- **Para P1a:** D6 (fechas del calendario), D7 (goals con `actual_operation`) y D10 (`genres` ambiguo) son decisiones de extracción. La verdad las tolera sin cambios.
