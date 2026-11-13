# P5 · Políticas de cadencia

**Resultado.** Un motor (`policies/engine.py`) encadena los sueños de P4 a lo largo de una persona según una política que decide después de cada sesión, y toma el examen de P2 cada 7 sesiones. Hay 11 políticas: nunca, cada k sesiones (k = 1, 2, 3, 5, 10, 20, 50) y tres disparadas por lo que trae la sesión. Corren todas de punta a punta sobre monthly/academic_researcher s1–210:

| Política | Sueños | $ sueños + detector | $ exámenes | Examen oficial | Sin preguntas marcadas | Sesiones esperando en un examen (con hechos) |
| --- | --: | --: | --: | --: | --: | --: |
| never | 0 | 0,0000 | 0,0113 | 23,9 % | 24,3 % | 108,5 (70,8) |
| every-50 | 4 | 0,0281 | 0,0248 | 59,2 % | 59,8 % | 25,2 (16,4) |
| every-20 | 10 | 0,0319 | 0,0257 | 76,1 % | 77,1 % | 9,2 (5,5) |
| every-10 | 21 | 0,0399 | 0,0266 | 82,3 % | 83,4 % | 4,5 (2,8) |
| every-5 | 42 | 0,0499 | 0,0259 | 89,2 % | 90,4 % | 2,0 (1,2) |
| triggered-phrases-change | 63 | 0,0598 | 0,0261 | 91,2 % | 92,3 % | 2,0 (1,1) |
| every-3 | 70 | 0,0629 | 0,0259 | 92,1 % | 93,3 % | 1,0 (0,7) |
| every-2 | 105 | 0,0770 | 0,0255 | 93,6 % | 94,9 % | 0,5 (0,4) |
| **triggered-phrases-any** | 159 | 0,0992 | 0,0251 | **96,1 %** (97,3 % en P5b) | 97,4 % | 0,4 (0,0) |
| triggered-model-any | 134 | 0,0888 + 0,0314 | 0,0260 | 95,4 % (96,5 % en P5b) | 96,6 % | 0,5 (0,1) |
| every-1 | 210 | 0,1242 | 0,0264 | **97,1 %** | 98,5 % | 0 (0) |

- **La cadencia pesa por el retraso, no por la pérdida** (P5a §4.2). Una pregunta sobre un hecho que un sueño ya leyó sale bien el 85–96 % de las veces con cualquier k. Si el hecho cambió después del último sueño, sale bien el 0–11 %. La precisión cae con las sesiones que esperan en cada examen, que crecen con k.
- **Disparar con cualquier hecho que vean unas frases gratis** (`triggered-phrases-any`) iguala a soñar después de cada sesión: 96,1–97,3 % contra 97,1 %, con el 76 % de los sueños y el 80 % del costo de soñar. Es la única política disparada que conviene (P5b): disparar solo con contradicciones pierde contra `every-3`, que cuesta lo mismo, y un detector con el modelo cuesta más que los sueños que ahorra.
- **Costo de P7, medido y proyectado** (§4.3). Se ajustó sobre 2.666 sueños y 1.012 exámenes cacheados y se comprobó corriendo `every-5` sobre una persona monthly entera (619 sesiones). Sueños: proyectado $0,1817, pagado $0,1777 (+2 %). Exámenes: proyectado $0,1283, pagado $0,1076 (+19 %, del lado seguro).
  - **Monthly completo, por persona:** $0,20 (`every-50`) a $0,66 (`every-1`); `triggered-phrases-any` $0,54. Los exámenes cada 7 son $0,12 por política.
  - **Las 10 personas monthly × las 7 políticas recomendadas** (§6): ≈ $22 sin repetir. Supera lo que queda en la organización (≈ $2,3), así que P7 necesita una muestra o más presupuesto. Esa decisión queda abierta (§6).
- **Decisión (c) implementada.** Hay 395 preguntas monthly y 151 weekly que ningún sueño fiel puede acertar. Quedan en el examen, marcadas por una regla sin modelo (`exam/unreachable.py`), y cada resultado sale con y sin ellas.

| Rol | Ruta |
| --- | --- |
| Tag | `p5` |
| Interfaz P5a/P5b | `docs/p5-interfaz.md` |
| Informe de P5a (cadencias fijas) | `docs/p5a-cadencias-fijas.md` |
| Informe de P5b (sueño disparado) | `docs/p5b-sueno-disparado.md` |
| Motor y conteo (P5) | `policies/engine.py` (`run_policy`, `PolicyRun`, `score`, `runs_table`) |
| Preguntas marcadas, decisión (c) (P5) | `exam/unreachable.py` (CLI con conteos por dominio) |
| Qué hizo cada sesión con la verdad, para medir detectores (P5) | `policies/session_changes.py` |
| Políticas fijas (P5a) | `policies/fixed.py` (`Never`, `Every`), medición en `policies/fixed_run.py` |
| Políticas disparadas (P5b) | `policies/triggered.py` (`PhraseDetector`, `ModelDetector`, `Screened`, `Triggered`), medición en `policies/triggered_detector.py`, `triggered_run.py`, `triggered_projection.py` |
| CLI de todas las políticas y proyección de costo (P5) | `policies/run.py`, `policies/projection.py` |
| Tests (7 de P5, P5a y P5b; 46 en total) | `tests/test_engine.py` (1), `tests/test_unreachable.py` (1), `tests/test_fixed.py` (2, P5a), `tests/test_triggered.py` (3, P5b) |
| Caché de las corridas (ignorado por git; P7 debería partir de acá) | `results/raw/p5/` de este worktree: 4.433 respuestas de P5a, P5b y P5 |

Uso para P6–P7:

```python
from answering.client import BudgetedClient
from policies.engine import run_policy, runs_table, score
from policies.run import policy_named

client = BudgetedClient("p7", limit_dollars=1.00)
runs = [run_policy(policy_named(name, "p7", 1.00), "monthly", "academic_researcher", client, through=210)
        for name in ("never", "every-1", "every-5", "every-20", "triggered-phrases-any")]
print(runs_table(runs))              # sueños, $ y examen en 4 cuentas (oficial, indulgente, y las dos sin marcadas)
```

```bash
uv run python -m policies.run monthly/<persona>:210 --policies never every-1 every-5 triggered-phrases-any --budget-name p7 --limit 1.00
uv run python -m policies.projection weekly monthly     # costo por política y persona, sin llamar a nada
```

## 1. Problema

El sueño de P4 corrige bien lo que lee, pero solo lee cuando lo llaman. P5 tiene que decidir **cuándo** llamarlo, y construir las políticas y el motor que P7 va a correr.

Ejemplo real, weekly/software_engineer (P5a §1). En la s9 el usuario dice "I need to remember to buy groceries later today". En la s33 dice "I actually finished buying groceries, so you can remove that from my to-do list".

| Examen | Lo que vale | never | every-1 | every-5 | every-10 | every-20 | every-50 |
| --: | --- | --- | --- | --- | --- | --- | --- |
| s14 | el pendiente está | no, `stale` | yes, `correct` | yes, `correct` | yes, `correct` | no, `stale` | no, `stale` |
| s35 | ya no está | no, `correct` | no, `correct` | no, `correct` | yes, `stale` (soñó en s30) | yes, `stale` (soñó en s20) | no, `correct` |

Aparecen las dos cosas que P5 tiene que separar:

- **El retraso:** every-10 y every-20 soñaron cuando el pendiente valía y no volvieron a soñar después de que se borró.
- **Los aciertos vacíos:** never y every-50 contestan bien la s35 sin haber sabido nunca nada.

Hacían falta tres piezas:

- Un **motor** común, para comparar políticas sobre lo mismo.
- **Políticas fijas** (P5a) y **disparadas** (P5b).
- Una **regla para contar** las preguntas que ningún sueño puede acertar (decisión (c), P4).

## 2. Opciones investigadas

El detalle, con las secciones citadas, está en P5a §2 y P5b §2.

| Fuente | Qué se tomó |
| --- | --- |
| Letta, sleep-time agents: código `letta/groups/sleeptime_multi_agent_v3.py` (commit 67013ef1) https://github.com/letta-ai/letta/blob/67013ef1/letta/groups/sleeptime_multi_agent_v3.py y blog https://www.letta.com/blog/sleep-time-compute/ | Consolidación cada N pasos (`turns_counter % sleeptime_agent_frequency == 0`), o por compactación de contexto, nunca por contenido. Es la cadencia fija de P5a. "The higher the frequency setting, the more tokens your agent will use". |
| Sleep-time compute, https://arxiv.org/abs/2504.13171 §5.3–5.4 | El cómputo offline rinde cuando después vienen preguntas predecibles sobre ese contexto: soñar tras una sesión de charla es puro costo. Es el argumento para disparar con cualquier hecho. |
| RecMem, https://aclanthology.org/2026.findings-acl.1619.pdf §3.2, §4.1, §6 | Consolida cuando un turno se repite (similitud ≥ θ, ≥ k veces), con un disparador sin LLM. En Memora un cambio se dice una sola vez, así que la recurrencia no dispararía. Se tomó la idea de un disparador barato sin LLM y el costo de construcción como métrica. |
| Dreams de Managed Agents, https://platform.claude.com/docs/en/managed-agents/dreams | El costo de un sueño crece con las sesiones que lee. Se confirmó: $0,000133 por sesión leída (§4.3). |
| P2a, `docs/p2a-que-preguntar-y-cuando.md` §3.1 | El examen cada 7, coprimo con 5, 20 y 50 (y con 2, 3 y 10), recorre todas las fases de cada cadencia. |

## 3. Análisis y elección

### 3.1 El motor (P5)

| Pieza | Elección | Por qué |
| --- | --- | --- |
| Decisión | `Policy.decide(notes, pending, client, run)` después de cada sesión. `pending` son las sesiones desde el último sueño. | Una sola interfaz para las fijas, que miran `len(pending)`, y las disparadas, que miran `pending[-1]`. |
| Sueño | Lee las notas y **todo** `pending`, y lo vacía | Cada sesión se lee exactamente una vez: las omisiones son permanentes (P4), y releer costaría. |
| Examen | Después de cada sesión N múltiplo de 7, con las notas que dejó el sueño de N | Semántica de P2: el examen de N es la primera pregunta de la sesión N+1. |
| Final | Sin sueño forzado | Ninguna persona tiene más de 6 sesiones después de su último examen, y ninguno las lee (P5a §3.2). Soñar justo antes de cada examen sería hacer trampa. |
| Caché | Por pedido, en `results/raw/p5/r<rep>/{dream,exam}/<period>/<persona>/`, compartido por todas las políticas | Dos políticas con las mismas notas reciben el mismo sueño y las mismas respuestas. Es más barato, y la comparación queda emparejada: never y every-50 comparten 7 de 7 exámenes hasta la s49, y se pagaron una vez (P5a §4.4). |
| Conteo | `score`: oficial, indulgente, y los dos sin las preguntas marcadas, más las cinco clases | Decisiones de P2 y de P5. |

### 3.2 Decisión (c): preguntas marcadas

`exam/unreachable.py` marca, sin modelo, tres clases de pregunta. El examen y su caché no cambian (detalle y conteos por dominio en `docs/p2-examen.md` § "Decisiones").

- **`unsaid_item`:** un ítem de lista que vale, cuyas palabras la sesión donde empezó a valer nunca dice. Ejemplo: "Mr. David Kim (Systems Integration Lead, Engineering Department)" cuando el usuario dijo "Mr. David Kim".
- **`relative_date`:** un gasto "last night" o "yesterday" que Memora fecha el día de la sesión, y los totales semanales que arrancan ese día.
- **`completed_task`:** un pendiente que Memora agrega cuando el usuario dice que lo terminó ("I completed a task to coordinate with the research team", s25). Lo medí: la regla estricta, en pasado y nombrando la tarea, encuentra 1 caso monthly y 0 weekly, y es correcto. La regla amplia agarra anuncios ("I need to complete logo design concepts").
- **Las paráfrasis no se marcan:** se pueden acertar y casi siempre se aciertan. Marcarlas sacaría el 13 % de las preguntas de pendientes monthly.

| | weekly | monthly |
| --- | --: | --: |
| Preguntas | 4.039 | 18.214 |
| Marcadas | 151 (3,7 %) | 395 (2,2 %) |
| de ellas content / expense / todo | 57 / 89 / 5 | 164 / 223 / 8 |

Efecto: sacar las marcadas sube la precisión entre 0,4 y 1,4 puntos y nunca cambian el orden de las políticas (tabla del encabezado). Casi no pesan sobre la cadencia, como anticipaba P4: son errores del texto de Memora, no del momento en que se sueña.

### 3.3 Políticas elegidas

| Política | Elección | Por qué (número) | Fuente |
| --- | --- | --- | --- |
| `Every(k)` | Sueña cuando `len(pending) ≥ k`; k = 1, 5, 10, 20, 50 | k=10 parte el salto 5→20 y es coprimo con 7. k=7 queda afuera porque coincide con el paso del examen: mediría siempre 0 de retraso. | P5a §3.1, §3.4 |
| `Never` | Piso | 23,9–27,0 %, igual que el piso de P3 con notas vacías | P5a §4.1 |
| `triggered-phrases-any` | Sueña tras toda sesión donde unas frases sobre los turnos del usuario ven un hecho | Recall 96–98 % contra la verdad, precisión 81–84 %, $0 de detector. Iguala a every-1 por el 80 % del costo. | P5b §3.2, §4.1 |
| `triggered-phrases-change` | Medida, **descartada** | Contra every-3, que cuesta lo mismo: −4,4 y −0,9 puntos. Los hechos nuevos esperan hasta la próxima contradicción (`new` −20 y −10 puntos). | P5b §3.1 |
| `triggered-model-any` | Medida, **descartada** para P7 | Es más precisa (98 %), pero el detector cuesta $0,00015 en cada sesión y ahorra menos sueños de lo que cuesta: $0,1202 contra $0,0992 en s1–210. En el examen no se distingue. | P5b §3.2 |
| every-2, every-3 | Solo como referencias de costo de las disparadas | Quedan entre every-5 y every-1 | P5b §4.2 |

## 4. Prueba

Todo corrió con `claude-haiku-5-5`, thinking adaptativo, effort `medium` para sueños y exámenes. El detector `model` corrió sin thinking y con effort `low` (P5b).

```
$ uv run pytest -q
..............................................                           [100%]
46 passed
```

### 4.1 Integración: las 11 políticas de punta a punta, monthly/academic_researcher s1–210

Copié los cachés de P5a y P5b a este worktree. 12 pedidos tenían la misma huella en P5a y P5b y respuestas distintas: son sueños del principio de cadenas que los dos corrieron por separado; por ejemplo, el primer sueño de monthly/academic_researcher, que lee solo la s1 desde notas vacías. Me quedé con los de P5a. Por eso las cadenas disparadas de P5b se separaban desde ahí, y las volví a correr (pagado: $0,2288):

```
$ uv run python -m policies.run monthly/academic_researcher:210 --policies triggered-phrases-any triggered-model-any --budget-name p5 --limit 1.00
p5 spent: $0.0029 before, $0.2317 after
```

Después, todas desde el caché, con tope $0 (falla si algo no está):

```
$ uv run python -m policies.run monthly/academic_researcher:210 --policies never every-1 every-2 every-3 every-5 every-10 every-20 every-50 triggered-phrases-change triggered-phrases-any triggered-model-any --check-cache
| policy | period/persona | rep | sessions | dreams | dream $ | decision $ | exam $ | exams | official | lenient | official without marked | lenient without marked | correct | stale | missing | invented | unparseable |
| never | monthly/academic_researcher | 0 | 210 | 0 | 0.0000 | 0.0000 | 0.0113 | 30 | 142/593 (23.9%) | 142/593 (23.9%) | 142/585 (24.3%) | 142/585 (24.3%) | 142 | 123 | 303 | 25 | 0 |
| every-1 | monthly/academic_researcher | 0 | 210 | 210 | 0.1242 | 0.0000 | 0.0264 | 30 | 576/593 (97.1%) | 576/593 (97.1%) | 576/585 (98.5%) | 576/585 (98.5%) | 576 | 16 | 1 | 0 | 0 |
| every-2 | monthly/academic_researcher | 0 | 210 | 105 | 0.0770 | 0.0000 | 0.0255 | 30 | 555/593 (93.6%) | 555/593 (93.6%) | 555/585 (94.9%) | 555/585 (94.9%) | 555 | 30 | 8 | 0 | 0 |
| every-3 | monthly/academic_researcher | 0 | 210 | 70 | 0.0629 | 0.0000 | 0.0259 | 30 | 546/593 (92.1%) | 546/593 (92.1%) | 546/585 (93.3%) | 546/585 (93.3%) | 546 | 38 | 9 | 0 | 0 |
| every-5 | monthly/academic_researcher | 0 | 210 | 42 | 0.0499 | 0.0000 | 0.0259 | 30 | 529/593 (89.2%) | 529/593 (89.2%) | 529/585 (90.4%) | 529/585 (90.4%) | 529 | 46 | 16 | 2 | 0 |
| every-10 | monthly/academic_researcher | 0 | 210 | 21 | 0.0399 | 0.0000 | 0.0266 | 30 | 488/593 (82.3%) | 488/593 (82.3%) | 488/585 (83.4%) | 488/585 (83.4%) | 488 | 68 | 32 | 5 | 0 |
| every-20 | monthly/academic_researcher | 0 | 210 | 10 | 0.0319 | 0.0000 | 0.0257 | 30 | 451/593 (76.1%) | 451/593 (76.1%) | 451/585 (77.1%) | 451/585 (77.1%) | 451 | 94 | 43 | 5 | 0 |
| every-50 | monthly/academic_researcher | 0 | 210 | 4 | 0.0281 | 0.0000 | 0.0248 | 30 | 351/593 (59.2%) | 351/593 (59.2%) | 350/585 (59.8%) | 350/585 (59.8%) | 351 | 123 | 102 | 17 | 0 |
| triggered-phrases-change | monthly/academic_researcher | 0 | 210 | 63 | 0.0598 | 0.0000 | 0.0261 | 30 | 541/593 (91.2%) | 541/593 (91.2%) | 540/585 (92.3%) | 540/585 (92.3%) | 541 | 32 | 18 | 2 | 0 |
| triggered-phrases-any | monthly/academic_researcher | 0 | 210 | 159 | 0.0992 | 0.0000 | 0.0251 | 30 | 570/593 (96.1%) | 570/593 (96.1%) | 570/585 (97.4%) | 570/585 (97.4%) | 570 | 21 | 2 | 0 | 0 |
| triggered-model-any | monthly/academic_researcher | 0 | 210 | 134 | 0.0888 | 0.0314 | 0.0260 | 30 | 566/593 (95.4%) | 566/593 (95.4%) | 565/585 (96.6%) | 565/585 (96.6%) | 566 | 23 | 4 | 0 | 0 |
...
p5 spent: $0.2317 before, $0.2317 after
```

La salida completa trae además, por política, el costo total, las sesiones por sueño, las sesiones esperando en cada examen, y la precisión por dominio y por probe. Lo que muestra:

- **El motor funciona igual para las dos familias.** Las fijas de P5a salen idénticas a su informe; las disparadas, con su propio caché.
- **Ruido de las disparadas.** La segunda muestra da 96,1 % para phrases-any (P5b: 97,3 %) y 95,4 % para model-any (P5b: 96,5 %), con las mismas decisiones de soñar. Es 1,1–1,2 puntos, dentro del ruido de P4 (1,9) y de P5a (2,8).
- **Por probe** (oficial, s1–210):
  - **`new`:** de 93,5 % (every-1) a 7,8 % (every-50) y 0 % (never), y 88,3 % con phrases-any. Es la columna que más separa a las políticas.
  - **`recent_change`:** favorece a quien sueña poco. never saca 71,1 %, porque con notas vacías "no está" es correcto para lo que se borró (P5a §4.2).
  - **`stable`:** 90,8–96,7 % para todas las que sueñan, salvo every-50 (67,6 %): con 4 sueños en 210 sesiones, muchos hechos estables todavía esperan su primer sueño. never: 0 %.

### 4.2 Una persona monthly entera con every-5 (para validar la proyección)

```
$ uv run python -m policies.run monthly/academic_researcher --policies every-5 --budget-name p5 --limit 1.00
| every-5 | monthly/academic_researcher | 0 | 619 | 123 | 0.1777 | 0.0000 | 0.1076 | 88 | 1577/1809 (87.2%) | 1578/1809 (87.2%) | 1575/1764 (89.3%) | 1576/1764 (89.3%) | 1577 | 123 | 67 | 42 | 0 |
p5 spent: $0.2317 before, $0.4412 after
```

Pagado: $0,2095 (s1–210 ya estaba en caché). La precisión sobre la persona entera (87,2 %) queda 2 puntos por debajo de s1–210 (89,2 %): los `invented` suben de 2 a 42 en 88 exámenes. Ese patrón tiene que mirarlo P7, porque s1–210 puede ser optimista.

### 4.3 Costo de la corrida completa de P7, por política

```
$ uv run python -m policies.projection weekly monthly
dream $ = 0.000204 + 0.000039 per 1,000 note characters + 0.000133 per session read (2666 dreams)
exam $ = 0.000454 + 0.000065 per 1,000 note characters (1012 exams)
a dream's notes / perfect notes after the same session: 1.00

check, every-5 over all of monthly/academic_researcher: projected 123 dreams $0.1817 + exams $0.1283 (measured: ...)
```

- **Cómo se ajusta.** El script ajusta el costo sobre todos los sueños y exámenes cacheados que no leen ninguna sesión después de la s210, así que el control de §4.2 queda **fuera de la muestra**. Contra lo pagado en §4.2: sueños $0,1817 contra $0,1777 (+2,3 %), exámenes $0,1283 contra $0,1076 (+19 %).
- **Por qué los exámenes salen sobreestimados.** Las notas de un sueño tardío miden 0,89–0,97 veces las perfectas, no 1,00 (lo vi en los sueños de §4.2).
- **Cómo proyecta.** Las fijas y las frases deciden sin leer las notas, así que sus sueños son exactos; lo que se extrapola es el largo de las notas. No proyecta `triggered-model-any`: su detector suma $0,092 por persona monthly (P5b §4.3).

| Política | weekly: $ por persona | monthly: sueños | monthly: $ sueños | monthly: $ exámenes | **monthly: $ por persona** | **monthly: 10 personas** |
| --- | --: | --: | --: | --: | --: | --: |
| never | 0,0099 | 0 | 0,0000 | 0,0396 | 0,0396 | 0,40 |
| every-50 | 0,0336 | 12 | 0,0886 | 0,1138 | 0,2024 | 2,02 |
| every-20 | 0,0370 | 30 | 0,1031 | 0,1169 | 0,2200 | 2,20 |
| every-10 | 0,0409 | 61 | 0,1268 | 0,1179 | 0,2448 | 2,45 |
| every-5 | 0,0473 | 122 | 0,1735 | 0,1184 | 0,2919 | 2,92 |
| every-3 | 0,0551 | 205 | 0,2355 | 0,1186 | 0,3541 | 3,54 |
| triggered-phrases-change | 0,0517 | 170 | 0,2095 | 0,1184 | 0,3279 | 3,28 |
| every-2 | 0,0646 | 307 | 0,3131 | 0,1187 | 0,4318 | 4,32 |
| triggered-phrases-any | 0,0796 | 451 | 0,4186 | 0,1188 | 0,5375 | 5,37 |
| every-1 | 0,0933 | 615 | 0,5450 | 0,1188 | 0,6639 | 6,64 |

Las 7 políticas recomendadas (§6) sobre las 10 personas monthly suman **$22,0** con 1 repetición, y $3,42 en weekly. Medido sobre s1–210, en lugar de la persona entera, cuestan $0,54 por persona monthly (suma de la columna "total $" de §4.1 para esas 7), menos lo que el caché comparte entre políticas.

### 4.4 Costo real

| Proceso | Tope | Gastado | Libro |
| --- | --: | --: | --- |
| P5a | $1,50 | $1,3693 | `results/spend/p5a.jsonl` (worktree de P5a) |
| P5b | $1,50 | $1,4034 | `results/spend/p5b.jsonl` (worktree de P5b) |
| P5 (integración) | $1,00 | $0,4412 | `results/spend/p5.jsonl` |
| **Total** | **$4,00** | **$3,2139** | |

Desglose de P5:

| Corrida | Pagado |
| --- | --: |
| Prueba del motor con la API (cadencia 7, weekly s1–14) | $0,0029 |
| Disparadas de nuevo tras el choque de cachés (§4.1) | $0,2288 |
| every-5 sobre monthly/academic_researcher entera (§4.2) | $0,2095 |

## 5. Opciones descartadas y por qué

| Opción | Por qué no | Dónde |
| --- | --- | --- |
| Sacar del examen las preguntas de Memora (opción b) o no marcarlas (opción a) | Elegí (c): marcar y reportar con y sin ellas | `docs/p4-sueno.md` § "Decisiones" |
| Marcar las paráfrasis | Se pueden acertar y casi siempre se aciertan; sería el 13 % de los pendientes monthly | §3.2 |
| Marcar pendientes "terminados" con una regla amplia | Agarra anuncios ("I need to complete…") y charla ("getting some things done") | §3.2 |
| Sueño forzado al final de la persona | Nadie lee esas sesiones; antes de un examen sería trampa | P5a §3.2 |
| `exam_every` mayor que 7 (21, 28, 49) para ahorrar exámenes | Sesga la fase: 21 en tramos cortos, 28 con la cadencia 20, 49 con la cadencia 50 | `docs/p5-interfaz.md`, P5a §4.6 |
| k=7 | Coincide con el paso del examen: siempre 0 de retraso | P5a §3.4 |
| Disparar solo con contradicciones | −4,4 y −0,9 puntos contra every-3, que cuesta lo mismo; los hechos nuevos esperan | P5b §3.1 |
| Detector con el modelo (con o sin notas) | Cuesta más que los sueños que ahorra y no mejora el examen. Con notas cuesta 3 veces más y no es más preciso. | P5b §3.2 |
| Disparar por recurrencia (RecMem) | En Memora un cambio se dice una sola vez | P5b §2 |
| Cachés separados por política | Pagaría dos veces los mismos sueños y exámenes, y dejaría las comparaciones sin emparejar | §3.1 |

## 6. Limitaciones y preguntas abiertas

- **Valida, no concluye.** Monthly: 2 personas en s1–210, con 1 repetición (P5a y P5b), y la integración repite las disparadas sobre una. Weekly: 1 persona, con 2 repeticiones. El orden de las fijas se mantiene en todas las corridas, y las diferencias entre vecinas (every-1 / phrases-any / every-2) son de 1–4 puntos, del tamaño del ruido (1,1–2,8). P7 necesita más personas.
- **Políticas recomendadas para P7:** never, every-1, every-5, every-10, every-20, every-50 y triggered-phrases-any. every-2, every-3, phrases-change y model-any ya respondieron su pregunta.
- **Decisión abierta: presupuesto y muestra de P7.**
  - **(a) Más personas sobre s1–210** (lo que recomiendan P5a y P5): ≈ $0,54 por persona monthly para las 7 políticas, o ≈ $1,1 con 2 repeticiones. Con lo que queda (≈ $2,3), alcanza para unas 2 personas monthly nuevas con 2 repeticiones, más las 2 ya medidas.
  - **(b) Pocas personas enteras:** ≈ $2,2 por persona monthly para las 7 políticas, 1 repetición. Ni una persona con 2 repeticiones entra en lo que queda.

  El retraso depende de k y no del largo del tramo, pero §4.2 muestra que la precisión baja 2 puntos de s1–210 a la persona entera: (a) puede ser optimista en valor absoluto y no en el orden.
- **El detector de frases está escrito para el inglés del simulador de Memora.** "I have to go now" dispara aunque no haya ningún hecho (P5b §6). Con usuarios reales el detector con el modelo sería más robusto, por ≈ $0,09 por persona monthly. P7 mide sobre Memora, así que alcanza con las frases.
- **Desvíos del contrato, aceptados:**
  - Los veredictos del detector se guardan bajo el nombre del detector (`decide/<detector>/`), no bajo el de la política. Así las políticas que usan el mismo detector comparten las llamadas.
  - `policies/triggered_run.py` tiene su propia `Every` mínima (`session_id % k`), que en estos datos decide igual que la de `policies/fixed.py`. `policies/run.py` usa la de P5a.
- **Choque de cachés al integrar.** Los mismos pedidos hechos en dos worktrees dan respuestas distintas. Me quedé con los de P5a, así que las tablas weekly de P5b solo se reproducen gratis en el worktree de P5b. Para P7: un solo caché, este, y nunca correr la misma política en dos worktrees.
- **`invented` crece después de la s210** (2 → 42 con every-5). No lo diagnostiqué.
- **El costo de los exámenes iguala o supera al de soñar** con k ≥ 10 ($0,12 por política y persona monthly). Bajarlo sin sesgar la fase obliga a muestrear preguntas dentro de cada examen, no exámenes. No lo probé.
