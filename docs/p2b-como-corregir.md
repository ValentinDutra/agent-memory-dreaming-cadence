# P2b · Cómo corregir

> **Nota de integración (P2).** P2 cambió una regla de este informe: en preguntas "¿existe?" (`field is None`) sobre algo que no vale, `unknown` ahora sale `missing`, no `correct`; solo es correcto donde la respuesta esperada es `unknown` (gustos que no valen). La prueba de humo por persona de `tests/test_grading.py` se reemplazó por `exam/smoke.py` sobre el examen real de P2a (`uv run python -m exam.smoke weekly monthly`). Ver `docs/p2-examen.md` §3.3.

**Resultado.** `exam/grading.py` corrige cada respuesta con un script, sin modelo y sin costo. Primero normaliza la respuesta y después la clasifica en una de cinco categorías: `correct`, `stale`, `missing`, `invented` y `unparseable` (P2 aceptó esta última). Todo se puede separar por dominio y por probe.

- **Prueba de humo sobre datos reales.** Se armaron 10.713 preguntas (weekly + monthly, 7 dominios, los 3 formatos). Un agente perfecto saca 100% `correct`. Uno que siempre dice `unknown` saca `missing`, salvo donde el hecho ya no vale. Uno que repite el estado anterior saca `stale`, salvo los hechos recién nacidos, que no tienen valor anterior.
- **Bonobo después del borrado:** la respuesta correcta es `unknown`. Con "like" sale `stale`. Con "dislike" sale `invented` en la lectura estricta, que es la oficial; `negates_removed_preference` permite contarla como correcta en la lectura laxa.
- **Juez LLM: no hace falta.** Todo hecho que cambia de valor es corto o cerrado: gustos, pendientes, fechas, metas, montos, presupuestos y elementos de listas. Los 522 campos largos de contenido nunca cambian.

| Rol | Ruta |
| --- | --- |
| Corrección | `exam/grading.py` (`render`, `expected_answer`, `grade`, `tally`, `tally_table`, `negates_removed_preference`) |
| Tests (6 casos + humo por persona) | `tests/test_grading.py` |
| Prueba de humo | `uv run python -m tests.test_grading weekly monthly` |

## 1. Problema

P3 contesta preguntas leyendo solo las notas, y el análisis (P7) necesita saber **por qué** falla cada respuesta: si la nota quedó vieja, si le falta un hecho nuevo o si el agente inventó algo. Para eso hacen falta tres cosas: una respuesta canónica por pregunta, una normalización que no castigue el formato y una regla para cada caso borde.

Ejemplo real, weekly/software_engineer, el artista Bonobo. Lo que dice el usuario en la sesión 30 (turno 12, `share_memory=True`):

> "Speaking of interesting characteristics, I used to really like Bonobo, but I'm just not into his music anymore. I guess my tastes have changed!"

Memora registra `operation: delete` con `{"item": "Bonobo", "preference": "like"}`, y P1 lo convierte en un hecho que deja de valer. Si se pregunta en la sesión 40 "Does the user like or dislike Bonobo? Answer like, dislike or unknown.":

| Respuesta del agente | ¿Qué significa? | Clase |
| --- | --- | --- |
| `like` | La nota no se actualizó después de la sesión 30 | `stale` |
| `unknown` | La nota se actualizó o nunca existió; en los dos casos no afirma nada falso | `correct` |
| `dislike` | La nota se actualizó, pero el agente afirma más de lo que dijo el usuario | `invented` (estricta) / `correct` (laxa) |
| `He used to, not anymore` | No es una de las opciones | `unparseable` |

Los otros dos casos de referencia:

- **deep house:** dislike en la 129, like desde la 132. En la 150, "dislike" es `stale`. En la 131, "like" es `invented`, porque todavía nunca había sido cierto.
- **Total de gastos:** en la sesión 147 el total es 258,23. El total anterior (247,93, de la s141) es `stale`, y "$258.23" es `correct` aunque la suma en float dé 258,22999999999996.

## 2. Opciones investigadas

| Fuente | Qué hace | Qué tomé |
| --- | --- | --- |
| Memora, paper §4.2, https://arxiv.org/abs/2604.20006 | Cada pregunta abierta tiene criterios sí/no. *memory presence*: lo válido tiene que estar. *forgetting absence*: lo invalidado no tiene que aparecer. Los decide un jurado de 3 LLM por mayoría, con 88,3% de acuerdo con humanos. FAMA = max(0, MPA − λ·(1 − FAA)). | La separación entre "recuerda lo válido" (≈ no `missing`) y "no usa lo viejo" (≈ no `stale`) |
| Memora, código: `vendor/Memora/data_generation/question_generation/memory_evaluation_generator.py` y `unified_question_generator.py` | Para un gusto borrado pregunta *"Does the response reflect or mention the user's preference for {item}?"* y espera `no`. Los totales se comparan al centavo: *"mention the total food spending amount of ${total_amount:.2f}"*. | Un borrado es ausencia, no la polaridad opuesta. Los totales se comparan al centavo. |
| Memora, instrucción al simulador del usuario: `data_generation/conversation_generation/instruction_generator.py:147` | *"User should express that they no longer {pref_type} '{item}'"* | Un borrado significa "ya no le gusta", no "no le gusta" |
| Memora, juez: `evals/model_eval/model_based_evaluator.py` `_parse_judge_response` | Si el juez no contesta sí ni no, guarda `unclear` aparte | Precedente para `unparseable` |
| LongMemEval §3.2 y §3.3, https://arxiv.org/abs/2410.10813; `src/evaluation/evaluate_qa.py` en https://github.com/xiaowu0162/LongMemEval | **Abstention:** ante información que nunca se mencionó, lo correcto es "I don't know". **Knowledge update:** la respuesta es correcta si trae el valor actualizado, aunque mencione el anterior. Usa un juez GPT-4o, con más de 97% de acuerdo con humanos. | "No sé" es correcto sobre un hecho que nunca existió |
| MemoryAgentBench, App. B.4.2 y §3.3, https://arxiv.org/abs/2507.05257; `utils/eval_other_utils.py` en https://github.com/HUST-AI-HYZ/MemoryAgentBench | FactConsolidation se corrige con *SubEM (Substring Exact Match)* después de `normalize_answer`, que pasa a minúsculas y quita la puntuación, los artículos y los espacios de más. Lo justifican así: *"the agent's responses are mostly informational entities"*. El prompt pide que gane el hecho más nuevo. | Para respuestas cortas alcanza con exact match normalizado; el juez se reserva para respuestas abiertas |
| STALE §3.5, §5, App. E.1 y App. F.1, https://arxiv.org/abs/2605.06527; `STALE/Evaluation/judge_prompts.py` en https://github.com/icedreamc/STALE | Juez LLM pass/fail, con 95,8% de acuerdo con humanos. **Dim 1:** *"Score 'false' if it assumes M_old is still true or claims ignorance."* **CUPMem:** un valor invalidado sin reemplazo se marca `UNKNOWN_CURRENT`. | Un valor invalidado sin reemplazo queda como "desconocido actual", así que `unknown` es la lectura estricta. STALE premia además "sé que ya no vale", y eso respalda la lectura laxa. |

## 3. Análisis y elección

### 3.1 Formato y normalización

| Formato | Respuesta canónica (`render`) | Normalización (`normalize`) | Si no parsea |
| --- | --- | --- | --- |
| `choice`, `field is None` ("¿existe?") | `yes` si el hecho vale, `no` si no | minúsculas, sin comillas ni punto final; `y`→`yes`, `n`→`no` | `unparseable` |
| `choice` con campo | el valor del campo, por ejemplo `like` | igual que arriba, más `likes`→`like` y `_` ≡ espacio (`personal tasks` = `personal_tasks`) | `unparseable` |
| `number` | número con hasta 2 decimales, sin ceros de más (`5.0`→`5`) | quita `$`, separadores de miles, `usd`/`dollars`/`steps`; redondea al centavo | `unparseable` |
| `value` | el texto del campo | si es un número → como `number`; si es una fecha (`2025-06-11`, `June 11, 2025`, `11 June 2025`) → ISO; si no, texto en minúsculas | nunca: todo texto es un valor |

`unknown`, "I don't know", "not sure", "no idea", "n/a", la respuesta vacía y `None` (el agente no contestó) se normalizan todos a `UNKNOWN`.

**Tolerancia numérica: al centavo, sin tolerancia relativa.**

- **Montos.** Los 1.139 montos de gastos (weekly + monthly) tienen como máximo 2 decimales. El más chico es 3,02, así que dos totales consecutivos nunca difieren en menos de 3,02.
- **Con una tolerancia del 1%, un total viejo pasaría por correcto.** En monthly, 291 de los 905 totales tienen al anterior a menos del 1%; en weekly, 0 de 214. Memora también compara al centavo (`${total_amount:.2f}`).
- **Pasos, metas y presupuestos** son enteros, así que la comparación es exacta.

### 3.2 Categorías y orden de decisión

`grade` aplica las reglas en este orden. La primera que se cumple decide.

1. **`unparseable`**: la respuesta no parsea en el formato de la pregunta.
2. **`correct`**: la respuesta normalizada es igual a `expected_answer` (= `render(question, question.current)`). Esto incluye volver a un valor anterior, como un presupuesto revertido a uno que ya tuvo: gana `correct`.
3. **`UNKNOWN`**: es `correct` si el hecho no vale (abstenerse está bien cuando no hay nada que afirmar) y `missing` si el hecho vale.
4. **`stale`**: la respuesta es igual a `render(question, state)` para algún estado de `history` distinto del actual.
5. **`invented`**: cualquier otra cosa.

Casos borde, todos con datos reales (los tests están en `tests/test_grading.py`):

| Caso | Ejemplo real | Clase | Por qué |
| --- | --- | --- | --- |
| Respuesta que no parsea | Bonobo s40: "maybe"; total de gastos: "a lot" | `unparseable` | Es un error de formato de P3, no de memoria. Ponerla en `invented` inflaría la tasa de alucinación; ponerla en `missing`, la señal de "hecho nuevo que todavía no llegó a las notas". |
| "No sé" sobre un hecho que nunca existió | todo "Renew passport", s150, `history == ()`: "not sure" | `correct` (también `no`) | LongMemEval ABS. No afirma nada falso. |
| "No sé" sobre un hecho que existe | deep house s131 | `missing` | Definición de `schema.py` |
| "No sé" sobre un hecho borrado | Bonobo s40 | `correct` | Ver §3.3 |
| `yes` sobre un `never_existed` | todo "Renew passport": "Yes" | `invented` | Ningún estado lo sostuvo; `history == ()` |
| `dislike` sobre un gusto borrado | Bonobo s40 | `invented` (estricta) | Ver §3.3 |
| Total igual a un total anterior | gastos weekly/software_engineer s147: "247.93", el total de la s141 | `stale` | Los totales crecen estrictamente (monto mínimo 3,02), así que coincidir con uno anterior significa que falta un gasto nuevo |
| Total con ruido de float | s147: `current` = 258,22999999999996, respuesta "$258.23" | `correct` | Se redondea al centavo |
| Fecha escrita en otro formato | Mechanic visit s104: "June 11, 2025" | `correct`; "2025-06-15" (antes de la reprogramación) → `stale`; "2025-06-12" → `invented` | Se normaliza a ISO |
| "no" a "¿existe?" sobre un hecho nuevo | evento de calendario recién agregado | `stale` | "no" era correcto antes de que se agregara. Una pregunta de valor sobre el mismo hecho da `missing`. P7 debe sumar `stale` + `missing` cuando el probe es `new` (ver §6). |

No pedí más categorías que `unparseable`.

### 3.3 Bonobo: ¿"no" o "no sé"? Elijo `unknown` y dejo medir la otra lectura

Evidencia:

| Fuente | Qué dice | Lectura |
| --- | --- | --- |
| El usuario, s30 t12 | "I used to really like Bonobo, but I'm just not into his music anymore" | Ya no le gusta; nunca dice que le disguste |
| Instrucción al simulador de Memora | "express that they no longer like '{item}'" | Ausencia |
| Todos los borrados de gustos de weekly + monthly | 194 borrados, todos de un `like`. 187 no usan palabras negativas ("anymore", "no longer", "not into"); 7 sí, y solo 2 dicen "dislike" o "can't stand" (monthly/content_writer s124, monthly/marketing_manager s143) | Ausencia en el 96% |
| P1 (`truth/changes.py`) | `delete` → `remove`: el hecho deja de valer, no pasa a dislike | Ausencia |
| Memora FAMA | El gusto borrado no tiene que "reflect or mention" en la respuesta. Decir "dislikes Bonobo" lo menciona, así que el juez probablemente lo marca como fallo. | Estricta |
| LongMemEval | La abstención solo cubre información que nunca se mencionó; no tiene borrados | No decide |
| STALE | CUPMem marca `UNKNOWN_CURRENT` cuando no hay reemplazo, pero la Dim 1 castiga el "claims ignorance" sin conciencia de que lo viejo ya no vale | Las dos |

**Elección: la respuesta canónica después de un borrado es `UNKNOWN`** (o `no` si la pregunta es "¿existe?"). `like` es `stale`. `dislike` es `invented` en el conteo oficial, porque afirma un valor que el hecho nunca tuvo.

**Las dos lecturas en el análisis.** "dislike" sobre Bonobo indica que la nota **sí** se actualizó. Contarla como alucinación penalizaría a las políticas que más sueñan por un problema de redacción. Por eso `negates_removed_preference(question, grade)` marca exactamente esos casos: campo `preference`, hecho borrado y clase `invented`. Así P7 puede reportar la tasa estricta y la laxa (`invented` → `correct`) sin volver a corregir. En el smoke el predicado no se activa, porque ningún agente sintético dice "dislike". Su alcance máximo son las preguntas sobre gustos borrados: 89 en weekly y 284 en monthly.

**Recomendación para P2a.** Redactar la pregunta de modo que `unknown` sea la respuesta natural después de un borrado. Por ejemplo: "What is the user's *current* preference about Bonobo: like, dislike, or unknown (no current preference)?". Así baja la ambigüedad antes de llegar a la corrección.

### 3.4 Exact match normalizado y no un juez LLM

Cuántos valores hay de cada tipo, contando todas las versiones (`timeline.versions`, weekly + monthly):

| Dominio / campo | Versiones | Forma | Cambia con el tiempo | Formato sugerido |
| --- | --: | --- | --- | --- |
| preference | 802 | `like`/`dislike` | sí | `choice` |
| todo | 568 | existe / no existe | sí (add/remove) | `choice` (¿existe?) |
| calendar `event_date` | 106 | fecha ISO | sí (37 reprogramaciones) | `value` |
| goal | 148 | entero | sí (66 updates) | `number` |
| expense `amount` | 1.139 | float de 2 decimales | no (solo se agregan) | `number` + total |
| steps `step_count` | 350 | entero | no (solo se agregan) | `number` + total |
| content, elemento de lista | 2.993 (758 de 1–3 palabras, 878 de 4–8, 1.357 de 9 o más) | existe / no existe | sí (609 removes) | `choice` (¿existe?); el texto va en el prompt, no en la respuesta |
| content `budget` | 249 | entero | sí (169 updates) | `number` |
| content, otros campos | 867: 151 de 1–3 palabras (`platform`, `content_type`), 194 de 4–8 (títulos, `project_lead`), **522 de 9 o más** (`project_description`, `email_purpose`, `main_message`…) | texto | **nunca** (solo add) | `value` solo para los cortos |

Según `truth/changes.py` (`_content_changes`) y el conteo de cambios por campo (§4), el único campo escalar de contenido que tiene `update` es `budget`. Los 522 textos largos solo se agregan, así que nunca pueden quedar `stale`: no miden nada de la cadencia de los dreams, salvo si llegaron a las notas.

- **Si P2a los pregunta, conviene hacerlo como existencia** ("¿el documento X tiene una descripción que menciona Y?") o no preguntarlos.
- **El juez solo haría falta en un caso:** que P2a pida reproducir un texto largo como `value`. Costaría 1 llamada por pregunta, con un ruido medido de 88,3% (Memora) a 97% (LongMemEval) de acuerdo con humanos, y ese ruido tapa diferencias chicas entre políticas.
- **Con exact match normalizado el ruido es 0 y el costo, $0**, en todo lo que cambia con el tiempo.

### 3.5 Relación con FAMA

| | FAMA (Memora) | P2b |
| --- | --- | --- |
| Pregunta | Abierta ("What music would you recommend?"), con varios criterios sí/no por pregunta | Un hecho, un campo, una respuesta cerrada |
| Cuándo | Una vez, al final del período | Después de cualquier sesión (P2a elige cuándo) |
| Quién corrige | Jurado de 3 LLM por mayoría (88,3% de acuerdo con humanos) | Script determinista |
| "Recuerda lo válido" | memory presence (MPA) | no `missing` |
| "No usa lo viejo" | forgetting absence (FAA) | no `stale` |
| Inventar | No se mide: un valor inventado solo baja MPA si desplaza a uno válido | `invented` |
| Abstenerse | No existe: las 300 preguntas weekly + monthly tienen al menos un criterio de presence (1.013 presence, 1.037 forgetting) | `unknown` es correcto donde nada vale |
| Agregado | Un número por pregunta: max(0, MPA − λ(1 − FAA)) | Conteos por (dominio, probe, clase), sin mezclar |
| Qué cuenta como viejo | `forgetting_evidence`, incompleta (defecto 6): `_extract_forgetting_evidence` solo agrega `old_item` en los updates y los `preference_update` no traen `old_item`, así que quedan sin marcar 146 flips like↔dislike (por ejemplo, Rita Hayworth en la s88); además faltan 109 presupuestos viejos (w+m) | Cualquier estado de `history` sacado de la verdad de P1, que incluye flips y presupuestos |

En resumen, `stale` es la versión por hecho, por sesión y completa de lo que FAA intenta medir. `missing` corresponde a MPA. FAMA no separa `invented` de `missing`.

## 4. Prueba

```
$ uv run pytest -q
..............................                                           [100%]
30 passed in 4.21s
```

Los 15 tests nuevos son:

- 5 casos anclados en datos reales: Bonobo, deep house, total de gastos, Mechanic visit y un `never_existed`.
- La prueba de humo en cada una de las 10 personas de weekly.

La prueba de humo arma preguntas sobre cada hecho justo después de cada sesión en que cambió, con `fact_states`. Suma "¿existe?" para eventos de calendario nuevos, 2 hechos `never_existed` por persona y un total de gastos y otro de pasos después de cada sesión que agrega uno. Después corrige tres agentes sintéticos:

```
$ /usr/bin/time -l uv run python -m tests.test_grading weekly monthly
        0.83 real   ...   52084736  maximum resident set size
```

Salida real de weekly:

```
== weekly: perfect (2209 questions)
| domain | probe | correct | stale | missing | invented | unparseable |
| preference | never_existed | 10 | 0 | 0 | 0 | 0 |
| preference | recent_change | 360 | 0 | 0 | 0 | 0 |
| todo | never_existed | 10 | 0 | 0 | 0 | 0 |
| todo | recent_change | 214 | 0 | 0 | 0 | 0 |
| calendar | recent_change | 63 | 0 | 0 | 0 | 0 |
| goal | recent_change | 30 | 0 | 0 | 0 | 0 |
| content | recent_change | 934 | 0 | 0 | 0 | 0 |
| expense | aggregate | 224 | 0 | 0 | 0 | 0 |
| expense | recent_change | 224 | 0 | 0 | 0 | 0 |
| steps | aggregate | 70 | 0 | 0 | 0 | 0 |
| steps | recent_change | 70 | 0 | 0 | 0 | 0 |

== weekly: always unknown (2209 questions)
| preference | never_existed | 10 | 0 | 0 | 0 | 0 |
| preference | recent_change | 89 | 0 | 271 | 0 | 0 |
| todo | never_existed | 10 | 0 | 0 | 0 | 0 |
| todo | recent_change | 92 | 0 | 122 | 0 | 0 |
| calendar | recent_change | 3 | 0 | 60 | 0 | 0 |
| goal | recent_change | 0 | 0 | 30 | 0 | 0 |
| content | recent_change | 91 | 0 | 843 | 0 | 0 |
| expense | aggregate | 0 | 0 | 224 | 0 | 0 |
| expense | recent_change | 0 | 0 | 224 | 0 | 0 |
| steps | aggregate | 0 | 0 | 70 | 0 | 0 |
| steps | recent_change | 0 | 0 | 70 | 0 | 0 |

== weekly: previous state (2189 questions)
| preference | recent_change | 0 | 157 | 203 | 0 | 0 |
| todo | recent_change | 0 | 214 | 0 | 0 | 0 |
| calendar | recent_change | 0 | 42 | 21 | 0 | 0 |
| goal | recent_change | 0 | 0 | 30 | 0 | 0 |
| content | recent_change | 0 | 704 | 230 | 0 | 0 |
| expense | aggregate | 0 | 214 | 10 | 0 | 0 |
| expense | recent_change | 0 | 0 | 224 | 0 | 0 |
| steps | aggregate | 0 | 60 | 10 | 0 | 0 |
| steps | recent_change | 0 | 0 | 70 | 0 | 0 |
```

Monthly (8.504 preguntas):

- **perfect:** 100% `correct`.
- **always unknown:** `correct` en 284 preguntas de preference, 387 de todo, 15 de calendar y 518 de content (los hechos que ya no valen) más los 20 `never_existed`; todo lo demás es `missing`.
- **previous state:** `stale` en 508 preguntas de preference, 833 de todo, 117 de calendar, 124 de goal, 3.236 de content, 905 totales de gastos y 270 totales de pasos.

Cómo leer las tablas:

- **"always unknown"** solo saca `correct` donde el hecho dejó de valer (89 gustos borrados, 92 pendientes cerrados, etc.) y en los `never_existed`.
- **"previous state"** saca `missing` solo en hechos recién nacidos, porque su estado anterior es "no existía". Esos son los 203 gustos nuevos, los 230 elementos de contenido nuevos, el primer total de cada persona (10) y todos los gastos y pasos sueltos, que solo se agregan.
- **Goal en weekly da 0 `stale`**, igual que en P1: en weekly ninguna meta cambia.

Tolerancia numérica, con el mismo código:

```
weekly  smallest gap between consecutive totals 3.06 largest total 431.9   consecutive totals within 1%: 0 of 214
monthly smallest gap between consecutive totals 3.02 largest total 1671.49 consecutive totals within 1%: 291 of 905
```

Las tablas de longitudes de §3.4 salen de dos scripts de una sola vez (no versionados) que recorren `timeline.versions` y `persona_changes` de weekly y monthly. La frase de los borrados sale de recorrer los turnos `share_memory` de las 194 sesiones `preference`/`delete`.

## 5. Opciones descartadas y por qué

| Opción | Por qué no |
| --- | --- |
| Juez LLM para todo (Memora, LongMemEval, STALE) | Cuesta 1 llamada por pregunta y agrega 3–12% de desacuerdo con humanos. Todo lo que cambia es corto o cerrado (§3.4). |
| Substring match (MemoryAgentBench) | En `choice` aceptaría "dislike" como "like" (substring) y "yes, but no longer" como "yes". Con respuestas cerradas, la igualdad exacta después de normalizar es más estricta y suficiente. |
| Tolerancia relativa (1%) en totales | En monthly, 291 de 905 totales viejos pasarían por correctos (§4) |
| "dislike" como respuesta correcta después de un borrado | El 96% de los borrados no expresa disgusto, y P1, Memora y FAMA lo tratan como ausencia. Queda como lectura laxa vía `negates_removed_preference`, no como regla. |
| "No sé" como `missing` sobre un hecho borrado o que nunca existió | Contradice la abstención de LongMemEval y castigaría la respuesta honesta de una nota bien actualizada |
| Respuesta no parseable como `invented` o `missing` | Mezcla un error de formato de P3 con un error de memoria. P2 aceptó `unparseable`. |
| Extraer la opción de una respuesta larga ("he no longer likes him" → like) | Las palabras de la opción aparecen dentro de frases que la niegan. Es más seguro marcar `unparseable` y que P3 pida una sola palabra. |

## 6. Limitaciones y preguntas abiertas

- **Hecho nuevo, dos clases según el formato.** Ante un hecho que todavía no llegó a las notas, una pregunta "¿existe?" da `stale` (decir "no" era correcto antes) y una pregunta de valor da `missing`. Las dos cosas son lo mismo para la cadencia. P7 tiene que leer `stale` + `missing` juntos cuando el probe es `new`, o P2a tiene que preguntar los hechos nuevos por valor siempre que pueda.
- **`None` (sin respuesta) se trata como `unknown`.** `Grade.given` queda `"unknown"` y no distingue "no contestó" de "dijo no sé". Si P3 tiene timeouts, conviene registrarlos aparte.
- **Normalización mínima.** Fechas en ISO, "June 11, 2025" y "11 June 2025"; no acepta "06/11/2025" (ambiguo) ni números en palabras ("five"). Si P3 le pide al modelo ISO y dígitos, alcanza. Si no, esas respuestas caen en `invented` (fechas) o `unparseable` (números).
- **El smoke no prueba la lectura laxa con datos de un agente real.** Cuántas veces un modelo responde "dislike" después de un borrado solo se sabrá en P7.
- **El texto del usuario a veces contradice a Memora.** En monthly/marketing_manager s143 el usuario dice "now I can't stand it" (teen pop) y Memora lo registra como `delete`. Ahí "dislike" es lo que dijo el usuario, y la lectura estricta lo marca `invented`. Son 2 de 194; la lectura laxa los cubre.
- **Defectos heredados de P1 que P2a debe evitar al preguntar:** fechas de eventos reprogramados que no coinciden con el texto (defecto 1; Mechanic visit está entre ellos) y hechos que el usuario dijo pero Memora no registró (defecto 2, "upbeat electronic music" en la s30). Un agente que los recuerde sacaría `invented`.
