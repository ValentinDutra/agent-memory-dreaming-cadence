# P5a · Cadencias fijas

**Resultado.** `policies/fixed.py` define dos políticas: `Never` ("never") y `Every(k)` ("every-k"), que sueña cuando se juntaron k sesiones desde el último sueño. Las medí con k = 1, 5, 10, 20 y 50 sobre weekly/software_engineer s1–161 (dos repeticiones) y sobre monthly/academic_researcher y monthly/startup_founder s1–210, con `exam_every=7`. Gasté **$1,3693** de los $1,50.

| Examen, cuenta oficial (r0) | weekly/software_engineer | monthly/academic_researcher | monthly/startup_founder | $ de sueños por sesión (weekly / monthly) |
| --- | --: | --: | --: | --: |
| never | 27,0 % | 23,9 % | 24,8 % | 0 |
| every-1 | 93,9 % | 97,1 % | 89,7 % | 0,00048 / 0,00059–0,00061 |
| every-5 | 83,1 % | 89,2 % | 84,7 % | 0,00021 / 0,00024–0,00025 |
| every-10 | 78,9 % | 82,3 % | 78,3 % | 0,00017 / 0,00019–0,00020 |
| every-20 | 71,6 % | 76,1 % | 70,7 % | 0,00015 / 0,00015 |
| every-50 | 55,4 % | 59,2 % | 53,7 % | 0,00012 / 0,00013–0,00014 |

- **El orden es el mismo en las 3 personas y en las 2 repeticiones:** every-1 > 5 > 10 > 20 > 50 > never. Entre r0 y r1 la misma política cambia hasta 2,8 puntos (§4.4).
- **La cadencia pesa por el retraso, no por la pérdida.** Si un sueño ya leyó el último cambio del hecho, la pregunta sale bien el 85–96 % de las veces con cualquier k. Si el hecho cambió después del último sueño, sale bien el 0–11 %. En la comparación línea por línea, los hechos que un sueño ya leyó están bien en la misma proporción con cualquier k: 97,7–98,5 % (weekly), 91,1–92,4 % (academic_researcher) y 95,7–96,7 % (startup_founder). Lo que crece con k son los hechos que esperan (§4.2).
- **Costo para P7.** Medido: un sueño cuesta ≈ $0,0002 + $0,00004 por 1.000 caracteres de notas + $0,00014 por sesión leída (ajuste sobre 574 sueños monthly). Extrapolado a una persona monthly completa: los sueños cuestan **$0,55–0,58 con k=1, $0,18 con k=5, $0,13 con k=10, $0,105 con k=20 y $0,09 con k=50**. Los exámenes cuestan ≈ $0,12 por política, tanto como soñar cada 10–50 (§4.5).
- **El final no necesita un sueño forzado.** Ninguna persona tiene más de 6 sesiones después de su último examen, y ningún examen las lee (§3.2).
- **k=10 entra.** Parte en dos el salto de 5 a 20: cuesta 20 % menos que k=5 por sesión y pierde 4–7 puntos de examen. Es coprimo con 7, así que el examen ve sus 10 fases (§3.4).

| Rol | Ruta |
| --- | --- |
| Tag | `p5` |
| Políticas (no importan `truth`, `exam` ni `policies.session_changes`) | `policies/fixed.py` (`Never`, `Every`, `policy_named`) |
| CLI que corre y mide (sí lee la verdad, para medir) | `policies/fixed_run.py` |
| Tests (2; 43 en total) | `tests/test_fixed.py` |
| Caché de sueños y exámenes (ignorado por git) | `results/raw/p5/r0/`, `results/raw/p5/r1/` |
| Libro de gastos | `results/spend/p5a.jsonl` |
| Salidas completas (ignoradas por git; los comandos de §4 las regeneran gratis) | `results/p5a/weekly.txt`, `results/p5a/weekly-r1.txt`, `results/p5a/monthly.txt` |

Uso:

```python
from answering.client import BudgetedClient
from policies.engine import run_policy, runs_table
from policies.fixed import Every, Never

client = BudgetedClient("p5", limit_dollars=1.00)
runs = [run_policy(policy, "monthly", "academic_researcher", client, through=210) for policy in (Never(), Every(5), Every(20))]
print(runs_table(runs))
```

## 1. Problema

El sueño de P4 corrige bien lo que lee, pero solo lee cuando lo llaman. Entre dos sueños, lo que el usuario dijo espera afuera de las notas. La pregunta de P5a es cuánto cuesta esa espera según cada cuánto se sueña, y cuánto se ahorra.

Ejemplo real, weekly/software_engineer:

- **s9:** el usuario dice "I need to remember to buy groceries later today".
- **s33:** dice "I actually finished buying groceries, so you can remove that from my to-do list".

Así contesta cada política (`--watch "Buy groceries"`, §4.1):

| Examen | Probe | never | every-1 | every-5 | every-10 | every-20 | every-50 |
| --: | --- | --- | --- | --- | --- | --- | --- |
| 14 | `new` (vale) | no, `stale` (sin sueño) | yes, `correct` (sueño s14) | yes, `correct` (s10) | yes, `correct` (s10) | no, `stale` (sin sueño) | no, `stale` (sin sueño) |
| 35 | `recent_change` (ya no vale) | no, `correct` (sin sueño) | no, `correct` (s35) | no, `correct` (s35) | yes, `stale` (s30) | yes, `stale` (s20) | no, `correct` (sin sueño) |

- **every-10 y every-20 fallan en la s35** porque soñaron cuando el pendiente valía y todavía no leyeron que se borró.
- **never y every-50 aciertan en la s35 sin haber sabido nunca nada:** con las notas vacías, "no está en la lista" es la respuesta correcta. Esto explica por qué `recent_change` favorece a las políticas que sueñan menos (§4.2).

## 2. Opciones investigadas

| Fuente | Qué dice sobre la cadencia | Qué se tomó |
| --- | --- | --- |
| The components of agent memory (Lance Martin), https://www.anthropic.com/engineering/components-of-agent-memory, § "Thinking backward, looking forward" | "It may be important instead to focus dreaming on information that's likely to change or to carefully tune the cadence of dreaming (e.g., based on how often memories are accessed)." No da una cadencia. | La pregunta del proyecto. La cadencia fija es la línea de base contra la que P5b compara el sueño disparado. |
| Dreams de Managed Agents, https://platform.claude.com/docs/en/managed-agents/dreams, § "How it works" y § "Billing" | Un sueño lee "1 to 100 sessions"; "Cost scales roughly linearly with the number and length of input sessions". No hay un calendario. | k=50 queda dentro del rango de un sueño real, y el costo lineal en las sesiones se confirmó (§4.5). |
| Letta, sleep-time agents. Código en https://github.com/letta-ai/letta/blob/67013ef1/letta/groups/sleeptime_multi_agent_v2.py (líneas 110–115). Blog en https://www.letta.com/blog/sleep-time-compute/, § "Configuring sleep-time agents". Docs en https://docs.letta.com/agent-sdk/memory/index.md, § "Dreaming". | El código dispara el agente de fondo cuando `turns_counter % sleeptime_agent_frequency == 0`, o en cada turno si la frecuencia es `None`. Blog: "The higher the frequency setting, the more tokens your agent will use: but the more time the agent will have to revise its learned context." Las docs ofrecen `trigger: "step-count"` con `stepCount` (el ejemplo usa 25), `"compaction-event"` u `"off"`. | Una cadencia fija de k pasos es lo que se despliega hoy. `Every(k)` es exactamente ese contador. |
| Auto-Dreamer, https://arxiv.org/html/2605.20616, § 5.4 "Ablating consolidation cadence" y App. B.2 | Barre k ∈ {1, 5, 20}, con k = 8, 10 y 5 como cadencias principales. k=1 rinde menos ("insufficient cross-session evidence for useful abstraction") y k=20 también ("a larger and noisier working region"). | Hay que medir un k intermedio entre 5 y 20: se agregó k=10. El efecto de k=1 no se repite acá porque el sueño guarda hechos, no abstracciones (§4.2). |
| P2a, `docs/p2-examen.md` § 3.1; P4, `docs/p4-sueno.md` § 4.4 | El examen cada 7 sesiones recorre todas las fases de 5, 20 y 50. Un sueño que lee k sesiones desde notas perfectas pierde 0,2 / 0,2 / 0,9 / 2,2 % de los hechos (weekly). | Comparación por fase (§3.3). La pérdida medida en una cadena (§4.2) se compara contra la de P4. |

## 3. Análisis y elección

### 3.1 Cómo encadenar

| Opción | Qué hace | Elección |
| --- | --- | --- |
| **`len(pending) >= k`** | Sueña cuando se juntan k sesiones sin soñar. Usa solo lo que ve el agente. | **Elegida** |
| `pending[-1].session_id % k == 0` | Igual en estos datos, porque los ids van de 1 a n sin huecos (verificado en weekly/software_engineer y en las 3 personas monthly que se usan). Si faltara una sesión, correría la fase. | Descartada: depende de la numeración. |
| Cada N días (`Session.date`) | Una sesión por día no está garantizada: el número de sesiones leídas cambiaría de sueño en sueño. | Descartada: no es la cadencia que se pidió y no se compara con P4 §4.4. |

El motor ya hace que cada sueño lea exactamente las sesiones desde el anterior. La columna "sessions read per dream" da 1,0 / 5,0 / 10,0 / 20,0 / 50,0 en todas las corridas (§4.5), y `tests/test_fixed.py` lo verifica sobre las sesiones reales sin llamar a la API.

### 3.2 El final

El motor no fuerza un sueño al final. Revisé si eso cambia algún examen:

- **Después del último examen.** De 0 a 6 sesiones por persona, en las 20 personas weekly y monthly (tabla "The end", §4.3). Ningún examen las lee, así que un sueño final solo costaría.
- **Antes del último examen.** Lo que una política deja sin soñar ahí es el retraso de esa fase, igual que en cualquier otro examen. En s1–210 el examen de la s210 encuentra 0 / 0 / 0 / 10 / 10 sesiones sin soñar con k = 1 / 5 / 10 / 20 / 50, y pesa 1/30 como los demás.
- **Decisión: nada más.** Hay dos alternativas, y las dos son peores:
  - **Un sueño final:** no lo lee ningún examen y le suma un sueño a cada política.
  - **Soñar antes de cada examen:** sería trampa, porque la política sabría el calendario del examen y el retraso desaparecería.
- **Consejo para P7:** pasar `through` = la sesión del último examen. Con el valor por omisión, every-1 paga sueños que nada mide: 2 en weekly/software_engineer y hasta 6 por persona.

### 3.3 Comparar justo

- **Mismo examen y misma semilla.** `build_exam` depende solo de `(period, persona)` y de `EXAM_SEED`, así que todas las políticas reciben las mismas preguntas con los mismos ids.
- **Misma fase.** gcd(7, k) = 1 para k = 5, 10, 20 y 50. Sobre las personas monthly completas, el retraso medio en un examen es 2,01 / 4,53 / 9,40 / 24,73 sesiones, y el ideal uniforme es 2,0 / 4,5 / 9,5 / 24,5. Los 4 k cubren todas sus fases ("Exam phase", §4.6). En s1–210 la media es 2,0 / 4,5 / 9,2 / 25,2.
- **El caché empareja.** Las políticas que llegan a un examen con las mismas notas reciben las mismas respuestas: never y every-50 en 7 exámenes de 7 (s7–s49, notas vacías), y 1 o 2 en los demás pares, en las 3 personas ("Exams shared through the cache", §4.3). El libro confirma que se pagaron una sola vez: la suma de los costos por corrida en weekly r0 da $0,2751 y lo pagado fue $0,2724. La diferencia, $0,0027, son esos exámenes compartidos, que cada corrida reporta como propios (contrato de P5).
- **Lo que no se empareja.** Dos políticas casi nunca piden el mismo sueño, así que cada una tiene su propio muestreo de sueños. Por eso hace falta r1 (§4.4).

### 3.4 ¿Hace falta otro k? Sí: 10

- **El hueco.** Entre 5 y 20, el retraso medio en un examen pasa de 2 a 9,5 sesiones y el costo por sesión cae 28–39 %. P4 midió que ahí la pérdida por sueño empieza a crecer: de 0,2 % a 0,9 %.
- **Las fuentes.** Auto-Dreamer usa k=8 y k=10 como cadencias principales.
- **La fase.** gcd(7, 10) = 1, así que el examen ve sus 10 fases.
- **Medido.** every-10 queda entre los dos, con 4–7 puntos menos que every-5 en las 3 personas. Cuesta $0,00017–0,00020 por sesión, contra $0,00021–0,00025 de every-5 y $0,00015 de every-20.
- **Descarté k=7.** Coincide con el paso del examen: cada examen caería justo después de un sueño y se vería igual que every-1.

## 4. Prueba

Todo corrió con `claude-haiku-5-5`, thinking adaptativo, effort `medium` y presupuesto `p5a`. Los comandos de abajo leen el caché y no gastan.

```
$ uv run pytest -q
...........................................                              [100%]
43 passed
```

Estimación antes de gastar (el modelo de P4a con notas perfectas; pago real entre paréntesis):

```
$ uv run python -m policies.fixed_run weekly software_engineer --dry-run
| never | 0 | 0.0000 | 23 | 0.0113 | 0.0113 |          (pagado: $0,0079)
| every-1 | 163 | 0.1193 | 23 | 0.0137 | 0.1330 |      (pagado: $0,0940, con --through 161)
...
$ uv run python -m policies.fixed_run monthly academic_researcher startup_founder --through 210 --dry-run
| every-1 | 210 | 0.1831 | 30 | 0.0207 | 0.2038 |      (academic_researcher, pagado: $0,1506)
```

En total, la estimación dio 1,04–1,09 veces lo pagado: weekly r0 $0,30 estimado contra $0,2724 pagado, y monthly $0,87 contra $0,8317. Por corrida, sobreestimó hasta 1,4 veces (every-1 weekly), porque el modelo de P4a cobra de más los sueños cortos (§4.5).

### 4.1 Corridas

```
$ uv run python -m policies.fixed_run weekly software_engineer --through 161 --project --watch "Buy groceries"
$ uv run python -m policies.fixed_run weekly software_engineer --through 161 --repetition 1 --policies never every-1 every-5 every-10 every-20
$ uv run python -m policies.fixed_run monthly academic_researcher startup_founder --through 210 --project
```

Las políticas son las de omisión del CLI (`never every-1 every-5 every-10 every-20 every-50`). `runs_table`, r0:

| policy | period/persona | dreams | dream $ | exam $ | official | lenient | official without marked | lenient without marked | correct | stale | missing | invented |
| --- | --- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| never | weekly/software_engineer | 0 | 0.0000 | 0.0079 | 115/426 (27.0%) | 115/426 (27.0%) | 115/416 (27.6%) | 115/416 (27.6%) | 115 | 79 | 222 | 10 |
| every-1 | weekly/software_engineer | 161 | 0.0771 | 0.0170 | 400/426 (93.9%) | 400/426 (93.9%) | 398/416 (95.7%) | 398/416 (95.7%) | 400 | 9 | 5 | 12 |
| every-5 | weekly/software_engineer | 32 | 0.0331 | 0.0180 | 354/426 (83.1%) | 354/426 (83.1%) | 353/416 (84.9%) | 353/416 (84.9%) | 354 | 44 | 16 | 12 |
| every-10 | weekly/software_engineer | 16 | 0.0271 | 0.0183 | 336/426 (78.9%) | 336/426 (78.9%) | 334/416 (80.3%) | 334/416 (80.3%) | 336 | 45 | 30 | 15 |
| every-20 | weekly/software_engineer | 8 | 0.0238 | 0.0171 | 305/426 (71.6%) | 305/426 (71.6%) | 302/416 (72.6%) | 302/416 (72.6%) | 305 | 62 | 44 | 15 |
| every-50 | weekly/software_engineer | 3 | 0.0199 | 0.0158 | 236/426 (55.4%) | 236/426 (55.4%) | 236/416 (56.7%) | 236/416 (56.7%) | 236 | 69 | 103 | 18 |
| never | monthly/academic_researcher | 0 | 0.0000 | 0.0113 | 142/593 (23.9%) | 142/593 (23.9%) | 142/586 (24.2%) | 142/586 (24.2%) | 142 | 123 | 303 | 25 |
| every-1 | monthly/academic_researcher | 210 | 0.1242 | 0.0264 | 576/593 (97.1%) | 576/593 (97.1%) | 576/586 (98.3%) | 576/586 (98.3%) | 576 | 16 | 1 | 0 |
| every-5 | monthly/academic_researcher | 42 | 0.0499 | 0.0259 | 529/593 (89.2%) | 529/593 (89.2%) | 529/586 (90.3%) | 529/586 (90.3%) | 529 | 46 | 16 | 2 |
| every-10 | monthly/academic_researcher | 21 | 0.0399 | 0.0266 | 488/593 (82.3%) | 488/593 (82.3%) | 488/586 (83.3%) | 488/586 (83.3%) | 488 | 68 | 32 | 5 |
| every-20 | monthly/academic_researcher | 10 | 0.0319 | 0.0257 | 451/593 (76.1%) | 451/593 (76.1%) | 451/586 (77.0%) | 451/586 (77.0%) | 451 | 94 | 43 | 5 |
| every-50 | monthly/academic_researcher | 4 | 0.0281 | 0.0248 | 351/593 (59.2%) | 351/593 (59.2%) | 350/586 (59.7%) | 350/586 (59.7%) | 351 | 123 | 102 | 17 |
| never | monthly/startup_founder | 0 | 0.0000 | 0.0101 | 144/581 (24.8%) | 144/581 (24.8%) | 144/541 (26.6%) | 144/541 (26.6%) | 144 | 131 | 294 | 12 |
| every-1 | monthly/startup_founder | 210 | 0.1282 | 0.0284 | 521/581 (89.7%) | 522/581 (89.8%) | 517/541 (95.6%) | 518/541 (95.7%) | 521 | 17 | 18 | 25 |
| every-5 | monthly/startup_founder | 42 | 0.0516 | 0.0270 | 492/581 (84.7%) | 492/581 (84.7%) | 490/541 (90.6%) | 490/541 (90.6%) | 492 | 29 | 34 | 26 |
| every-10 | monthly/startup_founder | 21 | 0.0412 | 0.0269 | 455/581 (78.3%) | 455/581 (78.3%) | 440/541 (81.3%) | 440/541 (81.3%) | 455 | 86 | 32 | 8 |
| every-20 | monthly/startup_founder | 10 | 0.0316 | 0.0249 | 411/581 (70.7%) | 411/581 (70.7%) | 400/541 (73.9%) | 400/541 (73.9%) | 411 | 107 | 55 | 8 |
| every-50 | monthly/startup_founder | 4 | 0.0290 | 0.0238 | 312/581 (53.7%) | 312/581 (53.7%) | 309/541 (57.1%) | 309/541 (57.1%) | 312 | 140 | 114 | 15 |

Todas las corridas tienen `decision $` 0 y `unparseable` 0. Sin esas columnas, la tabla es la que imprime el CLI.

- **every-1 replica a P4.** En academic_researcher da 97,1 % (P4 con cadencia 7: 97,3 %). En startup_founder, 89,7 %, y sube a 95,6 % sin las preguntas marcadas.
- **Las marcadas pesan casi solo en startup_founder** (40 de 581), por los gastos "last night" de P4 §3.3.
- **Dos dominios que no se recuperan con ningún k.** Expense de startup_founder (63,5 % con every-1, donde están los gastos "last night" de P4 §3.3) y content de academic_researcher (87,1 %, ítems con el texto de Memora). Dependen de Memora, no de la cadencia.

### 4.2 Retraso contra pérdida

Tabla "Waiting or lost". Cada pregunta sobre un hecho cae en una de dos clases:

- **Leída:** algún sueño ya leyó el último cambio del hecho (`last_change` ≤ el último sueño antes del examen).
- **Esperando:** el hecho cambió después del último sueño.

`never_existed` y `aggregate` quedan aparte, porque no preguntan por un solo hecho. La misma división se aplica a la comparación línea por línea de P4b (`compare_notes`) sobre las notas de cada examen.

| política | weekly: examen, leídas / esperando | weekly: hechos leídos bien | AR: examen, leídas / esperando | AR: hechos leídos bien | SF: examen, leídas / esperando | SF: hechos leídos bien |
| --- | --: | --: | --: | --: | --: | --: |
| never | — / 26 de 291 (8,9 %) | — | — / 27 de 421 (6,4 %) | — | — / 25 de 405 (6,2 %) | — |
| every-1 | 95,2 % de 291 / — | 98,5 % | 96,0 % de 421 / — | 91,5 % | 89,9 % de 405 / — | 96,0 % |
| every-5 | 89,8 % de 264 / 0 de 27 | 97,9 % | 94,1 % de 388 / 2 de 33 | 91,1 % | 90,1 % de 375 / 1 de 30 | 95,8 % |
| every-10 | 94,5 % de 238 / 0 de 53 | 98,5 % | 96,0 % de 347 / 3 de 74 | 91,2 % | 89,2 % de 333 / 1 de 72 | 95,7 % |
| every-20 | 95,1 % de 206 / 5 de 85 | 98,3 % | 94,7 % de 319 / 7 de 102 | 91,3 % | 90,1 % de 294 / 2 de 111 | 96,7 % |
| every-50 | 91,0 % de 134 / 17 de 157 | 97,7 % | 91,0 % de 233 / 14 de 188 | 92,4 % | 84,8 % de 204 / 14 de 201 | 95,7 % |

- **Una pregunta ya leída sale bien igual con cualquier k.** Va de 89,8 a 95,2 % en weekly, de 91,0 a 96,0 % en academic_researcher y de 84,8 a 90,1 % en startup_founder. En la comparación línea por línea, los hechos leídos están bien en la misma proporción con k=1 que con k=50: 98,5 contra 97,7 %, 91,5 contra 92,4 % y 96,0 contra 95,7 %. Es lo que P4 vio con ventanas: soñar seguido no degrada, y leer 50 sesiones pierde poco. Las diferencias están dentro del ruido: every-5 weekly da 89,8 % en r0 y 94,3 % en r1.
- **Lo que cambia con k es cuántas preguntas esperan.** Weekly: 0 / 27 / 53 / 85 / 157 de 291. Academic_researcher: 0 / 33 / 74 / 102 / 188 de 421. Startup_founder: 0 / 30 / 72 / 111 / 201 de 405. Una pregunta que espera sale bien el 0–11 % de las veces.
- **Esos aciertos son bajas.** El ítem borrado nunca se anotó, así que "no" o "unknown" resulta correcto. Por eso `recent_change` no es monótono: never acierta el 100 % en weekly y el 71–74 % en monthly, más que every-10, every-20 y every-50 (tabla "by probe"). En cambio, `new` ordena las cadencias de punta a punta: 95 / 60 / 28 / 17 / 3 % en weekly r0 con k = 1 / 5 / 10 / 20 / 50. `stable < 50` separa sobre todo a every-50: 93 / 86 / 93 / 83 / 42 %.
- **El control `stable >= 50` queda en 86–98 % con todo k.** Todas las cadencias ya soñaron después de ese cambio. every-50 da el valor más bajo en las 3 personas (89,2 / 90,5 / 86,2 %, contra 94,6–97,6 % de every-1). Puede ser la pérdida de leer 50 sesiones que midió P4, pero con 83–148 preguntas por celda está dentro del ruido.

### 4.3 El final y el caché compartido

Tabla "The end". Sesiones después del último examen, por persona:

- **Weekly:** de 0 a 5.
- **Monthly:** de 2 a 6.

Tabla "Exams shared through the cache", igual en las 3 personas:

| Par | Exámenes con las mismas notas | Con las mismas respuestas |
| --- | --: | --: |
| never y every-50 | 7 | 7 |
| never y every-20 | 2 | 2 |
| every-20 y every-50 | 2 | 2 |
| never y every-10, every-10 y every-20, every-10 y every-50 | 1 | 1 |

### 4.4 Ruido: segunda repetición de weekly

| política | r0 | r1 | diferencia | sueños $ r0 / r1 |
| --- | --: | --: | --: | --: |
| never | 27,0 % | 27,2 % | +0,2 | — |
| every-1 | 93,9 % | 91,8 % | −2,1 | 0,0771 / 0,0776 |
| every-5 | 83,1 % | 85,9 % | +2,8 | 0,0331 / 0,0346 |
| every-10 | 78,9 % | 78,6 % | −0,3 | 0,0271 / 0,0269 |
| every-20 | 71,6 % | 68,8 % | −2,8 | 0,0238 / 0,0237 |
| every-50 | 55,4 % | no corrió | | 0,0199 / — |

- **El ruido de una política es de hasta 2,8 puntos.** P4 midió 1,9. Las distancias entre k vecinos van de 4,2 a 16,2 puntos en weekly r0, así que el orden se sostiene.
- **La distancia entre every-5 y every-10 en weekly cambia de 4,2 a 7,3 puntos** según la repetición: para comparar dos k cercanos hacen falta más repeticiones.
- **El costo de los sueños varía menos del 5 %.**
- **every-50 r1 no corrió.** El cliente frena cuando el peor caso de la llamada siguiente pasa el tope: quedaban $0,1307 y el sueño de 50 sesiones podía costar, en el peor caso, $0,1366, aunque en la práctica cuesta ≈ $0,007. No subí el tope.

### 4.5 Costo de un sueño según k y según el tamaño de las notas

Tabla "What a dream costs", monthly (weekly en `results/p5a/weekly.txt`, con el mismo patrón):

| política | persona | $ por sueño | modelo de P4a | tokens de entrada | tokens de salida | $ de sueños por sesión |
| --- | --- | --: | --: | --: | --: | --: |
| every-1 | academic_researcher / startup_founder | 0,00059 / 0,00061 | 0,00085 / 0,00086 | 4.560 / 4.599 | 271 / 301 | 0,00059 / 0,00061 |
| every-5 | | 0,00119 / 0,00123 | 0,00124 / 0,00124 | 6.876 / 6.917 | 1.000 / 1.072 | 0,00024 / 0,00025 |
| every-10 | | 0,00190 / 0,00196 | 0,00173 / 0,00173 | 9.879 / 9.906 | 1.822 / 1.947 | 0,00019 / 0,00020 |
| every-20 | | 0,00319 / 0,00316 | 0,00271 / 0,00269 | 15.779 / 15.809 | 3.215 / 3.167 | 0,00015 / 0,00015 |
| every-50 | | 0,00702 / 0,00725 | 0,00568 / 0,00565 | 33.889 / 34.018 | 7.261 / 7.702 | 0,00013 / 0,00014 |

- **Ajuste por mínimos cuadrados sobre los 574 sueños monthly:** $ = 0,000197 + 0,000040 por 1.000 caracteres de notas + 0,000138 por sesión leída. El de P4a era 0,00047 + 0,00004 + 0,0001: sobreestimaba los sueños cortos y subestimaba los largos. En weekly (220 sueños) el ajuste da 0,000180 + 0,000044 + 0,000129.
- **La salida crece con k:** 271 tokens con k=1 y 7.261 con k=50. Con k=50 es la mitad del costo del sueño.
- **Un examen cuesta $ = 0,00042 + 0,000067 por 1.000 caracteres de notas** (ajuste sobre 360 exámenes monthly).

### 4.6 Proyección a una persona monthly completa (para P7)

**Medido:** los dos ajustes de §4.5 y la razón entre las notas y las notas perfectas en el mismo sueño (0,96, media de 280 exámenes monthly). **Extrapolado:** el tamaño de las notas en cada sueño se toma de las notas perfectas de la verdad (`render_notes(state_after(N))`) × 0,96, para todas las sesiones de la persona.

Validación: sobre s1–210, el modelo da lo medido con hasta 8 % de error. Por ejemplo, every-1 academic_researcher: $0,1312 extrapolado contra $0,1242 medido. every-5 startup_founder: $0,0478 contra $0,0516.

| política | academic_researcher (619 sesiones): sueños | $ sueños | $ por sesión | startup_founder (606): sueños | $ sueños | $ por sesión |
| --- | --: | --: | --: | --: | --: | --: |
| every-1 | 619 | 0,576 | 0,00093 | 606 | 0,546 | 0,00090 |
| every-5 | 123 | 0,182 | 0,00029 | 121 | 0,175 | 0,00029 |
| every-10 | 61 | 0,132 | 0,00021 | 60 | 0,128 | 0,00021 |
| every-20 | 30 | 0,106 | 0,00017 | 30 | 0,105 | 0,00017 |
| every-50 | 12 | 0,092 | 0,00015 | 12 | 0,091 | 0,00015 |

- **Soñar en cada sesión se encarece** con la persona completa: $0,00093 por sesión contra $0,00059 en s1–210, porque las notas crecen y cada sueño las paga enteras.
- **De k=1 a k=5 se ahorra 3,2 veces; de k=5 a k=50, 2 veces.**
- **Exámenes, extrapolados:** con `exam_every=7`, una persona monthly completa son 86–88 exámenes, ≈ $0,113–0,125 por política que sueña y $0,036 para never.
- **Una persona monthly completa con las 6 políticas cuesta ≈ $1,1 de sueños + $0,66 de exámenes** (academic_researcher).

Tabla "A cheaper exam" (los mismos exámenes, solo los de sesiones múltiplo de 21; gratis):

| política | weekly: paso 7 / paso 21 | espera media | AR: paso 7 / paso 21 | espera media |
| --- | --: | --: | --: | --: |
| every-10 | 78,9 / 77,0 % | 4,4 / 4,0 | 82,3 / 85,1 % | 4,5 / 4,5 |
| every-20 | 71,6 / **77,8 %** | 9,2 / **4,0** | 76,1 / 80,6 % | 9,2 / **5,5** |
| every-50 | 55,4 / 50,4 % | 25,3 / 26,9 | 59,2 / 58,2 % | 25,2 / 25,5 |

- **El paso 21 parece barato pero está sesgado en tramos cortos.** Es coprimo con 5, 10, 20 y 50, y costaría la tercera parte. En s1–161 y s1–210, sin embargo, every-20 cae siempre en la primera mitad de su ciclo (espera 4,0–5,5 en lugar de 9,5) y en weekly pasa por encima de every-10.
- **Sobre las personas monthly completas el sesgo baja pero sigue** ("Exam phase"): con el paso 21, every-20 espera 8,10 de media, y con el paso 7, 9,40.
- **El paso 7 sigue siendo el que compara justo.**

### 4.7 Costo real

| Corrida | Pagado |
| --- | --: |
| weekly/software_engineer s1–161, r0, 6 políticas | $0,2724 |
| monthly academic_researcher + startup_founder s1–210, r0, 6 políticas | $0,8317 |
| weekly/software_engineer s1–161, r1, 5 políticas | $0,2652 |
| **Total (`results/spend/p5a.jsonl`)** | **$1,3693** de $1,50 |

Por política, el costo está en `runs_table`.

## 5. Opciones descartadas y por qué

| Opción | Por qué no |
| --- | --- |
| `session_id % k == 0` | En estos datos es igual, pero depende de la numeración; `len(pending)` solo usa lo que ve el agente (§3.1). |
| Cadencia por días | No es la cadencia pedida, y la cantidad de sesiones leídas por sueño variaría (§3.1). |
| Sueño final forzado | Ningún examen lo lee: solo costaría (§3.2). |
| Soñar antes de cada examen | Trampa: la política vería el calendario del examen (§3.2). |
| k=7 | Coincide con el paso del examen: el retraso medido sería siempre 0 (§3.4). |
| `exam_every=21` para abaratar P7 | Sesgado en tramos cortos: every-20 gana 4,5–8,0 puntos (weekly, academic_researcher, startup_founder) y en weekly supera a every-10 (§4.6). |
| Subir el tope para correr every-50 r1 | El tope es de $1,50. Lo que faltaba era la holgura del peor caso, no el gasto real (§4.4). |
| Una segunda repetición monthly | No alcanzaba el presupuesto. Se eligió weekly porque cuesta la tercera parte. |

## 6. Limitaciones y preguntas abiertas

- **Muestra.**
  - Weekly: una persona, dos repeticiones (sin every-50 en r1).
  - Monthly: dos personas, una repetición, solo s1–210 (un tercio del período).
  - Esto valida el motor y las políticas; no alcanza para concluir sobre distancias de pocos puntos, como every-5 contra every-10.
- **La proyección a personas completas es extrapolada.** Supone que las notas siguen creciendo como las perfectas (× 0,96) y que el costo de un sueño sigue lineal más allá de s210. Los sueños medidos leyeron notas de 4.500–7.200 caracteres de media (§4.5): no hay sueños medidos con las notas de una persona completa.
- **`recent_change` engaña al comparar cadencias.** Casi todos son bajas, y una política que nunca anotó el hecho acierta. Para comparar políticas, P7 debería mirar `new`, `stable < 50` y la división leídas/esperando de §4.2, además de las 4 cuentas.
- **Los exámenes cuestan tanto como los sueños.** Con `exam_every=7`, una persona monthly completa son ≈ $0,12 por política. Si P7 quiere personas completas, el presupuesto alcanza para pocas. Mejor más personas en s1–210 que pocas completas, porque el retraso no depende del tramo, solo de k.
- **El costo de la espera es casi independiente del dominio,** salvo lo que ya es de Memora: content de academic_researcher y gastos "last night" de startup_founder.
- **Para P5b.** La línea de base de un sueño disparado es la curva de arriba. Para ganarle a every-k tiene que tener menos preguntas esperando con un costo por sesión parecido, o el mismo retraso por menos.
