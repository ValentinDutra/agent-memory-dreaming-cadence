# P2 · El examen

**Resultado.** Para cada persona hay un examen fijo, que depende solo de `(period, persona)` y de la verdad de P1. Se toma después de cada sesión múltiplo de 7, cubre los 7 dominios y se corrige con un script, sin modelo y sin costo.

- **Tamaño.** Weekly: 4.039 preguntas en 218 exámenes (18,5 por examen). Monthly: 18.214 preguntas en 873 exámenes (20,9 por examen).
- **Mezcla por dominio y examen.** Como máximo 2 `recent_change`, 1 `new`, 2 `stable` (uno con último cambio hace menos de 50 sesiones y otro de control, hace 50 o más), 1 `never_existed` y 1 `aggregate`.
- **Fase.** El paso 7 no comparte factores con 5, 20 ni 50. En monthly, las sesiones desde el último dream promedian 2,01 / 9,40 / 24,73 para las cadencias 5 / 20 / 50; el ideal uniforme es 2,0 / 9,5 / 24,5.
- **Corrección.** Normaliza la respuesta y la compara exacta. Cada respuesta cae en una de cinco clases: `correct`, `stale`, `missing`, `invented` o `unparseable`. Todos los conteos salen por (dominio, probe, clase).
- **Prueba de humo.** Tres agentes sintéticos sobre las 22.253 preguntas reales de weekly + monthly: perfecto, siempre "unknown" y siempre el valor anterior. Los tres dan **0 clases inesperadas**.
- **Bonobo después del borrado.** Lo correcto es `unknown`, "like" es `stale` y "dislike" es `invented` en el conteo oficial (estricto). La lectura laxa también se puede reportar (§6).

| Rol | Ruta |
| --- | --- |
| Tag | `p2` |
| Interfaz P2a/P2b | `docs/p2-interfaz.md`, `exam/schema.py` |
| Informe de P2a (qué preguntar y cuándo) | `docs/p2a-que-preguntar-y-cuando.md` |
| Informe de P2b (cómo corregir) | `docs/p2b-como-corregir.md` |
| Preguntas (P2a) | `exam/questions.py` (`build_exam`, `exam_sessions`, `EXAM_SEED`; CLI con estadísticas) |
| Corrección (P2b) | `exam/grading.py` (`render`, `expected_answer`, `grade`, `tally`, `tally_table`, `negates_removed_preference`) |
| Prueba de humo (P2) | `exam/smoke.py` |
| Tests (10 de P2; 25 con los de P1) | `tests/test_questions.py` (3), `tests/test_grading.py` (7) |

Uso para P3–P7:

```python
from exam.questions import build_exam
from exam.grading import grade, tally, tally_table

questions = build_exam("monthly", "software_engineer")   # igual para todas las políticas
exam_at_350 = [question for question in questions if question.session_id == 350]
# P3 contesta cada question.prompt leyendo solo las notas vigentes después de la sesión 350
grades = [grade(question, answer) for question, answer in zip(exam_at_350, answers)]
print(tally_table(tally(exam_at_350, grades)))           # (dominio, probe) × clase
```

## 1. Problema

Memora pregunta una sola vez, al final del período. Para medir la cadencia de los dreams hace falta preguntar en muchas sesiones N, sobre lo que el agente debería saber en ese momento. Además, el examen tiene que ser el mismo para todas las políticas, y su calendario no puede favorecer a ninguna cadencia. La corrección tiene que distinguir por qué falla cada respuesta.

Ejemplo real, weekly/software_engineer (verificado en la verdad de P1 y en el examen generado):

| Sesión | Verdad (P1) | Examen |
| --: | --- | --- |
| 17 | le gusta Bonobo | — |
| 30 | se borra Bonobo. El usuario dice: "I used to really like Bonobo, but I'm just not into his music anymore" | — |
| 35 | — | `recent_change`: "Does the user currently like or dislike 'Bonobo' (music artist)? Answer like, dislike, or unknown if the user has no current opinion." `history=(None, like)`, `current=None` |
| 82 | se agrega Mechanic visit (2025-06-15) | s84 `new`: se pregunta la fecha → `2025-06-15` |
| 87, 105 | se reprograma (defecto 1: la fecha guardada no coincide con lo que dijo el usuario) | a partir de la s91 solo se pregunta si existe |
| 129, 132 | deep house: se agrega como dislike y pasa a like | s133 `new`: `history=(None, dislike)`, `current=like` |
| 161 | gastos de la semana 2025-06-01 a 2025-06-07: 258,23 | `aggregate`: "247.93" (el total anterior) sale `stale` |

Las tres respuestas posibles en la s35 cuentan tres historias distintas. Con cadencia 50 no hubo ningún dream todavía, así que no hay nota. Con cadencia 20 hubo un dream después de la 20, cuando Bonobo valía: la nota dice "like" y la respuesta sale `stale`. Con cadencia 5 hubo un dream después de la 35: la nota ya no lo menciona y la respuesta es `unknown`, que sale `correct`.

### Hipótesis heredadas

| Hipótesis | Veredicto |
| --- | --- |
| Bonobo es "like" desde la 17 y desaparece en la 30 | **Confirmada.** `Version(preference, (music, artists, Bonobo), like, valid_from=17, valid_until=30)` |
| deep house invierte dislike→like en la 132 | **Confirmada.** Se agrega como dislike en la 129 y pasa a like en la 132. |
| Los cambios en Memora son explícitos, y eso facilita el dream | **Parcial**, medido con una heurística de palabras clave ("used to", "anymore", "no longer", "reschedul", "remove", "update", "revis"…) sobre los turnos `share_memory` de las sesiones con update o remove. Gustos: 123/123 en weekly y 396/396 en monthly. Content: 63/64 y 302/308. Calendar: 12/13 y 36/42. Todo: 83/92 y 359/387; las bajas implícitas son del tipo "I prepared the conference abstract". Goal: **8/66** en monthly; la meta nueva se enuncia sin mencionar la anterior ("I want to hit a goal of 6,000 steps per day"). Es una limitación para documentar: un dream que solo busque frases de cambio se pierde los updates de metas y los pendientes cumplidos. |

## 2. Opciones investigadas

El detalle, con las secciones citadas, está en P2a §2 y P2b §2.

| Fuente | Qué se tomó |
| --- | --- |
| Memora, https://arxiv.org/abs/2604.20006 §3.5 y §4.2; `vendor/Memora/data_generation/question_generation/` y `evals/model_eval/model_based_evaluator.py` | Preguntas armadas desde la traza del simulador, pero solo al final. Totales de la semana comparados al centavo (`${total_amount:.2f}`). Documentos nombrados por su título. FAMA = max(0, MPA − λ·(1−FAA)). Un gusto borrado tiene que estar *ausente* ("Does the response reflect or mention…" → no). El estado `unclear` del juez como precedente de `unparseable`. |
| MemoryAgentBench, FactConsolidation, https://arxiv.org/abs/2507.05257 §3.1 y App. B.4.2; https://github.com/HUST-AI-HYZ/MemoryAgentBench | Preguntas atómicas sobre la ranura que cambió, con respuesta corta. Varias preguntas por contexto (una llamada por examen). Corrección por SubEM normalizado, porque las respuestas "are mostly informational entities". |
| LongMemEval, https://arxiv.org/abs/2410.10813 §3; https://github.com/xiaowu0162/LongMemEval | Knowledge update. Abstention ("I don't know" ante algo nunca mencionado) → probe `never_existed` y opción `unknown` explícita en cada prompt. |
| STALE, https://arxiv.org/abs/2605.06527 §3 y App. E–F; https://github.com/icedreamc/STALE | Prompts que no presuponen el estado viejo (Premise Resistance). Filtro de distractores contra el texto. "Score 'false' if it assumes M_old is still true **or claims ignorance**". CUPMem: un valor invalidado sin reemplazo es `UNKNOWN_CURRENT`. |

## 3. Análisis y elección

### 3.1 Cuándo (P2a)

- **Examen después de cada sesión con `session_id % 7 == 0`.** El examen de N ve el dream de N: representa la primera pregunta de la sesión N+1.
- **Por qué 7.** Es coprimo con 5, 20 y 50, así que el examen recorre todas las fases del ciclo de cada cadencia. Un paso 10 con cadencia 20 dejaría el retraso siempre en {0, 10}.
- **Resultado medido** (salida completa en P2a §4):

| Cadencia | weekly: media (ideal) | weekly: restos | monthly: media (ideal) | monthly: restos |
| --: | --: | --: | --: | --: |
| 5 | 2,06 (2,0) | 5/5 | 2,01 (2,0) | 5/5 |
| 20 | 9,46 (9,5) | 20/20 | 9,40 (9,5) | 20/20 |
| 50 | 26,02 (24,5) | 23/50 | 24,73 (24,5) | 50/50 |

- **Disparado por contradicción.** P5 todavía no lo definió. Con el proxy "sesión con update o remove", la media es 3,2 sesiones (weekly) y 3,9 (monthly), sin alineación con el 7.

### 3.2 Qué y cuántas (P2a)

- **Sorteo.** `random.Random(f"{EXAM_SEED}/{period}/{persona}/{session_id}")` sobre candidatos ordenados. El examen es determinista e independiente de la política.
- **Probes**, definidos contra el examen anterior:
  - `recent_change`: valía y cambió o desapareció.
  - `new`: no valía y ahora vale.
  - `stable`: no cambió. Va en dos estratos: menos de 50 sesiones desde el último cambio (ahí se separan las cadencias 20 y 50) y 50 o más (control: todas las cadencias ya soñaron, así que un error es una nota buena rota o nunca escrita).
  - `never_existed`: distractor del arquetipo de la persona, filtrado contra todo el texto de sus conversaciones (defecto 2).
  - `aggregate`: total de la semana en curso.
- **Cómo se pregunta cada dominio:**

| Dominio | Forma | Defecto que evita |
| --- | --- | --- |
| preference | "currently like or dislike '{item}' ({categoría subcategoría})… or unknown if the user has no current opinion" | 5 ("Mediterranean" región/clima) |
| todo | "¿está en la lista?" | — |
| calendar | fecha (ISO) solo si nunca se reprogramó; si no, "¿está en el calendario?" | 1 (0/37 reprogramaciones coinciden con el texto) |
| goal | número | — |
| content | elemento de lista: "¿es uno de los {campo} de {documento '{título}'}?"; `budget`: número. La prosa larga no se pregunta: nunca cambia. | — |
| expense | monto por (fecha, tipo), solo si es único; más el total de la semana | el agente no conoce el `session_id` |
| steps | pasos por fecha; más el total de la semana | — |

### 3.3 Cómo corregir (P2b, con un cambio de P2)

- **Normalización.** Minúsculas, sin comillas ni punto final, `likes`→`like`, `y`/`n`. Números sin `$`, separadores de miles ni unidades, redondeados al centavo. Fechas a ISO. "I don't know", "not sure", "n/a", vacío o sin respuesta → `unknown`.
- **Sin tolerancia relativa en totales.** Con 1%, en monthly 291 de 905 totales anteriores pasarían por correctos (P2b §4).
- **Orden de decisión de `grade`:**
  1. `unparseable` si no parsea en el formato (choice fuera de las opciones, número no numérico).
  2. `correct` si es igual a `render(question, question.current)`.
  3. `missing` si es `unknown`.
  4. `stale` si es igual a lo que se habría contestado con algún estado anterior de `history`.
  5. `invented` en otro caso.
- **Cuándo `unknown` es correcto.** Solo cuando la respuesta esperada misma es `unknown`, o sea en preguntas de gusto sobre un gusto que no vale (borrado o `never_existed`): 302 preguntas en weekly y 1.138 en monthly.
- **Cambio de P2 sobre la regla de P2b.** P2b daba `unknown` = `correct` también en las preguntas "¿existe?" sobre algo que no vale: pendientes cerrados, elementos borrados, eventos cancelados y distractores. Lo cambié a `missing`, por tres razones:
  - **Hay una respuesta determinada.** Las listas son cerradas: una nota al día sabe que el pendiente ya no está y contesta "no".
  - **Una política sin notas aprobaba.** Contestando siempre "unknown" acertaba todas las bajas, 161 en weekly y 704 en monthly. Esas preguntas no la distinguían de una política que sí soñó.
  - **STALE lo respalda.** Su Dim 1 marca como falso el "claims ignorance" después de una invalidación.
  - **Lo que no cambia:** con un gusto la regla queda igual, porque "sin opinión actual" sí es el estado verdadero, y se mantiene la abstención de LongMemEval. El efecto sobre `never_existed` por existencia (643 en weekly, 2.605 en monthly) es que "no" sale `correct`, "yes" sale `invented` y "unknown" sale `missing`.
- **Sin juez LLM.** Todo lo que cambia es corto o cerrado. Los 522 textos largos de content solo se agregan y no se preguntan (P2b §3.4).

### 3.4 Gastos y pasos

Decidí que entraran en el examen, y quedan separados por dominio. Sus `recent_change` son 0, porque nunca cambian. Miden dos cosas:

- **El ítem suelto** (`new`/`stable`). Si un gasto nuevo todavía no llegó a las notas, la respuesta sale `missing`.
- **El total** (`aggregate`). Si a un total le faltan los gastos nuevos, coincide con un total anterior y sale `stale`.

Un error de suma sale `invented` dentro de `aggregate`, así que no se mezcla con los errores de memoria de los otros dominios.

## 4. Prueba

Integración: merge de las dos ramas, cambio de la regla de `unknown`, `exam/smoke.py` sobre el examen real y una línea más en el reporte de P2a (cuántos `recent_change` desaparecieron).

```
$ uv run pytest -q
.........................                                                [100%]
25 passed in 3.76s
```

### Estadísticas del examen

```
$ /usr/bin/time -l uv run python -m exam.questions weekly monthly
== weekly: exams every 7 sessions
  domain        recent_change            new         stable  never_existed      aggregate   total
  preference              112            138            340            218              0     808
  todo                     84             89            181            218              0     572
  calendar                  1             19            181            218              0     419
  goal                      0             21            209              0              0     230
  content                  85             99            332            207              0     723
  expense                   0            127            352              0            216     695
  steps                     0             67            323              0            202     592
  recent_change that disappeared (the rest changed value): preference 84, todo 84, calendar 1, goal 0, content 76, expense 0, steps 0
  total 4039 questions in 218 exams, 18.5 per exam, 133 prompt characters per question
...
== monthly: exams every 7 sessions
  domain        recent_change            new         stable  never_existed      aggregate   total
  preference              368            358           1608            873              0    3207
  todo                    344            343           1245            873              0    2805
  calendar                 15             49           1013            873              0    1950
  goal                     60             43           1096              0              0    1199
  content                  435            416           1625            859              0    3335
  expense                   0            502           1658              0            864    3024
  steps                     0            272           1626              0            796    2694
  recent_change that disappeared (the rest changed value): preference 265, todo 344, calendar 15, goal 0, content 345, expense 0, steps 0
  total 18214 questions in 873 exams, 20.9 per exam, 132 prompt characters per question
...
       11.75 real        11.30 user         0.18 sys
            58408960  maximum resident set size
```

Por persona hay entre 362 y 426 preguntas (weekly) y entre 1.725 y 1.920 (monthly). La tabla completa está en P2a §4.

Por tipo de respuesta (script ad hoc sobre `build_exam`):

| Dominio | weekly: ¿existe? | weekly: like/dislike | weekly: fecha | weekly: número | monthly: ¿existe? | monthly: like/dislike | monthly: fecha | monthly: número |
| --- | --: | --: | --: | --: | --: | --: | --: | --: |
| preference | 0 | 808 | 0 | 0 | 0 | 3.207 | 0 | 0 |
| todo | 572 | 0 | 0 | 0 | 2.805 | 0 | 0 | 0 |
| calendar | 281 | 0 | 138 | 0 | 1.206 | 0 | 744 | 0 |
| goal | 0 | 0 | 0 | 230 | 0 | 0 | 0 | 1.199 |
| content | 697 | 0 | 0 | 26 | 3.152 | 0 | 0 | 183 |
| expense | 0 | 0 | 0 | 695 | 0 | 0 | 0 | 3.024 |
| steps | 0 | 0 | 0 | 592 | 0 | 0 | 0 | 2.694 |
| **total** | **1.550** | **808** | **138** | **1.543** | **7.163** | **3.207** | **744** | **7.100** |

### Prueba de humo sin modelo

`exam/smoke.py` corrige tres agentes sintéticos sobre el examen real. Para cada pregunta, la clase esperada sale de la definición:

- Si la respuesta coincide con `render(current)`, la clase es `correct`.
- Si no coincide y es `unknown`, la clase es `missing`.
- Si no es ninguna de las dos, el valor viene de `history` y la clase es `stale`.

```
$ /usr/bin/time -l uv run python -m exam.smoke weekly monthly
== weekly: perfect (4039 questions, 0 unexpected outcomes)
== weekly: always unknown (4039 questions, 0 unexpected outcomes)
== weekly: previous state (4039 questions, 0 unexpected outcomes)
== monthly: perfect (18214 questions, 0 unexpected outcomes)
== monthly: always unknown (18214 questions, 0 unexpected outcomes)
== monthly: previous state (18214 questions, 0 unexpected outcomes)
       12.15 real        11.63 user         0.19 sys
            69238784  maximum resident set size
```

Por dominio, monthly (weekly tiene la misma forma; salida completa con `uv run python -m exam.smoke weekly monthly`):

| Dominio | perfecto: correct | siempre unknown: correct / missing | valor anterior: correct / stale / missing |
| --- | --: | --: | --: |
| preference | 3.207 | 1.138 / 2.069 | 873 / 623 / 1.711 |
| todo | 2.805 | 0 / 2.805 | 873 / 1.932 / 0 |
| calendar | 1.950 | 0 / 1.950 | 1.184 / 22 / 744 |
| goal | 1.199 | 0 / 1.199 | 0 / 442 / 757 |
| content | 3.335 | 0 / 3.335 | 859 / 2.457 / 19 |
| expense | 3.024 | 0 / 3.024 | 0 / 832 / 2.192 |
| steps | 2.694 | 0 / 2.694 | 0 / 671 / 2.023 |

`invented` y `unparseable` dan 0 en los tres agentes, porque ninguno inventa ni rompe el formato. Esas dos clases están probadas en `tests/test_grading.py` con casos reales:

- Bonobo: "dislike" sale `invented` y "maybe" sale `unparseable`.
- deep house en la s131: "like" sale `invented`.
- "Renew passport": "yes" sale `invented`.
- Total de la s161: "258.24" sale `invented` y "a lot" sale `unparseable`.

Cómo leer "valor anterior", con detalle por probe en la salida del script:

- **Preference:** las 873 `correct` son los `never_existed`; "valor anterior" contesta "unknown", que ahí es lo correcto. Los 368 `recent_change` salen todos `stale`, y los `new` salen `missing` (355 de 358; los otros 3 se agregaron y se invirtieron entre dos exámenes, como deep house, y salen `stale`; por ejemplo monthly/software_engineer s7, Sandra Bullock like → dislike).
- **Todo y content:** "¿existe?" sobre algo nuevo → "no" → `stale` (P2a §3.3: en `new` por existencia hay que leer `stale + missing` juntos).
- **Calendar:** 310 `stable` y 1 `new` salen `correct` con el valor anterior. Son eventos reprogramados que se preguntan por existencia, y la existencia no cambia con la reprogramación (ver §6).
- **Expense y steps:** los ítems sueltos no tienen valor anterior, así que salen `missing`. Los totales salen `stale` (832 y 671), salvo el primer total de cada semana.

## 5. Opciones descartadas y por qué

| Opción | Por qué no | Dónde |
| --- | --- | --- |
| Examinar solo al final (Memora) | Un solo punto por persona, con una fase fijada por el largo del período | P2a §5 |
| Paso múltiplo de una cadencia (10) | Con cadencia 20, el retraso queda en {0, 10} | P2a §5 |
| Paso 21 en monthly | Un tercio del costo, pero 21 ≡ 1 (mod 20) deja la cadencia 20 en media 8,10 | P2a §3.1 |
| Sesiones al azar con semilla | Son uniformes solo en esperanza; el paso coprimo es uniforme por construcción | P2a §5 |
| Examen antes del dream de la misma sesión | Suma 1 de retraso a todas las políticas, y ningún cambio de N sería acertable | P2a §3.1 |
| `stable` sin estratos, o solo de 50 o más | Las antigüedades 7–49, donde se separan 20 y 50, quedarían sin muestra | P2a §3.2 |
| Fecha de eventos reprogramados | La verdad contradice al usuario en 37/37 | P1 defecto 1 |
| Gasto por ordinal o por existencia con el monto en el prompt | Es ambiguo, o el prompt filtra la respuesta | P2a §5 |
| Una llamada por pregunta | Monthly costaría ≈ 970 M tokens contra ≈ 47 M por examen | P2a §3.2 |
| Juez LLM | Cuesta 1 llamada por pregunta y trae 3–12% de desacuerdo con humanos. Todo lo que cambia es corto o cerrado. | P2b §3.4 |
| Substring match (MemoryAgentBench) | "dislike" contiene "like" | P2b §5 |
| Tolerancia relativa en totales | Con 1%, 291/905 totales viejos pasarían por correctos en monthly | P2b §3.1 |
| "dislike" como correcto después de un borrado | El 96% de los borrados no expresa disgusto, y P1, Memora y FAMA lo tratan como ausencia. Queda como lectura laxa. | P2b §3.3 |
| `unknown` = `correct` en "¿existe?" sobre algo que no vale (regla original de P2b) | Una política sin notas acertaba todas las bajas (161 en weekly y 704 en monthly), y STALE marca el "claims ignorance" como falso | §3.3 |
| Respuesta no parseable como `invented` o `missing` | Mezcla una falla de formato de P3 con un error de memoria | P2b §3.2 |

## 6. Limitaciones y preguntas abiertas

- **Decisión: "dislike" después de un gusto borrado.** El conteo oficial lo marca `invented` (estricto). `negates_removed_preference` marca esos casos, así que P7 puede reportar también la tasa laxa (`invented` → `correct`). Puede tocar como máximo los `recent_change` de gustos borrados: 84 en weekly y 265 en monthly. El riesgo del estricto es que penaliza a una política que sí actualizó la nota ("ya no le gusta") cuando P3 la lee como "dislike". La redacción "unknown if the user has no current opinion" busca evitarlo. Recomiendo estricto como oficial y laxo como columna adicional.
- **Calendario mide poco.** Hay 1 (weekly) y 15 (monthly) `recent_change`, todos bajas. Las reprogramaciones no se pueden preguntar por fecha (defecto 1), y por existencia no quedan viejas: 310 `stable` de monthly no distinguen una nota vieja de una al día.
- **Celdas chicas.** goal tiene 0 `recent_change` en weekly y 60 en monthly. La cadencia se mide sobre todo en monthly, con preference, todo y content (IC 95% de unos ±5 pp por dominio).
- **`new` por existencia** (186 en weekly y 756 en monthly): un hecho nuevo que no llegó a las notas sale `stale` si el agente dice "no" y `missing` si dice "unknown". Para la cadencia hay que leer `stale + missing` juntos.
- **Weekly y la cadencia 50.** Con unos 22 exámenes por persona se cubren 23/50 fases (media 26,0 contra 24,5). Hay como mucho 3 dreams por persona, así que la cadencia 50 en weekly es casi "sin dreaming".
- **Correlación.** Los `stable` se repiten entre exámenes vecinos (Mechanic visit sale en 8 exámenes seguidos). El n efectivo es menor que el de las tablas, así que P7 debería usar bootstrap por persona.
- **Disparador por contradicción.** La fase se midió con un proxy; hay que repetir la medición cuando P5 lo defina.
- **Costo de P3.** Es una cota superior, con la verdad completa como proxy de las notas: con una llamada por examen y por política, ≈ 4,2 M tokens de entrada en weekly y ≈ 46,6 M en monthly (P2a §3.2). Lo que más pesa son las notas, no las preguntas.
- **Antigüedad del hecho.** No está en `Question`. P7 la puede recalcular desde el timeline. No agregué `changed_at` (YAGNI).
- **Hechos que el usuario dijo y Memora no registró (defecto 2).** No pueden ser distractores, pero tampoco se preguntan. Un agente que los recuerde no gana ni pierde puntos.
- **Normalización.** Acepta fechas ISO y "June 11, 2025"; no acepta "06/11/2025" ni números escritos en palabras. P3 tiene que pedir ISO y dígitos.
- **Scripts de P2a en `/tmp`.** P2a usó scripts descartables en `/tmp` para algunas tablas de su informe (estratos de `stable`, tamaño de las notas). No están versionados; las tablas de este informe salen de `exam/questions.py`, `exam/smoke.py` y scripts inline cuyo resultado se muestra.

## Decisiones

- **"dislike" después de un gusto borrado (2026-11-12).** Cuenta como `invented` en el conteo oficial (estricto), como recomendaba §6. La lectura indulgente, en la que esos casos pasan a `correct`, se reporta **siempre** como columna extra, calculada con `negates_removed_preference(question, grade)`. Ejemplo: weekly/software_engineer s35, Bonobo borrado en la s30; "dislike" es `invented` en la cuenta oficial y `correct` en la indulgente.
- **Preguntas que ningún sueño puede acertar: opción (c) (2026-11-12, registrada al empezar P5).** No se sacan del examen ni cambia `exam/questions.py`, así que el examen y su caché siguen iguales. Se **marcan** con una regla determinista, sin modelo, en `exam/unreachable.py` (`unreachable(period, persona) -> {question_id: motivo}`), y todo resultado se reporta **con y sin** ellas. La regla lee la verdad y las transcripciones:
  - **`unsaid_item`:** pregunta "¿está X en la lista?" (pendientes, calendario, elementos de documentos) mientras X vale, y la sesión donde X empezó a valer no dice todas las palabras de X (raíz de 4 letras, `truth.timeline.text_support`). Ejemplo: s44 de monthly/academic_researcher, el usuario dice "Mr. David Kim"; Memora guarda "Mr. David Kim (Systems Integration Lead, Engineering Department)" y el examen lo pregunta así en la s49.
  - **`relative_date`:** un gasto que el usuario dio en un turno con "last night" o "yesterday". Memora lo fecha siempre el día de la sesión (5 gastos en weekly, 34 en monthly; ningún registro de pasos se fecha así). Se marca la pregunta por ese gasto, el total semanal cuyo primer día es ese día y, desde P6a, la pregunta por el mismo tipo de gasto el día anterior una vez registrado el "last night" (ese día el usuario declaró dos). Un turno que además dice "today" no cuenta ("a $9.81 lunch today, mostly leftovers from yesterday", monthly/creative_designer s132; P6a). Ejemplo: monthly/startup_founder s112 (2025-06-06), "I spent $27.04 on dinner last night".
  - **`completed_task`:** pregunta "¿está X en la lista de pendientes?" mientras X vale, cuando Memora agregó X en una sesión donde un turno del usuario que nombra X dice que lo terminó, en pasado ("completed", "finished", "done with", "wrapped up", "took care of", "crossed off"). Ejemplo: s25 de monthly/academic_researcher, "I completed a task to coordinate with the research team"; Memora lo guarda como *alta* y la s28 pregunta si está en la lista. Es el ejemplo que P4 había atribuido a una paráfrasis. Revisión manual: la regla encuentra **1 caso en monthly y 0 en weekly**, y ese caso es correcto. Una regla más amplia (cualquier "complete", "finish" o "done" en un turno del usuario de la sesión del alta) no es confiable: agarra anuncios como "I need to complete logo design concepts by the end of the day" (monthly/creative_designer s461) y charla como "Just getting some things done". Queda sin marcar un caso dudoso: weekly/content_writer s3, "I also need to update the content calendar for work today" seguido de "I've actually completed all my tasks for today!", que no nombra la tarea.
  - **Paráfrasis: no se marcan.** Un ítem dicho con otras palabras se puede escribir y reconocer, y la mayoría se contesta bien: marcarlas sacaría 366 de las 2.805 preguntas de pendientes de monthly (13 %). El reporte las cuenta en la última columna.

  Preguntas marcadas (`uv run python -m exam.unreachable weekly monthly`):

  | Dominio | weekly: preguntas | weekly: marcadas | monthly: preguntas | monthly: marcadas | monthly: dichas con otras palabras (sin marcar) |
  | --- | --: | --: | --: | --: | --: |
  | preference | 808 | 0 | 3.207 | 0 | 0 |
  | todo | 572 | 5 (0,9 %) | 2.805 | 8 (0,3 %; 7 `unsaid_item` + 1 `completed_task`) | 366 |
  | calendar | 419 | 0 | 1.950 | 0 | 0 |
  | goal | 230 | 0 | 1.199 | 0 | 0 |
  | content | 723 | 57 (7,9 %) | 3.335 | 164 (4,9 %) | 137 |
  | expense | 695 | 89 (12,8 %) | 3.024 | 254 (8,4 %) | 0 |
  | steps | 592 | 0 | 2.694 | 0 | 0 |
  | **total** | **4.039** | **151 (3,7 %)** | **18.214** | **426 (2,3 %)** | **503** |

  En weekly, `relative_date` pesa mucho por los totales: el período entero es una semana, así que un gasto "last night" del primer día entra en todos los totales de esa persona (21 de management_consultant y 22 de startup_founder salen de un solo gasto cada uno). Test: `tests/test_unreachable.py`.
