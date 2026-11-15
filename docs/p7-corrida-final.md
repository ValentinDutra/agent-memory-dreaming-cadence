# P7 · Corrida final y análisis (re-corrida sin caché)

**Resultado.** 10 personas monthly × 7 políticas × 2 repeticiones sobre s1–210 (140 corridas), más `every-1` y `every-5` sobre la persona entera de academic_researcher y de startup_founder. Todo se pagó de nuevo después de perder el caché. Los IC al 95 % se calculan sobre personas: las 2 repeticiones se promedian dentro de cada persona y se remuestrean las 10 personas.

| política | sueños en s1–210 | mantener la memoria, $ por persona | oficial | sin marcadas |
| --- | --: | --: | --: | --: |
| `every-1` | 210 | 0,1223 [0,1192, 0,1252] | 94,1 [92,4, 95,7] | 96,3 [95,1, 97,3] |
| `triggered-phrases-any` | 157,7 | 0,0993 [0,0974, 0,1013] | 94,2 [92,5, 95,8] | 96,4 [95,1, 97,6] |
| `every-5` | 42 | 0,0492 [0,0483, 0,0500] | 87,2 [85,7, 88,5] | 89,3 [87,9, 90,5] |
| `every-10` | 21 | 0,0394 [0,0385, 0,0401] | 80,1 [79,1, 81,0] | 81,8 [81,3, 82,4] |
| `every-20` | 10 | 0,0317 [0,0312, 0,0322] | 72,9 [71,6, 74,0] | 74,3 [73,4, 75,2] |
| `every-50` | 4 | 0,0278 [0,0272, 0,0283] | 57,7 [56,5, 58,6] | 58,9 [58,1, 59,9] |
| `never` | 0 | 0 | 25,7 [24,9, 26,5] | 26,4 [25,6, 27,1] |

- **Soñar cuando el detector de frases ve un hecho rinde igual que soñar después de cada sesión, y cuesta el 81 %.** `every-1 − frases` da −0,1 [−0,6, +0,5] puntos en las 4 cuentas. `every-1` cuesta 1,23 [1,21, 1,26] veces más.
- **Soñar cada 5 sesiones pierde 7,0 [6,0, 8,1] puntos contra `every-1`,** y contra las frases 7,0 [5,8, 8,3], en las 10 de 10 personas.
- **Esa pérdida es atraso, no olvido.** `every-1 − every-5` da +29,0 [26,5, 31,7] en `new` y +25,6 [20,7, 30,0] en `recent_change`, pero +0,1 [−0,9, +1,3] en `stable` (hechos sin cambios).
- **El orden de las fijas,** every-1 > 5 > 10 > 20 > 50 > never, se cumple en las 20 celdas persona × repetición.
- **Soñar seguido no degrada la memoria acá.** En las 2 personas enteras, `every-1` le gana a `every-5` en los 3 tramos del mes.
- **La ventaja no se achica en forma general hacia el final del mes.** Por tramo, oficial: academic_researcher +5,6 / +6,3 / +2,6 y startup_founder +5,5 / +9,3 / +6,2. Lo que P6 había visto en una persona se repite en ella, pero no en la otra.
- **Costo:** P7a pagó $11,8724 de $13,00, contra $12,0752 estimados (−1,7 %). P7b y la integración, $0.

| Rol | Ruta |
| --- | --- |
| Tag | `p7` |
| Contrato P7a/P7b, adaptado a la re-corrida sin caché | `docs/p7-interfaz.md` |
| Informe de P7a (corrida, validación, costo) | `docs/p7a-corrida-final.md` |
| Informe de P7b (IC, diferencias emparejadas, trabajo relacionado, límites) | `docs/p7b-analisis.md` |
| Grilla: estimación, corrida, CSV, comparación con los números de antes | `final/grid.py` |
| Análisis y gráficos SVG | `final/analysis.py`, `final/charts.py` |
| Tablas y gráficos de este informe | `docs/p7/tables.md`, `docs/p7/*.svg` |
| CSV finales (copia fechada del commit 2853c99 de P7a, mismo sha256) | `data/p7-runs-final-2853c99.csv`, `data/p7-probes-final-2853c99.csv` (iguales a `data/p7-runs.csv` y `data/p7-probes.csv`) |
| Números de antes del borrado (commit 8e6bcff) | `data/p7-runs-before-loss.csv`, `docs/p7/before-loss/` |
| Tests (52; 1 nuevo en P7a) | `tests/test_grid.py` (2), `tests/test_analysis.py` (1) |

## 1. Problema

El post "The components of agent memory" (Lance Martin, Anthropic Engineering, https://www.anthropic.com/engineering/components-of-agent-memory) deja abierta esta pregunta: "It may be important instead to focus dreaming on information that's likely to change or to carefully tune the cadence of dreaming". P5 midió 11 políticas en 2 personas y una repetición, y las diferencias entre vecinas eran del tamaño del ruido (P5 §6). P7 tiene que ordenar las 7 políticas que recomendó P5 con IC sobre las 10 personas monthly. También tiene que medir en 2 personas si s1–210 exagera la ventaja de soñar seguido (P6 §3.4), que es la opción (b) que elegí (`docs/p6-inventadas.md` § "Decisiones").

**Pérdida del caché.** El 13/11 a las 15:33 se borraron los worktrees de P7, P7a y P7b. Con ellos se perdió `results/`: el caché unificado de P5+P6 (102 MB) y los libros de gasto, que estaban en `.gitignore` y no tenían copia. El código estaba commiteado. Esta re-corrida parte de `results/` vacío, así que cada llamada se pagó de nuevo. Eso incluye las corridas que el plan original sacaba del caché: s1–210 rep 0 de academic_researcher y startup_founder, y las 3 corridas enteras de P5/P6.

## 2. Opciones consideradas

| Opción | Qué es | Dónde |
| --- | --- | --- |
| Validar contra los números de antes con el ruido del que responde (≤ 1,2 pp) | Una corrida nueva vuelve a muestrear también los sueños, no solo las respuestas | P3b §4.3 |
| Validar con el ruido de una política repetida entera (2,8 pp) | Comparar con lo que se movió una política entre r0 y r1 en P5a | P5a §4.4, `docs/p7-interfaz.md` § Validación |
| Re-pagar las 3 corridas enteras de P5/P6 ($1,00 estimados) | Sin ellas, ninguna persona queda con las dos políticas enteras | `docs/p7-interfaz.md`, paso 2b |
| Cerrar sin la repetición 1 | Las conclusiones de la rep 0 ya tenían IC | §4.2 |
| IC sobre preguntas o sobre personas | Las preguntas de una persona no son independientes | P7b §2.1 |
| Trabajo relacionado | RecMem, Auto-Dreamer, "Useful Memories Become Faulty", sleep-time compute, STALE, Memora, leídos en la fuente | P7b §2.4 |

## 3. Análisis y elección

- **Validación con 2,8 puntos, y parar recién pasando 5,6.** Una corrida sin caché es una muestra nueva. Lo que no puede cambiar son las decisiones de soñar: sesiones, sueños, sesiones leídas, exámenes y preguntas. Las fijas y las frases deciden sin leer las notas, así que esos conteos tienen que salir exactos, y si no, es un bug. La precisión solo tiene que quedar dentro del ruido de una política repetida.
- **Las 3 corridas enteras se re-pagaron.** Decidí volver a pagarlas: sin ellas, la pregunta de la opción (b) quedaba sin respuesta.
- **La repetición 1 se terminó.** Subí el límite de la consola para eso. Hizo falta: con la rep 0 sola, `every-1 − frases` daba −0,6 [−1,2, −0,0] y parecía que las frases ganaban. Con las 2 repeticiones da −0,1 [−0,6, +0,5].
- **La unidad del IC es la persona.** Con `every-1`, el IC por persona mide 3,3 puntos de ancho. Si las preguntas contaran como independientes, mediría 1,2. La precisión va de 89,8 a 97,7 % según la persona (`docs/p7/tables.md`, "Why the persona is the unit" y "Official accuracy per persona").
- **Las dos muestras nunca se mezclan.** La de antes del borrado queda aparte, en `docs/p7/before-loss/`, y solo se usa para validar y para dimensionar el ruido.

## 4. Prueba

### 4.1 Comandos

```
PYTHONHASHSEED=0 uv run python -m final.grid estimate                 # estimación sin caché, $12,0752
PYTHONHASHSEED=0 uv run python -m final.grid run monthly/<persona>:210 --repetition <0|1> --limit 13.00
PYTHONHASHSEED=0 uv run python -m final.grid run monthly/<persona> --repetition 0 --limit 13.00 --policies <every-1|every-5>
PYTHONHASHSEED=0 uv run python -m final.grid table                    # reescribe los dos CSV desde el caché, tope $0
uv run python -m final.grid compare                                   # validación contra data/p7-runs-before-loss.csv
PYTHONHASHSEED=0 uv run python -m final.analysis data/p7-runs-final-2853c99.csv data/p7-probes-final-2853c99.csv --output docs/p7
uv run pytest -q                                                      # 52 passed
```

Corrí el último análisis desde esta rama, ya integrada: regenera `docs/p7/` byte por byte, sin cambios en git.

### 4.2 Corrida e interrupciones (P7a §4.2)

La corrida siguió el orden del contrato: rep 0 (academic_researcher y startup_founder primero, para validar), después las personas enteras (2a y 2b) y por último la rep 1. Se cortó 6 veces y en cada caso se retomó desde el caché, sin pagar dos veces lo que ya estaba:

- **2 cortes por el límite de uso de la organización** (13/11 17:05 y 14/11 05:44). En los dos, P7a paró sin reintentar, corrió `table` y commiteó. Se retomó cuando subí el límite, primero a $25 y después a unos $30. El segundo corte llegó con p7a en $8,62. Según nuestros libros, la organización llevaba ≈ $17,8 en el mes, así que algo fuera de este proyecto gastó el resto, o el límite efectivo no era $25. Desde acá no se puede ver la consola.
- **3 timeouts de lectura de red.** Cada uno se retomó una vez automáticamente, y ninguno se repitió en la misma llamada.
- **1 reinicio del daemon del host** (14/11 09:54), que mató la corrida sin error de la API.

### 4.3 Validación contra los números de antes del borrado (P7a §4.3)

`uv run python -m final.grid compare`: **22 ok, 1 para reportar y 0 stop.** Los 5 conteos exactos coinciden en las 23 filas (14 corridas s1–210 r0 de academic_researcher y startup_founder, más los 9 tramos de las 3 corridas enteras de 2b). La única fila fuera de 2,8 puntos es academic_researcher `every-10`: 82,3 % antes, 79,3 % en la rep 0 y 82,1 % en la rep 1. Era ruido de una sola repetición. El orden de las fijas se mantiene en las dos personas, antes y después.

### 4.4 La grilla s1–210 (`docs/p7/tables.md`)

Diferencias emparejadas, en puntos, calculadas dentro de cada persona remuestreada:

| A − B | oficial | sin marcadas | personas A > / = / < B | razón de costo de mantener |
| --- | --: | --: | --: | --: |
| `every-1 − frases` | −0,1 [−0,6, +0,5] | −0,1 [−0,6, +0,5] | 4 / 0 / 6 | 1,23 [1,21, 1,26] |
| `every-1 − every-5` | +7,0 [+6,0, +8,1] | +7,1 [+6,0, +8,2] | 10 / 0 / 0 | 2,49 [2,43, 2,55] |
| `frases − every-5` | +7,0 [+5,8, +8,3] | +7,2 [+6,0, +8,4] | 10 / 0 / 0 | 2,02 [2,00, 2,04] |

Por tipo de pregunta, oficial (`every-1 − every-5`):

| `new` | `recent_change` | `stable` (sin cambios) | `never_existed` (señuelo) | `aggregate` (total) |
| --: | --: | --: | --: | --: |
| +29,0 [26,5, 31,7] | +25,6 [20,7, 30,0] | +0,1 [−0,9, +1,3] | +0,0 [+0,0, +0,1] | +14,6 [9,8, 19,8] |

- **`every-1` y las frases solo se separan en `todo`:** −2,0 [−4,2, −0,1] a favor de las frases. Es 1 de 21 comparaciones por dominio con IC al 95 %, y puede salir así por azar (P7b §6).
- **`invented` de las dos formas** (decisión 2 de P6, rep 0, todas las personas):
  - Con `nothing_logged` reclasificado como `stale`, `never` pasa de 179 a 0 y `every-50` de 179 a 25.
  - `every-1` (91 → 90) y las frases (89 → 89) casi no cambian. Lo que les queda son totales incompletos: `partial_total`, que se reporta solo como diagnóstico, da 69 y 68.
- **Ruido entre repeticiones** (P7b §3.7):
  - Una política que sueña se mueve 0,9–1,6 puntos en promedio al repetir la misma persona, con un máximo de 5,8.
  - Una diferencia emparejada se mueve 1,2–1,6 puntos. Eso es del tamaño de todo el IC de `every-1 − frases`, y mucho menos que `every-1 − every-5`.

### 4.5 Personas enteras, por tramo (repetición 0)

| persona | tramo | `every-1` sin marcadas | `every-5` sin marcadas | `every-1 − every-5` oficial / sin marcadas |
| --- | --- | --: | --: | --: |
| academic_researcher | s1–210 | 569/585 (97,3) | 536/585 (91,6) | +5,6 / +5,6 |
| academic_researcher | s211–420 | 603/631 (95,6) | 563/631 (89,2) | +6,3 / +6,3 |
| academic_researcher | s421–fin | 495/545 (90,8) | 481/545 (88,3) | +2,6 / +2,6 |
| startup_founder | s1–210 | 522/539 (96,8) | 490/539 (90,9) | +5,5 / +5,9 |
| startup_founder | s211–420 | 637/664 (95,9) | 574/664 (86,4) | +9,3 / +9,5 |
| startup_founder | s421–fin | 529/549 (96,4) | 494/549 (90,0) | +6,2 / +6,4 |

- **academic_researcher:** la ventaja se achica hacia el final, como en la muestra de antes del borrado (+7,9 / +6,0 / +4,0, `docs/p7/before-loss/tables.md`). La misma persona y el mismo tramo se mueven hasta 2,3 puntos de una muestra a la otra, y la caída actual (3,0 puntos) apenas supera eso.
- **startup_founder:** `every-1` se mantiene en 96–97 % sin marcadas durante 606 sesiones, y la ventaja del último tramo queda por encima de la del primero.
- **Conclusión:** s1–210 ordena bien las dos políticas en los 6 tramos. La distancia la sobreestima en una persona y la subestima en la otra. Con 2 personas no hay IC por persona.

### 4.6 Costo real (P7a §4.6)

| Paso | Estimado | Pagado |
| --- | --: | --: |
| 1. s1–210 rep 0, 10 personas | 5,2751 | 5,2043 |
| 2a. `every-1` entera, startup_founder | 0,5210 | 0,5146 |
| 2b. 3 enteras re-pagadas | 1,0039 | 0,9203 |
| 3. s1–210 rep 1, 10 personas | 5,2751 | 5,2331 |
| **Total p7a** (libro `results/spend/p7a.jsonl` del worktree de P7a) | **12,0752** | **11,8724** de 13,00 |

| Proceso | Tope | Gastado |
| --- | --: | --: |
| P7a | $13,00 | $11,8724 |
| P7b | $0 | $0 |
| P7 (integración) | $1,00 | $0 |

Lo que el P7a anterior pagó antes del borrado no se puede saber exacto, porque su libro se perdió. Había estimado $0,1269 para la única corrida que terminó (startup_founder `triggered-phrases-any` s1–210). Hasta 4 llamadas cortadas (3 timeouts y el reinicio) pueden haberse cobrado sin quedar en el libro, a milésimos de dólar cada una.

## 5. Opciones descartadas y por qué

| Opción | Por qué no | Dónde |
| --- | --- | --- |
| Validar con el ruido del que responde (≤ 1,2 pp) | Marcaría como fuera de rango casi cualquier corrida nueva, porque también cambian los sueños | P7a §5 |
| Reintentar después del 400 de límite de uso | La regla lo prohíbe; el acceso volvía el 01/12 | P7a §5 |
| Cerrar sin la repetición 1 | Elegí terminarla. Sin ella, `every-1 − frases` parecía favorecer a las frases (−0,6 [−1,2, −0,0]) | §3 |
| Mezclar la muestra de antes del borrado con la nueva | Son sueños de corridas distintas; se usa aparte para validar y dimensionar el ruido | P7b §3.5 |
| IC binomial sobre preguntas | Da un IC 2,75 veces más angosto que el de personas con `every-1` (1,2 contra 3,3 puntos) | §3 |
| Reajustar el modelo de costo sobre el caché | El caché se perdió; se usa el modelo publicado de P5 §4.3, fijo en `final/grid.py` | `docs/p7-interfaz.md` |

## 6. Limitaciones y preguntas abiertas

- **Qué se puede afirmar, con IC sobre 10 personas:**
  - Las frases y `every-1` no se distinguen, y las frases cuestan el 81 %.
  - Las dos le ganan a `every-5` por ~7 puntos, en lo que cambió hace poco.
  - El orden de las cadencias fijas.
- **Qué no:**
  - Que una de las dos (frases o `every-1`) sea mejor.
  - Cuánto vale cada distancia más allá de s1–210: hay 2 personas enteras, sin IC y con una sola repetición.
  - Nada sobre otros modelos (solo Haiku 5.5), otros datos ni usuarios reales.
- **La caída de las frases de la rep 0 a la rep 1 es ruido** (`docs/p7c-diagnostico.md`, $0). `every-1 − frases` sube en 9 de 10 personas: p = 0,0107 a una cola en esa columna, pero con las 10 columnas de la tabla de ruido, la probabilidad de que alguna llegue a 9 de 10 por azar es 0,115 (permutando r0 y r1 dentro de cada persona; `uv run python -m final.repetitions signs`). Entre las dos corridas no cambió nada: modelo, thinking, effort, temperatura y `repeat` son iguales en las 13.823 respuestas. La caída grande de marketing_manager viene de un gasto que omitió el primer sueño de la r1, compartido por `every-1` y las frases. Los sueños de las frases no varían más que los de `every-1` (0,77 contra 1,03 puntos).
- **Memora dice los cambios en forma mayormente explícita** (Memora §3.3). El detector de frases está afinado a su inglés (P5b §6). STALE (§1) describe el caso que acá no se mide: el conflicto implícito, sin negación.
- **La compresión de academic_researcher tiene las causas de P6 también en la muestra nueva** (`docs/p7c-diagnostico.md` parte 2). `every-1` repite errores tardíos sobre gustos "ya no" (11 respuestas) y sobre posts o mails con títulos genéricos (16), que le restan 2,7 puntos a la brecha. Además, `every-5` deja de errar totales al final, que le restan 1,5 más. En startup_founder, `every-1` casi no tiene esos errores (2 y 5 respuestas), aunque Memora registra cambios parecidos; por qué los sueños los manejaron distinto no se leyó.
- **El IC percentil con 10 personas es ~5 % angosto,** porque el bootstrap no corrige el factor √((n−1)/n) (P7b §6).
- **Sueño adoptado:** todo P7 usó el sueño de P4a. El agente recomendado después de P8 es `triggered-phrases-any` con el sueño E (reglas que nombran lo que se omitía), medido solo con las frases: ver `docs/p8b-sueno-nombrado.md` § "Recomendación adoptada".
- **La comparación con RecMem y con "Useful Memories Become Faulty"** está en P7b §3.6. Nuestro sueño devuelve ediciones y no reescribe (P4a), y la exactitud de la nota no baja en 619 sesiones (P6b §3.3). Por eso soñar seguido no degrada acá. La advertencia de RecMem sobre el costo sí aplica: `every-1` cuesta 2,49 veces lo que `every-5` y no rinde más que las frases.
