# P8a · Diagnóstico de las omisiones

**Resultado.** Medí, con $0 y desde el caché de P7, cada hecho que los sueños de `triggered-phrases-any` y `every-1` dejan mal (rep 0 y rep 1, 10 personas, s1–210). Cada uno abre un episodio, y el episodio carga las respuestas mal sin marcadas mientras dura.

- **De 824 respuestas mal sin marcadas en las 4 corridas, 383 (46 %) vienen de hechos que el usuario dijo y el sueño no dejó bien.** No son todas del sueño:
  - **207 son de Memora.** El usuario simulado retira el hecho enseguida y la clave lo conserva. Por ejemplo: "I just spent $23.05 on dinner" y después "I was just making a general comment"; o "I need to call my family today", "How was it?", "It went well".
  - **176 son del sueño.**
- **El sueño casi no omite por descuido: omite por criterio.** Las 176 se juntan en tres huecos de las reglas:
  - pendientes dichos al pasar: 6,6 % omitidos, 93 respuestas;
  - listas de documentos que las reglas no nombran: 12–16 % contra 0,1–0,2 % las nombradas;
  - gustos dichos sin "like" ni "dislike": 33 respuestas.

  Gastos, pasos, metas y calendario dichos sin retirar: 0–0,2 %.
- **Es sistemático.** 120 de las 176 respuestas son de hechos omitidos en las dos repeticiones. Cuando `triggered-phrases-any` omite un hecho en r0, r1 omite el mismo en el mismo sueño 21 de 25 veces.
- **La ventana no influye.** Con 1 sesión se omite el 1,6–1,8 %; con 2–3 sesiones, el 1,0 %.
- **Corrección a P7c.** En marketing_manager r1, el primer sueño no dejó afuera la cena de $20,27: la anotó el 2025-05-27, porque el usuario dijo "a Tuesday night" en una sesión de domingo. Las 29 respuestas por política siguen perdidas, pero la causa es una frase ambigua de Memora, no una omisión (§4.5).
- **Arreglo elegido: un sueño con reglas que nombran lo que se omite** (`dreaming/dream_named.py`). Cambian solo 3 reglas y se agregan 561 caracteres al prompt; el formato, las ediciones y el parser son los de P4a. Un segundo pase o un sueño con más thinking repiten el mismo criterio. Las ventanas cortas no tienen qué arreglar.
- **P8b:** $1,29 con 1 repetición y $2,58 con 2 (modelo de `final/grid.py`); con lo que P7a pagó por las mismas corridas da $1,28 y $2,56. Del caché se reusan las corridas viejas, como línea de base, y las decisiones de soñar. Ningún sueño nuevo.

| | `triggered-phrases-any` r0 / r1 | `every-1` r0 / r1 | dónde |
| --- | --: | --: | --- |
| Respuestas mal sin marcadas (de 5.638) | 176 / 232 | 211 / 205 | §4.2 |
| De hechos dichos que el sueño omite sin que nada los retire | 27 / 36 | 72 / 41 | §4.2 |
| De hechos que Memora retira (el usuario se desdice, "it went well", otro día de la semana) | 37 / 66 | 38 / 66 | §4.2 |
| De las tres clases que ataca el arreglo | 23 / 28 | 63 / 35 | §4.3 |

| Rol | Ruta |
| --- | --- |
| Tag | `p8` |
| Medición, tablas y estimación de P8b | `final/omissions.py` (`measure`, `report`, `estimate`) |
| Sueño para P8b (archivo aparte; el de P4a no cambia) | `dreaming/dream_named.py` |
| Tests (2 nuevos; 55 en total) | `tests/test_omissions.py` (1), `tests/test_dream.py` (+1) |
| Salidas (ignoradas por git; las regenera `measure` en ~75 s) | `results/p8a/`: `encounters.csv`, `episodes.csv`, `answers.csv`, `runs.csv`, `cases.txt`, `report.txt`, `estimate.txt` |
| Caché | copia de `agent-memory-dreaming-cadence-archive/results-p7-2026-11-14` en `results/`. Tope $0; el libro `p7a.jsonl` queda idéntico al del archivo (`cmp`). |

## 1. Problema

P4b, P6 y P7c coinciden en que el error principal del sueño es dejar hechos afuera, no inventarlos. En P7c, una sola cena le costó 29 respuestas a cada política en marketing_manager r1. Mejorar el sueño mejora a todas las políticas, así que P8 se pregunta cómo hacer que omita menos. P8a lo diagnostica con $0: qué se omite, por qué, cuánto cuesta y qué arreglo vale la pena pagar en P8b.

Hay que separar tres cosas que en P7 aparecen juntas:

- **Lo que el sueño omite y podía anotar.**
- **Lo que la clave de Memora pide y la conversación no respalda.** P4 ya marcó tres clases como inalcanzables (`exam/unreachable.py`); esas no cuentan acá. Pero hay otras sin marcar.
- **Lo que no es omisión:** hechos bien en la nota que el que responde no reconoce, y líneas que el sueño no borra.

## 2. Opciones consideradas

### 2.1 Cómo medir

| Pregunta | Opciones | Elegida |
| --- | --- | --- |
| Qué es una omisión | (a) una pregunta mal del examen; (b) un hecho que entró o cambió en las sesiones que leyó un sueño y que la nota no tiene bien después de ese sueño, según `compare_notes` (P4b) | (b): cada hecho cuenta una vez y se sabe qué sueño lo dejó. El examen pregunta un hecho unas 20 veces. |
| Cuánto cuesta | (a) contar hechos; (b) cargarle a cada episodio las respuestas mal sin marcadas sobre su hecho mientras dura, más una parte de los totales mal cuyo rango incluye su fecha | (b): es lo que mueve la precisión de P7 |
| Cuándo termina | el primer sueño que lo deja bien, o el siguiente cambio de Memora sobre ese hecho, o la s210 | — |
| Qué es de Memora | (a) solo lo ya marcado; (b) además, reglas deterministas sobre la transcripción: el usuario retira el hecho en los 2 turnos siguientes, dice que ya lo hizo, o nombra otro día de la semana | (b), con un test sobre 4 sesiones reales y leyendo los casos caros (`results/p8a/cases.txt`) |
| Otros errores | pérdidas (un hecho bien que un sueño posterior pierde) y borrados no aplicados | contados aparte, para que la cuenta cierre |

Cada omisión queda en `results/p8a/episodes.csv` con:

- dominio, primer encuentro o cambio, y sesión donde se dijo;
- sesiones que leyó el sueño, caracteres de la nota que leyó y hechos de su ventana;
- qué dice la nota en su lugar, cómo termina y cuántas respuestas cuesta.

### 2.2 Arreglos candidatos

| Opción | Qué es | Fuente |
| --- | --- | --- |
| A. Segundo pase de verificación | Otra llamada por sueño: con las sesiones y la nota ya editada, devolver lo que falta | Chain-of-Verification, https://arxiv.org/abs/2309.11495; Self-Refine, https://arxiv.org/abs/2303.17651; "Large Language Models Cannot Self-Correct Reasoning Yet" (ICLR 2024), https://arxiv.org/abs/2310.01798: "LLMs struggle to self-correct their responses without external feedback" |
| B. Ventanas más cortas | Soñar sobre menos sesiones por vez | Auto-Dreamer §5.4, https://arxiv.org/html/2605.20616; RecMem App. C.1, https://aclanthology.org/2026.findings-acl.1619.pdf; P4b §4.5 |
| C. Lista de hechos antes de editar | En la misma llamada, listar primero cada hecho de las sesiones y después escribir las ediciones | Mem0 §2.1, https://arxiv.org/html/2504.19413: "the complete pipeline architecture consists of two phases: extraction and update" |
| D. Más thinking | Effort `high` en lugar de `medium` | https://platform.claude.com/docs/en/build-with-claude/effort: `high` "spends as many tokens as the task needs"; P4a §3.3 |
| E. Reglas que nombran lo omitido | Cambiar las reglas del prompt donde el sueño omite por criterio, con ejemplos | "Prompting best practices", https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices: "If you want Claude to do more than the task strictly requires, explicitly request it" |
| F. Red de seguridad en código | Un detector de frases ("I need to...") y, si la nota no tiene el pendiente, una segunda llamada solo para eso | — |

## 3. Análisis y elección

### 3.1 De dónde salen las 824 respuestas mal

Tabla 1 de `report`, suma de las 4 corridas:

| causa | respuestas | qué es |
| --- | --: | --- |
| Omitido, dicho, nada lo retira | 176 | **del sueño** |
| Omitido, Memora lo retira | 207 | de la clave de Memora (§3.2) |
| Omitido, like → dislike | 94 | la regla de P4a: "ya no me gusta" borra la línea y Memora registra dislike (373 borrados contra 64 dislikes, P4a §4.2) |
| Omitido, fecha relativa | 21 | gastos "last night" ya marcados; las 21 son totales sin marcar que cubren ese día |
| Omitido, no dicho | 0 | 132 episodios (ítems con palabras que el usuario no dijo), y ninguno cuesta una respuesta sin marcar: es consistente con la marca `unsaid_item` de P4 |
| Borrado no aplicado | 47 | gustos (32) y eventos (13) que el sueño deja después de que el usuario los saca |
| Perdido después de estar bien | 43 | 22 de documentos y 21 de totales |
| Sin episodio | 236 | 220 con el hecho **bien** en la nota según `compare_notes`: lectura o paráfrasis, no omisión |

### 3.2 Lo que es de Memora: 5 hechos, 207 respuestas

Son 5 hechos (`report`, línea "Facts the conversation takes back"):

- **content_writer, cena de $23,05 (s15).** "That makes sense; I actually just spent $23.05 on dinner myself." El asistente pregunta qué comió y el usuario contesta "Oh, I was actually just making a general comment." Los 4 sueños de 1 sesión la omiten. Cuesta 112 respuestas: 28 por corrida, 8 de ellas sobre el gasto y 20 de totales.
- **marketing_manager, cena de $20,27 (s1).** "I just spent $20.27 on dinner, which felt like a complex decision for a Tuesday night", en una sesión del domingo 2025-06-01. En r0 el sueño la anota el 2025-06-01. En r1 la anota el 2025-05-27, el martes anterior. Cuesta 58 respuestas, solo en r1.
- **content_writer, "Call family" (s29).** "I actually need to call my family today." → "How was the conversation with your family?" → "It went well, thanks for asking!" Memora conserva el pendiente hasta la s142. Cuesta 28 respuestas.
- **"Plan weekend reading time" (8 respuestas).** "Oh, that's not what I meant. I was just making a general statement."
- **"Prepare board presentation" (1 respuesta).** "It's going well".

La tabla 3 lo muestra como tasa:

- **Retirados:** el sueño omite 4 de 4 gastos y 4 de 4 pendientes.
- **"Ya lo hice":** 5 de 8 pendientes.
- **Dichos sin retirar:** 2 de 1.176 gastos (0,2 %).

Un sueño fiel a la conversación no tiene por qué anotarlos. El arreglo no los persigue. Marcarlos queda como decisión abierta (§6).

### 3.3 Lo que es del sueño: tres huecos de criterio

176 respuestas en 123 episodios (tabla 2):

| dominio | omitidos / encuentros | respuestas | qué pasa |
| --- | --: | --: | --- |
| pendientes | 43 / 648 (6,6 %) | 93 | Tareas dichas al pasar, en medio de otra charla: "Speaking of keeping up, I really need to update my estate planning soon." (business_executive s34), "it reminds me that I need to plan for literary event attendance soon" (content_writer s100, omitido en las 4 corridas). La regla dice "tasks the user plans to do", y el sueño no las toma como tareas. |
| documentos | 64 / 4.436 (1,4 %) | 42 | Las listas que las reglas nombran (key points, attendees, hashtags...) se omiten 2 + 4 veces en 1.996 encuentros por política (0,1–0,2 %). Las que no nombran (`roi_projection`, `competitive_analysis`, `risk_analysis`, `inspiration_references`) se omiten 15 y 11 veces en 94 (16 % y 12 %), y cuestan 23 respuestas. Sus ítems son oraciones largas, y la regla dice "Leave out long descriptions". Los presupuestos (18 respuestas) son otra cosa (§6). |
| gustos | 14 / 760 (1,8 %) | 33 | Dichos sin "like" ni "dislike": "When I travel, I really don't care about exploring the food scene" (startup_founder s97: dislike para Memora), "I've been really enjoying listening to Debussy lately" (management_consultant s108, omitido en las 4 corridas). |
| gastos | 2 / 1.176 (0,2 %) | 8 | "almost as much as I think about my $3.37 coffee every morning" (financial_analyst s186) |

En la nota, 86 de los 123 episodios no dejan nada en su lugar: son 160 de las 176 respuestas. El resto son paráfrasis o líneas de otro hecho (16 respuestas).

**Lo que no explica las omisiones** (tabla 4, solo omisiones llanas):

- **Sesiones leídas:** con `triggered-phrases-any`, 1,61 % con 1 sesión, 1,00 % con 2–3 y 0 de 38 con 4–6. `every-1`, que siempre lee 1 sesión, omite el 1,76 %.
- **Largo de la nota:** con `triggered-phrases-any` las omisiones bajan al crecer la nota (2,31 % con menos de 2.000 caracteres, 0,54 % con más de 8.000). Con `every-1` quedan en 1,5–1,6 % desde los 2.000 caracteres.
- **Hechos en la ventana:** la tasa sube con 11–20 hechos (3,6–4,3 %), pero todas esas ventanas son de un documento: 784 encuentros y 31 omisiones, todos de documentos. Ahí están las listas no nombradas y los presupuestos.
- **Recuperación:** 4 de 138 episodios se recuperan solos, ninguno con respuestas perdidas. Ningún sueño posterior relee la sesión (P4 §6). Lo que se omite queda hasta que Memora cambia el hecho (mediana 39 sesiones) o hasta la s210 (mediana 120).

### 3.4 Sistemático, no al azar

Tabla 5 de `report`:

- **`triggered-phrases-any`:** de 25 omisiones llanas en r0, r1 repite 21 (84 %) en el mismo sueño y agrega 9 nuevas.
- **`every-1`:** repite 26 de 39 (67 %) y agrega 3.
- **Respuestas de hechos omitidos en las dos repeticiones:** 120 de 176. Por dominio: documentos 39 de 42, gustos 29 de 33, pendientes 44 de 93.

Esto decide el arreglo:

- **Un segundo pase o más thinking repiten el mismo criterio.** Un pase que lee lo mismo con las mismas reglas recupera, a lo sumo, la parte que cambia entre dos sorteos. Esa parte es el 16 % de lo omitido en las frases y el 33 % en `every-1`.
- **Lo sistemático se arregla diciendo qué cuenta.**

### 3.5 Elección: E, reglas que nombran lo omitido

`dreaming/dream_named.py` cambia 3 de las reglas de P4a y nada más. El test comprueba que el prompt es idéntico salvo `RULES`, y que una respuesta se aplica igual.

- **Pendientes:** "tasks the user plans to do, also when said in passing while talking about something else and the conversation moves on at once ("I really need to renew my passport soon", "I'm trying to learn to cook"). Having to leave the conversation, or asking you to change a document, is not a task."
- **Gustos:** "One said in other words counts: "I've been enjoying X lately" or "I really liked X" is a like; "I don't care about X" is a dislike."
- **Documentos:** "every list it has, whatever the list is called (... risks, competitive analysis, ROI projections, inspiration references...), one item per line, ... even when an item is a whole sentence. Leave out only what the document is about, its description."

**Por qué E:**

- Ataca justo lo sistemático: 93 + 33 + 23 = 149 de las 176 respuestas del sueño.
- Cuesta 561 caracteres más de prompt (≈ 224 tokens, $0,000022 por sueño, +3,6 % del costo de los sueños de las frases).
- No necesita llamadas nuevas ni cambia el formato que leen `compare_notes` y el examen.

**El riesgo medido es anotar de más** (tabla 8):

- En s1–210, 823 turnos del usuario dicen "I need to / have to / am trying to / have been meaning to". Solo 157 son una tarea que Memora agrega en esa sesión.
- Del resto, 314 son despedidas ("I actually have to go") y 252 pedidos de cambiar un documento ("I need to remove some..."). Por eso la regla los excluye con palabras.
- Quedan 100 turnos que podrían volverse pendientes que Memora no tiene.
- Una línea de más no cambia ninguna pregunta del examen, salvo que coincida con un señuelo. P8b la ve como `unmatched` en `compare_notes`.

**Techo del arreglo en el examen.** Las tres clases cuestan a `triggered-phrases-any` 23 y 28 respuestas por corrida (§4.3): 0,41 y 0,50 puntos de 5.638. Aunque el arreglo las corrija todas, la precisión sin marcadas de las frases (96,4 %) sube menos de un punto. El ruido de una diferencia emparejada entre repeticiones es de 1,2–1,6 puntos por persona (P7b §3.7). Por eso P8b tiene que juzgar con la tasa de omisión por encuentro y usar el examen solo para ver que nada empeore.

### 3.6 P8b: costo y qué se reusa

`estimate`, el modelo de `final/grid.py` (P5 §4.3) más el prompt más largo:

| | sueños | exámenes | modelo: sueños + exámenes + reglas | con lo que pagó P7a por las mismas corridas |
| --- | --: | --: | --: | --: |
| 1 repetición | 1.577 | 300 | 0,9905 + 0,2651 + 0,0354 = **$1,2910** | 0,9953 + 0,2497 + 0,0354 = $1,2804 |
| 2 repeticiones | 3.154 | 600 | **$2,5819** | $2,5593 |

**Qué se reusa del caché:**

- **Las corridas de P4a con `triggered-phrases-any` (r0 y r1)** son la línea de base. No se vuelven a pagar.
- **Las decisiones de soñar** salen iguales sin llamar a nada: el detector de frases no lee la nota. Los sueños nuevos leen las mismas ventanas que los viejos, y la comparación se empareja hecho por hecho.
- **Ningún sueño:** la clave del caché incluye el prompt (`answering/client.py`), y el prompt cambia.
- **Los exámenes** solo se reusan si la nota queda idéntica byte a byte. Puede pasar en los primeros exámenes, pero no se puede saber antes. La estimación supone que no se reusa nada, así que es un tope.

**Una o dos repeticiones.** Dos sorteos del sueño viejo, en `triggered-phrases-any`, discrepan en 13 hechos llanos (4 de r0 que r1 escribe, 9 de r1 que r0 escribe). Las tres clases que ataca el arreglo suman 16 episodios en r0 y 18 en r1. Con 1 repetición, un arreglo que corrija la mayoría se distingue de ese ruido; uno que corrija la mitad, no.

## 4. Prueba/corrida

Todo con tope $0 desde la copia del caché de P7. Si faltara una llamada, `BudgetedClient("p7a", 0.0)` lanza `BudgetExceeded` antes de llamar; no pasó.

```
$ uv run pytest -q
55 passed
$ PYTHONHASHSEED=0 uv run python -m final.omissions measure > results/p8a/measure.txt     # 40 corridas, ~75 s
$ PYTHONHASHSEED=0 uv run python -m final.omissions report > results/p8a/report.txt
$ PYTHONHASHSEED=0 uv run python -m final.omissions estimate > results/p8a/estimate.txt
$ cmp results/spend/p7a.jsonl .../agent-memory-dreaming-cadence-archive/results-p7-2026-11-14/spend/p7a.jsonl && echo "ledger unchanged"
ledger unchanged
```

Corrí `measure` y `report` dos veces desde cero, y `report.txt` salió idéntico. En las salidas de abajo, "..." marca filas recortadas.

### 4.1 Las corridas

```
$ tail -2 results/p8a/measure.txt
startup_founder every-1 r1: 256 encounters, 14 episodes, 20 unmarked wrong answers
startup_founder triggered-phrases-any r1: 256 encounters, 13 episodes, 24 unmarked wrong answers
```

### 4.2 Tabla 1: de dónde salen las respuestas mal

```
| policy | rep | unmarked asked | wrong | omitted, said, plain | omitted, said, Memora takes it back | omitted, like to dislike | omitted, relative date | omitted, not said | removal kept | lost | no episode |
| triggered-phrases-any | 0 | 5638 | 176 | 27.0 | 37.0 | 25.0 | 7.0 | 0.0 | 14.0 | 13.0 | 53.0 |
| triggered-phrases-any | 1 | 5638 | 232 | 36.0 | 66.0 | 24.0 | 7.0 | 0.0 | 13.0 | 13.0 | 73.0 |
| every-1 | 0 | 5638 | 211 | 72.0 | 38.0 | 20.0 | 7.0 | 0.0 | 11.0 | 13.0 | 50.0 |
| every-1 | 1 | 5638 | 205 | 41.0 | 66.0 | 25.0 | 0.0 | 0.0 | 9.0 | 4.0 | 60.0 |
| all | both | 22552 | 824 | 176.0 | 207.0 | 94.0 | 21.0 | 0.0 | 47.0 | 43.0 | 236.0 |

Wrong answers with no episode, by how the notes the exam read hold what the question asks: correct 220, total complete 10, missing 4, some line about it 2
```

### 4.3 Tablas 3 a 5: tasas y repetición

```
| domain | after the fact | encounters | left out | rate | answers lost |
| expense | other weekday | 4 | 2 | 50.0% | 58.0 |
| expense | plain | 1176 | 2 | 0.2% | 8.0 |
| expense | taken back | 4 | 4 | 100.0% | 112.0 |
| todo | plain | 648 | 43 | 6.6% | 93.0 |
| todo | said done | 8 | 5 | 62.5% | 29.0 |
| todo | taken back | 4 | 4 | 100.0% | 8.0 |
...
### by document list
| every-1 | budget | 128 | 16 | 12.50% |
| every-1 | named in the rules | 1996 | 2 | 0.10% |
| every-1 | not named | 94 | 15 | 15.96% |
| triggered-phrases-any | budget | 128 | 16 | 12.50% |
| triggered-phrases-any | named in the rules | 1996 | 4 | 0.20% |
| triggered-phrases-any | not named | 94 | 11 | 11.70% |

Answers lost by the plain omissions the named dream's rules aim at (to-dos, likes and dislikes, document lists the rules do not name), per run:
- triggered-phrases-any r0: 23.0 answers, 16 episodes
- triggered-phrases-any r1: 28.0 answers, 18 episodes
- every-1 r0: 63.0 answers, 29 episodes
- every-1 r1: 35.0 answers, 20 episodes

## 5. Plain omissions: random or systematic
- triggered-phrases-any: of the 25 plain omissions of r0, r1 leaves out the same fact in the same dream 21 times (84%); r1 leaves out 9 facts r0 wrote
- every-1: of the 39 plain omissions of r0, r1 leaves out the same fact in the same dream 26 times (67%); r1 leaves out 3 facts r0 wrote
- answers lost by plain omissions of a fact left out in both repetitions (by either policy): 120.0 of 176.0
```

### 4.4 Tabla 8 y estimación

```
- 823 user turns in the 10 personas: leaving the conversation 314, asking to change a document 252, names a task Memora adds in that session 157, anything else 100
- sessions with at least one: 763 of 2100
- plain to-do omissions (distinct persona, session and task) whose turn says it that way: 22 of 24

$ cat results/p8a/estimate.txt
the named dream's rules are 561 characters longer: about 224 input tokens, $0.000022 more per dream
| 0 | 1577 | 300 | 0.9905 | 0.2651 | 0.0354 | 1.2910 | 0.9953 | 0.2497 | 1.2804 |
| 1 | 1577 | 300 | 0.9905 | 0.2651 | 0.0354 | 1.2910 | 0.9912 | 0.2523 | 1.2789 |
one repetition: grid model $1.2910, from what P7a paid $1.2804; two: $2.5819 and $2.5593
```

### 4.5 Las tres preguntas del log

1. **¿Qué son las 221 respuestas que no son ni omisiones (383) ni lectura (220)?** Sale de la tabla 1:
   - like → dislike: 94;
   - borrados no aplicados: 47;
   - pérdidas después de estar bien: 43;
   - totales sin marcar que cubren un gasto "last night": 21;
   - respuestas sin episodio y sin el hecho bien en la nota según `compare_notes`: 16. Son 10 totales con todos sus gastos en la nota (error de suma o de lectura), 4 hechos que faltan sin que un sueño los haya leído y 2 con alguna línea sobre el hecho.

   Suman 94 + 47 + 43 + 21 + 16 = 221.
2. **¿Qué son las otras 8 de las 176?** Un gasto (tabla 2, "omitted, said, plain | expense | 2 | ... | 8.0"): el café de $3,37 de financial_analyst s186, "almost as much as I think about my $3.37 coffee every morning". Lo omiten `every-1` r0 y `triggered-phrases-any` r1, y cada episodio carga 4 totales.
3. **marketing_manager r1, con la corrección de la cena:**
   - **Los números no cambian.** La cena le sigue costando 29 respuestas a cada política (tabla 7: `expense: 1 | other weekday | same amount, other date: - 2025-05-27 dinner: $20.27 | 29.0`): 8 sobre el gasto y 21 totales, como en P7c. Sigue siendo "más de la mitad de la caída de las frases": 29 de 55 (P7c §4.2).
   - **Cambia la causa.** No es "un gasto dicho al pasar" que el sueño omite. Es una frase de Memora que nombra un martes en una sesión de domingo: el sueño de r0 la fecha el día de la sesión y el de r1 el martes anterior. Las dos lecturas caben en la regla "the conversation's date unless the user gives another".
   - **El ejemplo correcto de "un error de un sueño mueve una persona hasta 5,8 puntos"** sigue siendo este caso, bien descrito: una frase ambigua de Memora, leída de dos formas por dos sorteos del mismo sueño, explica 29 de 572 preguntas, o sea 5,1 de los 5,8 puntos que caen las frases en esa persona.
   - **Lo que P7c tiene que corregir** es la frase "deja afuera la cena": debe decir "la fecha el 2025-05-27". La comparación con "lo que P4 y P6 llaman omisión del sueño" tampoco aplica a este caso. El caso que sí es una omisión, también de Memora, es la cena de content_writer, y no mueve nada entre repeticiones: se omite en las cuatro corridas.

## 5. Opciones descartadas y por qué

| Opción | Por qué no | Dónde |
| --- | --- | --- |
| A. Segundo pase de verificación | El 84 % (frases) y el 67 % (`every-1`) de lo omitido en r0 se vuelve a omitir en r1 con el mismo prompt: un pase con las mismas reglas repite el criterio. Además agrega una llamada que relee sesiones y nota en cada sueño, y Huang et al. miden que, en razonamiento, sin señal externa la autocorrección no mejora y a veces empeora. | §3.4 |
| B. Ventanas más cortas | No hay qué acortar. `every-1` lee siempre 1 sesión y omite el 1,76 %. Las frases omiten el 1,61 % con 1 sesión y el 1,00 % con 2–3. | §3.3 |
| C. Lista de hechos antes de editar | Pide el mismo juicio ("¿esto es un hecho?") con el mismo criterio, y suma salida en cada sueño. Si E no alcanza, es el paso siguiente, ya con las reglas nuevas. | §3.4 |
| D. Effort `high` | En P4a dio +1 pregunta de 426 por un 15 % más. `low` pierde pendientes, pero eso solo dice que el thinking importa para los pendientes, no que más thinking cambie un criterio que se repite en las dos repeticiones. | P4a §3.3 |
| F. Red de seguridad en código | El detector de frases atrapa 22 de los 24 pendientes omitidos, pero se dispara en 763 de 2.100 sesiones, y solo 157 de sus 823 turnos son tareas de Memora. Necesita una segunda llamada en un tercio de los sueños para lo mismo que E pide en el prompt. | §4.4 |
| Arreglar en el sueño lo que Memora retira | Sería enseñarle al sueño a ignorar "I was just making a general comment" y "It went well" para acertar la clave de un simulador. Queda como decisión abierta sobre las marcas (§6). | §3.2 |
| Cambiar la regla like → dislike | P4a la eligió por 373 borrados contra 64 dislikes dichos casi igual. Invertirla convierte los 373 en `invented`. | P4a §4.2 |

## 6. Limitaciones

- **`compare_notes` empareja por palabras.**
  - Una omisión puede ser una paráfrasis que no ata: 11 episodios "other words" y 26 "same name", 16 respuestas.
  - Un hecho "bien" puede ser uno que el que responde no reconoce: las 220 respuestas sin episodio.
  - Los presupuestos en euros ("- budget: €650,000") no se leen como presupuesto. Los presupuestos suman 18 respuestas, mezcladas con un `<replace>` fallido de academic_researcher s115 y valores distintos de sales_manager s35. No los separé uno por uno.
- **"Lo retira" se decide con expresiones regulares** sobre los 2 turnos del usuario que siguen al hecho, y "dicho" con `text_support`, que exige todas sus palabras. El test fija 4 sesiones reales. Leí los casos caros de `cases.txt`, no los 138.
- **Corrección de P8b (`docs/p8b-sueno-nombrado.md` §3.3):** las 21 respuestas de "fecha relativa" son la mitad de unos totales de creative_designer que rompió el sueño, no la fecha de Memora. Al leer "$15.84 on dinner last night" (s47), el sueño reemplazó la cena real del 2025-06-01 por esa. El reparto de los totales entre los episodios que cubren su rango le cargó la mitad al episodio de la fecha, aunque esa fecha no cambia el total de la semana.
- **Una respuesta mal sobre un hecho cuenta para cada episodio abierto sobre ese hecho.** Un total se reparte entre los episodios que cubren su rango. Las pérdidas y los borrados no aplicados son secundarios acá y no los leí.
- **El arreglo no se probó.** El test solo comprueba con el stub que el prompt cambia nada más que en las reglas y que la respuesta se lee igual. No sé cuánto corrige, ni cuántos pendientes de más escribe: hay 100 turnos candidatos (§3.5).
- **El techo en el examen es chico.** Las tres clases valen 0,41–0,50 puntos por corrida en las frases, dentro del ruido del examen. P8b tiene que leerse con la tasa de omisión, emparejada hecho por hecho.
- **Muestra:** s1–210, Haiku 5.5, 2 políticas. Las omisiones tardías de academic_researcher (P7c parte 2) no están acá.

### Decisiones abiertas

1. **Cuántas repeticiones en P8b.**
   - **(a) 2 repeticiones, $2,58.** Recomendado: es lo que P7 necesitó para no equivocarse de signo (−0,6 con la rep 0 sola, −0,1 con las dos).
   - **(b) 1 repetición, $1,29.** Alcanza si el arreglo corrige la mayoría de los 16–18 episodios por corrida que ataca; si corrige la mitad, queda dentro de los 13 hechos en que discrepan dos sorteos del sueño viejo.
2. **Cómo corre P8b el sueño nuevo.** `run_policy` (`policies/engine.py`) usa siempre `dreaming.dream.dream` y el caché `p5/r<rep>`.
   - **(a) Agregar dos parámetros con valor por omisión:** la función de sueño y el prefijo del caché. Las corridas viejas no cambian ni de clave. Toca `policies/`. Recomendado.
   - **(b) No tocar `policies/`:** que el script de P8b reemplace `policies.engine.dream` al empezar. Los sueños nuevos quedarían en la misma carpeta que los viejos, distinguibles solo por su contenido.
3. **Marcar lo que Memora retira.** 5 hechos, 207 respuestas en las 4 corridas (§3.2). Hay dos opciones:
   - **(a) Dejarlo como está:** sin marcar, y P8 lo reporta aparte.
   - **(b) Agregar a `exam/unreachable.py` una clase `taken_back`.** Cubriría "just making a general comment", "it went well" después de "How was it?" y un día de la semana que no es el de la sesión. Es un cambio de criterio como la decisión (c) de P4: sube las cuentas "sin marcadas" de todas las políticas por igual. Ejemplo: la cena de content_writer s15 y sus 20 totales dejarían de contar.

   Recomiendo (a) para P8b, porque el arreglo no los toca, y decidir (b) junto con el informe final.
