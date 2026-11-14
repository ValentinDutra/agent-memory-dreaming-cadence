# P7c · Diagnóstico con $0: el ruido entre repeticiones y los errores tardíos

**Resultado.**

- **La caída de las frases de la rep 0 a la rep 1 es ruido.** Entre las dos corridas no cambió nada: el modelo, thinking, effort, temperatura, `repeat` y `stop_reason` son los mismos en las 13.823 respuestas, y la rep 1 sacó muestras nuevas, no las de la rep 0.
- **La mayor parte del corrimiento está en las notas, no en la lectura.** De los 63 aciertos en que se movió `every-1 − frases`, 52 vienen de notas que dicen otra cosa y 7 de la misma nota contestada distinto.
- **La mitad de la caída de las frases es un solo gasto.** En marketing_manager r1, el primer sueño deja afuera la cena del 2025-06-01 ($20,27) y ningún sueño la vuelve a anotar hasta la s210. Ese sueño es la misma entrada del caché para `every-1` y para las frases. Le cuesta 29 aciertos a cada una: 21 totales de gastos y 8 preguntas por la cena.
- **Las notas de las frases varían menos que las de `every-1`** entre repeticiones (0,77 contra 1,03 puntos por sueño). La hipótesis "las frases son más ruidosas" no se sostiene.
- **9 de 10 en el mismo sentido es raro para una columna (p = 0,021, dos colas), pero no para una tabla de 10 columnas.** Si se respeta que las columnas dependen entre sí, alguna llega a 9 de 10 por azar el 11,5 % de las veces (8,4 % sin marcadas).
- **La compresión de academic_researcher (+5,6 → +2,6) tiene dos causas.** `every-1` repite errores tardíos sobre pocos hechos: 4 gustos "ya no" y 10 líneas de posts o emails bajo un título genérico, que restan 2,7 puntos. Además `every-5` deja de errar los totales en el último tramo, lo que resta otros 1,5.
- **En startup_founder no hay compresión** (+5,9 → +6,4) porque `every-1` casi no tiene esos errores tardíos: son 2 gustos y 3 líneas de documentos. `every-5` sigue errando totales y hechos que todavía no anotó.

| Rol | Ruta |
| --- | --- |
| Tag | `p7` |
| Parte 1: registros, cambios de clase, sueños, pruebas de signos, rastreo de un hecho | `final/repetitions.py` |
| Parte 2: errores de las personas enteras por causa y tramo | `final/compression.py` |
| `--repetition` y `--budget-name` nuevos; los casos como generador | `diagnosis/late_errors.py`, `diagnosis/growth.py` |
| Test (1) | `tests/test_repetitions.py` |
| Salidas (ignoradas por git; se regeneran con los comandos de §4) | `results/p7c/*.txt` |
| Caché | `results/raw/p5/r0/` y `r1/` de este worktree. Tope $0, ninguna llamada. |

## 1. Problema

**Parte 1.** En la tabla de ruido de P7b (`docs/p7/tables.md`, "Noise between repetitions"):

- `every-1 − triggered-phrases-any` sube de la rep 0 a la rep 1 en 9 de 10 personas, +1,1 puntos de media.
- Las frases bajan 1,0 de media y `every-1` queda plano.
- Las decisiones de soñar son idénticas en las 70 parejas.
- El caso más grande es marketing_manager: frases −5,8, `every-1` −4,4.

Una causa propia de las frases, como sueños con ventanas más largas, actúa igual en las dos repeticiones porque las decisiones son las mismas. No puede explicar por sí sola que la rep 1 dé menos. Quedan dos explicaciones: ruido que cayó del mismo lado, o algo que cambió entre la corrida del 13/11 y la del 14/11.

**Parte 2.** En las personas enteras nuevas, la brecha `every-1 − every-5` sin marcadas pasa de +5,6 a +2,6 en academic_researcher, y en startup_founder no se achica (+5,9 → +6,4) (`docs/p7/tables.md`). P6 la había explicado con la muestra vieja (`docs/p6-inventadas.md` §3.3). Hay que ver si esa explicación vale con la muestra nueva y por qué startup_founder no comprime.

## 2. Opciones consideradas

- **Dónde separar notas de lectura (parte 1):**
  - (a) comparar las notas línea por línea contra la verdad con `compare_notes` (`dreaming/quality.py`), como `diagnosis/growth.py notes`;
  - (b) para cada pregunta que cambió de clase entre repeticiones, mirar si la nota que leyó dice lo mismo.
- **Qué es "la nota dice lo mismo":**
  - las mismas líneas sobre el hecho (`diagnosis.invented.related_lines`);
  - el mismo estado según `compare_notes`;
  - para un total, que estén todos los gastos o pasos del rango.
- **Cómo medir si el ruido de las frases es mayor:** la diferencia entre repeticiones del mismo sueño (misma política, misma sesión, misma ventana), por política y por largo de ventana.
- **Qué pudo cambiar entre corridas:** los campos de cada respuesta cruda (`model`, `thinking`, `effort`, `temperature`, `repeat`, `max_tokens`, `stop_reason`, `usage`, `time`) y la clave del caché.
- **Pruebas:** prueba de signos, permutación intercambiando r0 y r1 dentro de cada persona (exacta, 2¹⁰ formas) y Bonferroni.
- **Parte 2:** `diagnosis/late_errors.py` da un caso mecánico por error. Las causas de P6 salieron de leer esos casos (P6 §3.3), y la correspondencia caso → causa reproduce exactamente sus conteos (§3.2).

## 3. Análisis y elección

### 3.1 Parte 1: herramientas

- **`final/repetitions.py`** en vez de agregar `--repetition` a cada tabla de `diagnosis/growth.py`. Las preguntas que hay que hacer cruzan las dos repeticiones (pregunta por pregunta, sueño por sueño), y `growth` mira una corrida a la vez. Igual agregué `--repetition` a `growth.py` y `late_errors.py`, como pedía la tarea.
- **Estado de la nota, en tres niveles,** para cada pregunta cuya clase cambió:
  - mismas líneas sobre el hecho: la diferencia es de lectura;
  - otras líneas pero el mismo estado: la nota está reescrita pero dice lo mismo;
  - otro estado: la nota dice otra cosa.

  Para los totales, el estado es "completo" si todos los ítems del rango están bien en la nota, como en `growth.aggregate_table`. Sin esto, los totales de marketing_manager caían en "mismo estado", porque la línea del café del día seguía ahí.
- **La permutación respeta la dependencia entre columnas.** Intercambiar r0 y r1 en una persona da vuelta el signo de sus 10 columnas a la vez. Para una sola columna, la permutación es la prueba de signos (el test lo comprueba con el caso real de 9 de 10).

### 3.2 Parte 2: herramientas

- **`late_errors` ahora expone los casos como generador** (`late_errors(run, after)`) y su `main` los imprime igual que antes. Corrí el comando de P6 sobre la muestra nueva para comprobarlo (§4.6).
- **Casos de `late_errors` → causas de P6** (`final/compression.py`, `P6_CAUSES`). Es la correspondencia que da los números de P6 §3.3 a partir de sus tablas de §4.3:

  | caso de `late_errors` | causa de P6 | P6, `every-1` / `every-5` |
  | --- | --- | --- |
  | preference, dropped like → dislike | gusto "ya no" | 12 / 9 |
  | content, a line with its name / correct in the notes | hashtag o documento bajo un título genérico | 10 + 4 / 0 + 2 |
  | calendar, dropped, no change in Memora | evento cancelado que Memora conserva | 5 / 4 |
  | todo, Memora added it again | pendiente implícito | 4 / 12 |
  | preference, correct in the notes | otro nombre en la nota | 4 / 2 |

  Leí los casos nuevos de content y preference "correct in the notes" para confirmar que caben (`results/p7c/late-errors.txt`). Content son hashtags (`#FutureNetworks` en la nota y "no" por respuesta) y puntos de un email. Preference son "The Best of Ella Fitzgerald" contra `Ella Fitzgerald (music / artists)` y "1920s" contra `1920s jazz`.
- **Todos los errores, no solo los de `late_errors`.** `late_errors` cubre los hechos vivos que la nota tiene bien o no tiene. `compression` cuenta también los totales, los señuelos y los hechos viejos o equivocados en la nota. Así la tabla suma el total de errores sin marcadas de cada tramo, y la brecha por causa suma la brecha de P7b.

## 4. Prueba

Todo con tope $0 desde el caché de P7a. En las salidas de abajo, "..." marca columnas o filas recortadas; el resto es la salida tal cual. Si faltara una llamada, `BudgetedClient("p7a", 0.0)` lanza `BudgetExceeded` antes de llamar; no pasó en ningún comando.

```
uv run pytest -q                       # 53 passed
```

### 4.1 Nada cambió entre las dos corridas

```
$ uv run python -m final.repetitions records > results/p7c/records.txt
| repetition | kind | calls | model | thinking | effort | temperature | repeat | max_tokens | stop_reason | service_tier / geo / speed | mean input tokens | mean output tokens | mean thinking tokens | calls per day |
| 0 | dream | 5274 | claude-haiku-5-5 (5274) | {"type": "adaptive"} (5274) | medium (5274) | model default (not settable) (5274) | 0 (5274) | 1 distinct, 32000-32000 | end_turn (5274) | standard / global / standard (5274) | 6,317 | 541 | 418 | 2026-11-13 (3579), 2026-11-14 (1695) |
| 0 | exam | 2200 | claude-haiku-5-5 (2200) | ... | 0 (2200) | 23 distinct, 4275-4605 | end_turn (2200) | standard / global / standard (2200) | 4,040 | 902 | 783 | 2026-11-13 (1626), 2026-11-14 (574) |
| 1 | dream | 4364 | claude-haiku-5-5 (4364) | {"type": "adaptive"} (4364) | medium (4364) | model default (not settable) (4364) | 0 (4364) | 1 distinct, 32000-32000 | end_turn (4364) | standard / global / standard (4364) | 5,511 | 578 | 445 | 2026-11-14 (4364) |
| 1 | exam | 1985 | claude-haiku-5-5 (1985) | ... | 0 (1985) | 23 distinct, 4275-4605 | end_turn (1985) | standard / global / standard (1985) | 3,501 | 879 | 762 | 2026-11-14 (1985) |

requests cached in both repetitions under the same key (same notes, sessions and questions): 407; with the same response text: 232
- dream: 97, same text 43; mean output tokens r0 1,228, r1 1,270; mean thinking tokens r0 934, r1 964
- exam: 310, same text 189; mean output tokens r0 427, r1 418; mean thinking tokens r0 318, r1 309
```

- **Modelo y ajustes:** iguales en las 13.823 respuestas. Ninguna se cortó por `max_tokens`.
- **Las medias de tokens de la tabla grande no se comparan entre sí:** la r0 incluye las personas enteras, con notas más largas. La comparación justa es sobre los 407 pedidos idénticos (mismas notas, sesiones y preguntas: los primeros sueños y los exámenes de `never`). Ahí el uso es el mismo: 1.228 contra 1.270 tokens de salida por sueño, y 427 contra 418 por examen.
- **La clave del caché se comporta igual.** La rep 1 vive en `p5/r1/` (`policies/engine.py`, `run_policy`) con `repeat` en 0, como la rep 0 en `p5/r0/`. De los 97 sueños con el mismo pedido en las dos repeticiones, 54 dieron otro texto: la rep 1 sacó muestras nuevas, no leyó las de la rep 0.
- **Fechas:** los sueños de s1–210 r0 de financial_analyst y sales_manager corrieron el 14/11 después de medianoche, el mismo día que toda la r1. Los otros 8 corrieron el 13/11 (tabla "first and last dream" de `records`). Esas dos personas tienen cambios de las frases de +0,4 y 0,0, y el resto entre −5,8 y +0,7. Con 2 personas contra 8 no se puede separar un efecto de fecha. Además un cambio del modelo afectaría igual a `every-1`, que usa el mismo modelo y el mismo prompt, y `every-1` queda plano.

### 4.2 Notas o lectura: cada pregunta que cambió de clase

```
$ PYTHONHASHSEED=0 uv run python -m final.repetitions flips > results/p7c/flips.txt
| persona | policy | asked | r0 correct | r1 correct | r1 − r0 | questions whose class changed | net, same note lines | net, other lines, same state | net, other state | live facts correct in r0 notes | in r1 notes |
| academic_researcher | every-1 | 593 | 570 | 576 | +6 | 14 | +1 | -1 | +6 | 380/394 | 384/394 |
| academic_researcher | triggered-phrases-any | 593 | 579 | 571 | -8 | 12 | -5 | -1 | -2 | 386/394 | 384/394 |
| business_executive | every-1 | 548 | 517 | 516 | -1 | 17 | -2 | -1 | +2 | 332/342 | 334/342 |
| business_executive | triggered-phrases-any | 548 | 525 | 520 | -5 | 7 | -3 | -2 | +0 | 337/342 | 337/342 |
| content_writer | every-1 | 614 | 549 | 554 | +5 | 10 | +2 | +1 | +2 | 378/409 | 380/409 |
| content_writer | triggered-phrases-any | 614 | 550 | 554 | +4 | 10 | +1 | +2 | +1 | 378/409 | 380/409 |
| creative_designer | every-1 | 596 | 558 | 568 | +10 | 30 | -3 | +0 | +13 | 374/388 | 380/388 |
| creative_designer | triggered-phrases-any | 596 | 552 | 552 | +0 | 12 | -3 | +3 | +0 | 373/388 | 373/388 |
| financial_analyst | every-1 | 565 | 542 | 550 | +8 | 10 | +0 | +0 | +8 | 353/364 | 358/364 |
| financial_analyst | triggered-phrases-any | 565 | 546 | 548 | +2 | 10 | +4 | +1 | -3 | 358/364 | 359/364 |
| management_consultant | every-1 | 583 | 531 | 539 | +8 | 10 | +0 | +1 | +7 | 358/381 | 365/381 |
| management_consultant | triggered-phrases-any | 583 | 545 | 543 | -2 | 8 | -1 | +0 | -1 | 372/381 | 370/381 |
| marketing_manager | every-1 | 572 | 553 | 528 | -25 | 41 | +0 | -1 | -24 | 354/363 | 351/363 |
| marketing_manager | triggered-phrases-any | 572 | 560 | 527 | -33 | 41 | -4 | +1 | -30 | 359/363 | 351/363 |
| sales_manager | every-1 | 573 | 561 | 559 | -2 | 6 | -2 | +0 | +0 | 364/371 | 364/371 |
| sales_manager | triggered-phrases-any | 573 | 559 | 559 | +0 | 4 | +0 | +0 | +0 | 364/371 | 364/371 |
| software_engineer | every-1 | 561 | 536 | 537 | +1 | 13 | -2 | +1 | +2 | 337/350 | 339/350 |
| software_engineer | triggered-phrases-any | 561 | 534 | 529 | -5 | 15 | -2 | -3 | +0 | 337/350 | 337/350 |
| startup_founder | every-1 | 581 | 523 | 521 | -2 | 14 | -3 | +1 | +0 | 357/380 | 356/380 |
| startup_founder | triggered-phrases-any | 581 | 525 | 517 | -8 | 28 | -3 | -4 | -1 | 357/380 | 353/380 |

| policy | asked | r1 − r0 | questions whose class changed | net, same note lines | net, other lines, same state | net, other state | live facts correct in notes, r1 − r0 |
| every-1 | 5786 | +8 | 165 | -9 | +1 | +16 | +24 |
| triggered-phrases-any | 5786 | -55 | 147 | -16 | -3 | -36 | -13 |
```

- **El corrimiento de `every-1 − frases` es de 63 aciertos** (+8 contra −55, 1,1 puntos sobre 5.786 preguntas). Se reparte así:
  - **52 (a), lo que escribieron los sueños:** +16 contra −36 en "otro estado".
  - **7 (b), cómo se contestó:** −9 contra −16 con las mismas líneas de nota.
  - **4 con la nota reescrita sin cambiar lo que dice.**
- **Las notas también lo muestran sin mirar las respuestas.** Los hechos vivos bien en la nota que leyó el examen suben 24 en `every-1` y bajan 13 en las frases.
- **Sin marketing_manager, las frases caen 22 aciertos y `every-1` sube 33** (resta de las filas). Las notas de `every-1` mejoran en r1 en creative_designer (+13), financial_analyst (+8) y management_consultant (+7). Las de las frases no se mueven. El corrimiento fuera de marketing es sobre todo suerte de `every-1`, no una caída de las frases.

### 4.3 marketing_manager: un gasto que el primer sueño deja afuera

```
$ PYTHONHASHSEED=0 uv run python -m final.repetitions trace --personas marketing_manager --policies every-1 triggered-phrases-any every-5 --fact expense 1
- every-1 r0: s1 correct
- every-1 r1: s1 missing
- triggered-phrases-any r0: s1 correct
- triggered-phrases-any r1: s1 missing
- every-5 r0: s5 correct
- every-5 r1: s5 missing

$ PYTHONHASHSEED=0 uv run python -m diagnosis.late_errors monthly/marketing_manager:210 --policies every-1 triggered-phrases-any every-5 --repetition 1 --budget-name p7a > results/p7c/late-errors-marketing-r1.txt
- s7 [expense/new] How much did the user spend on dinner on 2025-06-01, in dollars? Answer with a number or unknown.
  answer 'unknown' -> missing, expected '20.27'; fact missing in the notes
  a line with its name is in the notes: - 2025-06-01 coffee: $4.53
```

- **Qué pasa:** en r1 el sueño de la s1 anota el café del 2025-06-01 y no la cena de $20,27. El rastreo muestra un solo cambio de estado por corrida, así que ningún sueño posterior la agrega hasta la s210. Cada examen pregunta por ese gasto, y los totales semanales que lo incluyen quedan `invented` del s7 al s147 (`flips --personas marketing_manager --show`, `results/p7c/flips-marketing.txt`).
- **Por qué cae en `every-1` y en las frases a la vez:** las dos sueñan después de la s1 con notas vacías, así que hacen el mismo pedido y comparten la misma entrada del caché (`policies/engine.py`: "two policies that hold the same notes get the same dream"). `every-5` lee s1–s5 en otro pedido y también la omite en r1.
- **Cuánto pesa:** 29 aciertos en cada política, sacados de `flips --personas marketing_manager --show`:

  ```
  every-1, net change per question asked, largest first: monthly/marketing_manager/expense/total -21, monthly/marketing_manager/expense/1 -8, monthly/marketing_manager/todo/Plan dinner party +5, ...
  triggered-phrases-any, net change per question asked, largest first: monthly/marketing_manager/expense/total -21, monthly/marketing_manager/expense/1 -8, ...
  ```

  Es más de la mitad de la caída total de las frases (−55). En `every-1`, un pendiente que la nota de r1 tiene bien devuelve 5. Es el mismo tipo de error que P4 y P6 llaman omisión del sueño: un gasto dicho al pasar.

### 4.4 Las notas de las frases varían menos, no más

```
$ PYTHONHASHSEED=0 uv run python -m final.repetitions dreams > results/p7c/dreams.txt
| policy | window (sessions read) | dreams | mean in r0 | mean in r1 | mean r1 − r0 | mean abs(r1 − r0) | dreams that moved more than 2 points |
| every-1 | all | 2100 | 95.8 | 96.1 | +0.26 | 1.03 | 322 |
| triggered-phrases-any | 1 | 1181 | 96.3 | 95.8 | -0.55 | 0.76 | 114 |
| triggered-phrases-any | 2-3 | 378 | 96.5 | 95.9 | -0.55 | 0.81 | 41 |
| triggered-phrases-any | 4+ | 18 | 95.8 | 95.9 | +0.13 | 0.43 | 0 |
| triggered-phrases-any | all | 1577 | 96.3 | 95.8 | -0.54 | 0.77 | 155 |

| persona | every-1 | triggered-phrases-any |
| academic_researcher | -0.07 | -0.29 |
| business_executive | -0.02 | +0.00 |
| content_writer | +0.06 | +0.22 |
| creative_designer | +4.54 | +0.00 |
| financial_analyst | +0.36 | +0.84 |
| management_consultant | +0.33 | -0.37 |
| marketing_manager | -2.82 | -2.90 |
| sales_manager | +0.00 | -1.69 |
| software_engineer | +0.94 | +0.00 |
| startup_founder | -0.72 | -1.05 |

every-1: personas above zero 5, below 4; sign-flip test on the mean, two-sided: 0.6406; dreams whose notes are the same text in r0 and r1: 26
triggered-phrases-any: personas above zero 2, below 5; sign-flip test on the mean, two-sided: 0.1719; dreams whose notes are the same text in r0 and r1: 24
```

- **Cuánto se mueve el mismo sueño:** 0,77 puntos de media en las frases y 1,03 en `every-1`. Las ventanas de 4 o más sesiones son 18 de 1.577 sueños y se mueven 0,43.
- **Ventanas largas no explican nada acá:** el 75 % de los sueños de las frases leen una sola sesión (1.181 de 1.577).
- **El corrimiento por persona no tiene un sentido claro** en ninguna de las dos políticas: p = 0,64 en `every-1` y 0,17 en las frases. La media de las frases (−0,54) la arrastran marketing_manager (−2,90) y sales_manager (−1,69).
- **Los +0,00 no son un artefacto del caché.** Solo 24 de 1.577 sueños de las frases dejan exactamente el mismo texto en r0 y r1. Los demás reescriben la nota y mantienen los mismos hechos.

### 4.5 Pruebas de signos y comparaciones múltiples

```
$ uv run python -m final.repetitions signs > results/p7c/signs.txt
## official / asked: r1 − r0, points
| column | personas above zero | below | ties | sign test, one-sided | two-sided | mean | sign-flip test on the mean, two-sided |
| never | 0 | 2 | 8 | 0.2500 | 0.5000 | -0.07 | 0.5000 |
| every-1 | 6 | 4 | 0 | 0.3770 | 0.7539 | +0.13 | 0.8789 |
| every-5 | 4 | 5 | 1 | 0.5000 | 1.0000 | -0.26 | 0.6914 |
| every-10 | 3 | 6 | 1 | 0.2539 | 0.5078 | +0.17 | 0.8438 |
| every-20 | 7 | 3 | 0 | 0.1719 | 0.3438 | +0.36 | 0.6055 |
| every-50 | 4 | 6 | 0 | 0.3770 | 0.7539 | -0.07 | 0.8691 |
| triggered-phrases-any | 2 | 6 | 2 | 0.1445 | 0.2891 | -0.95 | 0.0703 |
| every-1 − triggered-phrases-any | 9 | 1 | 0 | 0.0107 | 0.0215 | +1.10 | 0.0059 |
| every-1 − every-5 | 5 | 5 | 0 | 0.6230 | 1.0000 | +0.37 | 0.5566 |
| triggered-phrases-any − every-5 | 3 | 6 | 1 | 0.2539 | 0.5078 | -0.71 | 0.2070 |

largest count on one side in any column: 9 of 10
if the 10 columns were independent, chance that at least one reaches 9 of 10 on one side by chance: 0.1952
swapping r0 and r1 within each persona (all columns together, 2^10 ways), share of the ways where some column reaches 9 of 10 on one side: 0.1152
smallest sign-flip p: 0.0059 (every-1 − triggered-phrases-any); times 10 columns (Bonferroni): 0.0586
```

Sin marcadas, las mismas columnas dan los mismos signos en `every-1 − frases` (9 de 10). Ahí la permutación da 0,0840 y Bonferroni 0,0586.

- **Una columna sola:** 9 de 10 hacia el mismo lado tiene p = 0,0107 con una cola y 0,0215 con dos.
- **La tabla mira 10 columnas.** Si fueran independientes, alguna llegaría a 9 de 10 por azar con probabilidad 0,195. No lo son: las diferencias se arman con las políticas, y sus signos se dan vuelta juntos si se intercambian r0 y r1 de una persona. Respetando eso, la probabilidad es 0,115 (0,084 sin marcadas).
- **La media (+1,10) es más llamativa que el conteo:** la permutación da p = 0,0059 para esa columna sola. Corregido por las 10 columnas da 0,059. La media también está inflada por marketing_manager, que es un solo gasto (§4.3).

### 4.6 Parte 2: errores tardíos de las personas enteras nuevas

```
$ PYTHONHASHSEED=0 uv run python -m diagnosis.late_errors monthly/academic_researcher monthly/startup_founder --policies every-1 every-5 --after 420 --budget-name p7a > results/p7c/late-errors.txt
$ PYTHONHASHSEED=0 uv run python -m final.compression > results/p7c/compression.txt
```

academic_researcher, sin marcadas: errores por causa y lo que cada causa suma a la brecha (puntos):

| causa | `every-1` s1–210 | `every-5` s1–210 | `every-1` s421–fin | `every-5` s421–fin | brecha s1–210 | brecha s421–fin | cambio |
| --- | --: | --: | --: | --: | --: | --: | --: |
| gusto "ya no": el sueño lo borra, Memora registra dislike | 0 | 0 | 11 | 1 | +0,0 | −1,8 | −1,8 |
| post o email bajo un título genérico | 5 | 3 | 16 | 9 | −0,3 | −1,3 | −0,9 |
| evento cancelado que Memora conserva | 0 | 0 | 5 | 4 | +0,0 | −0,2 | −0,2 |
| pendiente implícito que Memora vuelve a agregar | 6 | 2 | 8 | 12 | −0,7 | +0,7 | +1,4 |
| otro nombre en la nota | 0 | 0 | 4 | 2 | +0,0 | −0,4 | −0,4 |
| otro hecho simple que la nota tiene bien o no tiene | 4 | 24 | 0 | 16 | +3,4 | +2,9 | −0,5 |
| hecho viejo o equivocado en la nota | 0 | 4 | 0 | 4 | +0,7 | +0,7 | +0,1 |
| total de gastos o pasos | 0 | 10 | 5 | 6 | +1,7 | +0,2 | −1,5 |
| otro | 1 | 6 | 1 | 10 | +0,9 | +1,7 | +0,8 |
| **todos** | **16** | **49** | **50** | **64** | **+5,6** | **+2,6** | **−3,1** |

startup_founder, sin marcadas:

| causa | `every-1` s1–210 | `every-5` s1–210 | `every-1` s421–fin | `every-5` s421–fin | brecha s1–210 | brecha s421–fin | cambio |
| --- | --: | --: | --: | --: | --: | --: | --: |
| gusto "ya no" | 0 | 0 | 2 | 1 | +0,0 | −0,2 | −0,2 |
| post o email bajo un título genérico | 2 | 5 | 5 | 8 | +0,6 | +0,5 | −0,0 |
| evento cancelado que Memora conserva | 0 | 0 | 0 | 2 | +0,0 | +0,4 | +0,4 |
| pendiente implícito que Memora vuelve a agregar | 0 | 5 | 7 | 8 | +0,9 | +0,2 | −0,7 |
| otro hecho simple que la nota tiene bien o no tiene | 13 | 31 | 6 | 15 | +3,3 | +1,6 | −1,7 |
| hecho viejo o equivocado en la nota | 0 | 0 | 0 | 2 | +0,0 | +0,4 | +0,4 |
| total de gastos o pasos | 0 | 4 | 0 | 14 | +0,7 | +2,6 | +1,8 |
| otro | 2 | 4 | 0 | 5 | +0,4 | +0,9 | +0,5 |
| **todos** | **17** | **49** | **20** | **55** | **+5,9** | **+6,4** | **+0,4** |

Hechos distintos detrás de los errores de s421–fin (un mismo hecho se pregunta en cada examen):

| causa | academic `every-1` | academic `every-5` | startup `every-1` | startup `every-5` |
| --- | --: | --: | --: | --: |
| gusto "ya no" | 4 | 1 | 2 | 1 |
| post o email bajo un título genérico | 10 | 6 | 3 | 6 |
| pendiente implícito | 2 | 6 | 1 | 2 |
| otro hecho simple | 0 | 13 | 2 | 14 |
| total de gastos o pasos | 1 | 2 | 0 | 3 |

**Por qué comprime academic_researcher.** `every-1` pasa de 16 a 50 errores entre s1–210 y s421–fin. Los que suma son de las causas de P6:

- **Gustos "ya no":** 11 respuestas sobre 4 hechos. El sueño borra el gusto, Memora lo registra como dislike y el examen espera "dislike".
- **Posts y emails bajo un título genérico:** 16 respuestas sobre 10 líneas. La línea está en la nota, pero en un bloque que el que responde no reconoce como ese documento.
- **Otro nombre (4) y evento cancelado (5).**

Esas cuatro causas restan 3,3 puntos a la brecha. Los totales restan otros 1,5: `every-5` erraba 10 totales en s1–210 (21 en s211–420) y 6 en s421–fin, y `every-1` pasa de 0 a 5. Los pendientes implícitos van al revés (+1,4): `every-5` los pierde más.

**Por qué no comprime startup_founder.** `every-1` termina con 20 errores, 7 menos que en s211–420. Las causas que crecen en academic casi no aparecen: 2 respuestas de gustos "ya no" sobre 2 hechos, y 5 de documentos sobre 3 líneas. En cambio `every-5` sigue errando los totales (14) y otros hechos simples (15 respuestas sobre 14 hechos). De esos 15, 6 son gustos que nunca entraron a la nota (`every-1` tiene los mismos 6) y 5 son gastos con una línea parecida que `compare_notes` no ata al hecho (tabla "other single fact" de `results/p7c/compression.txt`).

- **La exposición a gustos "ya no" es parecida en las dos personas.** Memora registra 2/2/4 cambios like → dislike por tramo en startup_founder y 2/2/3 en academic_researcher. La diferencia está en cuántos de esos gustos borró el sueño de `every-1` (4 contra 2) y en cuántas líneas de documentos dejó bajo títulos genéricos (10 contra 3). No leí por qué; con una corrida por persona puede ser una decisión de sueño que salió distinto.

**Comparación con P6 (muestra vieja, academic_researcher, s421–fin, `docs/p6-inventadas.md` §3.3):**

| causa | P6 `every-1` / `every-5` | P7c `every-1` / `every-5` |
| --- | --: | --: |
| gusto "ya no" | 12 / 9 | 11 / 1 |
| hashtag o documento bajo un título genérico | 14 / 2 | 16 / 9 |
| evento cancelado que Memora conserva | 5 / 4 | 5 / 4 |
| pendiente implícito | 4 / 12 | 8 / 12 |
| otro nombre en la nota | 4 / 2 | 4 / 2 |
| brecha sin marcadas s1–210 → s421–fin | 8,1 → 4,1 | 5,6 → 2,6 |

- **Las causas de P6 se repiten** con la muestra nueva en `every-1`: 12 → 11, 14 → 16, 5 → 5, 4 → 8, 4 → 4.
- **Lo que cambia es `every-5`.** Los gustos "ya no" bajan de 9 a 1 y los documentos suben de 2 a 9. Juntas, esas dos causas le cuestan a `every-1` frente a `every-5` 15 respuestas en P6 (3 + 12) y 17 en P7c (10 + 7). La suma casi no cambia; cambia cuál de las dos pesa.
- **El tamaño de la compresión depende de pocas decisiones de sueño.** Un gusto que un sueño borra o pasa a dislike, o un post que se titula en forma genérica, se repite en unos 20 exámenes seguidos.

## 5. Opciones descartadas y por qué

- **Comparar solo la cuenta oficial de notas contra la verdad,** sin cruzar pregunta por pregunta: dice cuánto cambió la nota, no cuánto de ese cambio llegó a las respuestas. `flips` hace las dos cosas.
- **Estado del total por "hay alguna línea":** dejaba los 42 totales de marketing_manager en "mismo estado", porque la línea del café seguía ahí aunque faltaba la cena.
- **Prueba t sobre las medias:** con 10 personas y una de ellas a −5,8 por un solo gasto, la normalidad no se sostiene. La permutación exacta no la necesita.
- **Bonferroni sobre la prueba de signos sola:** trata las 10 columnas como independientes, y no lo son. La permutación por persona las mantiene juntas.
- **Leer a mano cada error de las personas enteras:** P6 lo hizo para fijar las causas, y acá se reusan con la correspondencia de §3.2, comprobada contra sus números. Leí solo los casos nuevos de "correct in the notes" para confirmar que caben.

## 6. Limitaciones

- **Ruido o efecto, con 10 personas:** la permutación por persona da 0,115 para "alguna columna con 9 de 10". Eso no descarta un efecto chico; dice que este patrón no alcanza para afirmarlo. Lo que inclina hacia ruido es que no cambió nada medible entre corridas (§4.1), que las notas de las frases no son más variables (§4.4) y que la mitad de la caída es un gasto omitido en un sueño compartido (§4.3).
- **El efecto de fecha no se puede separar:** solo 2 personas tienen la r0 del mismo día que la r1.
- **`compare_notes` empareja por palabras.** Puede dar por buena una línea que el que responde no usa ("otro nombre"), o no atar una línea a su hecho ("título genérico"). Por eso la separación notas/lectura de §4.2 es aproximada: "mismas líneas" usa `related_lines`, que tampoco es exacto para documentos.
- **Las causas de P6 vienen de leer academic_researcher.** En startup_founder la correspondencia es la misma, pero no leí sus casos uno por uno.
- **Una repetición de cada persona entera.** Con la muestra vieja y la nueva, `every-5` cambió 8 respuestas en gustos y 7 en documentos solo por volver a sortear los sueños. La compresión de academic_researcher (−3,1) es de una sola corrida.
- **`PYTHONHASHSEED=0`** en todos los comandos que usan `compare_notes`, por el desempate de `match_documents` (P6 §6).
