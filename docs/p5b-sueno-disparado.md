# P5b · Sueño disparado por contradicción

**Resultado.** Disparar el sueño **solo con contradicciones pierde** contra una cadencia fija del mismo costo. Acierta más los cambios recientes, pero los hechos nuevos quedan esperando hasta la próxima contradicción. Lo que sí sirve es disparar con **cualquier hecho nuevo**, y para eso alcanza un **detector de frases gratis**. Un detector con el modelo es más preciso, pero cuesta más que los sueños que ahorra.

| Política (costo = sueños + detector, sin exámenes) | weekly/software_engineer s1–161 (r0 / r1) | monthly/academic_researcher s1–210 | monthly/startup_founder s1–210 |
| --- | --: | --: | --: |
| `triggered-phrases-any`: sueña si la sesión trae cualquier hecho (frases) | **93,0 % / 92,7 %** · $0,067 | **97,3 %** · $0,103 | **89,5 %** · $0,106 |
| `triggered-model-any`: lo mismo, con una pregunta al modelo | 93,4 % · $0,085 | 96,5 % · $0,122 | — |
| `every-2` (referencia fija, P5a es dueño de las fijas) | 91,5 % / 90,4 % · $0,051 / $0,049 | 93,6 % · $0,077 | 88,8 % · $0,082 |
| `triggered-phrases-change`: sueña solo si la sesión cambia algo (frases) | 86,2 % · $0,037 | 91,2 % · $0,060 | — |
| `every-3` (referencia del mismo costo) | 90,6 % · $0,042 | 92,1 % · $0,063 | — |

Examen oficial de P2 con `exam_every=7`. Las cuatro cuentas y las cinco clases están en §4.2.

- **Contradicción sola contra `every-3`, costo parecido (la disparada cuesta un 5–12 % menos):** −4,4 y −0,9 puntos. Gana en `recent_change` (+7,7 y +18,4) y pierde en `new` (−20,0 y −10,4).
- **Cualquier hecho contra `every-2`:** +1,5 / +2,3 (weekly r0 / r1), +3,7 y +0,7 puntos, por 1,29–1,35 veces el costo de los sueños. La ventaja sale de `new` (+5 a +10 puntos). Supera el ruido de P4 (1,9 puntos) en dos de las cuatro corridas, así que esto **valida, no concluye**.
- **Proyección a monthly completo** (615 sesiones por persona, §4.3): `triggered-phrases-any` ≈ $0,42 por persona, contra $0,55 de `every-1` y $0,31 de `every-2`. El detector con el modelo costaría $0,092 por persona más.

| Rol | Ruta |
| --- | --- |
| Tag | `p5` |
| Detectores y política (sin `truth`/`exam`/`session_changes`) | `policies/triggered.py` (`PhraseDetector`, `ModelDetector`, `Screened`, `Triggered`) |
| Detector solo, contra la verdad de P1 | `policies/triggered_detector.py` |
| Punta a punta con el motor, y la referencia fija mínima `Every` | `policies/triggered_run.py` |
| Costo medido, ajuste y proyección | `policies/triggered_projection.py` |
| Tests (3, sin API) | `tests/test_triggered.py` |
| Salidas de las corridas (ignoradas por git; los comandos las regeneran desde el caché) | `results/p5b/*.txt`, caché en `results/raw/p5/` |

Uso:

```python
from answering.client import BudgetedClient
from policies.engine import run_policy
from policies.triggered import PhraseDetector, Triggered

policy = Triggered(PhraseDetector(), "any")                 # name "triggered-phrases-any"
run = run_policy(policy, "monthly", "academic_researcher", BudgetedClient("p5", 1.00), through=210)
```

## 1. Problema

Una cadencia fija sueña aunque la sesión no haya traído nada, y no sueña aunque la sesión haya cambiado algo. El objetivo es detectar después de cada sesión, y barato, si trae algo que las notas no reflejan, y soñar solo en ese caso.

Ejemplo real, monthly/academic_researcher s56 (2025-06-03). El usuario dice "I need to update the budget from $200,000 to $250,000" y después "let's revise that budget from $250,000 down to $225,000". El examen de la s56 pregunta el presupuesto actual de la propuesta 'Predictive Biomarker Discovery Platform for Rare Disease Diagnosis':

| Política | Último sueño antes del examen de s56 | Respuesta |
| --- | --- | --- |
| `every-3` | s54 | 200000 (`stale`) |
| `triggered-phrases-change` | s56: "update" y "revise" dispararon el sueño | 225000 (correcta) |

Y lo contrario, s1–7 de la misma persona. En s1 el usuario dice "I've always admired Katharine Hepburn's … performances", y hasta la s7 ninguna sesión trae un cambio. `triggered-phrases-change` no sueña ni una vez antes del examen de s7, así que contesta `unknown` (`missing`); `every-3` contesta "like".

En las sesiones de Memora, la parte que hay que recordar es una frase suelta en medio de una charla (AR s1, s2: "I just spent $5.16 on coffee"). Las sesiones sin nada son exactamente las `no_memory` del simulador: 75 de 210 en academic_researcher. Cada sesión mide unos 1.700 caracteres, en s1–210 y después por igual (`triggered_projection`: 1.720 y 1.714 de media en monthly). Un detector que lee solo la sesión cuesta lo mismo en toda la persona.

## 2. Opciones investigadas

| Fuente | Qué dice | Qué se tomó |
| --- | --- | --- |
| **RecMem**, https://aclanthology.org/2026.findings-acl.1619.pdf | **Qué dispara** (§3.2, Ec. 5): cada turno se guarda con su embedding; se consolida solo si entre los top-k turnos parecidos hay \|R_i\| ≥ θ_count con cos ≥ θ_sim (θ_sim = 0,7, θ_count = 5 en LoCoMo; 0,6 y 4 en LongMemEval-S, §4.1 y §3.6). **Qué cuesta** el disparador: un embedding (`text-embedding-3-small`) y una búsqueda vectorial, sin LLM ("LLMs are only invoked … when sustained recurrence are observed", resumen). Ese costo no se reporta: las tablas cuentan solo tokens de LLM. **Qué mide** (§4.1, Tablas 1–2): precisión con un juez LLM y tokens de construcción por conversación. Por ejemplo, LoCoMo con GPT-4.1-mini da 81,10 con 193,2K tokens, contra 1.520,8K de Mem0 (−87,3 %). **Límite** (§6, "Recurrence as a Proxy for Salience"): "may risk overlooking rare but critical events … that appear only once". Lo compensa porque guarda los turnos crudos y los puede recuperar. | **Por qué no sirve acá:** en Memora un cambio se dice una sola vez ("I just finished coordinating with the research team", AR s29), así que la recurrencia no dispararía nunca. Además, el diseño v1 responde solo desde las notas, sin turnos crudos como red. **Qué se tomó:** un disparador sin LLM y el LLM solo cuando hay señal, y la métrica de costo de construcción (acá: sueños + detector). **Diferencia de fondo:** RecMem dispara por parecido entre turnos; acá se dispara por el contenido de la sesión. |
| **Sleep-time compute**, https://arxiv.org/abs/2504.13171 (HTML v1) | §5.3: amortizar el cómputo offline entre 10 preguntas sobre el mismo contexto baja el costo por pregunta hasta 2,5× (los tokens de test cuestan t = 10 veces más). En la Fig. 9: "When there are fewer questions per context … it is less favorable". §5.4 y §7: rinde más cuando la pregunta es predecible desde el contexto; si no, "it may be preferable to apply standard test-time scaling". | Un sueño solo vale si después hay algo nuevo que preguntar. Soñar después de una sesión de charla (`no_memory`) es puro costo. Soñar después de una sesión con un hecho prepara justo la pregunta que puede venir. Es el argumento a favor del blanco "cualquier hecho". |
| **Letta**: código `letta/groups/sleeptime_multi_agent_v3.py` (commit 67013ef1, https://github.com/letta-ai/letta/blob/67013ef1/letta/groups/sleeptime_multi_agent_v3.py), docs https://docs.letta.com/agent-sdk/memory/index.md § "Dreaming" y blog https://www.letta.com/blog/sleep-time-compute/ § "Configuring sleep-time agents" | El agente de sueño corre cuando `turns_counter % sleeptime_agent_frequency == 0`. Hoy el disparador es `"off" \| "step-count" \| "compaction-event"`, con `stepCount`. El blog advierte: "The higher the frequency setting, the more tokens your agent will use". | Letta usa una cadencia fija, o la presión de contexto (compactación), nunca el contenido. Su `compaction-event` se parece al tope de espera (`max_wait`) de acá. |
| **P2**, `docs/p2-examen.md` § "Hipótesis heredadas" | Las frases de cambio cubren 396/396 gustos, 302/308 documentos, 36/42 calendario y 359/387 pendientes en monthly. Las metas, solo **8/66**: la meta nueva se enuncia sin nombrar la anterior. | Las frases de `CHANGE_PHRASES` parten de esa lista. El agujero de las metas se confirma en §4.1 (25/62). |

## 3. Análisis y elección

### 3.1 El blanco: cualquier hecho, no solo contradicciones

Se miden los dos (§4.1), pero la política tiene que disparar con **cualquier hecho**. El examen pregunta tanto por lo nuevo como por lo que cambió (60 preguntas `new` contra 26 `recent_change` en weekly s1–161; 77 contra 38 en monthly s1–210), y un hecho nuevo que espera el próximo sueño sale `missing`. Con el blanco "solo contradicciones", lo que espera en cada examen son 1,07–1,17 sesiones con hechos, contra 0,65–0,67 de `every-3` y 0,00 de `triggered-phrases-any` (§4.2, columna "of them with facts").

### 3.2 El detector: frases, gratis

Hay cuatro detectores, todos en `policies/triggered.py`, que devuelven `change`, `new` o `none`:

| Detector | Qué lee | $ por sesión | Cualquier hecho: disparos / precisión / recall | Solo cambio: disparos / precisión / recall |
| --- | --- | --: | --- | --- |
| `phrases` (`CHANGE_PHRASES`, `FACT_CUES`, sobre los turnos del usuario) | sesión | 0 | 76–80 % / 82 % / 96–97 % | 26–30 % / 57–62 % / 93–97 % |
| `model`: una llamada sin thinking, cita las líneas y termina en "Verdict:" | sesión | 0,000150 | 64–68 % / 98 % / 97–100 % | 22–24 % / 69–75 % / 95–96 % |
| `model-notes`: lo mismo, con las notas perfectas de s−1 | notas + sesión | 0,000447 (s1–210, crece con las notas) | 66 % / 96 % / 98 % | 28 % / 64 % / 100 % |
| `screened-model`: frases primero, el modelo solo si las frases ven algo | sesión | 0,000115–0,000119 | 60–66 % / 99–100 % / 94–97 % | 21–24 % / 68–76 % / 92–93 % |

Rangos sobre weekly/software_engineer s1–161 y monthly/academic_researcher s1–210; `model-notes` solo sobre la monthly.

**Por qué ganan las frases.** El modelo dispara menos (es más preciso), pero lo que ahorra en sueños es menos de lo que cuesta preguntarle. En weekly ahorra 18 sueños, y la política gasta $0,067 en sueños + $0 de detector, contra $0,061 + $0,024. En monthly ahorra 25, y la cuenta es $0,103 contra $0,091 + $0,031. Con el ajuste de §4.3, un sueño de 1–2 sesiones cuesta $0,00024 + $0,000039 por cada 1.000 caracteres de notas + $0,000118 por sesión. El detector cuesta $0,00015 por sesión en **todas** las sesiones. Solo convendría con notas de más de ~26.000 caracteres, y las perfectas de monthly no pasan de 24.178 (la cuenta está en §6). El examen tampoco distingue entre los dos detectores: 93,0 contra 93,4 % y 97,3 contra 96,5 %.

**Errores de las frases** (casos reales):
- Disparos de más: "I have to go now" (AR s3, `no_memory`) y "how people used to manage finances" (SE s10, un café nuevo marcado `change`).
- Cambios que no ven: las metas (25 de 62 en monthly), porque la meta nueva no nombra a la anterior.

Con el blanco "cualquier hecho", un cambio de meta igual dispara: las frases marcan el 100 % de las sesiones con una meta (118/118 en monthly), aunque no siempre como `change`.

**Errores del modelo** (casos reales, AR):
- "I also need to review journal submissions" (s8).
- "I actually just finished planning my reading for pleasure" (s77).
- "I actually really like [savanna climates]" (s112).

Los tres salieron `none`.

### 3.3 La política elegida

`Triggered(PhraseDetector(), "any")`, nombre `triggered-phrases-any`: sueña después de toda sesión en la que las frases ven un hecho o un cambio. No lleva `max_wait`, porque el sueño más largo medido leyó 3 sesiones (weekly) y 6 (monthly). Con el blanco "solo cambio" llegó a 11 y 19.

## 4. Prueba

Todas las llamadas usaron `claude-haiku-5-5` con el presupuesto `p5b`.
- **Sueños y exámenes:** `BudgetedClient` por omisión (thinking adaptativo, effort `medium`).
- **Detector:** `thinking={"type": "disabled"}`, effort `low`, `max_tokens=200`.

Todo sale gratis del caché `results/raw/p5/`.

```
$ uv run pytest -q
............................................                             [100%]
44 passed
```

### 4.1 El detector solo, contra la verdad de P1

```
$ uv run python -m policies.triggered_detector phrases weekly/software_engineer:161 monthly/academic_researcher:210 'weekly/*' 'monthly/*'
$ uv run python -m policies.triggered_detector model weekly/software_engineer:161 monthly/academic_researcher:210
$ uv run python -m policies.triggered_detector model-notes monthly/academic_researcher:210
$ uv run python -m policies.triggered_detector screened-model weekly/software_engineer:161 monthly/academic_researcher:210
```

La etiqueta de cada sesión es `session_change` ("none" / "add" / "change"). Los dominios salen de `timeline.changed_between(s−1, s)`. `model-notes` recibe las notas perfectas de s−1 (`render_notes(state_after(s−1))`), así que "algo que las notas no reflejan" coincide con la etiqueta. El script lee la verdad para medir; los detectores no.

Matrices de confusión (filas: verdad; columnas: veredicto none / new / change):

| | phrases, SE s1–161 | model, SE s1–161 | phrases, AR s1–210 | model, AR s1–210 | model-notes, AR s1–210 |
| --- | --- | --- | --- | --- | --- |
| none | 30 / 18 / 5 | 51 / 1 / 1 | 46 / 27 / 2 | 72 / 3 / 0 | 69 / 0 / 6 |
| add | 1 / 68 / 11 | 0 / 72 / 8 | 4 / 69 / 25 | 3 / 79 / 16 | 3 / 80 / 15 |
| change | 2 / 0 / 26 | 0 / 1 / 27 | 1 / 0 / 36 | 1 / 1 / 35 | 0 / 0 / 37 |

Las frases sobre **todas** las personas (gratis):

| Período | Sesiones | Cualquier hecho: disparos / precisión / recall | Solo cambio: disparos / precisión / recall |
| --- | --: | --- | --- |
| weekly | 1.551 | 76 % / 84 % / 96 % | 27 % / 64 % / 93 % |
| monthly | 6.150 | 73 % / 81 % / 98 % | 28 % / 63 % / 90 % |

Recall de cambios por dominio, frases, monthly completo:

| Dominio | Recall |
| --- | --: |
| content | 302/302 |
| preference | 383/396 (97 %) |
| todo | 334/387 (86 %) |
| calendar | 26/41 (63 %) |
| goal | 25/62 (40 %) |

Con cualquier hecho, el recall va del 84 % (calendar) al 100 % (content, expense, goal, steps).

Costo del detector `model`: $0,000150 por sesión con ~1.050 tokens de entrada; 371 llamadas, $0,0556. `model-notes`: $0,000447 por sesión con 3.888 tokens; 210 llamadas, $0,0938.

**Respuestas cortadas.** 13 de 371 respuestas de `model` y 19 de 210 de `model-notes` llegaron a los 200 tokens citando ítems de un documento sin escribir el veredicto. Cuentan como `change`, el lado seguro: son sesiones con hechos.

**El prompt de `model`** se ajustó una vez sobre weekly/software_engineer s1–35, que está dentro de la muestra. La primera versión pedía una sola palabra y no veía 4 de 25 sesiones con hechos, todas frases sueltas en medio de la charla. Las frases se escribieron antes de medir y no se tocaron después.

### 4.2 La política de punta a punta, con el motor de P5

```
$ uv run python -m policies.triggered_run weekly/software_engineer:161 --policies triggered-phrases-change every-3
$ uv run python -m policies.triggered_run weekly/software_engineer:161 --policies triggered-phrases-any triggered-model-any every-2
$ uv run python -m policies.triggered_run monthly/academic_researcher:210 --policies triggered-phrases-change every-3
$ uv run python -m policies.triggered_run monthly/academic_researcher:210 --policies triggered-phrases-any triggered-model-any every-2
$ uv run python -m policies.triggered_run monthly/startup_founder:210 --policies triggered-phrases-any every-2
$ uv run python -m policies.triggered_run weekly/software_engineer:161 --policies triggered-phrases-any every-2 --repetition 1
```

`weekly/software_engineer` tiene 163 sesiones. Se corre hasta la s161, el último examen, como en P4.

`runs_table` (las cuatro cuentas y las cinco clases del conteo oficial):

| policy | period/persona | rep | dreams | dream $ | decision $ | exam $ | official | lenient | official without marked | lenient without marked | correct | stale | missing | invented |
| --- | --- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| triggered-phrases-change | weekly/software_engineer | 0 | 42 | 0.0369 | 0.0000 | 0.0176 | 367/426 (86.2%) | 367/426 (86.2%) | 364/416 (87.5%) | 364/416 (87.5%) | 367 | 25 | 20 | 14 |
| every-3 | weekly/software_engineer | 0 | 53 | 0.0421 | 0.0000 | 0.0171 | 386/426 (90.6%) | 386/426 (90.6%) | 384/416 (92.3%) | 384/416 (92.3%) | 386 | 18 | 10 | 12 |
| triggered-phrases-any | weekly/software_engineer | 0 | 128 | 0.0668 | 0.0000 | 0.0179 | 396/426 (93.0%) | 396/426 (93.0%) | 394/416 (94.7%) | 394/416 (94.7%) | 396 | 12 | 4 | 14 |
| triggered-model-any | weekly/software_engineer | 0 | 110 | 0.0609 | 0.0242 | 0.0175 | 398/426 (93.4%) | 398/426 (93.4%) | 396/416 (95.2%) | 396/416 (95.2%) | 398 | 14 | 4 | 10 |
| every-2 | weekly/software_engineer | 0 | 80 | 0.0507 | 0.0000 | 0.0172 | 390/426 (91.5%) | 390/426 (91.5%) | 389/416 (93.5%) | 389/416 (93.5%) | 390 | 18 | 8 | 10 |
| triggered-phrases-any | weekly/software_engineer | 1 | 128 | 0.0667 | 0.0000 | 0.0171 | 395/426 (92.7%) | 395/426 (92.7%) | 392/416 (94.2%) | 392/416 (94.2%) | 395 | 14 | 5 | 12 |
| every-2 | weekly/software_engineer | 1 | 80 | 0.0494 | 0.0000 | 0.0176 | 385/426 (90.4%) | 385/426 (90.4%) | 383/416 (92.1%) | 383/416 (92.1%) | 385 | 23 | 8 | 10 |
| triggered-phrases-change | monthly/academic_researcher | 0 | 63 | 0.0598 | 0.0000 | 0.0263 | 541/593 (91.2%) | 541/593 (91.2%) | 540/586 (92.2%) | 540/586 (92.2%) | 541 | 32 | 17 | 3 |
| every-3 | monthly/academic_researcher | 0 | 70 | 0.0629 | 0.0000 | 0.0259 | 546/593 (92.1%) | 546/593 (92.1%) | 546/586 (93.2%) | 546/586 (93.2%) | 546 | 38 | 9 | 0 |
| triggered-phrases-any | monthly/academic_researcher | 0 | 159 | 0.1026 | 0.0000 | 0.0257 | 577/593 (97.3%) | 577/593 (97.3%) | 575/586 (98.1%) | 575/586 (98.1%) | 577 | 14 | 2 | 0 |
| triggered-model-any | monthly/academic_researcher | 0 | 134 | 0.0907 | 0.0314 | 0.0257 | 572/593 (96.5%) | 572/593 (96.5%) | 571/586 (97.4%) | 571/586 (97.4%) | 572 | 20 | 1 | 0 |
| every-2 | monthly/academic_researcher | 0 | 105 | 0.0770 | 0.0000 | 0.0255 | 555/593 (93.6%) | 555/593 (93.6%) | 555/586 (94.7%) | 555/586 (94.7%) | 555 | 30 | 8 | 0 |
| triggered-phrases-any | monthly/startup_founder | 0 | 156 | 0.1057 | 0.0000 | 0.0271 | 520/581 (89.5%) | 520/581 (89.5%) | 517/541 (95.6%) | 517/541 (95.6%) | 520 | 17 | 20 | 24 |
| every-2 | monthly/startup_founder | 0 | 105 | 0.0821 | 0.0000 | 0.0272 | 516/581 (88.8%) | 517/581 (89.0%) | 513/541 (94.8%) | 514/541 (95.0%) | 516 | 20 | 20 | 25 |

`unparseable` = 0 en todas las filas. En startup_founder, la columna "without marked" sube 6 puntos: son los gastos "last night" de P4 §3.3 (expense: 61/96 y 60/96).

**Dónde gana y dónde pierde** (oficial, por probe):

| Comparación | recent_change | new | stable | aggregate |
| --- | --- | --- | --- | --- |
| phrases-change contra every-3, SE | **100,0** contra 92,3 | 58,3 contra **78,3** | 93,2 contra 94,6 | 54,5 contra 68,2 |
| phrases-change contra every-3, AR | **94,7** contra 76,3 | 66,2 contra **76,6** | 95,4 contra 94,8 | 82,5 contra 93,0 |
| phrases-any contra every-2, SE r0 / r1 | 96,2 = 96,2 / 100,0 contra 96,2 | **95,0** contra 85,0 / **91,7** contra 81,7 | 94,1 contra 93,2 / 93,2 contra 91,2 | 68,2 contra 72,7 / 72,7 contra 75,0 |
| phrases-any contra every-2, AR | **97,4** contra 81,6 | **94,8** contra 84,4 | 96,4 contra 94,8 | 100 contra 94,7 |
| phrases-any contra every-2, SF | 88,2 contra 85,3 | **89,6** contra 84,4 | 89,8 contra 90,8 | 66,1 contra 62,5 |

Sesiones sin soñar en cada examen (media), y cuántas de ellas tenían hechos:

| Política | SE | AR | SF |
| --- | --- | --- | --- |
| phrases-change | 2,48 / 1,17 | 1,97 / 1,07 | — |
| every-3 | 1,04 / 0,65 | 1,00 / 0,67 | — |
| phrases-any | 0,26 / 0,00 | 0,40 / 0,00 | 0,27 / 0,10 |
| model-any | 0,48 / 0,00 | 0,53 / 0,07 | — |
| every-2 | 0,52 / 0,39 | 0,50 / 0,43 | 0,50 / 0,33 |

**Por dominio** (salida completa en `results/p5b/run-*.txt`): las diferencias de `phrases-any` contra `every-2` están en content (+5,2 y +11,7 puntos en SE r0 y r1, +4,9 en AR, +3,6 en SF) y en todo/expense/steps, que es donde llegan los hechos nuevos. `phrases-change` pierde en expense (68,0 contra 80,0 en SE; 83,5 contra 95,9 en AR): los gastos siempre son nuevos y nunca disparan el sueño.

### 4.3 Costo: medido y proyectado para P7

```
$ uv run python -m policies.triggered_projection weekly monthly
dream $ = 0.000240 + 0.000039 per 1,000 characters of notes + 0.000118 per session read (1413 measured dreams, mean absolute error $0.000108)
model detector: $0.000150 per call (371 measured calls)
```

El script reconstruye las 14 corridas de §4.2 desde el caché, con un cliente de tope $0, así que no llama a nada. Ajusta el costo de los 1.413 sueños medidos. El ajuste reproduce el costo de cada corrida con un error del 0–6 %; por ejemplo, $0,1026 medidos contra $0,1052 del ajuste en AR phrases-any. El modelo de P4a ($0,00047 de base) dejó la estimación de los sueños de 1–2 sesiones un 24–31 % por encima de lo pagado: el `--dry-run` de `triggered_run` lo usa, y es el lado seguro.

Después extrapola cada política a **todas** las sesiones de **las 10 personas** de cada período, con media por persona. Para la longitud de las notas toma la de las notas perfectas. Los sueños de frases y de cadencias fijas son exactos, porque deciden sin mirar las notas. Los de `model` se toman donde la verdad tiene un hecho (recall 97–100 %).

| Política | weekly: sueños / total $ | monthly: sueños / sueños $ / detector $ / total $ |
| --- | --- | --- |
| every-1 | 155 / 0,0801 | 615 / 0,5504 / 0 / 0,5504 |
| every-2 | 77 / 0,0489 | 307 / 0,3111 / 0 / 0,3111 |
| every-3 | 51 / 0,0386 | 204 / 0,2310 / 0 / 0,2310 |
| every-5 | 31 / 0,0302 | 123 / 0,1673 / 0 / 0,1673 |
| triggered-phrases-change | 42 / 0,0351 | 170 / 0,2043 / 0 / 0,2043 |
| **triggered-phrases-any** | 118 / 0,0652 | 451 / 0,4201 / 0 / **0,4201** |
| triggered-model-any | 103 / 0,0821 | 374 / 0,3583 / **0,0922** / 0,4504 |

- **Medido:** el detector `model` cuesta $0,000150 por llamada, en 371 llamadas. No lee notas, así que no crece a lo largo de la persona: las sesiones miden igual en s1–210 y s211–615.
- **Extrapolado:** 615 llamadas por persona monthly, $0,092, el 20 % del costo de su política. Un detector con notas costaría al menos 3 veces eso, y crecería con las notas.
- **Sin contar exámenes** (unos $0,0009 cada uno en monthly, medido en §4.2), `triggered-phrases-any` cuesta un 24 % menos que `every-1` en monthly y un 19 % menos en weekly.

### 4.4 Costo real

| Corrida | Pagado |
| --- | --: |
| Detector `model`, SE s1–35, primer prompt (descartado) | $0,0033 |
| Detector `model`, SE s1–161 y AR s1–210 (incluye s1–35 con el prompt final) | $0,0556 |
| Detector `model-notes`, AR s1–210 | $0,0939 |
| SE: phrases-change + every-3 | $0,1137 |
| SE: phrases-any + model-any + every-2 | $0,2232 |
| AR: phrases-change + every-3 | $0,1748 |
| AR: phrases-any + model-any + every-2 | $0,3458 |
| SF: phrases-any + every-2 | $0,2422 |
| SE r1: phrases-any + every-2 | $0,1509 |
| **Total `p5b`** (`results/spend/p5b.jsonl`) | **$1,4034 de $1,50** |

Las estimaciones previas (`--dry-run`) quedaron un 14–31 % arriba de lo pagado.

## 5. Opciones descartadas y por qué

| Opción | Por qué no |
| --- | --- |
| Disparar solo con contradicciones (`triggered-*-change`) | Por un 5–12 % menos que `every-3` pierde 4,4 y 0,9 puntos. Los hechos nuevos esperan: `new` baja de 78,3 a 58,3 y de 76,6 a 66,2. Gana en `recent_change`, pero eso pesa menos de la mitad que `new` en el examen. |
| Detector con el modelo, solo la sesión | Precisión del 98 % contra 82 %, pero cuesta $0,024–0,031 por tramo y ahorra $0,006–0,012 de sueños. Con el examen no se distingue de las frases (93,4 contra 93,0; 96,5 contra 97,3). Queda como opción para usuarios reales (§6). |
| Detector con el modelo, notas + sesión | 3 veces más caro ($0,000447 por sesión, creciente) y no más preciso: 6 sesiones `none` marcadas `change`. Además, sus llamadas no se comparten entre políticas, porque cada una tiene otras notas. |
| Frases primero y el modelo solo si las frases ven algo (`screened-model`) | Ahorra el 22 % del detector ($0,00003 por sesión) y pierde 3–8 sesiones con hechos de recall. Medido gratis desde el caché; no se corrió de punta a punta. |
| Recurrencia al estilo RecMem | Un cambio en Memora se dice una vez; RecMem mismo lo admite en §6. Además pide embeddings y un índice, fuera de las dependencias del proyecto. |
| Tope de espera (`max_wait`) | Con el blanco "cualquier hecho", el sueño más largo leyó 3–6 sesiones: el tope no cambia nada. Está implementado (`-wait<k>`) y su costo está estimado en el `--dry-run`, pero no se corrió. |
| Cadencia fija 7 como referencia | Con `exam_every=7` coincidiría con cada examen y siempre estaría fresca. Por eso las referencias son 2 y 3, coprimas con 7. |

## 6. Limitaciones y preguntas abiertas

- **Muestra.** 3 tramos (SE s1–161, AR s1–210, SF s1–210). Dos repeticiones solo para `phrases-any` y `every-2` en SE: +1,5 y +2,3 puntos. Las comparaciones de "solo cambio" son de una corrida en 2 personas. Quarterly no se midió. **Esto valida, no concluye.**
- **`every-1` no se corrió.** La proyección dice que `phrases-any` cuesta 19–24 % menos. Que acierte lo mismo es lo esperable: en los exámenes no espera ninguna sesión con hechos. Lo puede confirmar P5 al integrar con la `every-1` de P5a, si existe.
- **Las frases están escritas para el inglés del simulador de Memora.** Con usuarios reales no se sabe cuánto rinden. El detector `model` es la opción robusta y cuesta +$0,09 por persona monthly. Solo se paga cuando cada sueño evitado vale más que el detector en todas las sesiones. El modelo dispara unos 12 puntos menos (68 contra 80 % y 64 contra 76 % de las sesiones), así que cada sueño evitado cuesta $0,00015 / 0,12 ≈ $0,00125 de detector. Un sueño evitado ahorra $0,00024 + $0,000039 por cada 1.000 caracteres de notas: la sesión igual la lee el sueño siguiente. Las dos cosas se igualan con ~26.000 caracteres de notas. Las notas perfectas de monthly miden 11.657 en la s210 y 21.683 al final, con un máximo de 24.178 (`triggered_projection`): en monthly no llega a pagarse. Quarterly no se midió.
- **El detector `model` corta 13 de 371 respuestas** en documentos largos. Cuentan como `change`, que es correcto en esos casos. Pedir el veredicto primero lo arreglaría, pero cambiaría el prompt e invalidaría su caché.
- **Desvío del contrato (para P5).** `Triggered.decide` guarda los veredictos en `.../decide/<detector>/...` y no en `.../decide/<policy>/...`. Así las políticas con el mismo detector y la medición del detector solo comparten llamadas. Las frases no llaman a nada.
- **Referencias fijas.** `Every` en `policies/triggered_run.py` es mínima y decide `session_id % n == 0`. Si `policies/fixed.py` de P5a decide igual, al integrar sus sueños salen del mismo caché.
- **Para P7, presupuesto.** Monthly completo con las 10 personas cuesta, solo en sueños, $3,1 con `every-2`, $4,2 con `triggered-phrases-any` y $5,5 con `every-1`. Más de lo que queda en la organización: P7 va a necesitar una muestra.
- **Para P6.** El ajuste de §4.3 (1.413 sueños: $0,00024 + $0,000039 por 1.000 caracteres + $0,000118 por sesión) reemplaza la base de $0,00047 de P4a para sueños cortos.
