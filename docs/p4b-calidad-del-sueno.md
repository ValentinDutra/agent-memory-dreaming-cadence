# P4b · Calidad del sueño

**Resultado.** Medí el stub de `dreaming/dream.py` con dos instrumentos: el examen de P2/P3 y una comparación línea por línea contra la verdad de P1, calibrada en 3.951 notas perfectas sin un solo error.

- **Corrige lo que cambió.** Deep house pasa a like en todas las corridas. Bonobo deja de ser like en todas: desaparece o pasa a dislike.
- **No inventa valores.** 0 valores falsos sobre hechos vivos. Las 47 líneas "inventadas" son todas "dislike" sobre un like retirado (la cuenta indulgente).
- **Las notas no crecen sin control.** Miden 0,63–1,19 veces las notas perfectas.
- **Reescribir no degrada lo ya escrito.** Como máximo 1 hecho por cadena estuvo bien y después se perdió.
- **El error dominante es la omisión en el primer encuentro.** Lo que un sueño no anota la primera vez no vuelve: un email entero, tres documentos, un pendiente. Es aleatorio: la misma cadena dio 99,1 % y 68,6 % de hechos correctos en dos corridas.
- **Por sesiones leídas:** con 1–5 sesiones por sueño se pierde ~0,4 % de los hechos; con 50 se pierde ~4,5 %.

| Rol | Ruta |
| --- | --- |
| Tag | `p4` |
| Comparación notas-vs-verdad | `dreaming/quality.py` (`compare_notes`, `parse_notes`, `truth_facts`) |
| Medición (CLI que recibe el sueño) | `dreaming/quality_run.py` (`measure`, `chain`, `single`, `window`) |
| Calibración | `dreaming/quality_calibrate.py` |
| Tests (4, sin API) | `tests/test_quality.py` |

## 1. Problema

P5 va a comparar cadencias de sueño. Para eso necesita saber qué tan buenas son las notas que deja un sueño, y por qué fallan. El examen solo no alcanza:

- Hace 16–24 preguntas por sesión examinada, y las notas tienen 40–340 hechos vivos.
- No distingue un hecho que el sueño nunca anotó de uno que anotó y después perdió.
- No ve si las notas crecen.

Ejemplo real: el stub sobre las sesiones 1–35 de weekly/software_engineer (`results/raw/p4b/stub/weekly/software_engineer/single/`) escribió esto:

```
- Bonobo music (Music / Electronic): dislike          ← en s30 el usuario dijo "I'm just not into his music anymore"; la verdad lo borra
- Ann Leckie's books (Books / Science fiction): like  ← la verdad dice "Ann Leckie"
- 2025-06-01 groceries: $28.50                        ← la verdad dice "grocery"
### Social media post: Real-time video stream latency optimization   ← título inventado; el real es "Excited to share how our team..."
- Platform: LinkedIn                                  ← prosa que el formato de P3 no lleva
- Finalize new project proposal (Work)                ← el usuario lo dijo en s5, la hoja de respuestas de Memora no lo registra
  - Current navigation pipeline average latency is 340ms, 140ms over target threshold   ← paráfrasis del ítem guardado
```

Para medirlo hay que emparejar cada línea con su hecho, aunque el sueño lo nombre a su manera. Hay que decidir qué es "inventado" cuando el usuario sí dijo algo que la verdad no registra. Y hay que hacerlo de forma que P4 repita todo con el sueño de P4a sin tocar el código.

## 2. Opciones investigadas

| Fuente | Qué dice sobre medir una memoria consolidada | Qué tomé |
| --- | --- | --- |
| "Useful Memories Become Faulty When Continuously Updated by LLMs", https://arxiv.org/html/2605.12978v2 | §3 compara *Static* (consolidar todo el pozo de una vez) con *Stream* (actualizar después de cada lote). Fig. 2: "Static remains at the ceiling after R=10 and R=50 refresh rounds, whereas Stream falls to 52.6% by Round 10". §6.4 y App. L.2 separan tres mecanismos: *initial compression error* (lo que se pierde la primera vez), *cross-update conditioning* y *destructive rewriting* (editar en el lugar erosiona). §4.2: la memoria episódica cruda como línea de base. Mide sobre todo por utilidad en la tarea, con un juez LLM para etiquetar entradas (§6.2). | El experimento "1 sueño sobre N sesiones vs. N sueños de 1 sesión" (Static vs. Stream). Separar **"nunca anotado"** de **"perdido después de estar bien"** (columna `lost after correct`). |
| Auto-Dreamer, https://arxiv.org/html/2605.20616 | §5.1: reporta éxito y "final active memory-bank size in tokens (#Tok)". §5.4, barrido de cadencia k ∈ {1, 5, 20}: "Performance is lower when consolidation is too frequent (k=1) … also drops when consolidation is too infrequent (k=20)". App. A: "Information missed by the writer cannot generally be recovered by the consolidator". | El tamaño de las notas en tokens al lado de la calidad. El barrido por sesiones leídas. La hipótesis de la omisión irrecuperable, que acá se confirma. |
| RecMem (ACL Findings 2026), https://aclanthology.org/2026.findings-acl.1619.pdf | §4.1: exactitud con juez LLM y costo de construcción en tokens. App. C.1 (θ_count): consolidar menos unidades "can better preserve fine-grained details" pero cuesta más tokens; con lotes grandes "salient details are omitted". | Reportar el costo por sueño junto a la calidad, por tamaño de lote. |
| Dreams de Managed Agents, https://platform.claude.com/docs/en/managed-agents/dreams | Un dream corrige "duplicates, contradictions, and stale entries". Lee de 1 a 100 sesiones. "Start with a small batch of sessions and scale up once you're satisfied with the curation quality". La calidad se juzga revisando a mano la salida: no da métrica. | Las categorías `duplicate` y `stale`. La comparación automática reemplaza la revisión a mano. |
| "The components of agent memory", https://www.anthropic.com/engineering/components-of-agent-memory | "Dreaming can correct memory": el sueño corrige una nota contra la transcripción. "Dreaming can build new memory representations": "the wiki grew larger than the documents themselves … Like the mapmakers in Borges's … story". "Dreaming can promote notes up the memory hierarchy": Claude Code carga "only the first 200 lines or 25 KB of `MEMORY.md`", y "the top layer … has to stay relatively small". | Los casos de control como prueba de "corrige". El tamaño de las notas contra el de las notas perfectas como indicador del mapa de Borges. |

Ninguna de las cinco fuentes mide hechos uno por uno contra una verdad. Todas miden utilidad en la tarea, a veces con un juez LLM. Acá la verdad existe (P1), así que se puede medir directo.

## 3. Análisis y elección

### 3.1 Instrumento 1: comparación línea por línea (`dreaming/quality.py`)

**Qué se compara.** Los hechos que valen después de la sesión N (`state_after(N)` sin títulos ni prosa de documentos) contra las líneas de las notas, parseadas con el formato de P3.

| Resultado | Sobre | Significa |
| --- | --- | --- |
| `correct` | hecho vivo | la línea dice su valor actual |
| `stale` | hecho vivo | la línea dice un valor que tuvo antes (deep house `dislike` después de s132) |
| `wrong` | hecho vivo | la línea dice un valor que nunca tuvo |
| `missing` | hecho vivo | ninguna línea lo nombra, o el sueño lo metió en prosa |
| `+stale` | línea | nombra un hecho que dejó de valer, con un valor que tuvo |
| `+invented` | línea | nombra un hecho conocido con un valor que nunca tuvo. Caso único observado: "dislike" sobre un like retirado. Se reporta también la cuenta indulgente (decisión de P2). |
| `+duplicate` | línea | segunda línea para un hecho ya emparejado |
| `+unmatched_supported` / `_unsupported` | línea | no nombra nada de la verdad; se separa según si ≥ 75 % de sus raíces aparecen en las transcripciones leídas hasta N |
| `+prose`, `+unparsed` | línea | campo de documento fuera del formato ("- Platform: LinkedIn"); línea fuera de todo formato |

**Cómo se empareja.** Por dominio y por las palabras del nombre, nunca por la etiqueta:

- **Raíces:** las palabras de `truth.timeline.words`, cortadas a 5 letras y sin acentos.
- **Nombres** (gustos, pendientes, eventos, metas, gastos): coinciden si un conjunto de raíces contiene al otro, o si comparten ≥ 75 %. Así "Ann Leckie's books" se empareja con "Ann Leckie" y "2025-06-01 groceries" con "2025-06-01 grocery". "2025-06-02 coffee" no se empareja con "2025-06-01 coffee".
- **Ítems de documento** (oraciones que el sueño parafrasea): basta con compartir ≥ 50 % de raíces.
- **Documentos:** cada bloque `### ` va al documento de la verdad con el que comparte más ítems, más su título. El sueño reescribe los títulos.
- **Orden de emparejamiento:** uno a uno; primero la coincidencia exacta de nombre, después la de valor (para separar dos cafés del mismo día por monto) y después los hechos vivos.
- **Paráfrasis:** se cuentan aparte los `correct` emparejados sin nombre idéntico (columna `paraphrased`). El examen pregunta con las palabras de Memora y el que responde trata las listas como cerradas, así que una paráfrasis puede volverse un "no".
- **Eventos reprogramados:** solo se compara que existan, como en el examen, por el defecto 1 de P1 (la fecha guardada no coincide con lo que dijo el usuario).

**Calibración.** Pasando `render_notes(state_after(N))` de cada persona de los tres períodos en cada sesión de examen, todo tiene que salir `correct` y nada más.

### 3.2 Instrumento 2: el examen (`dreaming/quality_run.py`)

En cada sesión N múltiplo de 7, `measure` corre tres exámenes con `answer_exam` + `grade`:

- las notas del sueño;
- las notas perfectas (el **techo**);
- notas vacías (el **piso**).

Los tokens de las notas salen de los tokens de entrada del examen menos los del examen con notas vacías. Es el conteo exacto del tokenizador, sin otra llamada.

La columna `exam without expense totals` saca las sumas de gastos. Su error de 1 centavo es el límite conocido del que responde (una decisión de P3), no del sueño.

### 3.3 Experimentos

`measure(dream, period, persona, sequences, client, run_prefix)` recibe la función de sueño. Hay tres tipos de secuencia:

- **`chain(c, through)`:** sueños después de c, 2c, …. El primero recibe `notes=""` y cada uno lee `sessions_between(todas, último, ahora)`. Mide cadenas reales.
- **`single(N)`:** un sueño desde notas vacías sobre las sesiones 1..N. Es el "1 sueño sobre N sesiones".
- **`window(k, N)`:** un sueño sobre las k sesiones antes de N, que arranca de las notas **perfectas** de N−k. Aísla el error de *un* sueño según cuántas sesiones lee, sin el error acumulado de los anteriores.

Las notas perfectas iniciales son un instrumento de medición, no una política: el sueño sigue recibiendo solo `Session` y notas. `tests/test_transcripts.py` sigue pasando.

## 4. Prueba

Modelo `claude-haiku-5-5`, thinking adaptativo, effort `medium`, presupuesto `p4b`, sueño = stub. Cada comando se vuelve a correr gratis desde `results/raw/p4b/`. Agregando `--dry-run` imprime la estimación sin gastar.

```
$ uv run pytest -q
36 passed
$ uv run python -m dreaming.quality_calibrate weekly monthly quarterly
weekly: 225 perfect notes, 14176 live facts, 0 with any line not correct
monthly: 881 perfect notes, 185267 live facts, 0 with any line not correct
quarterly: 2845 perfect notes, 1650363 live facts, 0 with any line not correct
```

En las tablas, "hechos correctos" suma todos los puntos examinados de la secuencia. "notas / perfectas" es la razón de caracteres. "examen s/totales" es el examen sin las sumas de gastos. `r0` y `r1` son dos corridas del mismo sueño (`--run-prefix p4b/stub` y `p4b/stub-r1`).

### 4.1 ¿Corrige lo que cambió? Sí: ninguna corrida deja el valor viejo

```
$ uv run python -m dreaming.quality_run weekly software_engineer window --sizes 6 --at 35 --run-prefix p4b/<stub|stub-r1|stub-r2> --watch Bonobo
- window-k6-s35 N=35 'Bonobo': absent                        (3 de 3; notas de entrada después de s29: "Bonobo (music / artists): like")
$ uv run python -m dreaming.quality_run weekly software_engineer window --sizes 2 --at 133 --run-prefix p4b/<stub|stub-r1|stub-r2> --watch "deep house"
- window-k2-s133 N=133 'deep house': ['- deep house (music / genres): like']   (3 de 3; entrada después de s131: dislike)
```

En las cadenas:

- **Bonobo** está como `like` en s21 y s28 en las cuatro cadenas (c1 y c7, r0 y r1). Desde s35 falta en tres; en la cuarta (c7 r1) pasa a `dislike`.
- **Deep house** falta en s126 y dice `like` en s133, s140 y s161 (cadena c7). El sueño de s133 leyó el dislike de s129 y el like de s132, y dejó el último.
- **Un sueño único sobre 1–133** también deja `Deep house music: like` y no menciona Bonobo.

**Lo que no hace bien:** cuando el usuario retira un gusto ("I'm just not into his music anymore"), a veces escribe `dislike` en lugar de borrarlo. Pasa con Bonobo en los sueños únicos de s35 y s42, con "Ann Leckie's recent books" en las cadenas y con "White-water rafting" en la cadena larga. Pasa también en la cadena c7 r1 desde s35. Son **todas** las líneas `+invented` medidas: 47 en total, todas en la cuenta indulgente.

### 4.2 ¿Inventa hechos? ¿Pierde los que estaban bien?

En las 10 corridas: **0 `wrong` y 0 `stale` sobre hechos vivos**. Ninguna línea afirma un valor falso de un hecho que vale.

| Corrida | +stale | +invented (todas indulgentes) | +duplicate | sin emparejar con apoyo | sin emparejar sin apoyo | +prose |
| --- | --: | --: | --: | --: | --: | --: |
| window r0 / r1 (weekly) | 1 / 0 | 2 / 3 | 1 / 1 | 20 / 28 | 0 / 0 | 23 / 11 |
| single 7–56 r0 / r1 | 0 / 2 | 4 / 3 | 0 / 2 | 37 / 39 | 1 / 2 | 36 / 36 |
| chain 1–56, c1+c7, r0 / r1 | 0 / 2 | 4 / 6 | 0 / 2 | 91 / 70 | 0 / 0 | 42 / 46 |
| chain c7 1–161 | 5 | 23 | 4 | 204 | 0 | 165 |
| monthly window | 1 | 0 | 0 | 10 | 0 | 5 |
| startup_founder chain c7 1–154 | 14 | 1 | 0 | 421 | 0 | 20 |

**"Sin emparejar con apoyo" no es invención.** Los casos revisados son cosas que el usuario dijo y la hoja de respuestas de Memora no registra:

- s5: "I'm hoping to finalize a new project proposal and clear out my inbox"
- s30: "I'm leaning more towards upbeat electronic music now"
- s11: "increase brand visibility and attract new talent"

En startup_founder son además "intereses" sacados de la charla ("Technology", "Science", "Mythology": like). Las 3 líneas "sin apoyo" son inferencias plausibles, no datos falsos: "Run a few errands", "Run errands", "Artificial intelligence: like" (el usuario dice "AI").

**Pérdidas**, en la columna `lost after correct` de las cadenas: un hecho que estaba `correct` en un examen y deja de estarlo después, con el mismo valor en la verdad. Da **1, 1, 1, 0, 1 y 1** en las seis cadenas. Son dos hechos, que listé con `measure` sobre `Comparison.fact_outcomes`:

- **"Buy groceries"** (pendiente de s9 a s33): bien en s21 y borrado en s28, en las cadenas c1 r0, c1 r1 y c7 r0. Entre esos dos exámenes está el gasto "grocery" de s24; la causa no está probada.
- **"Product demo"** (startup_founder, el 2025-06-02): bien en s49 y borrado en s56, ya pasada su fecha.

Aparte, hay erosión de vocabulario como la que describe "Useful Memories" (App. D.2), pero sin pérdida de un hecho que estuvo bien. El usuario dijo "challenging weather conditions" (s72). Las notas de la cadena c7 en s161 dicen "Cold or wet travel conditions: dislike", y el hecho cuenta como `missing` en todos los exámenes desde s77.

### 4.3 ¿Crecen las notas sin control (el mapa de Borges)? No

| Notas en la última sesión | líneas | caracteres | tokens | perfectas: líneas / caracteres |
| --- | --: | --: | --: | --: |
| weekly/software_engineer, cadena c7, s161 (23 sueños) | 175 | 8.276 | 3.260 | 144 / 7.075 |
| weekly/startup_founder, cadena c7, s154 (22 sueños) | 113 | 5.239 | 2.209 | 132 / 6.387 |
| monthly/software_engineer, ventana k=50, s609 | 428 | 20.358 | 8.148 | 428 / 20.358 |

- **Tamaño frente a las perfectas:** la razón por corrida va de 0,63 a 1,19 (columna `chars / perfect`). El exceso sale de dos cosas: prosa de documentos que el formato no lleva ("Platform", "Main message") y hechos que el usuario dijo y la verdad no registra.
- **Crecimiento:** proporcional a los hechos vivos, no a las sesiones leídas. En la cadena c7, de s56 a s161 la razón pasa de 1,14 a 1,17 (calculada sobre la tabla por punto).
- **Notas más chicas que las perfectas:** cuando el sueño pierde documentos (startup_founder 0,74; cadena c7 r1 0,63).
- **El límite de 200 líneas del post:** las notas perfectas monthly ya lo pasan (428 líneas en s609), sin que el sueño agregue nada.

### 4.4 ¿Se degradan tras muchas reescrituras? 1 sueño sobre N vs. N sueños de 1

```
$ uv run python -m dreaming.quality_run weekly software_engineer chain --cadence 1 7 --through 56 [--run-prefix p4b/stub-r1] --errors
$ uv run python -m dreaming.quality_run weekly software_engineer single --at 7 14 21 28 35 42 49 56 [--run-prefix p4b/stub-r1] --errors
```

| Sesiones 1–56, 8 exámenes (s7…s56) | sueños | costo de los sueños | hechos correctos r0 / r1 | en s56 r0 / r1 | perdidos después de estar bien | examen s/totales r0 / r1 |
| --- | --: | --: | --: | --: | --: | --: |
| 56 sueños de 1 sesión (cadena c1) | 56 | $0,036 / $0,039 | 86,5 % / 92,8 % | 37/42 / 39/42 | 1 / 1 | 92,5 % / 94,3 % |
| 8 sueños de 7 sesiones (cadena c7) | 8 | $0,011 / $0,009 | 99,1 % / **68,6 %** | 42/42 / 32/42 | 1 / 0 | 96,2 % / 90,6 % |
| 1 sueño sobre 1..N (único) | 1 por N | $0,005 / $0,006 (s56) | **100 %** / 98,2 % | 42/42 / 42/42 | — | 93,4 % / 96,2 % |

Techo 100 %, piso 28,9 %. El sueño único más largo que corrí, sobre 1–133 (89.594 tokens de entrada, $0,0135), da 84/85 hechos, lo mismo que la cadena c7 en s133.

**Lectura.** No hay degradación por reescribir en sí: lo que estaba bien casi nunca se pierde. Las cadenas pierden en el **primer encuentro**:

- **c1 r0:** el sueño que leyó solo s13 (donde el usuario dicta el email) no anotó el email. Faltan sus 4 ítems en los 7 exámenes siguientes.
- **c1 r1:** el mismo email quedó como una línea de prosa ("main message: … 340ms … 62% …").
- **c7 r1:** el sueño de s8–14 no escribió ningún documento. Se perdieron 3 documentos para siempre.

Es lo que dice Auto-Dreamer (App. A) y el *initial compression error* de "Useful Memories" (§6.4). Como coincide con "Static vs. Stream" de ese paper, el sueño único es el más estable. Pero solo existe mientras las sesiones quepan en un prompt: 161 sesiones weekly ya son ~109k tokens.

### 4.5 ¿Cómo cambia la calidad según cuántas sesiones lee un sueño? (para P5)

```
$ uv run python -m dreaming.quality_run weekly software_engineer window --sizes 1 5 20 50 --at 56 77 98 119 133 161 [--run-prefix p4b/stub-r1] --errors
$ uv run python -m dreaming.quality_run monthly software_engineer window --sizes 1 5 20 50 --at 210 420 609 --errors
```

Cada sueño arranca de las notas perfectas de N−k, así que sus errores son solo suyos.

| k (sesiones leídas) | weekly: hechos faltantes (r0 + r1, de 912) | weekly: examen s/totales (r0 + r1, de 232) | weekly: $ por sueño | monthly: faltantes (de 772) | monthly: examen (de 62) | monthly: $ por sueño |
| --: | --: | --: | --: | --: | --: | --: |
| 1 | 3 (0,3 %) | 229 (98,7 %) | $0,0014 | 0 | 62 | $0,0041 |
| 5 | 4 (0,4 %) | 229 (98,7 %) | $0,0018 | 0 | 62 | $0,0046 |
| 20 | 11 (1,2 %) | 221 (95,3 %) | $0,0035 | 3 | 62 | $0,0061 |
| 50 | 41 (4,5 %) | 219 (94,4 %) | $0,0065 | 10 | 58 | $0,0092 |

Techo weekly 99,2 %, piso 25,4 %; techo monthly 100 %, piso 24,2 %.

- **Cuánto pierde un sueño:** crece con lo que lee. Con k=50 suelta ítems de documentos que ya estaban en las notas, por ejemplo los 6 hashtags en la ventana k50 de s56. Los dólares por sueño son el costo de los sueños de la tabla dividido por 6 (weekly) o por 3 (monthly).
- **Cuánto cuesta un sueño:** no es proporcional a k. Entre 57 % y 81 % del costo es salida, porque cada sueño reescribe las notas enteras (`results/raw/p4b/...`, sumando `usage`).
- **Leer de a una sesión:** desde notas perfectas es casi perfecto. En cadena es caro: 56 sueños cuestan 3,3–4,3 veces lo que 8 sueños de 7 sesiones. Y cada sueño es una oportunidad más de omitir algo para siempre.

### 4.6 Otros fallos del stub que P4a puede corregir

| Fallo | Ejemplo | Efecto |
| --- | --- | --- |
| Borra eventos cuya fecha ya pasó | "Sprint planning meeting: 2025-06-04" desaparece en 10 de las 48 ventanas (r0 + r1). "Product demo" desaparece en startup_founder. El prompt dice "Remove facts that stopped being true". | `missing` en calendar, "unknown" en el examen |
| Parafrasea ítems de documento | "…average latency is 340ms, 140ms over target…" | El examen pregunta con el texto de Memora y el que responde dice "no" (`stale` en content) |
| Guarda documentos como pendientes o como prosa | startup_founder: "Send strategic partnership proposal email to the Chief Learning Officer…" en To-do. 2 de 8 documentos quedan como bloque. | 515 hechos de content `missing` en 22 exámenes; examen 88,8 % |
| Anota intereses de la charla como gustos | startup_founder: "Technology", "Science", "Mythology": like | Más notas; el examen no lo castiga |
| Escribe instrucciones como valor | "- trail running (travel / destination types): remove" | `unparsed` |

**El texto del examen no siempre es lo que dijo el usuario.** En s13 el usuario dice "an average latency of 340ms, which is 140ms over our target threshold". Memora guarda "Current navigation pipeline shows 340ms average latency, exceeding target threshold by 140ms". Un sueño fiel a la conversación puede perder esa pregunta. El techo de P3 no lo ve porque las notas perfectas copian el texto de Memora.

### 4.7 Las dos medidas no ven lo mismo

- **La comparación línea por línea es más densa:** 456 hechos contra 122 preguntas en el mismo barrido.
- **Ve pérdidas que el examen apenas registra.** La cadena c7 r1 perdió 3 documentos (68,6 % de hechos) y el examen bajó solo a 90,6 %: pregunta 1–3 ítems de content por sesión.
- **El examen ve lo que la comparación da por bueno:** una paráfrasis cuenta como `correct` en la comparación y puede salir "no" en el examen.

P5–P7 deberían reportar las dos.

### 4.8 Costo real

| Comando (weekly/software_engineer salvo indicación) | pagado |
| --- | --: |
| sueño único 1–35 (primera prueba) + sus 3 exámenes | $0,0051 |
| `chain --cadence 1 7 --through 56` (r0 / r1) | $0,0597 / $0,0554 |
| `window --sizes 1 5 20 50 --at 56 77 98 119 133 161` (r0 / r1) | $0,1021 / $0,0952 |
| `single --at 7 … 56 133` (r0) / `single --at 7 … 56` (r1) | $0,0402 / $0,0306 |
| `chain --cadence 7 --through 161` | $0,0622 |
| casos de control (6 sueños) | $0,0115 |
| `monthly software_engineer window --sizes 1 5 20 50 --at 210 420 609` | $0,0901 |
| `weekly startup_founder chain --cadence 7 --through 161` | $0,0821 |
| **Total `p4b`** (libro `results/spend/p4b.jsonl`) | **$0,6345 de $1,20** |

Hubo 496 llamadas. Todas terminaron con `end_turn`; la entrada más grande fue de 89.594 tokens.

### 4.9 Cómo repite P4 todo con el sueño de P4a

```bash
D="--dream dreaming.dream:dream --budget-name p4 --limit 0.80 --run-prefix p4/p4a"
uv run python -m dreaming.quality_run weekly software_engineer window --sizes 1 5 20 50 --at 56 77 98 119 133 161 $D --errors --dry-run
uv run python -m dreaming.quality_run weekly software_engineer chain --cadence 1 7 --through 56 $D --watch Bonobo --errors
uv run python -m dreaming.quality_run weekly software_engineer single --at 7 14 21 28 35 42 49 56 $D --errors
uv run python -m dreaming.quality_run weekly software_engineer chain --cadence 7 --through 161 $D --watch Bonobo "deep house" --errors
uv run python -m dreaming.quality_run weekly software_engineer window --sizes 6 --at 35 $D --watch Bonobo
uv run python -m dreaming.quality_run weekly software_engineer window --sizes 2 --at 133 $D --watch "deep house"
uv run python -m dreaming.quality_run monthly software_engineer window --sizes 1 5 20 50 --at 210 420 609 $D --errors
uv run python -m dreaming.quality_run weekly startup_founder chain --cadence 7 --through 154 $D --errors
```

- **Costo:** con el stub, una pasada de este conjunto costó unos $0,45. El sueño de P4a puede costar distinto; `--dry-run` estima antes.
- **Exámenes de referencia:** el techo y el piso se guardan en `<primer segmento del prefijo>/reference`, así que con `p4/...` se pagan una vez para todo P4.
- **Repeticiones:** otra corrida con `--run-prefix p4/p4a-r1`.

## 5. Opciones descartadas

| Opción | Por qué no |
| --- | --- |
| Juez LLM para emparejar líneas con hechos (como RecMem §4.1 o "Useful Memories" §6.2) | Gasta presupuesto en cada medición y agrega ruido de otro modelo. La verdad ya está estructurada, y un emparejador determinista calibrado da 0 errores en 3.951 notas perfectas. |
| Comparar solo por texto exacto | Falla con las etiquetas del sueño: "Ann Leckie's books", "groceries", títulos de documento reescritos. |
| Emparejar documentos por el título | El sueño inventa títulos ("Real-time video stream latency optimization" por "Excited to share how our team…"). Se empareja por los ítems, con el título como desempate. |
| `difflib.SequenceMatcher` para las paráfrasis | No lo probé. Elegí la proporción de raíces compartidas porque no depende del orden de las palabras ("average latency is 340ms" vs. "shows 340ms average latency"). |
| Solo el examen | Muy pocas preguntas: no ve la pérdida de documentos enteros (§4.7) ni separa "nunca anotado" de "perdido". |
| Contar tokens con la API de conteo | Saldría de `BudgetedClient`. La resta de tokens entre el examen con notas y el examen vacío da el número exacto gratis. |
| Cadena c1 hasta s161 | Las notas crecen y cada sueño las reescribe entera: estimé ~$0,2. La pregunta c1 vs. c7 vs. único quedó respondida hasta s56, con dos corridas. |
| Sueño único sobre 1–161 | ~109k tokens: pasa los 100k y se cobraría a precio largo. Me quedé en 1–133 (89.594 tokens). |
| Ventanas que arrancan de notas de una cadena | Mezclan el error del sueño con el acumulado. Las notas perfectas aíslan el de un sueño. |

## 6. Limitaciones y preguntas abiertas

- **Una sola función de sueño (el stub), dos corridas por configuración, tres personas.** La varianza entre corridas es grande (cadena c7: 99,1 % vs. 68,6 %). P5 necesita ≥ 2 repeticiones y ≥ 2 personas por política, o va a comparar ruido.
- **El emparejador puede fallar con paráfrasis lejanas.** "Cold or wet travel conditions" no se empareja con "challenging conditions": cuenta como `missing` + una línea sin emparejar. `missing` incluye hechos que el sueño metió en prosa. El examen tampoco los encuentra en una lista cerrada.
- **"Con apoyo en las transcripciones" es una señal débil:** solo exige que las palabras aparezcan en algún lado. Revisé los casos citados a mano; el resto no.
- **"Perdido después de estar bien" se mide solo en los exámenes (cada 7 sesiones).** Una pérdida y recuperación dentro de esas 7 no se ve.
- **Las ventanas arrancan de notas perfectas:** miden un sueño aislado, no una política desplegable. En una cadena, sus omisiones se acumulan (§4.4).
- **Pregunta para P4a:**
  - borrar un gusto retirado en lugar de escribir `dislike`;
  - no borrar eventos pasados;
  - copiar los ítems de documento con las palabras del usuario;
  - mantener los documentos como documentos.

  Con eso el stub ganaría casi todo lo que pierde acá.
- **Pregunta para P2/P7:** los ítems de content del examen usan el texto de Memora, que no siempre es el del usuario (§4.6). ¿Se acepta como límite medido, igual que el centavo de los totales?
