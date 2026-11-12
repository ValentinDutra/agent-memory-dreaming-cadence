# P2a · Qué preguntar y cuándo

> **Nota de integración (P2).** Con la regla final de corrección, `unknown` en una baja preguntada por existencia sale `missing`, no `correct` (§6, segundo punto, queda resuelto así). El reporte del CLI agrega cuántos `recent_change` desaparecieron. Ver `docs/p2-examen.md` §3.3.

**Resultado.** `exam/questions.py` arma un examen fijo por `(period, persona)`:

- **Cuándo.** Se examina después de cada sesión múltiplo de 7.
- **Qué.** En cada examen y en cada uno de los 7 dominios entran como máximo 2 `recent_change`, 1 `new`, 2 `stable` (uno por estrato de antigüedad), 1 `never_existed` y 1 `aggregate`.
- **Tamaño.** Weekly: 4.039 preguntas en 218 exámenes. Monthly: 18.214 preguntas en 873 exámenes.
- **Fase.** Para cada cadencia fija, las sesiones desde el último dream quedan casi uniformes. En monthly la media es 2,01 / 9,40 / 24,73 para las cadencias 5 / 20 / 50; el ideal uniforme es 2,0 / 9,5 / 24,5.
- **Chequeo.** En las 22.253 preguntas, `grade(q, render(q, q.current))` da `correct`. En las de `recent_change`, `grade(q, render(q, q.history[-1]))` da `stale`.

| Rol | Ruta |
| --- | --- |
| Código | `exam/questions.py` (`EXAM_SEED`, `exam_sessions`, `build_exam`, CLI) |
| Tests (3) | `tests/test_questions.py` |
| Contrato | `docs/p2-interfaz.md` |

## 1. Problema

Hay que examinar al agente en muchas sesiones N, no solo al final como Memora. En cada N hay que preguntar lo que el agente debería saber en ese momento. Y el examen no puede favorecer a ninguna cadencia de dreaming.

Ejemplo real, weekly/software_engineer:

| Sesión | Qué pasa en la verdad (P1) | Qué pregunta el examen |
| --: | --- | --- |
| 17 | le gusta Bonobo | — |
| 28 | examen | — (Bonobo no salió sorteado) |
| 30 | se borra Bonobo | — |
| 35 | examen | `recent_change`: "Does the user currently like or dislike 'Bonobo' (music artist)? Answer like, dislike, or unknown if the user has no current opinion." `history=(None, like)`, `current=None` |
| 82 | se agrega Mechanic visit (2025-06-15) | — |
| 84 | examen | `new`: "On what date is the user's event 'Mechanic visit' scheduled?" → 2025-06-15 |
| 87, 105 | reprogramaciones (defecto 1: la fecha guardada no coincide con el texto) | a partir de la 91 se pregunta solo si existe, nunca la fecha |
| 129, 132 | deep house: se agrega como dislike y pasa a like | s133 `new`: `history=(None, dislike)`, `current=like` |

Una política que sueña cada 50 sesiones (después de la 50 y de la 100) llega a la s35 sin ningún dream. Con la cadencia 5 hubo un dream después de la 30 y otro después de la 35. Lo que el examen mide es esa diferencia.

Hay tres trampas de diseño:

- **La fase del calendario.** Si se examina cada 10 sesiones y se sueña cada 20, el examen cae siempre justo después de soñar o justo a mitad de ciclo. El retraso queda en {0, 10} y no en 0–19.
- **La identificación.** El agente no conoce el `session_id` de un gasto, y "Mediterranean" es a la vez una región y un clima.
- **Los distractores.** Un hecho que "nunca existió" puede ser algo que el usuario sí dijo y Memora no registró (defecto 2).

## 2. Opciones investigadas

| Fuente | Qué hace | Qué tomé |
| --- | --- | --- |
| Memora, https://arxiv.org/abs/2604.20006 §3.5 y §4.2; código en `vendor/Memora/data_generation/question_generation/unified_question_generator.py` | Arma las preguntas desde la traza del simulador y **solo en el último snapshot**: `extract_memory_snapshots` dice "All timeline types extract ONLY the final snapshot". Son 15 preguntas por persona (5 remembering, 5 reasoning, 5 recommending; ver `data/weekly/software_engineer/evaluation_questions_software_engineer.json`), cada una con criterios de *memory presence* y *forgetting absence*. FAMA = max(0, MPA − λ·(1−FAA)), con λ = N_forget / (N_presence + N_forget) por pregunta. | Los dominios y la verdad desde la traza. Los totales de la semana, porque Memora pregunta "What is my total food spending this week?" y "How many total steps have I taken this week?". La identificación de los documentos por título (`_generate_content_question_text`: `project_title`, `email_purpose`, `meeting_title`). La idea de FAMA de castigar lo viejo, que en P2b es `stale`. |
| MemoryAgentBench, https://arxiv.org/abs/2507.05257 §3.1 "Datasets for Selective Forgetting" y apéndice B.4.2; https://github.com/HUST-AI-HYZ/MemoryAgentBench | FactConsolidation usa pares contrafácticos de MQuAKE: el hecho viejo con número de serie menor y el nuevo con uno mayor. La pregunta es de un solo salto ("Which country was tool AA created in?") o multi-salto, y se corrige por SubEM. Varias preguntas comparten el mismo contexto: "multiple questions follow a single context" (LME(S\*): 5 contextos, 300 preguntas). | Preguntas atómicas y cortas sobre la ranura que cambió, con respuesta de un token. Hacer varias preguntas por contexto, lo que permite responder un examen entero en una sola llamada (§3, costo). |
| LongMemEval, https://arxiv.org/abs/2410.10813 §3.1 y apéndice del juez; https://github.com/xiaowu0162/LongMemEval | Knowledge update (KU). Abstention (ABS): 30 preguntas "false premise" sacadas de los otros tipos, donde lo correcto es "I don't know". El juez de KU acepta la respuesta "if the response contains some previous information along with an updated answer". | `never_existed` como abstención: preguntas sobre hechos plausibles que nunca valieron. Opción `unknown` explícita en todos los prompts. |
| STALE, https://arxiv.org/abs/2605.06527 §1 y §3; https://github.com/icedreamc/STALE | Cada conflicto se sondea en tres dimensiones: State Resolution, Premise Resistance (la consulta presupone el estado viejo) e Implicit Policy Adaptation. Cada dimensión se consulta "separately … preventing information leakage across dimensions". Los distractores se filtran para que no contradigan ni actualicen el hecho. | Prompts que **no** presuponen el estado: "currently like or dislike … or unknown". El filtro de distractores contra el texto, que en STALE se hace sobre las sesiones de relleno. |

Cuándo examinar, opciones:

1. Solo al final, como Memora.
2. Cada K sesiones con K múltiplo de alguna cadencia.
3. Sesiones al azar con semilla.
4. Cada K sesiones con K coprimo con 5, 20 y 50.

Qué preguntar de gastos: ítem por `(fecha, tipo)` cuando es único, el total diario por tipo, la existencia con el monto en el prompt, o el orden ("el segundo café del día").

## 3. Análisis y elección

### 3.1 Cuándo: cada 7 sesiones, después de la sesión y después del dream de esa sesión

- **El paso 7 no comparte factores con 5, 20 ni 50.** Por eso 7·k mod K recorre todos los restos antes de repetir. Un examen cae justo después de soñar 1 de cada K veces y no siempre.
- **No depende de la fase de P5.** Si P5 sueña después de las sesiones s ≡ c (mod K) para otra fase c, los restos solo se rotan y la distribución queda igual.
- **Medido (salida completa en §4):**

| Cadencia | Período | Media de sesiones desde el último dream | Ideal uniforme | Restos alcanzados |
| --: | --- | --: | --: | --: |
| 5 | weekly | 2,06 | 2,0 | 5/5 |
| 20 | weekly | 9,46 | 9,5 | 20/20 |
| 50 | weekly | 26,02 | 24,5 | 23/50 (hay ~22 exámenes por persona y todas usan la misma fase) |
| 5 | monthly | 2,01 | 2,0 | 5/5 |
| 20 | monthly | 9,40 | 9,5 | 20/20 |
| 50 | monthly | 24,73 | 24,5 | 50/50 |
| 1 | ambos | 0 | 0 | — |

**Disparado por contradicción.** P5 todavía no definió el disparador. Como aproximación, tomé "una sesión que hace update o remove de un hecho". Las sesiones desde ese disparador hasta el examen dan:

| Período | Media | Mediana | Retraso 0 | Máximo |
| --- | --: | --: | --: | --: |
| weekly | 3,19 | 2 | 21 % | 15 |
| monthly | 3,85 | 2 | 20 % | 28 |

No hay alineación artificial con el 7.

**El orden "examen después de la sesión N, dream después de la sesión N, el examen ve el dream" está bien y lo mantengo.**

- **Es realista.** El dream corre offline entre sesiones, y el examen de N representa la primera pregunta del usuario en la sesión N+1.
- **El orden inverso** (examinar antes del dream de N) solo suma 1 al retraso de todas las políticas.
  - La cadencia 1 dejaría de ser "siempre al día" y ninguna política podría acertar un cambio de la sesión N.
  - Eso agrega ruido igual para todas y no informa nada.
- **Lo que sí importa es la fase**, y la resuelve el paso coprimo.

**Paso 7 en ambos períodos.** Con el mismo paso, un `recent_change` siempre tiene entre 0 y 6 sesiones de antigüedad, y weekly y monthly se pueden comparar. Probé 21 en monthly:

| Paso en monthly | Exámenes | Preguntas | Cadencia 20: media del retraso (ideal 9,5) |
| --: | --: | --: | --: |
| 7 | 873 | 18.214 | 9,40 |
| 21 | 287 | 6.965 | 8,10 |

Con 21 los exámenes bajan a un tercio y los `recent_change` de preferencias quedan en 292 (con 7 son 368). Pero como 21 ≡ 1 (mod 20) y hay ~29 exámenes por persona, los retrasos 1–9 de la cadencia 20 salen el doble de veces que los demás. Por eso me quedo con 7.

### 3.2 Qué y cuántas: cuotas por dominio y examen

| Probe | Qué es | Cuota |
| --- | --- | --- |
| `recent_change` | Valía en el examen anterior y ahora cambió o desapareció | 2 |
| `new` | No valía en el examen anterior y ahora vale | 1 |
| `stable`, estrato < 50 | Sin cambios desde el examen anterior, último cambio hace menos de 50 sesiones | 1 |
| `stable`, estrato ≥ 50 | Sin cambios desde hace 50 sesiones o más | 1 |
| `never_existed` | Hecho plausible que nunca valió (preference, todo, calendar, content) | 1 |
| `aggregate` | Total de la semana en curso (expense, steps) | 1 |

- **El sorteo** usa `random.Random(f"{EXAM_SEED}/{period}/{persona}/{session_id}")` sobre candidatos ordenados. El examen no depende de la política ni del orden de ejecución.
- **El estrato ≥ 50 es el control.** Cualquier intervalo de 50 sesiones contiene un dream de cada cadencia fija ≤ 50, así que todas las políticas que sueñan ya tuvieron oportunidad de escribir la nota. Un error ahí es una nota buena que el dream rompió o nunca escribió bien.
- **El estrato < 50 cubre el hueco de antigüedades 7–49.** Ahí la cadencia 20 ya alcanzó la nota y la cadencia 50 todavía no. Sin este estrato, ninguna pregunta separaría 20 de 50: `recent_change` tiene 0–6 sesiones de antigüedad, y ahí las dos casi nunca soñaron.

Tamaño resultante para cada política:

| Período | Preguntas | Exámenes | Por examen | Respuestas (6 políticas) |
| --- | --: | --: | --: | --: |
| weekly | 4.039 | 218 | 18,5 | 24.234 |
| monthly | 18.214 | 873 | 20,9 | 109.284 |

**Error por dominio.** El IC 95 % para una proporción cercana a 0,5 es ±1,96·√(0,25/n).

| Celda | n | IC 95 % |
| --- | --: | --: |
| monthly `recent_change` preference | 368 | ±5,1 pp |
| monthly `recent_change` todo | 344 | ±5,3 pp |
| monthly `recent_change` content | 435 | ±4,7 pp |
| monthly `recent_change` goal | 60 | ±12,7 pp |
| monthly `recent_change` calendar | 15 | ±25 pp |
| weekly `recent_change` preference | 112 | ±9,3 pp |
| weekly `recent_change` content | 85 | ±10,6 pp |
| weekly `recent_change` calendar | 1 | — |
| weekly `recent_change` goal | 0 | — |
| `stable` (cualquier dominio, monthly) | > 1.000 | — |
| `never_existed` (cualquier dominio, monthly) | > 800 | — |

- **El límite son los datos, no la cuota.** Weekly tiene 0 updates de metas. Ninguna de sus 10 reprogramaciones de calendario se pregunta por fecha (defecto 1). De sus 3 bajas de eventos, 2 se agregan y se borran entre dos exámenes (financial_analyst 50→52, marketing_manager 99→100), así que no hay cambio neto que preguntar.
- **La cadencia se mide sobre todo en monthly.** Weekly sirve para preference, todo y content.

**Costo estimado.** No llamé a ningún modelo. Supongo una llamada por examen y por política, como en MemoryAgentBench. Como proxy del tamaño de las notas usé la verdad completa de P1 renderizada en una línea por hecho (`/tmp/p2a_notes_size.py`): weekly ≈ 2.257 tokens por examen (máximo 17.052 caracteres) y monthly ≈ 7.907 (máximo 56.158 caracteres).

| Período | Llamadas | Tokens de entrada por llamada | Entrada total | Salida total |
| --- | --: | --- | --: | --: |
| weekly | 218 × 6 = 1.308 | ≈ 300 de instrucciones + 2.257 de notas + 615 de preguntas (18,5 × 133 caracteres / 4) ≈ 3.200 | ≈ 4,2 M | ≈ 0,2 M (~8 por respuesta) |
| monthly | 873 × 6 = 5.238 | ≈ 300 + 7.907 + 690 ≈ 8.900 | ≈ 46,6 M | ≈ 0,9 M |

- **Las notas pesan 4 a 11 veces más que las preguntas.** Bajar preguntas casi no cambia el costo. Lo que lo mueve es la cantidad de exámenes.
- **La política sin dreaming tiene notas vacías**, así que estos totales son una cota superior.
- **Con una llamada por pregunta**, monthly pasaría a ≈ 970 M tokens. P3 tiene que responder por examen.

### 3.3 Cómo preguntar cada dominio

| Dominio | Pregunta (`field`, `answer_format`) | Por qué |
| --- | --- | --- |
| preference | "Does the user currently like or dislike '{item}' ({categoría y subcategoría})? Answer like, dislike, or unknown if the user has no current opinion." (`preference`, choice) | Va por clave completa: la etiqueta dice "travel region" o "travel climate", así que "Mediterranean" no es ambiguo (defecto 5). Pide la opinión **actual** y explica la abstención, como necesita P2b. No presupone el estado (STALE, Premise Resistance). |
| todo | "Is the task '{description}' currently on the user's to-do list?" (existencia) | El único valor es `task_type`, que se adivina por el nombre ("Fix critical bug" → trabajo). |
| calendar | Fecha (`event_date`, value) **solo si el evento nunca se reprogramó hasta N**. Si no, o si fue borrado, existencia. | Las altas coinciden con el texto 71/71; las reprogramaciones, 0/37 (P1 §4, defecto 1). Una reprogramación no entra como `recent_change`. Weekly: 1 `recent_change` de calendario; monthly: 15, todos borrados. |
| goal | "What is the user's current weekly budget goal for {coffee} expenses, in dollars?" o "current daily step goal" (`value`, number) | La subcategoría identifica la meta. Las metas de comida son semanales (`goal_metadata.json`: "Weekly food budget goals"). |
| content | Elemento de lista: "Is '{element}' currently one of the {field} of the user's {project proposal '{title}'}?" (existencia). Presupuesto: "What is the current budget of …?" (`value`, number). | Los demás campos escalares son prosa larga que nunca cambia: todos los updates de content son de presupuesto, y las altas y bajas son de elementos. El documento se nombra por su título (como Memora), cortado a 12 palabras. Una pregunta por elemento; cada examen sortea entre todos los documentos vivos. |
| expense | "How much did the user spend on {type} on {date}, in dollars?" (`amount`, number), **solo si ese (fecha, tipo) tiene un único gasto en N** | Sin `session_id`, (fecha, tipo) es la única identificación sin ambigüedad. Los duplicados existen: weekly/software_engineer tiene 2 cafés el 2025-06-01. Esos quedan cubiertos por el total. |
| steps | "How many steps did the user log for {date}?" (`step_count`, number) | Hay un registro por fecha. |
| expense / steps `aggregate` | "What is the total of the user's food expenses dated from {inicio de la semana} to {fecha de N}?" / "How many steps in total …" (`value`, number) | Es la pregunta de Memora con fechas explícitas, porque el agente no sabe qué día es "hoy". `history` son los totales anteriores, así que un total sin los gastos nuevos sale `stale`. |

**Para P7, sobre `new` por existencia.** Todo `new` de todo y de elementos de content se pregunta por existencia, igual que 1 de calendario por período.

| Período | `new` por existencia | `new` por valor |
| --- | --: | --: |
| weekly | 186 | 374 |
| monthly | 756 | 1.227 |

Con la corrección de P2b, en esas preguntas "no" sale `stale` y "unknown" sale `missing`. **En `new` por existencia hay que leer `stale + missing` juntos.**

### 3.4 `never_existed`

- **De dónde salen los candidatos:**
  - preference: las listas del arquetipo de la persona en `preference_metadata.json`, el mismo arquetipo del que el simulador sacó sus gustos (por ejemplo, "Boards of Canada" para software_engineer).
  - todo y calendar: las listas de `activity_metadata.json` de la persona.
  - content: elementos del mismo campo en documentos de **otras** personas, de `content_meta_data_{period}.jsonl`.
- **Filtros:**
  - Se descarta todo lo que alguna vez fue hecho para la persona.
  - Se descarta todo lo que aparece en **cualquier** turno de **cualquier** sesión del período (usuario o asistente, comparando en minúsculas). Los decenios se buscan también en su forma hablada ("1980s" → "80s").
  - Este filtro de texto cubre el defecto 2: algo que el usuario dijo y Memora no registró no puede salir como distractor.
- **Efecto del filtro de texto:** saca 226 de 3.072 candidatos de preferencias en weekly y 328 de 2.854 en monthly. Ejemplos: "stargazing" y "marine life" para academic_researcher.
- **Los dos casos conocidos del defecto 2 no pueden ser distractores.**
  - "upbeat electronic music" (software_engineer): su lista de música no tiene ningún ítem con "electronic" ni "upbeat".
  - "90s alternative rock" (startup_founder): "1990s" fue un hecho de esa persona.
- **Goal, expense y steps no tienen `never_existed`.** Las 6 metas posibles casi siempre se fijan. Inventar un gasto o un conteo de pasos ya sale como `invented` en las preguntas numéricas.

## 4. Prueba

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
  total 4039 questions in 218 exams, 18.5 per exam, 133 prompt characters per question
  by persona: exams, questions by domain
    academic_researcher     22    391  {'calendar': 38, 'content': 70, 'expense': 70, 'goal': 20, 'preference': 79, 'steps': 56, 'todo': 58}
    business_executive      20    362  {'calendar': 42, 'content': 64, 'expense': 62, 'goal': 21, 'preference': 71, 'steps': 59, 'todo': 43}
    content_writer          21    400  {'calendar': 49, 'content': 68, 'expense': 68, 'goal': 24, 'preference': 77, 'steps': 58, 'todo': 56}
    creative_designer       21    404  {'calendar': 43, 'content': 70, 'expense': 68, 'goal': 22, 'preference': 81, 'steps': 59, 'todo': 61}
    financial_analyst       22    417  {'calendar': 35, 'content': 75, 'expense': 70, 'goal': 22, 'preference': 84, 'steps': 61, 'todo': 70}
    management_consultant   22    422  {'calendar': 47, 'content': 81, 'expense': 70, 'goal': 25, 'preference': 84, 'steps': 62, 'todo': 53}
    marketing_manager       22    370  {'calendar': 25, 'content': 61, 'expense': 66, 'goal': 22, 'preference': 83, 'steps': 58, 'todo': 55}
    sales_manager           23    422  {'calendar': 43, 'content': 80, 'expense': 71, 'goal': 27, 'preference': 87, 'steps': 62, 'todo': 52}
    software_engineer       23    426  {'calendar': 46, 'content': 77, 'expense': 75, 'goal': 26, 'preference': 80, 'steps': 61, 'todo': 61}
    startup_founder         22    425  {'calendar': 51, 'content': 77, 'expense': 75, 'goal': 21, 'preference': 82, 'steps': 56, 'todo': 63}
  sessions since the last dream at exam time (dream after session N when N % cadence == 0)
    cadence  5: mean  2.06 (uniform  2.00), lags hit 5/5  0:40 1:42 2:49 3:40 4:47
    cadence 20: mean  9.46 (uniform  9.50), lags hit 20/20  0:10 1:12 2:10 3:10 4:10 5:10 6:10 7:19 8:10 9:10 10:10 11:10 12:10 13:10 14:17 15:10 16:10 17:10 18:10 19:10
    cadence 50: mean 26.02 (uniform 24.50), lags hit 23/50  0:0 1:0 2:0 3:0 4:7 5:10 6:10 7:10 8:0 9:0 10:0 11:2 12:10 13:10 14:10 15:0 16:0 17:0 18:0 19:10 20:10 21:10 22:0 23:0 24:0 25:0 26:10 27:10 28:10 29:0 30:0 31:0 32:0 33:10 34:10 35:10 36:0 37:0 38:0 39:0 40:10 41:10 42:10 43:0 44:0 45:0 46:0 47:9 48:10 49:10
== monthly: exams every 7 sessions
  domain        recent_change            new         stable  never_existed      aggregate   total
  preference              368            358           1608            873              0    3207
  todo                    344            343           1245            873              0    2805
  calendar                 15             49           1013            873              0    1950
  goal                     60             43           1096              0              0    1199
  content                 435            416           1625            859              0    3335
  expense                   0            502           1658              0            864    3024
  steps                     0            272           1626              0            796    2694
  total 18214 questions in 873 exams, 20.9 per exam, 132 prompt characters per question
  by persona: exams, questions by domain
    academic_researcher     88   1809  {'calendar': 200, 'content': 321, 'expense': 303, 'goal': 123, 'preference': 328, 'steps': 273, 'todo': 261}
    business_executive      85   1725  {'calendar': 170, 'content': 333, 'expense': 292, 'goal': 121, 'preference': 305, 'steps': 260, 'todo': 244}
    content_writer          89   1883  {'calendar': 221, 'content': 337, 'expense': 309, 'goal': 121, 'preference': 336, 'steps': 277, 'todo': 282}
    creative_designer       87   1839  {'calendar': 209, 'content': 332, 'expense': 305, 'goal': 118, 'preference': 322, 'steps': 269, 'todo': 284}
    financial_analyst       87   1748  {'calendar': 172, 'content': 334, 'expense': 303, 'goal': 122, 'preference': 319, 'steps': 268, 'todo': 230}
    management_consultant   86   1820  {'calendar': 196, 'content': 329, 'expense': 301, 'goal': 121, 'preference': 313, 'steps': 264, 'todo': 296}
    marketing_manager       86   1797  {'calendar': 190, 'content': 338, 'expense': 293, 'goal': 118, 'preference': 311, 'steps': 266, 'todo': 281}
    sales_manager           90   1920  {'calendar': 207, 'content': 344, 'expense': 316, 'goal': 118, 'preference': 338, 'steps': 272, 'todo': 325}
    software_engineer       89   1854  {'calendar': 189, 'content': 342, 'expense': 307, 'goal': 123, 'preference': 326, 'steps': 276, 'todo': 291}
    startup_founder         86   1819  {'calendar': 196, 'content': 325, 'expense': 295, 'goal': 114, 'preference': 309, 'steps': 269, 'todo': 311}
  sessions since the last dream at exam time (dream after session N when N % cadence == 0)
    cadence  5: mean  2.01 (uniform  2.00), lags hit 5/5  0:171 1:174 2:179 3:173 4:176
    cadence 20: mean  9.40 (uniform  9.50), lags hit 20/20  0:40 1:50 2:49 3:43 4:40 5:40 6:40 7:50 8:50 9:46 10:41 11:40 12:40 13:40 14:50 15:50 16:44 17:40 18:40 19:40
    cadence 50: mean 24.73 (uniform 24.50), lags hit 50/50  0:10 1:10 2:19 3:20 4:20 5:20 6:20 7:20 8:10 9:16 10:20 11:20 12:20 13:20 14:20 15:10 16:14 17:20 18:20 19:20 20:20 21:20 22:10 23:13 24:20 25:20 26:20 27:20 28:20 29:10 30:11 31:20 32:20 33:20 34:20 35:20 36:10 37:10 38:20 39:20 40:20 41:20 42:20 43:10 44:10 45:20 46:20 47:20 48:20 49:20
       12.19 real        11.63 user         0.19 sys
            67190784  maximum resident set size
```

`stable` por estrato (`/tmp/p2a_split.py`, un script descartable):

| Período | Dominio | < 50 | ≥ 50 |
| --- | --- | --: | --: |
| weekly | preference | 204 | 136 |
| weekly | todo | 148 | 33 |
| weekly | content | 197 | 135 |
| weekly | goal | 74 | 135 |
| monthly | preference | 828 | 780 |
| monthly | todo | 703 | 542 |
| monthly | content | 836 | 789 |
| monthly | goal | 303 | 793 |
| monthly | calendar | 351 | 662 |

Coherencia con la corrección de P2b (`/tmp/p2a_check.py`). Para cada pregunta comprueba cuatro cosas:

- `grade(q, render(q, q.current)) == "correct"`.
- Si es `recent_change`, `grade(q, render(q, q.history[-1])) == "stale"`.
- `history` arranca en `None`, salvo en `never_existed`, donde vale `()` y `current` es `None`.
- `fact is None` si y solo si la pregunta es `aggregate`.

Además, los `question_id` son únicos.

```
$ PYTHONPATH=. uv run python /tmp/p2a_check.py weekly monthly
weekly 4039 questions; problems: none
monthly 18214 questions; problems: none

$ uv run pytest -q
.................................                                        [100%]
33 passed in 3.77s
```

`tests/test_questions.py` (3 tests sobre weekly/software_engineer):

1. El examen es determinista, cada `(history, current)` coincide con `fact_states` y la respuesta perfecta sale `correct`.
2. Bonobo en la s35 (`recent_change`, `(None, like)` → `None`) y deep house en la s133 (`new`, `(None, dislike)` → `like`).
3. Mechanic visit se pregunta por fecha solo antes de la 87 y después solo por existencia.

## 5. Opciones descartadas y por qué

| Opción | Por qué no | Evidencia |
| --- | --- | --- |
| Examinar solo al final (Memora) | Un solo punto por persona. La fase respecto del dream la fija el largo del período: weekly/software_engineer termina en la 163, que es 163 mod 50 = 13. | `unified_question_generator.py`, `extract_memory_snapshots` |
| Paso múltiplo de una cadencia (10) | Con la cadencia 20 el retraso queda en {0, 10}; con la 50, en {0, 10, 20, 30, 40}. | Ejemplo del enunciado |
| Paso 21 en monthly | Un tercio del costo, pero 21 ≡ 1 (mod 20) deja la cadencia 20 en media 8,10 en vez de 9,5. Además, las antigüedades de `recent_change` (0–20) ya no son comparables con weekly. | §3.1 |
| Sesiones al azar con semilla | Uniforme solo en esperanza, con varianza. El paso coprimo es uniforme por construcción y más fácil de explicar. | — |
| Examen antes del dream de la misma sesión | Suma 1 de retraso a todas las políticas, y ningún cambio de la sesión N se podría acertar. | §3.1 |
| `stable` sin estratos | La mayoría de los estables son viejos (contenido agregado temprano), así que el hueco 7–49, que es donde se separan 20 y 50, quedaría casi sin muestra. | §3.2 |
| `stable` solo con antigüedad ≥ 50 | Es un control limpio, pero deja sin preguntas las antigüedades 7–49. Lo descarté al ver el hueco. | §3.2 |
| Gasto por ordinal ("el segundo café del día") | Depende de que las notas preserven el orden, y es ambiguo si la nota los fusiona. | — |
| Gasto por existencia con el monto en el prompt | El prompt filtra la respuesta: un agente que dice "yes" a todo acierta. Habría que fabricar gastos de control. | — |
| Fecha de eventos reprogramados | La verdad (la regla de Memora) contradice al usuario en 37/37. Un agente que anotó lo que dijo el usuario saldría `invented`. | P1 §4, defecto 1; weekly/academic_researcher s150: "next Tuesday" 06-10 frente a 06-22 guardado |
| Campos escalares de content en prosa | No cambian nunca, y comparar prosa exige un juez con modelo (costo ≠ 0). | Todos los updates de content son `budget_revised` o `budget_reverted` (`truth/changes.py`) |
| Distractores de otros arquetipos o inventados | Son menos plausibles. Las listas del propio arquetipo son el universo del que el simulador sacó los gustos reales. | `truth/changes.py:_preference_lists` |
| Una llamada por pregunta (STALE consulta cada dimensión por separado) | Monthly costaría ≈ 970 M tokens. Los prompts no revelan valores, solo nombres, así que agruparlas filtra poco. | §3.2 |

## 6. Limitaciones y preguntas abiertas

- **Hay celdas chicas, por los datos.** Weekly tiene 1 `recent_change` de calendario y 0 de goal; monthly tiene 15 de calendario y 60 de goal. En calendario el cambio dominante es la reprogramación, que no se puede preguntar por fecha (defecto 1).
- **En las bajas preguntadas por existencia, "unknown" sale `correct`.** Pasa en todo, elementos de content y calendario, por la regla de P2b de que abstenerse está bien cuando nada vale. Una política sin notas acierta esas bajas contestando "unknown". En `recent_change` de baja, lo que distingue a las políticas es la tasa de `stale` ("yes"), no la de `correct`. **Pregunta para P2/P7:** ¿reportar `recent_change` separado entre "cambió de valor" y "desapareció"? Se puede derivar de `current is None`.
- **`new` por existencia:** hay que leer `stale + missing` juntos (§3.3).
- **Antigüedad del hecho.** Los estratos de `stable` y la antigüedad de `recent_change` (0–6) no están en `Question`. P7 los puede recalcular con el timeline (`session_id − valid_from` de la versión vigente). **Sugerencia opcional para P2:** un campo `changed_at: int | None` en `Question` le ahorraría ese cálculo a P7. No es necesario para P3.
- **Correlación.** Las preguntas de una misma persona y de exámenes vecinos están correlacionadas: los estables se repiten (Mechanic visit sale en 8 exámenes seguidos, de la s112 a la s161). El n efectivo es menor que el de la tabla. P7 debería usar bootstrap por persona.
- **Weekly y la cadencia 50.** Con ~22 exámenes por persona y la misma fase en todas, se cubren 23/50 restos (media 26,0 frente a 24,5). Es aceptable; desfasar por persona lo arreglaría, a cambio de más código.
- **El disparador por contradicción** está medido con un proxy (update o remove). Cuando P5 lo defina, hay que repetir la medición.
- **El filtro de texto** busca la subcadena en minúsculas: sobre-filtra ("rock" dentro de "rocket"), lo cual es el lado seguro. Una paráfrasis del usuario que no contenga el nombre no se detecta.
- **El costo es una estimación.** Las notas reales dependen del dream de P4. Usé la verdad completa como proxy, que es una cota razonable si el dream no escribe de más.
