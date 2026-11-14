# P7b · Análisis de la grilla final (re-corrida)

**Resultado.** La grilla final está completa: 10 personas monthly × 7 políticas × 2 repeticiones sobre s1–210 (140 corridas) y las 4 corridas enteras (`every-1` y `every-5` en academic_researcher y startup_founder), según los CSV de P7a en su commit 2853c99. IC al 95 % por persona: se promedian las 2 repeticiones dentro de cada persona y se remuestrean las 10 personas (10.000 veces, semilla 20261113).

| política | sueños | mantener la memoria, $ por persona | oficial | sin marcadas |
| --- | --: | --: | --: | --: |
| `every-1` | 210 | 0,1223 [0,1192, 0,1252] | 94,1 [92,4, 95,7] | 96,3 [95,1, 97,3] |
| `triggered-phrases-any` | 157,7 | 0,0993 [0,0974, 0,1013] | 94,2 [92,5, 95,8] | 96,4 [95,1, 97,6] |
| `every-5` | 42 | 0,0492 [0,0483, 0,0500] | 87,2 [85,7, 88,5] | 89,3 [87,9, 90,5] |

- **Soñar cuando unas frases ven un hecho rinde igual que soñar después de cada sesión, por el 81 % del costo.** `every-1 − frases` da −0,1 [−0,6, +0,5] puntos oficial y −0,1 [−0,6, +0,5] sin marcadas; 4 personas a favor de `every-1` y 6 de las frases. **Con las 2 repeticiones el IC sigue conteniendo el 0, ahora cerca del centro.** La leve ventaja de las frases que daba la repetición 0 sola (−0,6 [−1,2, −0,0]) no se sostuvo: de la repetición 0 a la 1, esa diferencia sube +1,1 puntos en promedio (§3.7). `every-1` cuesta 1,23 [1,21, 1,26] veces más.
- **Soñar cada 5 sesiones pierde 7,0 [6,0, 8,1] puntos contra `every-1`** (7,1 [6,0, 8,2] sin marcadas), en las 10 de 10 personas, y 7,0 [5,8, 8,3] contra las frases. Cuesta 2,49 [2,43, 2,55] veces menos que `every-1`.
- **La pérdida es de retraso, no de memoria:** `every-1 − every-5` da +29,0 [26,5, 31,7] en `new`, +25,6 [20,7, 30,0] en `recent_change` y +14,6 [9,8, 19,8] en `aggregate`, pero +0,1 [−0,9, +1,3] en `stable` (sin cambios).
- **El orden de las fijas,** every-1 > 5 > 10 > 20 > 50 > never, se da en las 10 de 10 personas.
- **Ruido entre repeticiones:** la precisión oficial de una política que sueña cambia 0,9–1,6 puntos en promedio (en valor absoluto) al repetir la misma persona, y como mucho 5,8. Las diferencias entre personas son mayores (desvío de 2,8 en `every-1`), por eso la unidad es la persona.
- **`invented` reclasificado:** con `nothing_logged` como `stale`, `never` pasa de 2,8 % [2,5, 3,1] a 0,0 % y `every-50` de 2,8 % a 0,4 % [0,1, 0,8]. `every-1` y las frases no cambian (1,6 % y 1,7 %): lo que les queda son totales incompletos.
- **La ventaja de soñar seguido no se achica en general hacia el final del mes.** `every-1 − every-5` por tramo (s1–210 / s211–420 / s421–end), oficial: academic_researcher +5,6 / +6,3 / +2,6; startup_founder +5,5 / +9,3 / +6,2. `every-1` va arriba en los 6 tramos. La compresión que vio P6 se repite en academic_researcher y no aparece en startup_founder. Con 2 personas no hay IC (§3.6).

| Rol | Ruta |
| --- | --- |
| Tag | `p7` |
| Contrato P7a/P7b | `docs/p7-interfaz.md` |
| Análisis: tablas Markdown, IC por persona, diferencias emparejadas | `final/analysis.py` |
| Gráficos SVG escritos a mano (librería estándar) | `final/charts.py` |
| Tablas y gráficos de la muestra nueva | `docs/p7/tables.md`, `docs/p7/*.svg` |
| Tablas y gráficos de la muestra de antes del borrado (aparte, sin mezclar) | `docs/p7/before-loss/tables.md`, `docs/p7/before-loss/*.svg` |
| Copia fechada de los CSV finales de P7a (commit 2853c99 de su rama, sha256 idénticos); genera `docs/p7/` | `data/p7-runs-final-2853c99.csv`, `data/p7-probes-final-2853c99.csv` |
| Copias anteriores (solo repetición 0): con personas enteras (419c13b) y sin ellas (11d8edf) | `data/p7-*-whole-419c13b.csv`, `data/p7-*-r0-11d8edf.csv` |
| Copia anterior: 1 persona, antes del límite de la API (commit 670f08c) | `data/p7-runs-2026-11-13.csv`, `data/p7-probes-2026-11-13.csv` |
| CSV de antes del borrado (commit 8e6bcff) | `data/p7-runs-before-loss.csv`, `data/p7-probes.csv` |
| Test (sin API) | `tests/test_analysis.py` (1) |

## 1. Problema

El post de Lance Martin, "The components of agent memory" (Anthropic Engineering, https://www.anthropic.com/engineering/components-of-agent-memory, § "Thinking backward, looking forward"), deja abierta esta pregunta: "It may be important instead to focus dreaming on information that's likely to change or to carefully tune the cadence of dreaming (e.g., based on how often memories are accessed)". El proyecto la responde con un diseño en el que las sesiones no escriben notas: solo escribe el sueño, y el examen (cada 7 sesiones) se contesta leyendo solo las notas.

P7a corre la grilla final (10 personas monthly de Memora, 7 políticas, s1–210, 2 repeticiones, más personas enteras) y escribe dos CSV. P7b los convierte en lo que se puede afirmar:

1. **Cuánto rinde cada política por lo que cuesta mantener la memoria,** con intervalos que no confundan 600 preguntas de una persona con 600 observaciones independientes.
2. **Si `triggered-phrases-any` (soñar cuando unas frases ven un hecho) iguala a soñar después de cada sesión,** y cuánto le gana a `every-5`.
3. **Dónde se separan las políticas:** por tipo de pregunta y por dominio.
4. **Si la ventaja de soñar seguido se achica hacia el final del mes** (P6 §3.3), en las personas enteras.

Ejemplo real de por qué la unidad no puede ser la pregunta (P6 §3.1): en academic_researcher, dos gastos "last night" (s429 y s470) que la clave de Memora fecha un día después arruinan 25 totales semanales en cada cadena que sueña. Un solo café omitido en la s236 arruina 10 totales de `every-1`. Las preguntas de una persona vienen en racimos que fallan juntos.

## 2. Opciones consideradas

### 2.1 Unidad del intervalo

| Opción | Qué supone |
| --- | --- |
| (a) Binomial sobre las preguntas | Cada pregunta es independiente |
| (b) Bootstrap por persona, con las repeticiones promediadas dentro de cada persona (`docs/p7-interfaz.md` § "El análisis") | Las personas son independientes; dentro de una persona, nada |
| (c) Bootstrap por racimo (persona, hecho) | Los hechos de una persona son independientes |
| (d) Modelo jerárquico (persona, repetición, pregunta) | Una forma paramétrica en cada nivel |

### 2.2 Comparación entre políticas

| Opción | Qué hace |
| --- | --- |
| (a) Dos IC independientes, y ver si se solapan | Ignora que las dos políticas comparten persona, examen y caché |
| (b) Diferencia emparejada dentro de cada persona remuestreada | La diferencia entre personas (startup_founder es más difícil para todas) se cancela |

### 2.3 Gráficos

| Opción | Por qué se consideró |
| --- | --- |
| Una librería de gráficos (matplotlib) | Es cómoda, pero agrega una dependencia y la Mac está al límite de memoria |
| SVG escrito a mano con la librería estándar | Lo pide el contrato, y son 4 gráficos simples |

### 2.4 Trabajo relacionado (leído en la fuente)

| Fuente | Qué dice, con sección |
| --- | --- |
| RecMem, https://aclanthology.org/2026.findings-acl.1619.pdf | §1 y Fig. 1: los sistemas existentes hacen "eager memory consolidation" en cada interacción. §4.2: en LoCoMo con GPT-4.1-mini usa 193,2K tokens de construcción contra 1.520,8K de Mem0 y 1.459,9K de A-Mem, y los sistemas que consolidan en cada turno "anchor later mentions of an evolving topic to different summaries, fragmenting the thread" (razonamiento temporal). §4.3: sin la memoria "subconscious" (las interacciones crudas) baja de 81,10 a 51,88. App. C.1: un θ_count más bajo consolida antes, "can better preserve fine-grained details" y cuesta más tokens; subirlo de 5 a 6 baja de 81,1 a 78,9. |
| Useful Memories Become Faulty, https://arxiv.org/html/2605.12978v2 | Resumen: "As consolidation proceeds, memory utility first rises, then degrades, and can fall below the no-memory baseline". Recomienda "gate consolidation explicitly rather than firing it after every interaction". §6.4 y Tabla 5 (ARC-AGI Stream, GPT-5.4, paso 400): "in-place rewriting is the most damaging single step", prohibirla recupera +6,8 puntos, y "pruning (delete without rewrite) actually helps". App. L.2: el costo de que cada actualización dependa de las anteriores "scales with the number of updates" (400 actualizaciones con lotes de 1, contra 50 con lotes de 8). |
| Auto-Dreamer, https://arxiv.org/html/2605.20616 | §5.4: en ScienceWorld rinde menos consolidar cada k = 1 sesiones ("insufficient cross-session evidence for useful abstraction") y también cada k = 20 ("a larger and noisier working region"). ALFWorld es más robusto (≈ 5 pp de rango). App. A: "Information missed by the writer cannot generally be recovered by the consolidator unless source trajectories make it salient". |
| Sleep-time compute, https://arxiv.org/abs/2504.13171 | §5.3: amortizar el cómputo offline entre 10 consultas por contexto baja 2,5× el costo por consulta. §5.4 y §7: rinde más cuanto más predecible es la consulta a partir del contexto. |
| STALE, https://arxiv.org/abs/2605.06527 | §1: define "Implicit Conflict: a situation where a new observation invalidates an earlier memory without syntactic negation". La Tabla 1 marca LongMemEval y FactConsolidation como benchmarks de contradicciones "explicit". Según el resumen, el mejor modelo evaluado llega a 55,2 %. |
| Memora, https://arxiv.org/abs/2604.20006 | §3.2 y Tabla 2: monthly tiene 10 personas y 615 sesiones por persona en promedio; las operaciones son 63 % agregar, 16 % cambiar y 21 % borrar. §3.3: cada sesión con memoria tiene "a memory phase where the target operation is expressed". |

## 3. Análisis y elección

### 3.1 La persona es la unidad del IC (opción 2.1b)

- **Las preguntas de una persona fallan en racimo.** Un monthly es junio de 2025 con unas 20 sesiones por día. El total semanal se pregunta unas 20 veces seguidas, así que un gasto mal fechado u omitido cuenta unas 20 veces (P6 §3.1). Los 40 errores tardíos de `every-1` en academic_researcher caen sobre 17 hechos distintos (P6 §6).
- **Las personas difieren más que las repeticiones, y más que lo que dice la binomial.** Con las 2 repeticiones promediadas (`docs/p7/tables.md`, "Why the persona is the unit" y "Official accuracy per persona"), `every-1` va de 89,8 % (content_writer y startup_founder) a 97,7 % (sales_manager), con un desvío entre personas de 2,8 puntos. Repetir la misma persona la mueve 1,2 puntos en promedio (§3.7). El IC por persona mide 3,3 puntos de ancho; el binomial, que trata las 5.786 preguntas de la repetición 0 como independientes, mide 1,2. Con las frases, 3,3 contra 1,2. La binomial afirmaría una precisión casi tres veces más exacta de lo que se mueve entre usuarios.
- **(c) no alcanza:** los hechos de una persona tampoco son independientes, porque los 21 totales de una semana comparten gastos.
- **(d) no se justifica** con 10 personas y 2 repeticiones: agrega supuestos y no cambia la conclusión.
- **Cómo se calcula** (`final/analysis.py`):
  1. Para cada persona, la tasa de cada repetición, y después el promedio de las repeticiones.
  2. 10.000 remuestreos de las personas con reemplazo, con semilla 20261113.
  3. El IC percentil al 95 %.

  Solo entran las personas que tienen la repetición 0 de las 7 políticas, así todas las políticas se comparan sobre las mismas personas.
- **Mínimo de 4 personas para mostrar un IC.** Con n personas, un remuestreo repite n veces una persona dada con probabilidad n⁻ⁿ: 25 % con 2 y 3,7 % con 3. Las dos pasan el 2,5 %, así que con 3 personas o menos el "IC" percentil es solo la persona más baja y la más alta. Con 4 la probabilidad baja a 0,4 %. Por debajo de 4 personas, las tablas muestran la media y `[—]`.

### 3.2 Diferencias emparejadas (opción 2.2b)

Para A − B, la diferencia se calcula dentro de cada persona, y lo que se remuestrea es esa lista de diferencias. Se comparan tres pares en las 4 cuentas (oficial, indulgente, y las dos sin las preguntas marcadas):

- `every-1 − triggered-phrases-any`
- `every-1 − every-5`
- `triggered-phrases-any − every-5`

Para cada par se reporta también el costo de mantener la memoria (diferencia y cociente) y cuántas personas tienen A por encima, igual y por debajo de B.

### 3.3 Qué va en cada eje del gráfico principal

- **x: `maintenance_cost`**, la suma de los sueños y el detector (0 para las frases), en $ por persona sobre s1–210. Los exámenes quedan afuera: son instrumentación, no parte de la política, y cuestan casi lo mismo en todas las que sueñan ($0,0245–0,0267 en academic_researcher; $0,0112 con `never`, que contesta con notas vacías).
- **y: precisión,** en dos paneles: oficial y sin marcadas.
- **Las fijas van unidas en orden de k,** y `triggered-phrases-any` va aparte, como rombo. Las barras de IC aparecen desde 4 personas.

### 3.4 `invented` de las dos formas (decisión 2 de P6)

- **Regla actual:** un "0" o un "no" dado cuando el hecho todavía no valía cuenta como `invented`.
- **Regla nueva (`nothing_logged`):** esas respuestas pasan a `stale`. La precisión no cambia.

`partial_total` (un total al que le falta un gasto) va solo como columna de diagnóstico (decisión 3).

### 3.5 Lo que dicen los datos: 10 personas, 2 repeticiones, s1–210

`docs/p7/tables.md`, generado desde `data/p7-*-final-2853c99.csv`. Media de las 10 personas, cada una con sus 2 repeticiones promediadas [IC 95 % por persona]:

| política | sueños | mantener $ | oficial | indulgente | sin marcadas | indulgente sin marcadas |
| --- | --: | --: | --: | --: | --: | --: |
| never | 0 | 0,0000 | 25,7 [24,9, 26,5] | 25,7 [24,9, 26,5] | 26,4 [25,6, 27,1] | 26,4 [25,6, 27,1] |
| every-50 | 4 | 0,0278 [0,0272, 0,0283] | 57,7 [56,5, 58,6] | 57,7 [56,5, 58,6] | 58,9 [58,1, 59,9] | 58,9 [58,1, 59,9] |
| every-20 | 10 | 0,0317 [0,0312, 0,0322] | 72,9 [71,6, 74,0] | 72,9 [71,6, 74,0] | 74,3 [73,4, 75,2] | 74,3 [73,4, 75,2] |
| every-10 | 21 | 0,0394 [0,0385, 0,0401] | 80,1 [79,1, 81,0] | 80,1 [79,1, 81,0] | 81,8 [81,3, 82,4] | 81,8 [81,3, 82,4] |
| every-5 | 42 | 0,0492 [0,0483, 0,0500] | 87,2 [85,7, 88,5] | 87,3 [85,8, 88,6] | 89,3 [87,9, 90,5] | 89,4 [88,1, 90,5] |
| triggered-phrases-any | 157,7 | 0,0993 [0,0974, 0,1013] | 94,2 [92,5, 95,8] | 94,3 [92,6, 95,9] | 96,4 [95,1, 97,6] | 96,5 [95,2, 97,7] |
| every-1 | 210 | 0,1223 [0,1192, 0,1252] | 94,1 [92,4, 95,7] | 94,2 [92,5, 95,8] | 96,3 [95,1, 97,3] | 96,4 [95,2, 97,3] |

Diferencias emparejadas en las 4 cuentas (puntos; personas con A arriba / igual / abajo; cociente del costo de mantener):

| A − B | oficial | indulgente | sin marcadas | indulgente sin marcadas | A > / = / < B (oficial) | mantener $: cociente |
| --- | --: | --: | --: | --: | --: | --: |
| `every-1 − triggered-phrases-any` | −0,1 [−0,6, +0,5] | −0,1 [−0,6, +0,5] | −0,1 [−0,6, +0,5] | −0,1 [−0,7, +0,4] | 4 / 0 / 6 | 1,23 [1,21, 1,26] |
| `every-1 − every-5` | +7,0 [+6,0, +8,1] | +6,9 [+5,9, +8,1] | +7,1 [+6,0, +8,2] | +7,0 [+6,0, +8,2] | 10 / 0 / 0 | 2,49 [2,43, 2,55] |
| `triggered-phrases-any − every-5` | +7,0 [+5,8, +8,3] | +7,0 [+5,8, +8,3] | +7,2 [+6,0, +8,4] | +7,2 [+6,0, +8,4] | 10 / 0 / 0 | 2,02 [2,00, 2,04] |

- **`every-1` contra frases: no se distinguen.** El IC contiene el 0 en las 4 cuentas, y las diferencias de cada persona van de −1,5 a +1,8 puntos ("Official accuracy per persona"). Con la repetición 0 sola el IC llegaba justo al 0 (−0,6 [−1,2, −0,0]); con las 2 repeticiones la media va a −0,1 y el IC queda centrado. Lo que se puede afirmar: las frases no son peores que soñar en cada sesión en más de 0,6 puntos, ni mejores en más de 0,5, y cuestan el 81 %.
- **Las frases ahorran sueños, no precisión:** hacen 157,7 sueños contra 210 en s1–210, porque no sueñan cuando la sesión no trae hechos (P5b §3.2).
- **Por tipo de pregunta (oficial):**
  - **`new`:** `every-1` 93,8 [92,1, 95,7], frases 93,7 [91,9, 95,7], `every-5` 64,8, `every-10` 34,4, `every-20` 18,9, `every-50` 5,2, `never` 0.
  - **`recent_change`:** `every-1` 95,6, frases 94,4, `every-5` 69,9. `never` saca 80,8 [77,2, 84,2]: son aciertos vacíos, porque con notas vacías "no está" es correcto para lo que se borró (P5 §1).
  - **`stable` (sin cambios):** 86,6–93,8 % en todas las que sueñan, salvo `every-50` (65,1). `every-1 − every-5` da +0,1 [−0,9, +1,3]: soñar cada 5 no olvida, llega tarde.
  - **`never_existed` (señuelo):** 99,8–100 % en las 7.
  - **`aggregate` (total):** `every-1` 85,8 [76,4, 94,5], frases 84,5 [75,0, 93,7], `every-5` 71,2, `every-50` 11,3. Es la columna más ancha: un gasto mal fechado u omitido arruina ~20 totales seguidos (§3.1).
  - **`every-1 − frases` por tipo:** todos los IC contienen el 0 (`recent_change` +1,1 [−0,3, +2,2], `stable` −0,5 [−1,3, +0,1], `aggregate` +1,3 [−0,2, +3,9]).
- **Por dominio (oficial),** la mayor ventaja de `every-1` sobre `every-5` está en `expense` (+12,0 [+8,0, +16,1]) y `content` (+8,0 [+6,5, +9,5]); la menor, en `calendar` (+1,5 [+0,4, +2,9]). `every-1 − frases` solo excluye el 0 en `todo`, a favor de las frases: −2,0 [−4,2, −0,1]. Con 7 dominios × 3 pares, un IC al 95 % que excluya el 0 por azar es esperable; no lo tomo como hallazgo.
- **`invented` de las dos formas.** Tasas por pregunta, media de las 10 personas con las 2 repeticiones [IC], y conteos de la repetición 0, las 10 personas sumadas:

  | política | `invented`, regla actual | `nothing_logged` como `stale` | sin marcadas, actual → reclasificado | conteo rep 0: actual → reclasificado | `partial_total` rep 0 (diagnóstico) |
  | --- | --: | --: | --: | --: | --: |
  | never | 2,8 % [2,5, 3,1] | 0,0 % [0,0, 0,0] | 2,6 % → 0,0 % | 179 → 0 | 165 |
  | every-50 | 2,8 % [2,6, 3,1] | 0,4 % [0,1, 0,8] | 2,6 % → 0,1 % | 179 → 25 | 129 |
  | every-20 | 1,8 % [1,2, 2,5] | 1,0 % [0,4, 1,7] | 1,5 % → 0,6 % | 103 → 57 | 58 |
  | every-10 | 1,3 % [0,9, 1,7] | 0,9 % [0,5, 1,4] | 0,8 % → 0,4 % | 83 → 58 | 50 |
  | every-5 | 1,6 % [0,9, 2,5] | 1,4 % [0,6, 2,3] | 0,8 % → 0,6 % | 93 → 81 | 59 |
  | triggered-phrases-any | 1,7 % [0,8, 2,7] | 1,7 % [0,8, 2,7] | 0,9 % → 0,9 % | 89 → 89 | 68 |
  | every-1 | 1,6 % [0,7, 2,5] | 1,6 % [0,7, 2,5] | 0,8 % → 0,8 % | 91 → 90 | 69 |

  `nothing_logged` es atraso de quien sueña poco: con la regla nueva desaparece en `never` y casi en `every-50`, y en `every-1` y las frases casi no hay (1 en `every-1`, 0 en las frases). Lo que queda en `every-1` y las frases es otra cosa: en la repetición 0, 69 de las 91 de `every-1` son totales incompletos, el patrón de P6 §3.1 (un gasto que el sueño omitió o que Memora fechó distinto, repetido en ~20 totales), y la mitad son preguntas marcadas. La precisión no cambia con ninguna de las dos reglas.

**Validación contra la muestra de antes del borrado** (`docs/p7/before-loss/tables.md`, analizada aparte). academic_researcher y startup_founder son las dos personas con las 7 políticas en las dos muestras. Diferencias oficiales de la repetición 0 (columnas de diferencias de "Official accuracy per persona": antes del borrado en `docs/p7/before-loss/tables.md`; nueva en `docs/p7/tables.md` del commit 6b806e4, generado desde `data/p7-*-whole-419c13b.csv`, que solo tiene la repetición 0):

| A − B, oficial (puntos) | academic, antes | academic, nueva | startup, antes | startup, nueva |
| --- | --: | --: | --: | --: |
| `every-1 − triggered-phrases-any` | +1,0 | −1,5 | +1,0 | −0,3 |
| `every-1 − every-5` | +7,9 | +5,6 | +5,0 | +5,5 |
| `triggered-phrases-any − every-5` | +6,9 | +7,1 | +4,0 | +5,9 |

En cada persona, `every-1 − frases` cambia de signo entre dos muestras de las mismas corridas, y entre la repetición 0 y la 1 se mueve +2,4 en academic_researcher y +1,0 en startup_founder (§3.7). Por eso el IC por persona, y no una persona, es lo que permite decir "no se distinguen".

### 3.6 Soñar seguido no degrada la memoria acá, y por qué

Comparación con RecMem y con "Useful Memories Become Faulty". Los dos papers dan razones para no consolidar en cada interacción:

- **RecMem** (§1, §4.2): consolidar en cada turno es caro y fragmenta los temas que evolucionan.
- **"Useful Memories Become Faulty"** (resumen, §6.4, App. L.2): la utilidad sube y después cae, y el daño crece con la cantidad de actualizaciones.

**Nosotros no vemos degradación por soñar seguido.** `every-1` hace un sueño por sesión y queda por encima de `every-5` en los 3 tramos de las 2 personas enteras (repetición 0, `docs/p7/tables.md`, "Whole personas"):

| persona | tramo | `every-1` oficial / sin marcadas | `every-5` oficial / sin marcadas | `every-1 − every-5` oficial / sin marcadas |
| --- | --- | --: | --: | --: |
| academic_researcher | s1–210 | 96,1 / 97,3 | 90,6 / 91,6 | +5,6 / +5,6 |
| academic_researcher | s211–420 | 94,8 / 95,6 | 88,5 / 89,2 | +6,3 / +6,3 |
| academic_researcher | s421–end | 85,7 / 90,8 | 83,1 / 88,3 | +2,6 / +2,6 |
| startup_founder | s1–210 | 90,0 / 96,8 | 84,5 / 90,9 | +5,5 / +5,9 |
| startup_founder | s211–420 | 94,1 / 95,9 | 84,8 / 86,4 | +9,3 / +9,5 |
| startup_founder | s421–end | 94,6 / 96,4 | 88,4 / 90,0 | +6,2 / +6,4 |

- **startup_founder:** `every-1` sin marcadas se mantiene en 96,8 / 95,9 / 96,4 % a lo largo de 606 sesiones. La brecha no se achica: el último tramo (+6,2) queda por encima del primero (+5,5). El oficial de s1–210 es bajo para las dos políticas porque ahí cae la semana marcada de esta persona (P6 §3.2).
- **academic_researcher:** las dos políticas bajan hacia el final (sin marcadas, `every-1` de 97,3 a 90,8 y `every-5` de 91,6 a 88,3), y la brecha baja de +5,6 a +2,6. Es lo mismo que en la muestra de antes del borrado (+7,9 / +6,0 / +4,0; `docs/p7/before-loss/tables.md`): la compresión se repite en esta persona.
- **Cuánto se mueve una brecha entre muestras.** La misma persona y el mismo tramo, en las dos muestras de academic_researcher: +7,9 contra +5,6, +6,0 contra +6,3 y +4,0 contra +2,6. Hasta 2,3 puntos. La caída de academic_researcher (3,0 puntos ahora, 3,9 antes) apenas supera eso; la diferencia entre las dos personas en s421–end (2,6 contra 6,2) también.
- **Qué se puede afirmar con 2 personas:** el orden (`every-1` arriba en los 6 tramos, en las dos cuentas) y que la compresión no es general: aparece en una persona y no en la otra. **Qué no:** cuánto cambia la brecha para la población de personas, ni si en promedio se achica. Con 2 personas no hay IC por persona (§3.1), y s1–210 no sobreestima la brecha en forma sistemática: la sobreestima en academic_researcher y la subestima en startup_founder.

La explicación medida tiene dos partes:

1. **El sueño devuelve ediciones, no reescribe** (P4a §3.2). Manda `<append>` y `<replace>` sobre líneas puntuales; lo que no toca queda igual. P4a midió la variante que reescribe (`dreaming/dream_rewrite.py`, cadencia 7, monthly s1–210):
   - En el examen empata: 96,1 contra 95,5 %.
   - Cambió 53 líneas de un sueño al siguiente, contra 49 hechos que de verdad cambiaron. Editando, 49 = 49 (P4a §4.2).
   - Cuesta 1,65 veces más en monthly s1–210, y 4,6 veces más con un sueño de 1 sesión sobre notas de 20.000 caracteres (P4a §3.2).

   Reescribir en el lugar es justamente lo que "Useful Memories Become Faulty" identifica como el paso más dañino (Tabla 5), y nuestro sueño no lo hace.
2. **La exactitud de la nota no baja en 619 sesiones** (P6b §3.3). Con un sueño por sesión, la nota de `every-1` tiene bien el 91,4 %, 93,0 % y 92,3 % de los hechos vivos en s1–210, s211–420 y s421–619. Las líneas stale, falsas o duplicadas no pasan de 5 por nota de unas 330 líneas.

En academic_researcher la ventaja sí se achica. P6 §3.3 lo explicó sobre la muestra de antes del borrado (no volví a clasificar los errores tardíos de la muestra nueva: necesita el caché de P7a, y P7b no lee el caché):

- **Memora confunde "ya no me gusta" con "no me gusta".** Pesa sobre las dos políticas (12 errores de `every-1` contra 9 de `every-5`).
- **Los sueños frecuentes titulan los documentos en forma genérica.** Es un costo propio de soñar seguido: 14 hashtags mal ubicados con `every-1` contra 2 con `every-5`.

Ese costo es chico, no da vuelta el orden, y en startup_founder no se ve.

**Por qué los papers ven otra cosa.** En "Useful Memories Become Faulty" y en Auto-Dreamer, el consolidador abstrae lecciones o procedimientos a partir de trayectorias. Acá el sueño anota hechos que el usuario dice en una fase dedicada de la conversación (Memora §3.3), y no hay nada que generalizar de más. La advertencia de RecMem sobre el costo sí aplica, y se ve en el eje x: `every-1` cuesta 2,49 [2,43, 2,55] veces lo que `every-5` y 1,23 [1,21, 1,26] veces lo que las frases, y no rinde más que las frases (−0,1 [−0,6, +0,5]).

### 3.7 Ruido entre repeticiones

`docs/p7/tables.md`, "Noise between repetitions": repetición 1 − repetición 0, por persona, en puntos (oficial). La sección es nueva en `final/analysis.py` (`repetition_section`). Las decisiones de soñar son idénticas entre repeticiones: sueños, sesiones leídas, exámenes y preguntas no cambian en ninguna de las 70 parejas de corridas (primera línea de la sección). Lo que cambia es lo que escribe cada sueño y lo que contesta cada examen.

| | never | every-1 | every-5 | every-10 | every-20 | every-50 | frases | `every-1 − frases` | `every-1 − every-5` | `frases − every-5` |
| --- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| media | −0,1 | +0,1 | −0,3 | +0,2 | +0,4 | −0,1 | −1,0 | +1,1 | +0,4 | −0,7 |
| media del valor absoluto | 0,1 | 1,2 | 1,5 | 1,6 | 1,6 | 0,9 | 1,2 | 1,2 | 1,6 | 1,5 |
| mayor valor absoluto | 0,5 | 4,4 | 3,5 | 3,0 | 4,1 | 1,7 | 5,8 | 2,4 | 2,9 | 2,7 |
| personas por encima de 0 | 0 | 6 | 4 | 3 | 7 | 4 | 2 | 9 | 5 | 3 |

- **Una política repetida sobre la misma persona se mueve 0,9–1,6 puntos en promedio** (`never`, que no sueña, 0,1). Varios valores pasan los 2,8 de P5a §4.4; los mayores son de marketing_manager (`every-1` −4,4, frases −5,8) y software_engineer (`every-20` −4,1).
- **Una diferencia emparejada se mueve 1,2–1,6 puntos en promedio.** Es del tamaño de todo el IC de `every-1 − frases` (1,1 de ancho), y mucho menor que `every-1 − every-5` (+7,0). Por eso hacía falta la repetición 1 para la primera comparación, y no para la segunda.
- **Un patrón que no expliqué.** `every-1 − frases` sube de la repetición 0 a la 1 en 9 de las 10 personas (media +1,1): las frases bajan 1,0 puntos en promedio y `every-1` no se mueve. La caída más grande es la de marketing_manager (−5,8 puntos), pero el signo se repite en 9 personas. Con la repetición 0 parecía que las frases ganaban; con la 1, que pierden; promediadas, empatan. No lo diagnostiqué: hace falta el caché de P7a para ver qué sueños cambiaron, y P7b no lo lee.

## 4. Prueba

Todo con `PYTHONHASHSEED=0`, desde este worktree, sin llamar a la API.

```
$ PYTHONHASHSEED=0 uv run pytest -q
...................................................                      [100%]
51 passed
```

**La copia fechada es idéntica a los CSV finales de P7a, commit 2853c99:**

```
$ (cd <P7a> && git show 2853c99:data/p7-runs.csv) > data/p7-runs-final-2853c99.csv
$ (cd <P7a> && git show 2853c99:data/p7-probes.csv) > data/p7-probes-final-2853c99.csv
$ shasum -a 256 data/p7-runs-final-2853c99.csv data/p7-probes-final-2853c99.csv | cut -c1-16
e840e8f1ca68e4fa
e887fb0acc2ccd92
```

Son los mismos sha256 que `git show 2853c99:data/p7-*.csv` en el worktree de P7a: 152 filas de corridas (140 de la grilla y 12 de tramos enteros) y 3.724 de probes.

**Análisis final:**

```
$ PYTHONHASHSEED=0 uv run python -m final.analysis data/p7-runs-final-2853c99.csv data/p7-probes-final-2853c99.csv --output docs/p7
...
| academic_researcher | yes | 0,1 | 0,1 | 0,1 | 0,1 | 0,1 | 0,1 | 0,1 |
...
| every-1 | 10 | 210.0 | 0.1223 [0.1192, 0.1252] | 0.0252 | 94.1 [92.4, 95.7] | 94.2 [92.5, 95.8] | 96.3 [95.1, 97.3] | 96.4 [95.2, 97.3] |
| every-5 | 10 | 42.0 | 0.0492 [0.0483, 0.0500] | 0.0251 | 87.2 [85.7, 88.5] | 87.3 [85.8, 88.6] | 89.3 [87.9, 90.5] | 89.4 [88.1, 90.5] |
| triggered-phrases-any | 10 | 157.7 | 0.0993 [0.0974, 0.1013] | 0.0251 | 94.2 [92.5, 95.8] | 94.3 [92.6, 95.9] | 96.4 [95.1, 97.6] | 96.5 [95.2, 97.7] |
...
| every-1 − triggered-phrases-any | official | -0.1 [-0.6, +0.5] | 4 / 0 / 6 |
| every-1 − triggered-phrases-any | lenient | -0.1 [-0.6, +0.5] | 4 / 0 / 6 |
| every-1 − triggered-phrases-any | official without marked | -0.1 [-0.6, +0.5] | 5 / 0 / 5 |
| every-1 − triggered-phrases-any | lenient without marked | -0.1 [-0.7, +0.4] | 4 / 1 / 5 |
| every-1 − triggered-phrases-any | maintenance $ | 0.0229 [0.0209, 0.0256] | ratio 1.23 [1.21, 1.26] |
| every-1 − every-5 | official | +7.0 [+6.0, +8.1] | 10 / 0 / 0 |
| every-1 − every-5 | official without marked | +7.1 [+6.0, +8.2] | 10 / 0 / 0 |
| every-1 − every-5 | maintenance $ | 0.0731 [0.0703, 0.0757] | ratio 2.49 [2.43, 2.55] |
...
Runs whose dreams, sessions_read, exams, asked differ between repetitions: none.
...
| mean | -0.1 | +0.1 | -0.3 | +0.2 | +0.4 | -0.1 | -1.0 | +1.1 | +0.4 | -0.7 |
| mean of absolute values | 0.1 | 1.2 | 1.5 | 1.6 | 1.6 | 0.9 | 1.2 | 1.2 | 1.6 | 1.5 |
| largest absolute value | 0.5 | 4.4 | 3.5 | 3.0 | 4.1 | 1.7 | 5.8 | 2.4 | 2.9 | 2.7 |
| personas above zero | 0 | 6 | 4 | 3 | 7 | 4 | 2 | 9 | 5 | 3 |
...
Repetition 0, every planned whole run with all three stretches. Missing: none.
...
| academic_researcher | s1-210 | official | 570/593 (96.1) | 537/593 (90.6) | +5.6 |
| academic_researcher | s211-420 | official | 604/637 (94.8) | 564/637 (88.5) | +6.3 |
| academic_researcher | s421-end | official | 496/579 (85.7) | 481/579 (83.1) | +2.6 |
| startup_founder | s1-210 | official | 523/581 (90.0) | 491/581 (84.5) | +5.5 |
| startup_founder | s211-420 | official | 638/678 (94.1) | 575/678 (84.8) | +9.3 |
| startup_founder | s421-end | official | 530/560 (94.6) | 495/560 (88.4) | +6.2 |
```

**Muestra de antes del borrado** (aparte):

```
$ PYTHONHASHSEED=0 uv run python -m final.analysis data/p7-runs-before-loss.csv data/p7-probes.csv --output docs/p7/before-loss
...
| academic_researcher | 23.9 | 97.1 | 89.2 | 82.3 | 76.1 | 59.2 | 96.1 | +1.0 | +7.9 | +6.9 | 8 |
| startup_founder | 24.8 | 89.7 | 84.7 | 78.3 | 70.7 | 53.7 | 88.6 | +1.0 | +5.0 | +4.0 | 42 |
...
| academic_researcher | s1-210 | official | 576/593 (97.1) | 529/593 (89.2) | +7.9 |
| academic_researcher | s211-420 | official | 603/637 (94.7) | 565/637 (88.7) | +6.0 |
| academic_researcher | s421-end | official | 506/579 (87.4) | 483/579 (83.4) | +4.0 |
```

Salidas completas: `docs/p7/tables.md` y `docs/p7/before-loss/tables.md`. Cada una empieza con el comando que la generó y el sha256 de sus dos CSV.

## 5. Opciones descartadas y por qué

| Opción | Por qué no |
| --- | --- |
| IC binomial sobre las preguntas | Supone independencia. En `every-1` las personas van de 89,8 a 97,7 % y la binomial da 1,2 puntos de ancho, contra 3,3 por persona (§3.1); hay racimos de unas 20 preguntas que fallan juntas (P6 §3.1). |
| Bootstrap por hecho | Los hechos de una persona comparten gastos y documentos |
| Modelo jerárquico | 10 personas y 2 repeticiones no alcanzan para estimar sus varianzas sin supuestos fuertes |
| Mostrar el IC percentil con 2 o 3 personas | Es solo la persona más baja y la más alta (§3.1) |
| Comparar IC no emparejados | Desperdicia que todas las políticas comparten persona, examen y caché |
| Mezclar las dos muestras en una tabla | Son muestras distintas de los mismos sueños: P7a usa la de antes del borrado solo para validar. Acá se analizan por separado y se comparan lado a lado. |
| matplotlib | Una dependencia nueva para 4 gráficos simples, con la memoria de la Mac al límite |

## 6. Limitaciones: qué se puede afirmar y qué no

- **Qué se puede afirmar, con IC sobre 10 personas:**
  - Las frases y `every-1` no se distinguen: −0,1 [−0,6, +0,5] puntos. Las frases cuestan el 81 %.
  - Las dos le ganan a `every-5` por 7,0 puntos (IC de 5,8 a 8,3), en las 10 personas, y la ventaja está en lo que cambió hace poco, no en lo estable.
  - El orden de las cadencias fijas.
- **Qué no:**
  - Que las frases sean mejores, ni que `every-1` lo sea. Además, la diferencia subió de la repetición 0 a la 1 en 9 de 10 personas, y no sé por qué (§3.7).
  - Cuánto vale cada distancia más allá de s1–210 (ver abajo).
  - Nada sobre otros modelos, otros datos ni usuarios reales.
- **2 repeticiones por persona.** Con el ruido de §3.7, alcanzan para `every-1 − every-5` y justo para `every-1 − frases`. Las personas enteras tienen una sola.
- **Compresión de distancias: 2 personas, sin IC.** Se pueden mostrar los números de cada persona y ver si van en la misma dirección; no van. Un mismo tramo se mueve hasta 2,3 puntos entre dos muestras (§3.6), del tamaño de las diferencias entre tramos. Las corridas enteras tienen una sola repetición.
- **Las corridas nuevas son una muestra nueva, no las de P5/P6.** Se perdió el caché, así que se volvieron a pagar los sueños y los exámenes. P7a las validó contra los números de antes del borrado: conteos exactos y precisión dentro de 2,8 puntos, salvo `every-10` con −3,0, dentro del doble del ruido (P5a §4.4).
- **Memora dice los cambios en forma mayormente explícita.** Hay una fase de la sesión donde se expresa la operación (Memora §3.3), y las frases del detector ven el 96–97 % de las sesiones con hechos (P5b §3.2). STALE (§1) muestra el caso que acá no se mide: el conflicto implícito, sin negación. Con conflictos implícitos, el detector de frases y quizás el sueño rendirían menos.
- **El detector de frases está afinado al inglés del simulador de Memora** (P5b §6): "I have to go now" dispara sin hechos, y las metas nuevas no nombran a las anteriores.
- **Un solo modelo, Haiku 5.5,** con thinking adaptativo y effort `medium`, para el sueño y para el que responde.
- **s1–210 es un tercio del mes.** Ordena bien `every-1` y `every-5` en los 3 tramos de las 2 personas enteras. Para la distancia, el error va en las dos direcciones: en academic_researcher el último tramo da la mitad (+2,6 contra +5,6), y en startup_founder algo más (+6,2 contra +5,5).
- **Aun con 10 personas, el IC percentil es algo angosto:** el bootstrap no corrige el factor √((n−1)/n), que es un 5 % con n = 10.
- **Las barras de IC del gráfico principal son cortas** (hasta 3,3 puntos y $0,0060): casi no se ven al lado de las distancias entre políticas.
- **Muchas comparaciones.** Por probe y por dominio hay 15 y 21 diferencias emparejadas con IC al 95 %; alguna puede excluir el 0 por azar (§3.5, `todo`).
