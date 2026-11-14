# P6 · Diagnóstico de las respuestas inventadas

**Resultado.** Las `invented` de P5 no salen de notas que se pudren con la vida del agente. Clasifiqué cada una en 8 corridas de persona entera (2 personas monthly, 5 y 3 políticas), con 0 sin explicar:

- **La mayoría las pone Memora.** Son 2 gastos "last night" que la clave fecha un día después de lo que dijo el usuario. Arruinan todos los totales de su semana: 25 de las 42 de `every-5` en academic_researcher, y 24 a 30 en las otras cadenas que sueñan.
- **El resto es atraso, no invención.** La nota todavía no tiene el dato y el que responde dice "0" o "no". Ahí `invented` repite lo que ya mide `missing`, y crece al soñar menos: en s1–210, 0 con `every-1` y 25 con `never`.
- **Las líneas falsas del sueño son 0 a 2 por persona entera.** El sueño no inventa valores, y con notas perfectas el que responde acierta 1.809 de 1.809.
- **Sin las preguntas marcadas**, el `invented` del último tramo (s421–619) es 0 con `every-1` y `every-20`, 1 con `every-5` y 2 con `triggered-phrases-any`.

**Para P7: s1–210 alcanza para ordenar las políticas, no para medir cuánto se separan.** El orden fue el mismo en los 3 tramos de las 2 personas. Pero en academic_researcher la ventaja de `every-1` sobre `every-5` se reduce de 8,1 a 4,1 puntos hacia el final del mes (sin marcadas). Esa compresión no es `invented`. Son `stale`/`missing` de Memora (gustos "ya no", un evento cancelado que la clave conserva) y de documentos con títulos genéricos que el sueño no separa bien (§3.3).

| | s1–210 | persona entera | dónde |
| --- | --: | --: | --- |
| `every-5`, academic_researcher: `invented` | 2 | 42 (25 de Memora, marcadas) | §3.1 |
| `every-5`, academic_researcher: oficial / sin marcadas | 89,2 % / 90,4 % | 87,2 % / 89,4 % | §4.2 |
| `every-1` − `every-5`, academic_researcher, sin marcadas (puntos) | 8,1 | 4,1 en s421–619 | §3.3 |
| `invented` sin marcadas, s421–end, cadenas que sueñan | — | 0–2 por política | §3.2 |
| Líneas falsas que escribió un sueño, por persona entera | 0 | 0–2 | §3.1 |

| Rol | Ruta |
| --- | --- |
| Tag | `p6` |
| Interfaz P6a/P6b | `docs/p6-interfaz.md` |
| Informe de P6a (causa de cada inventada) | `docs/p6a-origen-de-las-inventadas.md` |
| Informe de P6b (¿crece con la vida?) | `docs/p6b-crece-con-la-vida.md` |
| Cada respuesta mal, con su nota y el sueño que escribió cada línea (P6) | `diagnosis/invented.py` |
| Causa de cada `invented` (P6a) | `diagnosis/causes.py`; también `perfect_notes.py`, `criteria.py`, `marks_diff.py` |
| Tasas por tramo, mezcla vs. tasa, exactitud de las notas por sueño (P6b) | `diagnosis/growth.py` |
| Errores tardíos de quien sueña seguido, uno por uno (P6, integración) | `diagnosis/late_errors.py` |
| Arreglo de un bug: marcas `relative_date` (P6a) | `exam/unreachable.py`, `tests/test_unreachable.py` |
| Tests (49 en total; 3 nuevos en P6) | `tests/test_causes.py` (1), `tests/test_growth.py` (1), `tests/test_unreachable.py` (+1) |
| Caché (ignorado por git; P7 debería partir de acá) | `results/raw/p5/r0/` (P5 + lo que pagó P6b) y `results/raw/p6a/` de este worktree |

## 1. Problema

En P5, `every-5` sobre monthly/academic_researcher dio 2 `invented` en s1–210 (0,3 %) y 42 sobre la persona entera (2,3 % de 1.809). La precisión bajó de 89,2 % a 87,2 %. Una `invented` debería ser el peor error: el agente afirma algo que nunca fue cierto. Si crece con la vida del agente, P7 sobre s1–210 sería optimista.

Ejemplo real, `every-5`, s595: "What is the total of the user's food expenses dated from 2025-06-22 to 2025-06-27?". La respuesta es 260.82 y lo esperado 291.2, así que sale `invented`.

- **La nota:** tiene `- 2025-06-21 dinner: $30.38`.
- **La transcripción:** en la s470 (2025-06-22) el usuario dijo *"I spent $30.38 on dinner last night"*.
- **La clave de Memora:** fecha ese gasto el 22, así que el total del 22 al 27 "debería" incluirlo.

El sueño anotó lo que dijo el usuario, y los 21 totales de esa semana salen `invented` en las cuatro cadenas que sueñan.

## 2. Cómo se dividió

| Subproblema | Pregunta | Tope | Gastado |
| --- | --- | --: | --: |
| P6a | ¿De dónde sale cada `invented`? Una causa por respuesta, con evidencia | $0,80 | $0,0987 |
| P6b | ¿Crece con las sesiones? ¿Depende de la política? | $1,60 | $1,4447 |
| P6 (integración) | Interfaz, causas sobre las corridas nuevas de P6b, errores tardíos, recorrección | $0,60 | $0,0000 |

Las hipótesis de cada subproblema están en P6a §2 y P6b §2. Las que importan para la conclusión:

| # | Hipótesis | Resultado |
| --- | --- | --- |
| H1 | El sueño escribe líneas falsas, y más cuanto más larga es la nota | **Descartada.** 0–2 líneas falsas por persona entera; la exactitud de la nota no baja en 619 sesiones (P6b §3.3). |
| H2 | El que responde lee mal notas largas | **Descartada para `invented`.** Con notas perfectas, 1.809/1.809 (579/579 en s421–619). Los 8 errores tardíos de `every-1` "con la nota bien" son nombres que no coinciden y documentos mal identificados (§3.3). |
| H3 | Memora o la corrección fabrican `invented` | **Confirmada.** Fechas "last night" (marcadas), un total "0" con la nota todavía vacía, un evento cancelado que la clave conserva. |
| H4 | Crece porque cambia la mezcla del examen | **Descartada.** Con la mezcla del primer tramo da lo mismo (P6b §3.2). La suba es de tasa, y esa tasa es la de la semana marcada. |
| H5 | El orden de las políticas cambia con el tiempo | **Descartada** en 2 personas × 3 tramos. Las distancias sí cambian (§3.3). |

## 3. Análisis y conclusión

### 3.1 Cada `invented`, por causa (P6a, extendido a las corridas de P6b)

P6a escribió un clasificador sin modelo, `diagnosis/causes.py`, y lo probó sobre `every-5` y las 11 políticas de s1–210. Al integrar lo corrí sobre las 8 corridas de persona entera, incluidas las 6 que pagó P6b después. Ninguna respuesta quedó `unexplained`.

monthly/academic_researcher, persona entera (`results/p6/causes-academic.txt`):

| causa | grupo | never | every-1 | every-5 | every-20 | phrases-any |
| --- | --- | --: | --: | --: | --: | --: |
| `memora_relative_date` (gasto "last night") | Memora | 9 | 25 | 25 | 24 | 24 |
| `grader_empty_total` (nota sin gastos del rango: total 0) | corrección | 48 | 0 | 3 | 7 | 0 |
| `reader_nothing_for_absent` (nota sin el dato: "0"/"no", no "unknown") | lector | 8 | 0 | 3 | 10 | 0 |
| `dream_omission` (el sueño leyó el gasto y no lo anotó) | sueño | 0 | 10 | 9 | 0 | 10 |
| `dream_false_line` (valor que el hecho nunca tuvo) | sueño | 0 | 1 | 1 | 0 | 2 |
| `memora_kept_removed` (el usuario lo dejó, la clave no) | Memora | 0 | 0 | 1 | 0 | 1 |
| `reader_misread` (nota con lo esperado, respuesta otra) | lector | 0 | 0 | 0 | 1 | 0 |
| **total** | | **65** | **36** | **42** | **42** | **37** |

monthly/startup_founder, persona entera (`results/p6/causes-startup.txt`): `never` 58, `every-5` 31, `every-20` 15. Son las mismas causas: `memora_relative_date` 10/30/8, `grader_empty_total` 40/0/4 y `reader_nothing_for_absent` 8/1/3. Ninguna es del sueño.

- **Una raíz arruina muchos exámenes.** Un monthly es junio de 2025, con unas 20 sesiones por día. El total semanal se pregunta unas 20 veces seguidas, así que un gasto mal fechado u omitido cuenta unas 20 veces (P6b §3.1).
  - Las 10 `dream_omission` de `every-1` son un solo café: *"grabbing a $4.11 coffee can be a small break"*, s236.
  - Las 25 `memora_relative_date` son dos gastos, s429 y s470.
- **Las líneas falsas del sueño son 1 o 2 por cadena.** Una es Thomas Mann, `dislike`, después de *"Mann's work always felt a bit too dense for me"* (s416). Memora borra el gusto, y la cuenta indulgente que decidió el usuario en P2 ya da esta respuesta por correcta.
- **Lo que el sueño sí hace mal es omitir, no inventar.** Es el mismo hallazgo de P4: un gasto dicho al pasar, un pendiente implícito.

### 3.2 No crece con la vida del agente (P6b)

`invented` por tramo de 210 sesiones, academic_researcher, oficial / sin marcadas (`results/p6/growth-academic.txt`, con las marcas ya arregladas):

| política | s1–210 | s211–420 | s421–619 |
| --- | --: | --: | --: |
| every-1 | 0 / 0 | 11 / 11 | 25 / **0** |
| triggered-phrases-any | 0 / 0 | 11 / 11 | 26 / **2** |
| every-5 | 2 / 2 | 14 / 14 | 26 / **1** |
| every-20 | 5 / 5 | 13 / 13 | 24 / **0** |
| never | 25 / 25 | 23 / 23 | 17 / 10 |

- **La suba oficial es la semana marcada.** En academic_researcher la semana del "last night" es la última. En startup_founder es la primera, y por eso s1–210 es allí su peor tramo: `every-5` da 4,5 % de `invented`, contra 0,3 % y 0,5 % después.
- **El pico de s211–420 es la omisión del café** (10 de las 11 de `every-1` y de phrases-any).
- **La nota no se pudre.** Se triplica (de 7 mil a 21 mil caracteres) y el 89–96 % de los hechos vivos sigue bien en todos los tramos. Las líneas stale, falsas o duplicadas no pasan de 5 por nota de ~320 líneas (P6b §3.3).

### 3.3 Lo que sí cambia: la ventaja de soñar seguido se achica en academic_researcher

Sin marcadas, academic_researcher (`results/p6/growth-academic.txt`):

| tramo | every-1 | phrases-any | every-5 | every-20 | never | every-1 − every-5 |
| --- | --: | --: | --: | --: | --: | --: |
| s1–210 | 98,5 % | 97,4 % | 90,4 % | 77,1 % | 24,3 % | 8,1 |
| s211–420 | 95,4 % | 93,5 % | 89,2 % | 73,2 % | 24,2 % | 6,2 |
| s421–619 | 92,7 % | 92,1 % | 88,6 % | 76,5 % | 26,1 % | 4,1 |

`every-1` cae 5,8 puntos y `every-5`, 1,8. En startup_founder `every-5` no cae (90,9 → 86,9 → 90,9 %), y no hay `every-1` tardío para comparar. Al integrar leí uno por uno los errores de `every-1` en s421–619 sobre un hecho vivo (`diagnosis/late_errors.py`, `results/p6/late-errors-academic.txt`):

| caso | `every-1` | `every-5` | qué pasa (ejemplo real) |
| --- | --: | --: | --- |
| Gusto "ya no": el sueño borra la línea, Memora registra `dislike` | 12 | 9 | s420: *"I used to really like Marlon Brando's acting… his style just doesn't appeal to me anymore"*. Memora: like → dislike. El sueño aplica su regla de P4a (sin "dislike" dicho, se borra) y responde `unknown`. Es la ambigüedad de Memora de P4a §4.2 (373 borrados y 64 cambios a dislike, dichos casi igual). |
| Hashtag de un post: la línea está, en un bloque que no se reconoce como ese post | 10 + 4 | 0 + 2 | s462: el post "Exploring novel approaches to network resilience…" quedó en la nota como `### Social media post: LinkedIn Research Update`, y `- #FutureNetworks` quedó sin sangría, fuera de su lista. El que responde contesta "no". |
| Evento cancelado que la clave conserva (`memora_kept_removed`) | 5 | 4 | s586: *"I'm no longer planning to attend the academic conference"*. Memora borra el pendiente y deja el evento. |
| Pendiente implícito que Memora vuelve a agregar y ningún sueño anota | 4 | 12 | s552: *"I need to plan some reading for pleasure soon."* |
| Otro nombre: la nota guarda un ítem parecido | 4 | 2 | "The Best of Ella Fitzgerald" (música escuchada) contra la nota `Ella Fitzgerald (artists / singers): like`; "1920s" (década) contra `1920s jazz (genres)` |

- **La compresión no viene de `invented`.** Viene de dos cosas: la ambigüedad de Memora entre "ya no" y "dislike", y los documentos (posts) que un sueño frecuente vuelve a titular en forma genérica.
- **Los hashtags son la mayor diferencia entre `every-1` y `every-5`:** 14 contra 2. P6b vio la misma señal en las notas: las líneas sin hecho de `every-1` y phrases-any pasan de 8 a 36–41 por sueño, y las de `every-5` de 8,5 a 25,6.
- **Corrección a P6b §3.5.** El "error con la nota bien" de `every-1`, 0,8 % → 3,2 %, no muestra que el que responde lea peor una nota larga. Con las marcas arregladas son 8 de 340 (2,4 %), y los 8 son los dos últimos casos de la tabla. `compare_notes` empareja por palabras y los da por buenos.

### 3.4 Conclusión para P7

- **Puede quedarse en s1–210 para ordenar las políticas.** El orden fue el mismo en 2 personas × 3 tramos, con el conteo oficial y sin marcadas. `invented` en s1–210 no es optimista en cuanto a notas falsas: mide atraso, y depende de la cadencia.
- **Tiene que reportar siempre "sin marcadas" al lado del oficial.** El conteo oficial depende de en qué semana cae un gasto "last night": puede volver a s1–210 optimista (academic_researcher) o pesimista (startup_founder). Las marcas ahora cubren también el día anterior de un "last night" (§3.5).
- **No debería presentar las distancias de s1–210 como las del agente a largo plazo.** En academic_researcher, la ventaja de soñar en cada sesión sobre cada 5 se reduce a la mitad hacia el final del mes. Con una sola persona tardía con `every-1`, no se sabe si es general. Medir un tramo tardío cuesta lo mismo que la persona entera, porque cada sueño depende de los anteriores (P6b §3.7).
- **Si hay presupuesto,** lo más útil es `every-1` y `every-5` enteras en 1–2 personas más: ≈ $0,66 + $0,29 por persona, menos lo cacheado de s1–210. Es lo único que s1–210 no puede ver.

### 3.5 Bug arreglado: marcas `relative_date` (P6a)

`exam/unreachable.py` tenía dos errores, cada uno con un test anclado en un caso real (`tests/test_unreachable.py::test_the_day_a_last_night_expense_belongs_to_is_marked_once_it_is_logged`):

1. **No marcaba la pregunta del día anterior.** La regla no marcaba la pregunta por el mismo tipo de gasto el día que quiso decir el usuario. Ese día el usuario declaró dos, y la clave tiene uno. Caso: s441, cena del 2025-06-19, esperado 45.45, nota con $45.45 y $45.81.
2. **Contaba un "yesterday" que no fecha el gasto.** monthly/creative_designer s132: *"I just had a $9.81 lunch today, mostly leftovers from yesterday"*.

Qué cambia:

- **Marcadas monthly:** de 395 a 426 (+35 y −4). Gastos: de 223 a 254. Los gastos "last night" pasan de 35 a 34.
- **Weekly:** no cambia.
- **P5 en s1–210:** idéntico en las 11 políticas, verificado en §4.1.
- **P5, `every-5` entera, "oficial sin marcadas":** de 1575/1764 (89,3 %) a 1575/1761 (89,4 %).
- **Los "sin marcadas" de s421–end en el informe de P6b** se midieron antes del arreglo. Los valores al día están en §3.2–3.3. Por ejemplo, `every-1` da 92,7 % y no 92,2 %, y el orden no cambia.
- **El conteo oficial y el caché del examen** no cambian.
- **Documentos actualizados:** `docs/p2-examen.md` (tabla de marcadas) y `docs/p5-politicas.md`.

## 4. Prueba

Todo con `claude-haiku-5-5`, desde el caché salvo las corridas de P6a §4.3 (notas perfectas) y P6b §4.2. Los comandos de lectura de P6b y `late_errors` usan `PYTHONHASHSEED=0` (§6).

```
$ uv run pytest -q
49 passed
```

### 4.1 P5 en s1–210 sigue idéntico después del arreglo

```
$ uv run python -m policies.run monthly/academic_researcher:210 --policies never every-1 every-2 every-3 every-5 every-10 every-20 every-50 triggered-phrases-change triggered-phrases-any triggered-model-any --check-cache > results/p6/p5-s1-210-recheck.txt
$ diff <(grep -E "^\| (never|every|triggered)" results/p5/integration.txt | head -11) <(grep -E "^\| (never|every|triggered)" results/p6/p5-s1-210-recheck.txt | head -11) && echo "s1-210 identical to P5"
s1-210 identical to P5
```

### 4.2 Personas enteras, desde el caché (tope $0)

```
$ uv run python -m policies.run monthly/academic_researcher --policies never every-1 every-5 every-20 triggered-phrases-any --check-cache
| policy | ... | official | lenient | official without marked | lenient without marked | correct | stale | missing | invented | unparseable |
| never | ... | 437/1809 (24.2%) | 437/1809 (24.2%) | 437/1761 (24.8%) | 437/1761 (24.8%) | 437 | 329 | 977 | 65 | 1 |
| every-1 | ... | 1685/1809 (93.1%) | 1686/1809 (93.2%) | 1683/1761 (95.6%) | 1684/1761 (95.6%) | 1685 | 50 | 38 | 36 | 0 |
| every-5 | ... | 1577/1809 (87.2%) | 1578/1809 (87.2%) | 1575/1761 (89.4%) | 1576/1761 (89.5%) | 1577 | 123 | 67 | 42 | 0 |
| every-20 | ... | 1335/1809 (73.8%) | 1336/1809 (73.9%) | 1330/1761 (75.5%) | 1331/1761 (75.6%) | 1335 | 291 | 141 | 42 | 0 |
| triggered-phrases-any | ... | 1664/1809 (92.0%) | 1666/1809 (92.1%) | 1662/1761 (94.4%) | 1664/1761 (94.5%) | 1664 | 61 | 47 | 37 | 0 |
p5 spent: $0.4412 before, $0.4412 after

$ uv run python -m policies.run monthly/startup_founder --policies never every-5 every-20 --check-cache
| never | ... | 437/1819 (24.0%) | ... | 437/1752 (24.9%) | ... | 437 | 394 | 930 | 58 | 0 |
| every-5 | ... | 1572/1819 (86.4%) | ... | 1566/1752 (89.4%) | ... | 1572 | 121 | 95 | 31 | 0 |
| every-20 | ... | 1358/1819 (74.7%) | ... | 1340/1752 (76.5%) | ... | 1358 | 302 | 144 | 15 | 0 |
```

Salidas completas: `results/p6/academic-whole.txt`, `results/p6/startup-whole.txt`.

### 4.3 Causas, tramos y errores tardíos

```
$ uv run python -m diagnosis.causes monthly/academic_researcher --policies never every-1 every-5 every-20 triggered-phrases-any --stretches --quiet --check-cache > results/p6/causes-academic.txt
$ uv run python -m diagnosis.causes monthly/startup_founder --policies never every-5 every-20 --stretches --quiet --check-cache > results/p6/causes-startup.txt
$ PYTHONHASHSEED=0 uv run python -m diagnosis.growth exam monthly/academic_researcher --policies never every-1 every-5 every-20 triggered-phrases-any > results/p6/growth-academic.txt
$ PYTHONHASHSEED=0 uv run python -m diagnosis.growth exam monthly/startup_founder --policies never every-5 every-20 > results/p6/growth-startup.txt
$ PYTHONHASHSEED=0 uv run python -m diagnosis.late_errors monthly/academic_researcher --policies every-1 every-5 --after 420 > results/p6/late-errors-academic.txt
```

Salida de `late_errors` (tablas finales):

```
## every-1 on monthly/academic_researcher, exams after s420
| calendar | dropped, no change in Memora | 5 |
| content | a line with its name, not tied to it | 10 |
| content | correct in the notes, answer wrong | 4 |
| preference | correct in the notes, answer wrong | 4 |
| preference | dropped, Memora: like -> dislike | 12 |
| todo | Memora added it again, no dream wrote it back | 4 |
## every-5 on monthly/academic_researcher, exams after s420
| calendar | dropped, no change in Memora | 4 |
| calendar | never in the notes | 1 |
| content | correct in the notes, answer wrong | 2 |
| content | never in the notes | 2 |
| expense | a line with its name, not tied to it | 4 |
| preference | Memora added it again, no dream wrote it back | 1 |
| preference | correct in the notes, answer wrong | 2 |
| preference | dropped, Memora: like -> dislike | 9 |
| preference | never in the notes | 1 |
| steps | a line with its name, not tied to it | 4 |
| todo | Memora added it again, no dream wrote it back | 12 |
| todo | never in the notes | 2 |
```

- **Las 5 "dropped, no change in Memora" de calendar** son el Academic conference de la s586. Memora no registra ningún cambio del evento porque borra solo el pendiente.
- **Las "a line with its name" de expense y steps de `every-5`** son de `related_lines`, que empareja fechas vecinas por palabras (`docs/p6-interfaz.md`). No las usé en §3.3.

### 4.4 Costo real

| Proceso | Tope | Gastado | Libro |
| --- | --: | --: | --- |
| P6a | $0,80 | $0,0987 | `results/spend/p6a.jsonl` |
| P6b | $1,60 | $1,4447 | `results/spend/p6b.jsonl` |
| P6 (integración) | $0,60 | $0,0000 | (todo desde el caché) |
| **Total** | **$3,00** | **$1,5434** | |

P6b pagó 6 corridas de persona entera: academic_researcher `never` + `every-20` $0,1686, `every-1` $0,5147 y phrases-any $0,3900; startup_founder `never` + `every-5` $0,2275 y `every-20` $0,1439. La proyección de P5 daba $1,593, un 7–15 % por encima de lo pagado en cada corrida. P6a pagó 88 exámenes con notas perfectas.

**Caché.** Copié a este worktree el de P6a (`results/raw/p6a/`) y el de P6b (`results/raw/p5/r0/`, 1.122 pedidos nuevos). Antes comprobé que ningún archivo con el mismo nombre en dos worktrees tuviera contenido distinto. P7 tiene que partir de este caché.

## 5. Hipótesis y opciones descartadas

| Opción | Por qué no | Dónde |
| --- | --- | --- |
| "El sueño acumula líneas falsas" | 0–2 por persona entera, y la exactitud de la nota es estable | §3.1, P6b §3.3 |
| "El que responde suma mal totales largos" | Las 33 sumas de `every-5` son exactas sobre la nota. startup_founder, con 15 gastos por total, saca 0 de 21. | P6a §3.2, P6b §3.4 |
| "Leer notas de 21 mil caracteres falla más" | Con notas perfectas del mismo largo, 579/579. Los 8 "con la nota bien" son emparejamientos flojos de `compare_notes`. | §3.3 |
| Cambiar la regla oficial de corrección (total incompleto, "0" sin datos) | Es un criterio, no un bug: se midió aparte y queda como decisión abierta | §6, P6a §4.4 |
| Contar cada hecho distinto una sola vez (P6b, opción b) | Cambia la regla de P2 y la decisión (c) ya separa la mayor parte de las repeticiones | P6b §6 |
| Arreglar el desempate de `compare_notes` por orden de hash | No toca el examen; mueve ±0,2 puntos los conteos de líneas. Basta con fijar `PYTHONHASHSEED=0`. | §6 |
| Medir un tramo tardío en lugar de la persona entera | Cuesta lo mismo: cada sueño depende de todos los anteriores | P6b §3.7 |

## 6. Limitaciones y decisiones abiertas

- **Dos personas monthly.** Hay `every-1` y phrases-any tardíos solo en academic_researcher, y una sola repetición. Los errores no son independientes: los 40 errores tardíos de `every-1` caen sobre 17 hechos distintos. Por eso no doy intervalos de confianza. La compresión de §3.3 es una señal de una persona, no un resultado general.
- **El clasificador de P6a empareja entradas por fecha y monto,** y `related_lines` por palabras. Para gastos trae fechas vecinas. P6a muestra la evidencia de cada raíz de las 42 de `every-5`, y yo leí los casos de §3.3. Las respuestas de las otras corridas se clasificaron con la misma regla, sin leerlas una por una.
- **`compare_notes` (P4b) no es determinista entre procesos.** En `dreaming/quality.py` (`match_documents`), `max` sobre un `set` desempata según el orden del hash, y eso mueve ±0,2 puntos los conteos de líneas (P6b §6). No lo cambié porque no afecta el examen. Todo comando que lo usa fija `PYTHONHASHSEED=0`, y P7 debería hacer lo mismo.
- **Decisiones abiertas (criterios de corrección, ninguno aplicado):**
  1. **`nothing_logged`** (recomendado por P6a, y también por mí). Un "0" o un "no" donde el hecho todavía no valía contaría como `stale`, no como `invented`. La precisión no cambia, y `invented` pasa a significar "afirmó algo que nunca fue cierto". s1–210 queda en 0 `invented` en las 11 políticas (`never` baja de 25 a 0) y `every-5` entera baja de 42 a 34. Ejemplo: s147, total del 2025-06-08, respuesta "0" con la nota del s145, cuando ese día todavía no tenía gastos.
  2. **`partial_total`**, solo como columna de diagnóstico: un total al que le falta un gasto no es un monto inventado. `every-5` entera bajaría de 42 a 9. No lo recomiendo como oficial, porque una suma parcial puede coincidir por azar.
  3. **Muestra de P7.** Hay dos opciones:
     - **(a)** s1–210 en las 10 personas, reportando oficial y sin marcadas, y declarando que las distancias entre las políticas que sueñan seguido pueden achicarse hasta la mitad más adelante en el mes. **Recomendado.**
     - **(b)** Lo mismo, más `every-1` y `every-5` enteras en 1–2 personas para verificar la compresión: ≈ $0,7–0,8 por persona por encima de (a).

## Decisiones

Tomadas sobre §6, antes de P7 (2026-11-13). Rigen para P7.

1. **Muestra: opción (b).** Las 10 personas monthly sobre s1–210, con 7 políticas (`never`, `every-1`, `every-5`, `every-10`, `every-20`, `every-50`, `triggered-phrases-any`) y 2 repeticiones. Además, `every-1` y `every-5` sobre la persona entera de monthly/startup_founder (academic_researcher entera ya está medida en P5–P6). Así se mide en 2 personas cuánto se achica la distancia entre `every-1` y `every-5` hacia el final del mes.
2. **`nothing_logged`: de las dos formas.** Un "0" o un "no" dado cuando el hecho todavía no valía se reporta con la regla actual (`invented`) y también reclasificado como `stale`. La precisión no cambia.
3. **`partial_total`: solo diagnóstico.** Va como columna aparte y nunca entra en la cuenta oficial.
4. **Siempre 4 cuentas:** oficial (estricta), indulgente, y las dos sin las preguntas marcadas.
