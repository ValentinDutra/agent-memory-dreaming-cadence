# P1 · La verdad en cada momento

**Resultado.** Para cada persona y cada sesión N, `truth/` calcula de forma determinista qué hechos sobre el usuario son ciertos después de la sesión N. No usa ningún modelo.

- **Cobertura.** 7 dominios: preference, todo, calendar, expense, steps, goal y content.
- **Contra la evidencia de Memora.** La verdad reproduce la evidencia de **598 de 600** preguntas de evaluación: weekly 149/150, monthly 150/150, quarterly 299/300. Las 2 que no coinciden son defectos de Memora: un mismo nombre en dos subcategorías.
- **Consistencia interna.** Ningún cambio cae sobre un hecho inexistente ni sobre un valor anterior distinto: 0 inconsistencias en 27.614 sesiones.

| Rol | Ruta |
| --- | --- |
| Tag | `p1` |
| Interfaz | `docs/p1-interfaz.md` |
| Informe de P1a (extracción) | `docs/p1a-cambios.md` |
| Informe de P1b (representación y validación) | `docs/p1b-estado.md` |
| Extracción de cambios (P1a) | `truth/changes.py` |
| Verdad en el tiempo y validación contra el texto (P1b) | `truth/timeline.py` |
| Validación contra la evidencia de Memora (P1a) | `truth/evidence.py` |
| Tests (15) | `tests/test_changes.py`, `tests/test_timeline.py` |

Uso para P2–P7:

```python
from truth.changes import persona_changes
from truth.timeline import build_timeline

timeline = build_timeline(persona_changes("monthly", "software_engineer"))
timeline.state_after(300)            # {(domain, key): value}: lo cierto después de la sesión 300
timeline.changed_between(300, 350)   # {(domain, key): (antes, después)}: solo los cambios netos
timeline.versions                    # Version(domain, key, value, valid_from, valid_until)
timeline.inconsistencies             # vacío en weekly, monthly y quarterly
```

## 1. Problema

Memora publica las conversaciones. Para cada sesión publica además el cambio que su simulador le aplicó a la memoria: `session_type`, `operation` y `operation_details`. El estado de la memoria después de cada sesión no se publica. La verdad hay que reconstruirla aplicando esos cambios en orden, y después hay que comprobar que es confiable.

Ejemplo real, `weekly/academic_researcher`, el actor favorito:

| Sesión | `operation_details` | Lo que dice el usuario (`share_memory=True`) | Verdad después de la sesión |
| --: | --- | --- | --- |
| 5 | add `Joan Crawford`, like | — | le gusta Joan Crawford |
| 40 | `value_update` Joan Crawford → Grace Kelly | "I actually used to prefer Joan Crawford, but I've really come to appreciate Grace Kelly…" | le gusta Grace Kelly |
| 50 | `value_update` Grace Kelly → Rita Hayworth | "I used to really like Grace Kelly, but I've found myself much more drawn to Rita Hayworth lately" | le gusta Rita Hayworth |
| 88 | `preference_update` Rita Hayworth like → dislike | "I used to really like Rita Hayworth, but I've gone off her movies lately" | no le gusta Rita Hayworth |

Un dream que corrió por última vez después de la sesión 39 tiene una nota vieja ("le gusta Joan Crawford"). Para corregirla necesita saber el cambio neto entre la 39 y la 88: sale Joan Crawford y entra Rita Hayworth con dislike. Grace Kelly entró y salió en el medio, así que no hace falta anotarla. Eso es exactamente lo que devuelve `changed_between(39, 88)`.

Hay dos detalles que importan:

- **El reloj es `session_id`, no `date`.** En weekly hay unas 150 sesiones repartidas en 7 fechas.
- **Las preguntas de Memora tienen su propio sesgo.** Memora pregunta solo al final del período, y su `forgetting_evidence` identifica los hechos por nombre. Por eso no sirve como verdad sesión a sesión, pero sí como validación externa del estado final.

## 2. Opciones investigadas

Las fuentes primarias, con el detalle de qué se tomó de cada una, están en `docs/p1a-cambios.md` §2 y `docs/p1b-estado.md` §2.

| Tema | Opción | Fuente |
| --- | --- | --- |
| Qué es la verdad | La traza del simulador de Memora (estado antes y después de cada sesión) | Paper de Memora, https://arxiv.org/abs/2604.20006 §3.2; repo https://github.com/geniesinc/Memora (`data_generation/session_simulator.py`, `question_generation/unified_question_generator.py`) |
| Qué es un hecho | Ranuras `(dominio, slot)`, con lo viejo archivado como STALE | STALE, https://arxiv.org/abs/2605.06527; repo https://github.com/icedreamc/STALE |
| Conflictos | Hechos numerados en los que gana el más nuevo | MemoryAgentBench, https://arxiv.org/abs/2507.05257; repo https://github.com/HUST-AI-HYZ/MemoryAgentBench |
| Auditoría de la verdad | Un resolvedor last-write-wins encuentra respuestas oro inalcanzables | https://arxiv.org/html/2610.09193 (P1a solo leyó el resumen; P1b citó §3.3) |
| Representación en el tiempo | Intervalos de validez bitemporales en cada arista | Zep/Graphiti, https://arxiv.org/html/2501.13956 §2.2.3 |
| Representación en el tiempo | Historia de sesiones con `answer_session_ids` | LongMemEval, https://github.com/xiaowu0162/LongMemEval |
| Representación en el tiempo | Snapshot completo por sesión | Opción trivial; ningún benchmark la publica |

## 3. Análisis y elección

### P1a · Extraer los cambios: hechos atómicos clave → valor, gana la última escritura

Cada operación de Memora se convierte en `Change(add | update | remove)` sobre un hecho `(domain, key)`. Las claves son las mismas con las que el simulador identifica cada elemento.

| Dominio | Clave | Valor | Qué cambia con el tiempo |
| --- | --- | --- | --- |
| preference | `(category, subcategory, item)` | like / dislike | add, remove, flip like↔dislike, reemplazo (`value_update` = remove + add) |
| todo | `(description,)` | task_type | add, remove |
| calendar | `(event_name,)` | event_type, event_date = `created_at` + offset | add, update (reprogramación), remove |
| expense | `(session_id,)` | date, type, amount | solo add |
| steps | `(date,)` | step_count | solo add |
| goal | `(subcategory,)` | value | add, update (`actual_operation`) |
| content | `(doc, field)` o `(doc, field, element)` | value | add, update (presupuesto), remove (elemento) |

Decisiones clave, cada una verificada contra el código del simulador y los datos:

- **Delete de un gusto.** Borra el hecho; no lo convierte en dislike.
- **Listas `already_*`.** Son historial de consumo: solo se agregan (117 adds, 0 updates o deletes).
- **Categoría de la preferencia.** `operation_details` no la trae. Se toma del arquetipo de la persona, y eso ubica el 100% de los 1.076 `genres` ambiguos.
- **Agregados.** Los totales, promedios y metas cumplidas no son hechos: se derivan de los gastos y pasos atómicos, igual que en Memora.
- **Calendario.** Que un evento venza no es un cambio. "Próximo" se decide al hacer la consulta.
- **`operation_converted`.** La `operation` publicada ya es la operación que realmente corrió. Los `*_to_no_memory` no cambian nada.

### P1b · Representar y validar: intervalos de validez sobre `session_id`

- **Representación.** Cada valor que tuvo un hecho es una `Version(valid_from, valid_until)`, construida en una sola pasada.
- **Costo.** Ocupa O(cambios), no O(sesiones × hechos). `timeline.py` no menciona ningún dominio, así que los 5 dominios que agregó P1a funcionaron sin tocarlo.
- **Inconsistencias.** Cada `Change` se compara con el valor vigente: `add_existing`, `update_missing`, `remove_missing`, `previous_mismatch`. Si alguna aparece, gana lo más nuevo y queda registrada. Con los datos reales hay 0.

### Integración

- **Las ramas se fusionaron sin conflictos.** Lo único que cambió de la interfaz fue la clave de `preference`, que pasó de `(subcategory, item)` a `(category, subcategory, item)`. `timeline.py` no depende de la forma de la clave.
- **Las decisiones que P1b dejó abiertas para P1a quedaron resueltas por P1a:**
  - D6, fechas de calendario: se usa la regla de Memora.
  - D7, goals que en realidad son updates: se leen de `actual_operation`, y `old_value` coincide en 66 de 66.
  - D10, `genres` ambiguo: se resuelve con la categoría tomada del arquetipo.
- **Corregí un artefacto de la integración en `truth/timeline.py`.** El chequeo de texto de P1b buscaba el último componente de la clave, que en los dominios nuevos es un `session_id`, una fecha o un nombre de campo. Ahora `fact_mention` usa el monto, los pasos, el valor de la meta o el valor del campo, y `words` ignora los separadores de miles ("6,200" → "6200"). Efecto en weekly:

  | Medida (weekly) | Antes | Después |
  | --- | --: | --: |
  | Gastos con texto `full` | 4/224 | 222/224 |
  | Pasos con texto `full` | 0/70 | 70/70 |
  | Metas con texto `full` | 21/30 | 30/30 |
  | Turnos `share_memory` que no nombran ningún hecho cambiado | 461 | 118 |

  En monthly ese último número bajó de 1.600 a 241. Los 2 gastos `partial` que quedan son de formato ("$5" frente a 5.0).
- **Hay dos validadores contra Memora, y se usa `truth/evidence.py` (P1a) como el oficial.** El `evidence_check` de P1b compara nombres sin mirar el documento, así que en monthly marca 4 falsos "olvidado pero vivo": un stakeholder borrado de un documento sigue en otro (`business_executive`, "VP of Supply Chain Innovation" vive en `project_proposal_1`). Los revisé uno por uno. `truth/evidence.py` compara por documento y por familia de pregunta, y da 150/150. El de P1b sigue siendo útil porque compara el `valid_from` de cada hecho con el `session_id` de la evidencia.

## 4. Prueba

Una sola corrida del código integrado sobre todas las personas de weekly y monthly:

```
$ uv run pytest -q
...............                                                          [100%]
15 passed in 4.24s

$ /usr/bin/time -l uv run python -m truth.timeline weekly monthly
        1.85 real         1.60 user         0.18 sys
```

Hechos vivos después de la última sesión (salida real, recortada):

```
== weekly: facts alive after the last session, by persona
  academic_researcher       109  {'calendar': 1, 'content': 59, 'expense': 24, 'goal': 3, 'preference': 10, 'steps': 7, 'todo': 5}
  business_executive        130  {'calendar': 2, 'content': 87, 'expense': 19, 'goal': 2, 'preference': 11, 'steps': 7, 'todo': 2}
  ...
  startup_founder           118  {'calendar': 2, 'content': 70, 'expense': 23, 'goal': 2, 'preference': 14, 'steps': 7}
== weekly: inconsistencies none
...
== monthly: facts alive after the last session, by persona
  academic_researcher       412  {'calendar': 5, 'content': 267, 'expense': 85, 'goal': 5, 'preference': 18, 'steps': 28, 'todo': 4}
  business_executive        448  {'calendar': 3, 'content': 291, 'expense': 91, 'goal': 5, 'preference': 25, 'steps': 28, 'todo': 5}
  ...
== monthly: inconsistencies none
```

```
$ uv run python -m truth.evidence weekly monthly
| **total** | | 203/34/89 | 122/0/92 | 21/10/3 | 224/0/0 | 70/0/0 | 30/0/0 | 807/18/91 | | | | |
- sales_manager pref_travel_general_163: memory=True forgetting=False forgotten but not stale: ['Mediterranean']
| **total** | | 453/112/284 | 446/0/387 | 50/27/15 | 915/0/0 | 280/0/0 | 56/66/0 | 3133/151/518 | | | | |
```

Las tablas completas por persona están en `docs/p1a-cambios.md` §4. Las columnas son preference, todo, calendar, expense, steps, goal y content, cada una como add/update/remove.

### Números consolidados

| | weekly | monthly |
| --- | --: | --: |
| Sesiones | 1.551 (145–163 por persona) | 6.150 (601–635) |
| Sesiones que cambian algún hecho | 1.032 | 3.742 |
| Cambios add / update / remove | 1.477 / 62 / 275 | 5.333 / 356 / 1.204 |
| Hechos distintos por persona (mín–máx, media) | 134–154, 145,2 | 472–513, 493 |
| Hechos vivos al final por persona (mín–máx, media) | 109–130, 120,2 | 396–448, 412,9 |
| … de ellos, gustos + pendientes | 8–20, 14,4 | 14–32, 22,8 |
| Inconsistencias internas | 0 | 0 |
| Preguntas de Memora reproducidas | 149/150 | 150/150 |
| Cambios con soporte en el texto `share_memory`: full / partial / absent | 1.669 / 143 / 2 | 6.486 / 399 / 8 |

Quarterly, con el código integrado: `uv run python -m truth.timeline quarterly` tarda 7,5 s, usa 62 MB de RSS como máximo y da 0 inconsistencias. `uv run python -m truth.evidence quarterly` reproduce 299/300 preguntas; la que falla es `creative_designer pref_music_general_1991`, 'Vampire Weekend' (defecto 5).

**Cuántos hechos se vuelven viejos.** Son los que importan para el costo de soñar. La tabla cuenta, para todas las personas juntas, los hechos que existieron alguna vez y los que tuvieron al menos un valor que dejó de ser cierto:

| Dominio | weekly: existieron | weekly: quedaron viejos | monthly: existieron | monthly: quedaron viejos |
| --- | --: | --: | --: | --: |
| preference | 203 | 108 | 421 | 288 |
| todo | 102 | 79 | 215 | 200 |
| calendar | 21 | 9 | 49 | 28 |
| goal | 30 | 0 | 56 | 37 |
| content | 802 | 101 | 2.994 | 561 |
| expense | 224 | 0 | 915 | 0 |
| steps | 70 | 0 | 280 | 0 |

Gastos y pasos nunca quedan viejos: son solo de agregar. Todo lo que un dream tiene que corregir está en preference, todo, calendar, goal y content.

### Hipótesis heredadas

| Hipótesis | Veredicto |
| --- | --- |
| Unas 155 sesiones por persona en weekly y unas 615 en monthly | **Confirmada.** 145–163 (1.551 en total) y 601–635 (6.150). |
| Unos 26 hechos de gustos y pendientes por persona en weekly | **Aproximada.** Existieron alguna vez entre 27 y 33 (media 30,5); vivos al final, entre 8 y 20 (media 14,4). |
| Las fechas de calendario no coinciden con la conversación (s87: "+7 days" para "next Tuesday") | **Confirmada solo para reprogramaciones.** La s87 es un `update`: "next Tuesday" dicho un miércoles es +6 días, y Memora guarda +7. Los eventos nuevos coinciden en 71/71; las reprogramaciones, en 0/37. |
| s30: el turno 14 tiene `share_memory=True` sin registro, y el turno 15 es texto del asistente etiquetado `user_agent` | **Confirmada**, las dos partes. |
| `value_update` reemplaza un ítem; `preference_update` invierte like/dislike | **Confirmada.** 179 `value_update` y 146 `preference_update` en weekly+monthly. |

### Defectos del dataset

Ninguno rompe la verdad, porque la verdad sigue a `operation_details`. Los que afectan a P2–P4 son:

| # | Defecto | Cuántos | Ejemplo | Para quién importa |
| -- | --- | --: | --- | --- |
| 1 | Reprogramación de calendario cuya fecha no coincide con el texto | 37 (w+m), 47 (q) | weekly/academic_researcher s150: "next Tuesday" (06-10) frente a lo guardado (06-22) | P2: no preguntar la fecha de un evento reprogramado |
| 2 | Hecho nuevo en un turno `share_memory` que `operation_details` no registra | 3 confirmados; 2 de 10 en una muestra de los 118 turnos weekly sin mención | weekly/software_engineer s30 t14 "upbeat electronic music"; weekly/startup_founder s29 t18 "90s alternative rock" | P2: no penalizar a un agente que lo recuerde |
| 3 | Texto del asistente etiquetado como del usuario | 233 / 962 candidatos (w/m); en la muestra, 2 o 3 de cada 8 son reales | weekly/software_engineer s30 t15 | P3/P4: la transcripción no es solo "lo que dijo el usuario" |
| 4 | `value_update` cuyo ítem viejo solo nombra el asistente, o nadie | 13 + 1 (w+m+q) | weekly/marketing_manager s86: Taylor Swift aparece solo en la pregunta del asistente | P4: el dream tiene que leer también los turnos del asistente |
| 5 | Mismo nombre en dos subcategorías; Memora pide olvidar algo que también pide recordar | 2 preguntas (w+q) | weekly/sales_manager, "Mediterranean": la región se borró y el clima sigue vivo | P2: identificar los hechos por clave, no por nombre |
| 6 | `forgetting_evidence` de Memora incompleta | 146 flips de gusto y 109 presupuestos viejos no marcados (w+m) | weekly/academic_researcher s88, Rita Hayworth pasa de like a dislike | P2: la verdad propia es más estricta que FAMA |
| 7 | Ediciones de contenido que la conversación pide pero Memora no aplica | 13 (q) | quarterly/academic_researcher s295 | Solo quarterly |
| 8 | Hueco en `session_id` | 1 | monthly/management_consultant: falta la 579 | Ninguno: `state_after(579)` devuelve lo mismo que la 578 |

Revisé además una posible contradicción de polaridad en weekly/startup_founder s29 ("I used to really like 80s music, but I've gone off it"). Es un `delete` de "1980s: like", así que el texto coincide. Un escaneo con palabras clave negativas sobre las 282 sesiones de preferencias de weekly encontró 0 adds de like con texto negativo.

## 5. Opciones descartadas

| Opción | Por qué no sirve | Evidencia |
| --- | --- | --- |
| Snapshot completo por sesión | Crece como sesiones × hechos vivos y no responde mejor ninguna consulta | Quarterly, solo con gustos y pendientes: 76 MB contra 0,32 MB de intervalos (P1b §4) |
| Registro de eventos crudo como representación principal | Pierde "desde cuándo" vale cada valor y obliga a repetir la validación en cada consulta | Se mantiene como entrada (`list[Change]`) |
| Bitemporal completo (Graphiti) | El segundo eje coincide con el primero: en Memora nada se corrige hacia atrás | — |
| ACTIVE/STALE/UNKNOWN decidido por un modelo (CUPMem) | Cuesta llamadas a un modelo, y en Memora los conflictos son explícitos | 0 inconsistencias |
| Documento entero como un hecho | Memora evalúa y olvida por elemento, así que un solo cambio volvería viejo todo el documento | `forgetting_evidence` de contenido trae `(field, value)` |
| Agregados como hechos | Cada gasto nuevo volvería viejo el total, e inflaría la tasa de cambio | Memora también los deriva de la lista atómica |
| Extraer la verdad de la conversación | Cuesta llamadas a un modelo, contradice la traza y trae hechos sin registrar | 0/37 reprogramaciones coinciden; defecto 2 |
| Identificar hechos por nombre | Es la causa de las 2 discrepancias con Memora y de los 4 falsos positivos del `evidence_check` de P1b | "Mediterranean", "Vampire Weekend", stakeholders compartidos |
| Clave de preferencia sin categoría (el stub) | Hoy no colisiona, pero no dice si un género es de cine o de música, y las preguntas son por categoría | P1a §5 |
| Anclar las reprogramaciones en `updated_at` | Tampoco coincide con el texto y se aparta de la regla con la que evalúa Memora | s150: 06-26 contra 06-10 |
| Emitir un `remove` cuando un evento vence | No es una operación de Memora, y confundiría "olvidado" con "ya ocurrió" | P1a §5 |

## 6. Limitaciones y preguntas abiertas

- **La validación externa solo cubre el estado final.** Memora pregunta únicamente al final del período. Los estados intermedios se validan de forma indirecta: 0 precondiciones fallidas, los snapshots de contenido reconstruidos en cada sesión (964/964 en w+m) y el `valid_from` comparado con el `session_id` de la evidencia.
- **El chequeo de texto es heurístico:** compara raíces de 4 letras. Los 143 / 399 `partial` son casi todos campos largos de contenido parafraseados. La muestra manual es chica: 10 cambios `full`, 10 turnos sin mención y 8 turnos de usuario seguidos.
- **Las fechas de eventos reprogramados no se pueden verificar contra la conversación** (defecto 1). La verdad sigue la regla de Memora.
- **Queda una decisión para P2:** si el examen pregunta los 7 dominios o solo los que cambian. Expense y steps nunca quedan viejos, así que no miden nada sobre la cadencia de los dreams. Content es el 54–67% de los hechos vivos, y 101 (weekly) y 561 (monthly) de sus hechos quedan viejos alguna vez.
- **Hay dos validadores contra Memora con solapamiento** (`truth/evidence.py` y `timeline.evidence_check`). Se pueden unificar si P2 lo necesita; hoy el oficial es `truth/evidence.py`.
