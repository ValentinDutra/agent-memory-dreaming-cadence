# P4a · Qué entra y qué sale del sueño

**Resultado.** El sueño elegido (`dreaming/dream.py`):

- **Lee** las notas actuales y **todas** las transcripciones, sin filtrar. Cada sesión lleva su número, su fecha y su día de la semana, y los turnos van etiquetados `User` / `Assistant`.
- **Devuelve solo ediciones**, al estilo del `str_replace` del memory tool: `<append section=…>` agrega líneas al final de una sección, y `<replace><old>…</old><new>…</new></replace>` cambia o borra líneas. El código las aplica y entrega las notas completas en el formato de P3.
- **Usa thinking adaptativo con effort `medium`**, la configuración por omisión de `BudgetedClient`.
- **Hace una llamada por sueño.**

En calidad, editar y reescribir empatan dentro del ruido. Editar cuesta 1,5–1,65× menos en las cadenas medidas, y hasta 4,6× menos con las notas grandes de monthly. Sin thinking, el sueño se rompe.

| Medición (examen de P2/P3 sobre las notas del sueño, cadencia 7) | editar (elegido) | reescribir |
| --- | --: | --: |
| weekly/software_engineer, 23 sueños, 426 preguntas (techo con notas perfectas: 97,7 %) | **93,7 %** (repetición: 94,1 %) | 93,0 % |
| monthly/software_engineer, s1–210, 30 sueños, 561 preguntas | **95,5 %** | 96,1 % |
| weekly/marketing_manager, 22 sueños, 370 preguntas | **96,5 %** | — |
| Costo de los sueños: weekly / monthly s1–210 | **$0,0307 / $0,0432** | $0,0466 / $0,0713 |
| Tokens de salida: weekly / monthly s1–210 | **26.931 / 40.478** | 60.438 / 98.140 |
| Un sueño de 1 sesión sobre notas monthly de 20k caracteres | **$0,0011** (157 de salida) | $0,0051 (8.255 de salida) |
| Ediciones que no aplicaron (effort `medium`) | 1 de 106 sueños | — |

**Modelo de costo para P6** (ajustado por mínimos cuadrados en §4.4). S son las sesiones leídas y C los caracteres de las notas de entrada.

- Entrada ≈ 1.100 + 0,40·C + 615·S tokens.
- Salida ≈ 720 + 75·S tokens (250 + 65·S en el primer sueño, con notas vacías).
- En dólares: **≈ $0,00047 + $0,00004 por cada 1.000 caracteres de notas + $0,0001 por sesión leída**.
- Los prompts quedan por debajo de 100k tokens mientras S ≤ (98.900 − 0,40·C)/615: unas 145 sesiones con notas monthly.

| Rol | Ruta |
| --- | --- |
| Tag | `p4` |
| Sueño elegido (ediciones) | `dreaming/dream.py` (`dream`, `dream_with_failures`, `parse_edits`, `apply_edits`, `canonical`) |
| Variante descartada (reescritura) | `dreaming/dream_rewrite.py` |
| Medición (CLI: `chain`, `scale`, `speakers`, `preference-changes`) | `dreaming/dream_compare.py` |
| Tests (2 nuevos; 34 con los demás) | `tests/test_dream.py`; `tests/test_transcripts.py` sigue pasando con este `dream` |

Uso, igual que el stub:

```python
from answering.client import BudgetedClient
from dreaming.dream import dream
from dreaming.transcripts import load_transcripts, sessions_between

client = BudgetedClient("p5", limit_dollars=2.00)   # thinking adaptativo, effort medium: obligatorio (§3.3)
sessions = load_transcripts("monthly", "software_engineer")
result = dream(notes, sessions_between(sessions, last_dream, now), client, run="p5/cadence-20/monthly/software_engineer")
notes = result.notes                                  # completas, en el formato de P3
```

## 1. Problema

Un sueño recibe las notas y las sesiones desde el último sueño, y devuelve notas nuevas. Hay que decidir tres cosas:

- **Qué lee:** todo, o un filtro.
- **Qué escribe:** las notas enteras, o solo los cambios.
- **Cuánto piensa.**

Cada decisión mueve el costo, y cada una puede romper la memoria.

Ejemplo real, weekly/software_engineer, sesión 30 (2025-06-02):

```
User: Speaking of interesting characteristics, I used to really like Bonobo, but I'm just not into his music anymore. ...
Assistant: That's totally understandable! What kind of music are you finding yourself drawn to these days ...
User: I think I just outgrew his style; I'm leaning more towards upbeat electronic music now.
User: That sounds like a fun shift in taste! It's always interesting how preferences evolve.     <- es el asistente (defecto 3 de P1)
```

Un sueño correcto borra la línea `- Bonobo (music / artists): like` y no toca las demás. Tres riesgos:

- **Filtrar lo que lee.** Si el sueño lee solo los turnos del usuario, el último turno lo engaña (defecto 3). Peor: en weekly/marketing_manager s86, lo único que nombra a Taylor Swift es la pregunta del asistente, "Have your preferences in artists changed recently, maybe from Taylor Swift to someone like SZA?", y el usuario contesta "I'm really into SZA these days" (defecto 4). Sin los turnos del asistente, Taylor Swift no se borra nunca.
- **Reescribir.** Las notas monthly llegan a ~20k caracteres (~8k tokens, §4.4). Una reescritura las paga enteras como salida en cada sueño, aunque la sesión nueva solo borre una línea. Además, "Useful Memories Become Faulty" mide que reescribir en el lugar erosiona la memoria (§2).
- **Editar.** Una edición cuyo texto viejo no coincide con las notas no se aplica. Si el sueño la da por hecha, el hecho viejo queda.

## 2. Opciones investigadas

| Fuente | Qué dice (sección) | Qué se tomó |
| --- | --- | --- |
| Dreams de Managed Agents, https://platform.claude.com/docs/en/managed-agents/dreams | § "How it works": un sueño toma un memory store y de 1 a 100 sesiones, y produce un store nuevo con "duplicates merged, stale or contradicted entries replaced with the latest value". § "Steer with instructions": "The pipeline is a synthesis pass over the inputs, not an editor applied to the text of the store"; las ediciones puntuales van por la Memory Stores API. § "Billing": "Cost scales roughly linearly with the number and length of input sessions." | El sueño de Anthropic **reescribe** (síntesis) y su costo crece lineal con las sesiones. Lo lineal lo medimos (§4.4). La reescritura es una de las dos opciones comparadas. |
| Cookbook "Dreaming with a dynamic workflow", https://platform.claude.com/cookbook/managed-agents-cma-dreaming-with-a-dynamic-workflow | § 1 "Load your sessions": transcripción en texto plano con etiquetas por hablante (`USER:`, `AGENT:`…). `analyzer_system.md`: "Read your assigned file IN FULL"; "For shared index files, add your entries with a targeted edit; don't rewrite the whole file"; "Check what's already there first, then add what's new". § "Facts go stale": "An early fact must be dated and superseded, not copied". El organizador corre en Claude Haiku 5.5. | **Leer la transcripción entera**, en texto plano y con hablantes. **Editar en lugar de reescribir.** Cada sesión lleva su fecha. |
| Memory tool, https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool | § `str_replace`: `old_str` tiene que aparecer "verbatim" y una sola vez; si no, "No replacement was performed" o "Multiple occurrences of old_str … Please ensure it is unique". `new_str` es opcional: sin él, borra. § `insert`: inserta después de un número de línea. | La semántica de `<replace>`: líneas exactas, únicas, y `<new>` vacío para borrar. `insert` por número de línea se reemplazó por `<append section>`, porque los números de línea se corren dentro de una misma respuesta. |
| Sleep-time compute, https://arxiv.org/abs/2504.13171 (HTML v1) | §3: el paso offline reescribe el contexto, S(c) → c′. App. K: `rethink_memory` reemplaza el contexto entero. §5.2: subir el esfuerzo de razonamiento en el paso offline mejora la precisión hasta 18 % (Stateful AIME). §5.3: amortizar c′ entre 10 consultas baja 2,5× el costo por consulta. | Pensar durante el sueño. Lo medimos: sin thinking cae a 70,4 % (§4.3). |
| Auto-Dreamer, https://arxiv.org/html/2605.20616 | §4.1: reescribe solo una región, B⋆ = (B∖R) ∪ C_θ(R, T_R); lo que está fuera de R no se toca. §5.4 y App. B.2: con k = 1 sesión por consolidación hay "insufficient cross-session evidence"; con k = 20, una región "larger and noisier … strains its context and tool-use budget". | Tocar solo lo que cambia. Medimos el costo y la calidad contra el tamaño del lote (1–50 sesiones, §4.4); la frecuencia es de P5. |
| RecMem, https://aclanthology.org/2026.findings-acl.1619.pdf | §3.3: actualiza en forma incremental ("merge-first"), no reescribe. Tabla 1 (LoCoMo, GPT-4.1-mini): 193,2K tokens de construcción contra 1.520,8K de Mem0 (−87,3 %). App. C.1: un cúmulo más grande "increases summarization difficulty", y se omiten detalles. | Incremental es más barato. Cuidado con los lotes grandes: lo medimos con 50 sesiones (20–21/21, §4.4). |
| Useful Memories Become Faulty, https://arxiv.org/html/2605.12978v2 | Tabla 5 y §6.4: "in-place rewriting is the most damaging single step"; prohibir la reescritura en el lugar recupera +6,8 puntos, y podar sin reescribir ayuda ("pruning … actually helps"). App. G.2: en un paso, 50 ítems (48.506 caracteres) colapsan en 1 ítem de 1.960. | Riesgo concreto de la reescritura. Lo medimos como "deriva" (§4.2). |

## 3. Análisis y elección

### 3.1 Qué ve el sueño: todo, en orden, con hablantes y fecha

| Opción | Ahorro | Qué rompe | Decisión |
| --- | --- | --- | --- |
| **Transcripción completa** | — | — | **Elegida** |
| Solo turnos del usuario | El asistente escribe el 62 % de los caracteres en las 5 personas medidas (§4.5): ≈ 380 de los ≈ 615 tokens por sesión, **$0,000038 por sesión**. Una persona monthly entera (628 sesiones) ahorra ≈ $0,024 por política. | El defecto 4 (14 casos en w+m+q, P1): el ítem viejo solo lo nombra el asistente. Con todo el texto, Taylor Swift se borra bien (s91 → `unknown`, `correct`, §4.2). El defecto 3 tampoco se arregla filtrando, porque el turno mal etiquetado dice `user_agent`. | Descartada: ahorra centavos y pierde hechos. |
| Descartar la charla trivial | Hasta ~1/3 de las sesiones no cambia nada (1.032 de 1.551 sí cambian algo en weekly, P1). | Hace falta un modelo o una heurística para saber cuáles. P2 midió que las frases de cambio no alcanzan: las metas cambian sin decirlo (8/66 en monthly). | Descartada: la entrada es la parte barata (§3.4). |

**Presentación.** Cada sesión va en `<session number="30" date="2025-06-02" weekday="Monday">`, con turnos `User: …` / `Assistant: …`, en orden de `session_id`.

- **El día de la semana** se deriva de la fecha, así que no rompe la regla anti-trampa. Hace falta porque el usuario dice "next Tuesday" (weekly/software_engineer s87, un miércoles).
- **`User` / `Assistant`** reemplazan a `user_agent` / `ai_agent`, que suenan a dos agentes.
- **El prompt avisa dos cosas:** que las etiquetas a veces están mal (defecto 3), y que las preguntas del asistente dan contexto a la respuesta (defecto 4), con un ejemplo inventado ("from X to Y").

### 3.2 Qué devuelve: ediciones aplicadas por código

Las dos variantes usan el mismo prompt (formato, reglas y transcripciones). Solo cambia el pedido final.

- **Calidad: empate.** Weekly: 399 y 401 (dos corridas) contra 396 de 426. Monthly s1–210: 536 contra 539 de 561. El ruido medido entre dos corridas iguales es de 2 preguntas (§4.1).
- **Deriva: ninguna en weekly, poca en monthly.** Contamos las líneas que desaparecen o cambian de un sueño al siguiente y las comparamos con los hechos que de verdad cambiaron o se fueron en esos mismos tramos. Weekly: 28 = 28 en las dos variantes, así que a este tamaño Haiku no erosiona las notas al reescribir. Monthly s1–210: editar 49 = 49; reescribir 53 contra 49, o sea 4 líneas perdidas o reescritas sin motivo.
- **Costo: decide.** La salida de una reescritura crece con el tamaño de las notas: 8.414 + 64·S tokens con 20k caracteres. La de una edición, con lo que cambió: 724 + 74·S. Con un sueño por sesión sobre notas monthly, reescribir cuesta 4,6× ($0,0051 contra $0,0011). Lo que separa a las cadencias (P5) es justamente el costo fijo de cada sueño, y reescribir lo multiplica.
- **Ediciones que fallan:** 1 de 106 sueños con effort `medium` (todas las corridas de §4). Fue en monthly s7: un `<replace>` sobre una línea de Sandra Bullock que nunca se había escrito; inofensivo. `dream_with_failures` las devuelve, y `dream_compare` las imprime.

**Cómo se aplican** (`apply_edits`):

1. Las ediciones se aplican en orden.
2. `<replace>` compara líneas enteras sin espacios alrededor. Si el bloque viejo no aparece exactamente una vez, la edición no se aplica y se reporta, como el `str_replace` del memory tool.
3. `<append>` agrega al final de la sección, y la crea si no existe.
4. `canonical` deja las secciones en el orden de P3, escribe `- (none)` exactamente cuando una lista cerrada queda vacía, y deja una línea en blanco antes de cada documento. Para las 161 notas perfectas de weekly/software_engineer, `canonical(render_notes(x)) == render_notes(x)`; el test 2 lo usa.

### 3.3 Thinking y effort: adaptativo, `medium`

| Configuración del sueño (editar, weekly, cadencia 7) | Correctas | Tokens de salida | Costo | Ediciones fallidas |
| --- | --: | --: | --: | --: |
| Sin thinking | 300/426 (70,4 %) | 7.913 | $0,0207 | 6 |
| Adaptativo, `low` | 390/426 (91,5 %) | 20.781 | $0,0275 | 1 |
| **Adaptativo, `medium`** | **399/426 (93,7 %)**; repetición 401 (94,1 %) | 26.931 | $0,0307 | 0 |
| Adaptativo, `high` | 400/426 (93,9 %) | 36.678 | $0,0354 | 0 |

- **Sin thinking**, el sueño escribe `<old>` que no existen y deja hechos afuera. Por ejemplo, "Refactor legacy code" (s1) y la meta de 8.000 pasos (s16) no están en ninguna de sus notas de la s7 a la s35; con thinking sí están. Los pendientes quedan `stale` 26 veces.
- **`low`** pierde pendientes: todo `stale` 11, contra 1 con `medium`. 9 son pendientes vigentes que no están en las notas ("Optimize database queries" en 7 exámenes, "Schedule car maintenance" en 2), y 2 son pendientes cumplidos que no borró.
- **`high`** gana 1 pregunta, dentro del ruido, por un 15 % más.

`medium` es además el valor por omisión de `BudgetedClient`, así que P5 no tiene que configurar nada.

### 3.4 Dónde está el costo

Con los precios de Haiku 5.5 ($0,10 / $0,50 por millón):

| Parte del sueño | Cuánto pesa | Costo |
| --- | --- | --- |
| Parte fija (prompt ≈ 1.100 tokens de entrada; salida y thinking ≈ 720 tokens) | — | $0,00047 por sueño |
| Releer las notas | ≈ 0,40 tokens por carácter: 20k caracteres son 8k tokens | $0,0008 por sueño |
| Cada sesión leída | ≈ 615 tokens de entrada y ≈ 75 de salida | $0,0001 |

Lo que crece con la cadencia (sueños más seguidos) es la parte fija más la relectura de las notas. Lo que se paga por sesión es igual en cualquier cadencia.

**Proyección, no medida:** monthly, 628 sesiones, notas de 10k caracteres en promedio. Cada sueño cuesta $0,00087 sin contar las sesiones, y las sesiones suman 628 × $0,0001 = $0,062 en total.

| Cadencia | Sueños | Costo total | Con reescritura |
| --: | --: | --: | --: |
| 1 | 628 | 628 × 0,00087 + 0,062 ≈ **$0,61** | ≈ $1,90 (+ 4.100 tokens de salida por sueño ≈ +$0,002) |
| 5 | 126 | ≈ $0,17 | — |
| 20 | 31 | ≈ $0,09 | — |
| 50 | 13 | ≈ $0,07 | — |

## 4. Prueba

Todo corrió con `claude-haiku-5-5`, presupuesto `p4a` y temperatura por omisión. Los exámenes usan P3 tal cual: `answer_exam` con el cliente por omisión (adaptativo, `medium`) y `grade`. Las respuestas crudas están en `results/raw/p4a/…` y las notas de cada sueño en `results/p4a/notes/…`. Cada comando se vuelve a correr gratis desde el caché: al volver a correrlos para este informe, el gasto no se movió de $0,5669.

```
$ uv run pytest -q
..................................                                       [100%]
34 passed
```

### 4.1 Editar contra reescribir, weekly/software_engineer, cadencia 7

```
$ uv run python -m dreaming.dream_compare chain edits weekly software_engineer --cadence 7 --errors
dream s7: 7 sessions, 5467 in, 707 out, $0.0009, 0 failed edits, 313 chars
...
dream s161: 7 sessions, 8295 in, 1524 out, $0.0016, 0 failed edits, 7232 chars
| **total** | 426 | 399 | 12 | 3 | 12 | 0 |  correct 93.7%
dreams: 23, 171962 input and 26931 output tokens, $0.0307, 0 failed edits.
drift: 28 note lines dropped or reworded from one dream to the next; 28 facts changed or went away in the truth over the same spans

$ uv run python -m dreaming.dream_compare chain edits weekly software_engineer --cadence 7 --repeat 1 --errors
| **total** | 426 | 401 | 13 | 5 | 7 | 0 |  correct 94.1%
dreams: 23, 168934 input and 27963 output tokens, $0.0309, 0 failed edits.

$ uv run python -m dreaming.dream_compare chain rewrite weekly software_engineer --cadence 7 --errors
| **total** | 426 | 396 | 14 | 5 | 11 | 0 |  correct 93.0%
dreams: 23, 163942 input and 60438 output tokens, $0.0466, 0 failed edits.
drift: 28 note lines dropped or reworded from one dream to the next; 28 facts changed or went away in the truth over the same spans
```

| weekly, por dominio | editar | editar (repetición) | reescribir | techo (P3) |
| --- | --: | --: | --: | --: |
| preference | 76/80 | 75/80 | 75/80 | 80/80 |
| todo | 60/61 | 61/61 | 60/61 | 61/61 |
| calendar | 46/46 | 46/46 | 46/46 | 46/46 |
| goal | 26/26 | 26/26 | 26/26 | 26/26 |
| content | 66/77 | 64/77 | 64/77 | 77/77 |
| expense | 64/75 | 68/75 | 64/75 | 65/75 |
| steps | 61/61 | 61/61 | 61/61 | 61/61 |

**Casos de control.** Con las dos variantes y en las dos corridas:

- Bonobo en la s35: `unknown` (`correct`).
- deep house: `like` en la s133 (`new`) y en las s140, s154 y s161.
- Mechanic visit: `2025-06-15` en la s84 (`new`) y "yes" de la s112 a la s161.

**De dónde vienen los errores** (los de editar, `--errors`):

- **expense `invented`: 11 de 11.** Es el error de 1 centavo del que responde (techo: 10). No es de memoria.
- **13 de los 16 restantes son comunes a las dos variantes:**
  - **9 son ítems de documentos** que las notas tienen con otras palabras, o que el sueño partió en dos líneas. En los que revisé, el texto de la verdad no es el que dijo el usuario. El examen pregunta por "Automated CI/CD pipeline with comprehensive test coverage above 85%", y el usuario dijo "an automated CI/CD pipeline". Pregunta por "Requires dedicated DevOps support and comprehensive API documentation for third-party integrations", y el usuario dijo "the need for dedicated DevOps support and comprehensive API documentation" (s118).
  - **3 son "challenging conditions"** (travel climate), que no aparece en ninguna transcripción de la persona.
  - **1 es un error del sueño:** el usuario dice "I just fixed that critical bug" en la s114, y "Fix critical bug" sigue en los pendientes en la s119.

  Ninguna variante de entrada o salida arregla los 12 primeros. Le corresponde a P4b separar lo que el texto no dice.
- **Errores propios de reescribir:** faltan `#VideoEngineering` (s14 y s28) y "Embedded Software Team" (s21), que editar sí tiene. Son hechos que nunca escribió, no hechos que perdió: la deriva da 28 = 28.

### 4.2 Monthly y otra persona weekly

```
$ uv run python -m dreaming.dream_compare chain edits monthly software_engineer --cadence 7 --through 210 --errors
| **total** | 561 | 536 | 10 | 13 | 2 | 0 |  correct 95.5%
dreams: 30, 229368 input and 40478 output tokens, $0.0432, 1 failed edits.
drift: 49 note lines dropped or reworded from one dream to the next; 49 facts changed or went away in the truth over the same spans

$ uv run python -m dreaming.dream_compare chain rewrite monthly software_engineer --cadence 7 --through 210 --errors
| **total** | 561 | 539 | 8 | 12 | 2 | 0 |  correct 96.1%
dreams: 30, 222161 input and 98140 output tokens, $0.0713, 0 failed edits.
drift: 53 note lines dropped or reworded from one dream to the next; 49 facts changed or went away in the truth over the same spans

$ uv run python -m dreaming.dream_compare chain edits weekly marketing_manager --cadence 7 --errors
    s91 recent_change: Does the user currently like or dislike 'Taylor Swift' (music artist)?... -> unknown (correct)
    error s98 preference recent_change: Does the user currently like or dislike 'SZA' (music artist)? ... -> unknown (expected dislike, missing)
| **total** | 370 | 357 | 10 | 2 | 1 | 0 |  correct 96.5%
dreams: 22, 154393 input and 24306 output tokens, $0.0276, 0 failed edits.
```

**Sandra Bullock** (monthly, s7) es el error más repetido: 8 de los 25 errores de editar y 8 de los 22 de reescribir. El usuario dice "I used to like her, but now I find her roles a bit repetitive and I'm just not as keen on her movies anymore", y la verdad registra like → dislike. La regla del prompt ("si deja de gustarle sin decir que no le gusta, borrá la línea") la convierte en `unknown`. SZA en marketing_manager s98 es el mismo caso.

La regla está bien elegida para la mayoría:

```
$ uv run python -m dreaming.dream_compare preference-changes weekly
weekly: {'like removed': 89, 'like -> dislike': 18}
$ uv run python -m dreaming.dream_compare preference-changes monthly
monthly: {'like removed': 284, 'like -> dislike': 46}
```

Son 373 borrados contra 64 cambios a dislike, y el texto de Memora los dice casi igual ("not into his music anymore" contra "not as keen on her movies anymore").

### 4.3 Thinking y effort

```
$ uv run python -m dreaming.dream_compare --thinking disabled --effort medium chain edits weekly software_engineer --cadence 7 --errors
| **total** | 426 | 300 | 41 | 52 | 33 | 0 |  correct 70.4%
dreams: 23, 167768 input and 7913 output tokens, $0.0207, 6 failed edits.
$ uv run python -m dreaming.dream_compare --thinking adaptive --effort low chain edits weekly software_engineer --cadence 7 --errors
| **total** | 426 | 390 | 18 | 6 | 12 | 0 |  correct 91.5%
dreams: 23, 171153 input and 20781 output tokens, $0.0275, 1 failed edits.
$ uv run python -m dreaming.dream_compare --thinking adaptive --effort high chain edits weekly software_engineer --cadence 7 --errors
| **total** | 426 | 400 | 11 | 5 | 10 | 0 |  correct 93.9%
dreams: 23, 170988 input and 36678 output tokens, $0.0354, 0 failed edits.
```

Ejemplo de edición fallida sin thinking (sueño de la s49): `Replace(old=('- (none)', '## Calendar', '- (none)'), …)`. El bloque viejo no existe en las notas, así que el pendiente nuevo "Set up home network security" no entró.

### 4.4 Costo contra sesiones leídas y tamaño de las notas

Un sueño sobre las últimas S sesiones antes de la s602 de monthly/software_engineer:

- **Notas vacías:** primer sueño.
- **Notas perfectas:** `render_notes(state_after(602 − S))`, de 19.823 a 20.235 caracteres, como si el sueño anterior hubiera sido perfecto. En este caso se toma además el examen de la s602.

```
$ uv run python -m dreaming.dream_compare scale monthly software_engineer --at 602
```

| variante | notas | sesiones | caracteres de notas | entrada | salida | costo | ediciones fallidas | examen s602 |
| --- | --- | --: | --: | --: | --: | --: | --: | --: |
| editar | vacías | 1 | 0 | 1.724 | 144 | $0,0002 | 0 | — |
| editar | vacías | 5 | 0 | 4.488 | 696 | $0,0008 | 0 | — |
| editar | vacías | 20 | 0 | 12.992 | 1.609 | $0,0021 | 0 | — |
| editar | vacías | 50 | 0 | 32.049 | 3.356 | $0,0049 | 0 | — |
| editar | perfectas | 1 | 20.235 | 9.803 | 157 | $0,0011 | 0 | 21/21 |
| editar | perfectas | 5 | 20.152 | 12.528 | 1.286 | $0,0019 | 0 | 20/21 |
| editar | perfectas | 20 | 19.915 | 20.941 | 2.958 | $0,0036 | 0 | 21/21 |
| editar | perfectas | 50 | 19.823 | 39.908 | 4.104 | $0,0060 | 0 | 20/21 |
| reescribir | vacías | 1 | 0 | 1.415 | 144 | $0,0002 | 0 | — |
| reescribir | vacías | 5 | 0 | 4.179 | 769 | $0,0008 | 0 | — |
| reescribir | vacías | 20 | 0 | 12.683 | 1.313 | $0,0019 | 0 | — |
| reescribir | vacías | 50 | 0 | 31.740 | 2.807 | $0,0046 | 0 | — |
| reescribir | perfectas | 1 | 20.235 | 9.494 | 8.255 | $0,0051 | 0 | 21/21 |
| reescribir | perfectas | 5 | 20.152 | 12.219 | 8.955 | $0,0057 | 0 | 20/21 |
| reescribir | perfectas | 20 | 19.915 | 20.632 | 9.722 | $0,0069 | 0 | 20/21 |
| reescribir | perfectas | 50 | 19.823 | 39.599 | 11.573 | $0,0097 | 0 | 20/21 |

```
edits, empty notes: input = 1113 + 616*sessions, output = 255 + 63*sessions
edits, perfect notes: input = 9176 + 612*sessions, output = 724 + 74*sessions
edits: each character of notes adds 0.398 input tokens
rewrite, empty notes: input = 804 + 616*sessions, output = 297 + 51*sessions
rewrite, perfect notes: input = 8868 + 612*sessions, output = 8414 + 64*sessions
rewrite: each character of notes adds 0.398 input tokens
```

**Verificación del modelo contra la cadena weekly de editar:**

- Medido: 23 sueños de 7 sesiones, $0,0307, o sea **$0,00133 por sueño**.
- Las notas de entrada promediaron ≈ 5.200 caracteres. Sale de la entrada media: 171.962/23 = 7.477 tokens = 1.100 + 0,40·C + 615·7.
- El modelo da $0,00047 + 5,2 × $0,00004 + 7 × $0,0001 = **$0,00138**, un 4 % más que lo medido.

Un lote de 50 sesiones no pierde calidad: 20/21 o 21/21 con las dos variantes.

### 4.5 Cuánto escribe cada hablante

```
$ uv run python -m dreaming.dream_compare speakers weekly software_engineer marketing_manager
weekly/software_engineer: 163 sessions, 295743 characters, user_agent 37.4%, ai_agent 62.6%
weekly/marketing_manager: 156 sessions, 260551 characters, user_agent 37.9%, ai_agent 62.1%
$ uv run python -m dreaming.dream_compare speakers monthly software_engineer academic_researcher startup_founder
monthly/software_engineer: 628 sessions, 1085274 characters, user_agent 37.8%, ai_agent 62.2%
monthly/academic_researcher: 619 sessions, 1048348 characters, user_agent 38.0%, ai_agent 62.0%
monthly/startup_founder: 606 sessions, 1034897 characters, user_agent 38.2%, ai_agent 61.8%
```

### 4.6 Costo real

| Corrida | Costo |
| --- | --: |
| editar, weekly/software_engineer, cadencia 7 (23 sueños + 23 exámenes) | $0,0475 |
| reescribir, ídem | $0,0645 |
| grilla de costo monthly (16 sueños + 8 exámenes) | $0,0670 |
| editar sin thinking / `low` / `high` (weekly) | $0,0383 / $0,0447 / $0,0525 |
| editar, repetición (weekly) | $0,0485 |
| editar / reescribir, monthly s1–210 | $0,0667 / $0,0950 |
| editar, weekly/marketing_manager | $0,0422 |
| **Total (`results/spend/p4a.jsonl`)** | **$0,5669 de $1,00** |

Los exámenes cuestan entre $0,0006 y $0,0010 cada uno. El costo por corrida incluye los exámenes. Las partes salen de las diferencias del libro que imprime cada comando ("p4a spent $A -> $B").

## 5. Opciones descartadas y por qué

| Opción | Por qué no | Dónde |
| --- | --- | --- |
| Reescribir las notas enteras (el stub, y el pipeline de Dreams) | Misma calidad dentro del ruido. Paga las notas enteras como salida en cada sueño: 1,5× en weekly, 1,65× en monthly s1–210, 4,6× con un sueño de 1 sesión sobre notas de 20k caracteres. En monthly perdió o reescribió 4 líneas sin motivo (53 contra 49). | §3.2, §4.1, §4.2, §4.4 |
| Leer solo los turnos del usuario | Ahorra ≈ $0,000038 por sesión. Pierde el ítem viejo del defecto 4, que el sueño completo resuelve (Taylor Swift en la s91). | §3.1, §4.2 |
| Filtrar la charla trivial | Necesita un modelo o una heurística, y P2 mostró que las frases de cambio no alcanzan (metas 8/66). Ahorraría solo en la parte barata. | §3.1 |
| Sin thinking | 70,4 %; 6 ediciones fallidas que dejan afuera hechos nuevos, y hechos dichos que nunca escribe | §3.3, §4.3 |
| Effort `low` | 91,5 %; pierde pendientes vigentes y no borra cumplidos (todo `stale` 11) | §3.3 |
| Effort `high` | +1 pregunta (dentro del ruido) por un 15 % más | §3.3 |
| `insert` por número de línea (memory tool) | Los números se corren con cada edición de la misma respuesta. `<append section>` no depende de ellos. | §2 |
| El memory tool real (tool use, varios turnos) | Cada turno reenvía las transcripciones (el cookbook lo marca como "most of what this run costs"), y `BudgetedClient` no maneja herramientas. Una sola respuesta con todas las ediciones cuesta una llamada. | §2 |
| Más de una llamada por sueño (extraer y después integrar) | Con una llamada, la calidad ya queda a 4 puntos del techo, y lo que falta es mayormente texto que no dice lo que dice la verdad (§4.1). La interfaz pide una salvo números que muestren lo contrario. | §4.1 |
| Reintentar las ediciones fallidas | 1 en 76 sueños con thinking, inofensiva | §3.2 |
| "Ya no le gusta" → dislike | Hay 373 borrados contra 64 cambios a dislike; esa regla convertiría Bonobo en `invented` | §4.2 |

## 6. Limitaciones y preguntas abiertas

- **La señal de calidad es el examen, no una comparación contra la verdad.** Son 426–561 preguntas por cadena, con un ruido de unas 2. Alcanza para descartar "sin thinking" y `low`, pero no separa editar de reescribir: ese empate se decidió por costo. La medición rigurosa es de P4b.
- **Muestra.** Weekly: 2 personas. Monthly: 1 persona hasta la s210, más la grilla de la s602. Quarterly no se midió. La deriva de la reescritura podría crecer con notas más grandes o con más sueños encadenados: solo se midió hasta 30 sueños.
- **Lo que el sueño no puede arreglar:**
  - Ítems de documentos que el usuario parafrasea (el examen pregunta el texto de Memora).
  - Hechos que no aparecen en ninguna transcripción ("challenging conditions").
  - like → dislike dicho igual que un borrado (Sandra Bullock, SZA).

  Le corresponde a P4b medir cuántos errores son de este tipo, para que P7 no los cargue a la cadencia.
- **Etiquetas propias.** El sueño escribe "Upbeat electronic music (music / genres)" (defecto 2: el usuario lo dijo, la verdad no lo registra) y "(films / genres)" donde P3 dice "movies". El examen no lo penaliza porque pregunta por el ítem.
- **Ediciones fallidas.** `dream()` respeta el contrato y no las reporta; `dream_with_failures` sí. Si P5 quiere contarlas por política, tiene que llamar a esa función.
- **El modelo de costo** sale de 1 persona monthly y de notas de hasta 20k caracteres. La parte por sesión (≈ 615 tokens) coincide con las 5 personas de §4.5, que tienen ≈ 1.700–1.800 caracteres por sesión. Con notas de más de ~25k caracteres conviene volver a correr `scale`.
- **Proyección por cadencia (§3.4).** Es aritmética sobre el modelo, no una medición: la mide P6.
