# P8b · El sueño con reglas que nombran lo omitido

**Resultado.** Corrí el sueño E de P8a (`dreaming/dream_named.py`) con `triggered-phrases-any`, 10 personas monthly, s1–210, r0 y r1. Pagué $2,7152 de $3,00, contra $2,5819 estimados. Comparé cada hecho con el mismo hecho, en el mismo sueño, de las corridas de P7 con el sueño de P4a.

- **Hace lo que promete.** Las omisiones de las tres clases que ataca bajan de 34 a 9 (−74 %): 30 hechos arreglados y 5 rotos. McNemar exacto da p = 0,013 en r0 y p = 0,0013 en r1.
  - documentos con listas que las reglas no nombraban: 11 → 0;
  - pendientes dichos al pasar: 17 → 6;
  - gustos dichos con otras palabras: 6 → 3.
- **No rompe lo demás.** Las demás omisiones llanas quedan igual (21 → 20), y los borrados no aplicados también (73 → 77, 7 arreglados contra 11 rotos).
- **El examen no empeora; con las 2 repeticiones mejora.** Sin marcadas pasa de 96,4 % a 97,2 %: +0,77 [+0,10, +1,62] puntos de media por persona, con 8 personas que suben, 1 igual y 1 que baja. Las cuatro cuentas dan entre +0,77 y +0,87, todas con IC por encima de 0. Solo con r0 queda plano (−0,01 [−1,41, +1,15]).
- **Las respuestas mal sin marcadas pasan de 408 a 320 (−88).** Las clases atacadas explican 38. Del resto, la mayor parte es ruido de lectura o una edición de gastos que el sueño viejo hacía mal y el nuevo no (§3.3). La cena ambigua de marketing_manager se cancela entre repeticiones: cayó mal una vez con cada sueño.
- **Cuesta más.** Los sueños cuestan un 10,4 % más ($2,1939 contra $1,9865 en las 2 repeticiones). La nota es un 15 % más larga (7.424 contra 6.468 caracteres por sueño) y casi duplica las líneas sin hecho en la verdad (18,4 contra 10,2 por sueño), sobre todo ítems de documentos. Mantener la memoria cuesta ≈ $0,1097 por persona, contra $0,0993 con el sueño viejo y $0,1223 de `every-1` en P7.

| Rol | Ruta |
| --- | --- |
| Tag | `p8` |
| Sueño probado (P8a) | `dreaming/dream_named.py` |
| Motor: `run_policy(..., dream_function=dream, cache_prefix="p5")` | `policies/engine.py`; test `tests/test_engine.py::test_the_default_dream_and_cache_make_the_same_requests_as_before_p8b` |
| Estimación, corrida y comparación | `final/named_dream.py` (`estimate`, `run`, `compare`) |
| Caché nuevo | `results/raw/p8b/r0/`, `r1/`; libro `results/spend/p8b.jsonl` |
| Salidas (ignoradas por git) | `results/p8b/compare.txt`, `compare-r0.txt`, `estimate-before.txt`, `grid-table-check.txt`, `logs/run-r0.txt`, `logs/run-r1.txt` |

## 1. Problema

P8a encontró que el sueño de P4a omite por criterio, no por descuido. Los hechos dichos que deja afuera, sin que nada los retire, se juntan en tres huecos de las reglas:

- pendientes dichos al pasar;
- gustos dichos sin "like" ni "dislike";
- listas de documentos que las reglas no nombraban.

En las dos repeticiones de P7 se omitían casi los mismos hechos. P8a eligió cambiar solo esas tres reglas (sueño E) y estimó P8b en $2,58. P8b tiene que responder:

- ¿Bajan esas omisiones?
- ¿Se rompe otra cosa?
- ¿Empeora el examen?
- ¿Cuánto cuesta?

El techo en el examen era chico (0,41–0,50 puntos por corrida en las frases), así que decidí juzgar con la tasa de omisión emparejada y usar el examen solo para ver que nada empeore.

## 2. Opciones consideradas

| Pregunta | Opciones | Elegida |
| --- | --- | --- |
| Repeticiones | 1 ($1,29) o 2 ($2,58) | 2. Una sola habría engañado: con r0 sola el examen queda plano (§4.3). |
| Cómo corre el motor otro sueño | (a) dos parámetros en `run_policy` con valor por omisión; (b) reemplazar `policies.engine.dream` desde el script | (a), con un test más la reconstrucción byte a byte de los CSV de P7 |
| Línea de base | volver a pagar el sueño viejo, o usar las corridas de P7 | Las de P7. P7c mostró que entre esas corridas no cambió nada del modelo ni de sus ajustes. |
| Medida principal | el examen; los hechos emparejados (mismo hecho, mismo sueño); los hechos sin emparejar | Emparejados: el detector de frases no lee la nota, así que los dos sueños leen las mismas ventanas. McNemar exacto sobre los discordantes. |
| Ruido de referencia | — | Los discordantes entre r0 y r1 del mismo sueño, viejo y nuevo |
| Lo que Memora retira | marcarlo o no | Sin marcar, reportado aparte |

## 3. Análisis y conclusión

### 3.1 Las omisiones atacadas bajan tres cuartos

Tablas "P4a's dream (first) against the named dream (second)" de `compare`, sumando r0 y r1:

| clase | hechos emparejados por repetición | omitidos, sueño viejo | omitidos, sueño E | arreglados | rotos |
| --- | --: | --: | --: | --: | --: |
| documentos, listas no nombradas | 47 | 6 + 5 = 11 | 0 | 11 | 0 |
| pendientes dichos al pasar | 162 | 7 + 10 = 17 | 3 + 3 = 6 | 15 | 4 |
| gustos con otras palabras | 190 | 3 + 3 = 6 | 2 + 1 = 3 | 4 | 1 |
| **las tres** | **399** | **34** | **9** | **30** | **5** |
| resto de lo dicho sin retirar | 1.534 | 9 + 12 = 21 | 11 + 9 = 20 | 4 | 3 |

- **Ruido de referencia:** dos sorteos del sueño viejo discrepan en las tres clases en 10 hechos (4 en un sentido y 6 en el otro), y dos sorteos del sueño E en 3. Que el sueño E arregle 30 y rompa 5 no se explica por sortear de nuevo.
- **Las omisiones que quedan siguen siendo sistemáticas:** de las 5 de r0, r1 repite 3.

### 3.2 Lo demás no se rompe

- **Borrados no aplicados:** 73 → 77 (7 arreglados contra 11 rotos; p = 1,00 en r0 y 0,23 en r1). Los dos sorteos del sueño viejo ya discrepaban en 13. Lo vigilaría: los gustos que el usuario saca pasan de 11 + 11 a 9 + 13, y la regla nueva ("I don't care about X" es dislike) toca ese terreno.
- **Lo que Memora retira, like → dislike, no dicho:** no se mueve más que entre dos sorteos del mismo sueño.
- **`invented` en el examen:** 202 → 184 en las dos repeticiones.

### 3.3 El examen: +0,8 puntos en 2 repeticiones, y de dónde salen

Las respuestas mal sin marcadas (tabla 2 de `compare`), sumando r0 y r1:

| causa (episodios de `final.omissions`) | sueño viejo | sueño E | diferencia |
| --- | --: | --: | --: |
| omitido, dicho sin retirar | 63 | 30 | −33 (las tres clases: 51 → 13, −38) |
| omitido, Memora lo retira | 103 | 103 | 0 |
| omitido, like → dislike | 49 | 40 | −9 |
| omitido, fecha relativa | 14 | 0 | −14 |
| borrado no aplicado | 27 | 29 | +2 |
| perdido después de estar bien | 26 | 19 | −7 |
| sin episodio (lectura) | 126 | 99 | −27 |
| **total** | **408** | **320** | **−88** |

- **La cena de marketing_manager ("a Tuesday night" un domingo)** cayó mal en r1 con el sueño viejo y en r0 con el sueño E. Las dos frases dicen lo mismo y las reglas de gastos no cambiaron. Por eso r0 queda plano y r1 sube 1,56 puntos, y por eso sumar las dos repeticiones la cancela.
- **"Fecha relativa" −14 y parte de "perdido" −7 son un solo caso.** En creative_designer s47 el usuario dice "$15.84 on dinner last night". En las 2 corridas viejas de las frases (y en la r0 de `every-1`), esos totales salen mal. En la r0 de las frases leí la causa: el sueño reemplazó en la nota la cena real del 2025-06-01 ($20,45) por la nueva, y los totales de la semana quedaron cortos. P8a repartió esos totales entre el episodio de fecha relativa y el de la cena perdida. En las 2 corridas nuevas el sueño agregó la línea sin borrar la otra, y el total da 95,98. Las reglas de gastos son las mismas, así que no atribuyo esta diferencia al arreglo.
- **"Sin episodio" −27** está dentro de lo que se mueve entre dos sorteos del sueño viejo (53 en r0, 73 en r1). Son respuestas con el hecho bien en la nota.
- **Lo atribuible al arreglo son las 38 respuestas de las tres clases**, 0,34 puntos de 11.276. El IC del examen (+0,10 a +1,62) también incluye lo de arriba, que es suerte de este par de sorteos.

### 3.4 Costo: la nota más completa es más larga

| | sueño viejo (P7, r0 + r1) | sueño E (r0 + r1) | cambio |
| --- | --: | --: | --: |
| costo de los sueños | $1,9865 | $2,1939 | +10,4 % |
| costo de los exámenes | $0,5020 | $0,5214 | +3,9 % |
| tokens de salida por sueño | 347 | 383 | +10 % |
| caracteres de la nota, media por sueño | 6.468 | 7.424 | +15 % |
| líneas sin hecho en la verdad, por sueño | 10,2 | 18,4 | ×1,8 |
| de ellas, documentos / gustos / pendientes | 6,4 / 3,5 / 0,1 | 12,3 / 5,0 / 0,8 | |
| líneas de prosa por sueño | 1,2 | 1,0 | |

- **Las líneas de más son sobre todo ítems de documentos.** Es lo esperable de "every list it has, whatever the list is called". Memora no guarda todas las listas, y `compare_notes` no las empareja con nada.
- **Los pendientes de más son 0,8 por sueño.** P8a calculó hasta 100 turnos candidatos en s1–210; los turnos de despedida y los pedidos de cambiar un documento quedaron afuera, como pedía la regla.
- **La nota más larga encarece cada sueño y cada examen siguientes.** Aun así, las frases con el sueño E ($0,1097 por persona) cuestan menos que `every-1` con el sueño viejo ($0,1223, P7).

### 3.5 Conclusión

- **El sueño E corrige lo que P8a diagnosticó.** Tres cuartos de las omisiones atacadas desaparecen, en las dos repeticiones y por encima del ruido. No se rompe nada medible.
- **El examen no empeora con ninguna de las 4 cuentas, y en 2 repeticiones sube 0,8 puntos.** De eso, 0,34 es atribuible al arreglo y el resto es azar de este par de sorteos.
- **El precio es un 10 % más en los sueños y notas un 15 % más largas.**
- **Recomiendo adoptarlo como el sueño de `triggered-phrases-any`.** La pregunta de Lance Martin no cambia: soñar cuando el detector de frases ve un hecho sigue siendo la política barata que rinde como `every-1`, ahora con menos omisiones. Lo que queda de las omisiones es casi todo de Memora (lo que el usuario retira, like → dislike), y P8 no lo persigue.

## 4. Prueba/corrida

### 4.1 El motor nuevo con los valores por omisión reproduce P7

```
$ PYTHONHASHSEED=0 uv run python -m final.grid table > results/p8b/grid-table-check.txt
data/p7-runs.csv: 152 rows; data/p7-probes.csv: 3724 rows
not fully cached, left out (0):
$ git diff --stat data/        # vacío
$ cmp data/p7-runs.csv data/p7-runs-final-2853c99.csv && cmp data/p7-probes.csv data/p7-probes-final-2853c99.csv && echo identical
identical
$ uv run pytest -q
56 passed
```

### 4.2 Estimación y corrida

```
$ PYTHONHASHSEED=0 uv run python -m final.named_dream estimate        # antes de pagar
| academic_researcher | 0 | 159 | 30 | 0.1390 |
...
| startup_founder | 1 | 156 | 30 | 0.1314 |
total still to pay: $2.5819; p8b spent so far: $0.0000

$ PYTHONHASHSEED=0 uv run python -m final.named_dream run --repetition 0 --limit 3.00 > results/p8b/logs/run-r0.txt
academic_researcher r0: done, 159 dreams, $0.1420 this persona, p8b spent $0.1420
...
startup_founder r0: done, 156 dreams, $0.1435 this persona, p8b spent $1.3606
$ PYTHONHASHSEED=0 uv run python -m final.named_dream run --repetition 1 --limit 3.00 > results/p8b/logs/run-r1.txt
academic_researcher r1: done, 159 dreams, $0.1380 this persona, p8b spent $1.4987
...
startup_founder r1: done, 156 dreams, $0.1430 this persona, p8b spent $2.7152

$ PYTHONHASHSEED=0 uv run python -m final.named_dream estimate | tail -1
total still to pay: $0.0000; p8b spent so far: $2.7152
```

- **Sin incidentes:** no hubo timeouts, ni el 400 de límite, ni reinicios.
- **El código que pagó está commiteado** en d278f02 (motor, runner, `final/omissions.py`). Lo commiteé durante la r0, con el mismo contenido que ya corría. La sección 4 de `compare` y la columna "no episode" se agregaron después de la corrida y solo leen el caché.

| | estimado | pagado |
| --- | --: | --: |
| r0 | 1,2910 | 1,3606 |
| r1 | 1,2910 | 1,3546 |
| **total** (libro `results/spend/p8b.jsonl`) | **2,5819** | **2,7152** de 3,00 (+5,2 %) |

El modelo de costo de P5 (fijo en `final/grid.py`) supone notas del largo de las perfectas, y el sueño E las escribe un 15 % más largas: de ahí sale el +5 %.

### 4.3 Comparación

```
$ PYTHONHASHSEED=0 uv run python -m final.named_dream compare > results/p8b/compare.txt
### P4a's dream (first) against the named dream (second), r0
| said, plain, aimed at | all | 399 | 16 | 5 | 14 | 3 | 2 | 0.0127 |
| said, plain, other | all | 1534 | 9 | 11 | 1 | 3 | 8 | 0.6250 |
| removal | all | 376 | 38 | 37 | 4 | 3 | 34 | 1.0000 |
### P4a's dream (first) against the named dream (second), r1
| said, plain, aimed at | all | 399 | 18 | 4 | 16 | 2 | 2 | 0.0013 |
| said, plain, aimed at | content | 47 | 5 | 0 | 5 | 0 | 0 | 0.0625 |
| said, plain, aimed at | todo | 162 | 10 | 3 | 9 | 2 | 1 | 0.0654 |
| said, plain, other | all | 1534 | 12 | 9 | 3 | 0 | 9 | 0.2500 |
| removal | all | 376 | 35 | 40 | 3 | 8 | 32 | 0.2266 |
### noise: P4a's dream r0 (first) against P4a's dream r1 (second)
| said, plain, aimed at | all | 399 | 16 | 18 | 4 | 6 | 12 | 0.7539 |
### noise: the named dream r0 (first) against the named dream r1 (second)
| said, plain, aimed at | all | 399 | 5 | 4 | 2 | 1 | 3 | 1.0000 |

## 3. The exam, four counts (s1-210, 10 personas)
| official | 0 | 5475/5786 (94.6%) | 5481/5786 (94.7%) | +0.08 [-1.37, +1.32] | 5 / 1 / 4 |
| official | 1 | 5420/5786 (93.7%) | 5513/5786 (95.3%) | +1.60 [+0.37, +3.01] | 7 / 0 / 3 |
| official | both | 10895/11572 (94.1%) | 10994/11572 (95.0%) | +0.84 [+0.13, +1.72] | 8 / 1 / 1 |
| lenient | both | 10909/11572 (94.3%) | 11011/11572 (95.2%) | +0.87 [+0.16, +1.75] | 8 / 0 / 2 |
| official without marked | 0 | 5462/5638 (96.9%) | 5462/5638 (96.9%) | -0.01 [-1.41, +1.15] | 6 / 0 / 4 |
| official without marked | 1 | 5406/5638 (95.9%) | 5494/5638 (97.4%) | +1.56 [+0.35, +2.96] | 7 / 0 / 3 |
| official without marked | both | 10868/11276 (96.4%) | 10956/11276 (97.2%) | +0.77 [+0.10, +1.62] | 8 / 1 / 1 |
| lenient without marked | both | 10882/11276 (96.5%) | 10973/11276 (97.3%) | +0.80 [+0.12, +1.64] | 8 / 0 / 2 |

## 4. Outcomes of the exam answers, and what the notes hold beyond the truth (mean per dream)
| old | 0 | 5475 | 145 | 77 | 89 | 0 | 6,466 | 3.71 | 0.17 | 6.20 | 0.13 | 10.26 | 1.34 |
| old | 1 | 5420 | 170 | 83 | 113 | 0 | 6,470 | 3.29 | 0.08 | 6.51 | 0.23 | 10.16 | 1.15 |
| new | 0 | 5481 | 130 | 75 | 100 | 0 | 7,474 | 5.20 | 0.85 | 13.46 | 0.23 | 19.85 | 0.62 |
| new | 1 | 5513 | 120 | 69 | 84 | 0 | 7,373 | 4.73 | 0.74 | 11.22 | 0.13 | 16.85 | 1.47 |

## 5. Cost of the runs
| old | 0 | 1577 | 0.9953 | 0.2497 | 349 |
| old | 1 | 1577 | 0.9912 | 0.2523 | 345 |
| new | 0 | 1577 | 1.0993 | 0.2614 | 383 |
| new | 1 | 1577 | 1.0946 | 0.2600 | 384 |
p8b ledger: $2.7152
```

"..." marca filas recortadas; las tablas completas están en `results/p8b/compare.txt`, que se regenera con el mismo comando y tope $0.

**Lo que leí a mano:**

- **La cena de marketing_manager:** el primer sueño E de r0 anota `- 2025-05-27 dinner: $20.27`, igual que el sueño viejo en r1.
- **La cena de creative_designer s47:** las notas de la s49 con el sueño viejo r0 no tienen `2025-06-01 dinner: $20.45`, y las del sueño E sí. Respuestas al total: 75.53 contra 95.98 esperado.

## 5. Opciones descartadas y por qué

| Opción | Por qué no | Dónde |
| --- | --- | --- |
| Una sola repetición | Con r0 sola el examen da −0,01 y la cena de marketing_manager tapa el efecto. Las omisiones emparejadas sí se veían (p = 0,013). | §4.3 |
| Volver a pagar el sueño viejo como control simultáneo | P7c mostró que modelo, thinking, effort y `repeat` son iguales entre corridas. Las corridas de P7 sirven y costaban $2,49 más. | P7c §4.1 |
| Reemplazar `policies.engine.dream` desde el script | Elegí los parámetros. Con ellos el caché nuevo queda en `p8b/` y no se mezcla con el de P7. | §2 |
| Atribuir al arreglo toda la mejora del examen | Solo 38 de las 88 respuestas son de las clases atacadas. La fecha relativa, la cena de marketing_manager y "sin episodio" se mueven igual entre dos sorteos del sueño viejo. | §3.3 |
| Seguir con la lista previa (C de P8a) | No hace falta: E ya corrige tres cuartos de su blanco, y lo que queda es casi todo de Memora | §3.5 |

## 6. Limitaciones

- **Muestra:** 10 personas, s1–210, una política, 2 repeticiones y un modelo (Haiku 5.5). No medí el sueño E con `every-1` ni sobre personas enteras. Las omisiones tardías de academic_researcher (P7c parte 2) no están en esta muestra.
- **El emparejamiento hecho por hecho usa `compare_notes`** y hereda sus límites (P8a §6). Un ítem de documento puede contar como arreglado si una línea nueva comparte la mitad de sus raíces.
- **La regla de gustos nueva toca los borrados.** Los gustos que el usuario saca y la nota conserva pasan de 22 a 22 en total, pero con 7 arreglados y 11 rotos entre todos los borrados. No alcanza para decir que empeora; vale mirarlo si el sueño E pasa a personas enteras.
- **La nota más larga se acumula.** En s1–210 suma un 15 %. En una persona entera puede pesar más en el costo y en lo que el que responde tiene que leer. P6 mostró que la exactitud de la nota no cae con el largo, pero con el sueño viejo.
- **Corrección a P8a:** las 21 respuestas de "fecha relativa" de P8a §3.1 son la mitad de los totales que rompió un reemplazo del sueño viejo (la cena de creative_designer s47 sobre la del 2025-06-01). No son de la fecha de Memora sola. Esos totales se reparten por igual entre los episodios que cubren su rango, y este caso muestra que ese reparto puede cargarle a un episodio un total que no cambia.
- **Lo que Memora retira (207 respuestas en P7) sigue sin marcar**, como decidí. Es lo que más pesa entre los errores que quedan, junto con like → dislike.

### Decisión abierta

**Adoptar el sueño E.** Las opciones son:

- **(a) Adoptarlo como el sueño del agente**, y declarar en el informe final que la recomendación "soñar cuando el detector de frases ve un hecho" se midió con el sueño de P4a en P7 y con el sueño E en P8b (frases solamente).
- **(b) Dejar el de P4a** y reportar P8b como una mejora medida aparte.

Recomiendo (a): corrige el error principal del sueño con un costo que sigue por debajo de `every-1`.

## Recomendación adoptada

Decisión (2026-11-14): opción (a). **El agente recomendado es `triggered-phrases-any` con el sueño E** (`dreaming/dream_named.py`).

- **Con qué se midió cada cosa:**
  - **La comparación entre políticas (P7)** usó el sueño de P4a (`dreaming/dream.py`): 7 políticas, 10 personas, 2 repeticiones. Ahí las frases rinden como `every-1` y cuestan el 81 %.
  - **El sueño E se midió solo con las frases**, en P8b: 10 personas, s1–210, 2 repeticiones, contra las corridas de las frases de P7.
- **Qué no se midió:**
  - El sueño E con las otras 6 políticas (`never`, `every-1`, `every-5`, `every-10`, `every-20`, `every-50`). Que las frases sigan rindiendo como `every-1` con el sueño E es una suposición: los dos usan el mismo sueño, pero no se midió.
  - El sueño E sobre personas enteras (más allá de s1–210).
- **El código no cambia de valor por omisión.** `run_policy` sigue usando `dreaming.dream.dream` y el caché `p5`, para que las corridas de P7 se reconstruyan idénticas desde el caché (§4.1). El sueño E se pasa explícito: `dream_function=dreaming.dream_named.dream`.
