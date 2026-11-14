# P7a · Corrida final (re-corrida sin caché)

**Estado (14/11): grilla completa.** Están las 140 corridas s1–210 (10 personas × 7 políticas × 2 repeticiones) y las 4 personas enteras. La corrida se cortó dos veces por el límite de uso de la organización, una vez por un reinicio del daemon del host y tres veces por timeouts de red. Cada vez se retomó desde el caché (§4.2).

- **Hecho:** las repeticiones 0 y 1 de las 10 personas y las 4 personas enteras (2a y 2b). `table` no deja ninguna corrida afuera: `data/p7-runs.csv` tiene 152 filas y `data/p7-probes.csv` 3.724.
- **Validación contra los números de antes del borrado:** los 5 conteos exactos coinciden en las 23 filas. La precisión oficial queda dentro de 2,8 puntos en 22 filas, y `every-10` de academic_researcher se movió −3,0 (se reporta y se sigue). El orden de las fijas se mantiene.
- **Costo:** p7a pagó $11,8724 de $13,00, contra $12,0752 estimados (−1,7 %). La repetición 0 costó $5,2043 contra $5,2751 (−1,3 %), las 4 enteras $1,4349 contra $1,5249 (−5,9 %) y la repetición 1 $5,2331 contra $5,2751 (−0,8 %).
- **Orden de las fijas:** every-1 > 5 > 10 > 20 > 50 > never en precisión oficial, en las 10 personas y las 2 repeticiones (tabla de §4.4).
- **Personas enteras:** la brecha every-1 − every-5 sin marcadas se achica en el último tramo de academic_researcher (+5,6 → +6,3 → +2,6 puntos, restando conteos y no porcentajes redondeados, `docs/p7/tables.md`), pero no en startup_founder (+5,9 → +9,5 → +6,4) (§4.5).

| Rol | Ruta |
| --- | --- |
| Tag | `p7` |
| Contrato | `docs/p7-interfaz.md` |
| Código (estimación, corrida, CSV, comparación) | `final/grid.py` |
| Test nuevo | `tests/test_grid.py` (1: un conteo que se mueve para, un corrimiento de 4 puntos se reporta) |
| CSV para P7b | `data/p7-runs.csv`, `data/p7-probes.csv` |
| Números de antes del borrado | `data/p7-runs-before-loss.csv` (no se toca) |
| Caché y libro de gasto (ignorados por git) | `results/raw/p5/r0/`, `results/raw/p5/r1/`, `results/spend/p7a.jsonl` |
| Salida de cada `run` (ignorada por git) | `results/logs/` |

## 1. Problema

P7 corre la grilla final de las decisiones de P6 (`docs/p6-inventadas.md` § "Decisiones"): 10 personas monthly × 7 políticas × s1–210 × 2 repeticiones, más `every-1` y `every-5` sobre startup_founder y academic_researcher enteras.

El 13/11 se borraron los worktrees de P7 y del P7a anterior, y con ellos `results/`: el caché unificado de P5+P6 y los libros de gasto, que estaban en `.gitignore`. No hay copia. Eso cambió tres cosas:

- **Toda llamada se paga de nuevo,** incluidas las 3 corridas enteras que P5 y P6b ya habían pagado (paso 2b). Decidí volver a pagarlas.
- **La estimación no puede ajustar el modelo de costo** sobre el caché. Usa el de P5 fijo en `final/grid.py` (`DREAM_MODEL`, `EXAM_MODEL`, `docs/p5-politicas.md` §4.3).
- **"Idéntica a P5/P6 desde el caché" ya no se puede comprobar.** Una corrida nueva vuelve a muestrear los sueños y las respuestas. La validación pasa a ser la de `docs/p7-interfaz.md` § Validación: conteos exactos iguales y precisión dentro del ruido.

## 2. Opciones consideradas

- **Validar comparando el CSV nuevo contra `data/p7-runs-before-loss.csv`,** por (persona, política, alcance, tramo). Es lo que fija el contrato.
- **Umbral de la precisión:** el ruido de una política repetida entera, hasta 2,8 puntos (`docs/p5a-cadencias-fijas.md` §4.4), y el doble (5,6) para parar. El ruido del que responde con notas fijas es menor (≤ 1,2 pp, `docs/p3b-techo-piso-ruido.md` §4.3), pero acá también cambian los sueños.
- **Dónde poner la comparación:** un subcomando de `final/grid.py` o un módulo aparte en `final/`.
- **Ante un timeout de red:** parar y avisar, o retomar desde el caché. Fijé la regla durante la corrida: retomar una vez, y parar si la misma llamada vuelve a dar timeout.

## 3. Análisis y elección

- **`compare` como subcomando de `final/grid.py`.** Lee los dos CSV con la librería estándar y no llama a la API ni al motor. Va junto a `estimate`, `run` y `table` porque comparte el esquema y las constantes de la grilla.
- **Qué compara:**
  - Exactos: `sessions`, `dreams`, `sessions_read`, `exams`, `asked`. Las fijas y el detector de frases deciden sin leer las notas (`policies/projection.py`), así que una diferencia acá es un bug.
  - Precisión oficial (`official / asked`) en puntos: `ok` hasta 2,8, `report` hasta 5,6, `stop` más allá o si se movió un conteo exacto. Sale con código 1 si hay algún `stop`.
  - Orden de las fijas sobre s1–210: every-1 > 5 > 10 > 20 > 50 > never, antes y después.
- **Test:** uno solo, anclado en la fila real de `every-5` de academic_researcher (529/593, P5 §4.1). 505/593 queda a 4,0 puntos y da `report`. Un `dreams` de 209 en `every-1` da `stop`.
- **Orquestación:** cada corrida es `final.grid run`, una a la vez, seguida de `table` y un commit de los CSV. Los scripts de shell que las encadenan viven en `results/logs/` (ignorado por git). Solo llaman a los comandos commiteados y no producen ningún número del informe.

## 4. Prueba

### 4.1 Estado y estimación

```
$ uv run pytest -q
52 passed

$ PYTHONHASHSEED=0 uv run python -m final.grid estimate
| 1. s1-210 r0 | software_engineer | 436 | 199 | 0.4961 |
| 1. s1-210 r0 | content_writer | 433 | 200 | 0.5108 |
| 1. s1-210 r0 | marketing_manager | 448 | 200 | 0.5136 |
| 1. s1-210 r0 | business_executive | 442 | 200 | 0.5155 |
| 1. s1-210 r0 | creative_designer | 441 | 199 | 0.5157 |
| 1. s1-210 r0 | management_consultant | 442 | 200 | 0.5206 |
| 1. s1-210 r0 | startup_founder | 439 | 200 | 0.5364 |
| 1. s1-210 r0 | financial_analyst | 439 | 200 | 0.5387 |
| 1. s1-210 r0 | academic_researcher | 443 | 200 | 0.5624 |
| 1. s1-210 r0 | sales_manager | 450 | 200 | 0.5653 |
| 2a. whole r0 | startup_founder every-1 | 396 | 56 | 0.5210 |
| 2b. whole r0, paid before by P5/P6 | startup_founder every-5 | 79 | 56 | 0.2214 |
| 2b. whole r0, paid before by P5/P6 | academic_researcher every-1 | 409 | 58 | 0.5503 |
| 2b. whole r0, paid before by P5/P6 | academic_researcher every-5 | 81 | 58 | 0.2322 |
| 3. s1-210 r1 | (las mismas 10, los mismos montos) | | | 5.2751 |
total: s1-210 r0 $5.2751 + whole r0, new $0.5210 + whole r0, paid before $1.0039 + s1-210 r1 $5.2751 = $12.0752
```

El total entra en el tope de $13,00. Revisé la estimación antes de gastar nada.

### 4.2 Corridas e interrupciones

Cada corrida es `PYTHONHASHSEED=0 uv run python -m final.grid run monthly/<persona>:210 --repetition <0|1> --limit 13.00`. Las enteras son `run monthly/<persona> --repetition 0 --limit 13.00 --policies <every-1|every-5>`.

- **13/11 17:05, primer corte por el límite de la organización,** en startup_founder r0 `every-1`. No reintenté, corrí `table` y commiteé (670f08c). Se retomó cuando subí el límite a $25.
- **13/11 21:55, timeout de lectura** (`httpx.ReadTimeout`) en creative_designer r0 `every-50`. Se retomó desde el caché, y lo que faltaba se pagó sin otro timeout.
- **14/11, timeout de lectura** en financial_analyst r0 `every-10`. Se retomó una vez, sin otro timeout.
- **14/11 05:44, segundo corte por el límite de la organización,** en content_writer r1 `triggered-phrases-any`. No reintenté. `table` y commit (52f9094). Se retomó a las 09:21, cuando subí el límite a unos $30.
- **14/11 09:54, reinicio del daemon del host:** mató la corrida de marketing_manager r1 después de `every-5`, sin error de la API. Se retomó a las 10:20 desde el caché.
- **14/11, timeout de lectura** en management_consultant r1, durante `every-1`. Se retomó una vez, sin otro timeout.

### 4.3 Validación contra los números de antes del borrado

```
$ uv run python -m final.grid compare
| persona | policy | scope | stretch | exact columns that moved | official before | official after | difference (points) | verdict |
| academic_researcher | never | s1-210 | s1-210 | none | 23.9 % | 23.9 % | +0.0 | ok |
| academic_researcher | every-1 | s1-210 | s1-210 | none | 97.1 % | 96.1 % | -1.0 | ok |
| academic_researcher | every-5 | s1-210 | s1-210 | none | 89.2 % | 90.6 % | +1.3 | ok |
| academic_researcher | every-10 | s1-210 | s1-210 | none | 82.3 % | 79.3 % | -3.0 | report |
| academic_researcher | every-20 | s1-210 | s1-210 | none | 76.1 % | 76.1 % | +0.0 | ok |
| academic_researcher | every-50 | s1-210 | s1-210 | none | 59.2 % | 60.5 % | +1.3 | ok |
| academic_researcher | triggered-phrases-any | s1-210 | s1-210 | none | 96.1 % | 97.6 % | +1.5 | ok |
| startup_founder | never | s1-210 | s1-210 | none | 24.8 % | 24.8 % | +0.0 | ok |
| startup_founder | every-1 | s1-210 | s1-210 | none | 89.7 % | 90.0 % | +0.3 | ok |
| startup_founder | every-5 | s1-210 | s1-210 | none | 84.7 % | 84.5 % | -0.2 | ok |
| startup_founder | every-10 | s1-210 | s1-210 | none | 78.3 % | 77.6 % | -0.7 | ok |
| startup_founder | every-20 | s1-210 | s1-210 | none | 70.7 % | 69.4 % | -1.4 | ok |
| startup_founder | every-50 | s1-210 | s1-210 | none | 53.7 % | 52.8 % | -0.9 | ok |
| startup_founder | triggered-phrases-any | s1-210 | s1-210 | none | 88.6 % | 90.4 % | +1.7 | ok |
| startup_founder | every-5 | whole | s1-210 | none | 84.7 % | 84.5 % | -0.2 | ok |
| startup_founder | every-5 | whole | s211-420 | none | 85.4 % | 84.8 % | -0.6 | ok |
| startup_founder | every-5 | whole | s421-end | none | 89.5 % | 88.4 % | -1.1 | ok |
| academic_researcher | every-1 | whole | s1-210 | none | 97.1 % | 96.1 % | -1.0 | ok |
| academic_researcher | every-1 | whole | s211-420 | none | 94.7 % | 94.8 % | +0.2 | ok |
| academic_researcher | every-1 | whole | s421-end | none | 87.4 % | 85.7 % | -1.7 | ok |
| academic_researcher | every-5 | whole | s1-210 | none | 89.2 % | 90.6 % | +1.3 | ok |
| academic_researcher | every-5 | whole | s211-420 | none | 88.7 % | 88.5 % | -0.2 | ok |
| academic_researcher | every-5 | whole | s421-end | none | 83.4 % | 83.1 % | -0.3 | ok |

order every-1 > 5 > 10 > 20 > 50 > never, s1-210 official:
- academic_researcher: before holds, after holds
- startup_founder: before holds, after holds

verdicts: 22 ok, 1 report (over 2.8 points), 0 stop (a count moved or over 5.6 points)
```

- **Conteos exactos:** iguales en las 23 filas, incluidas las 3 corridas enteras de 2b por tramo.
- **`every-10` de academic_researcher, −3,0 puntos:** apenas pasa el ruido de P5a (2,8). La distancia a sus vecinas sigue siendo amplia: 11,3 puntos bajo every-5 y 3,2 sobre every-20, así que el orden no cambia. En la repetición 1 dio 82,1 % (tabla de §4.4), casi lo de antes del borrado (82,3 %). El −3,0 se explica por el ruido de una repetición.

### 4.4 La grilla s1–210 (4 cuentas)

```
$ PYTHONHASHSEED=0 uv run python -m final.grid table
data/p7-runs.csv: 152 rows; data/p7-probes.csv: 3724 rows
not fully cached, left out (0):
```

Columnas de la salida de `table`, con coma decimal. `mantenimiento $` son los sueños más el detector, sin exámenes.

| persona | política | rep | sueños | mantenimiento $ | oficial | indulgente | oficial sin marcadas | indulgente sin marcadas |
| --- | --- | --: | --: | --: | --: | --: | --: | --: |
| academic_researcher | never | 0 | 0 | 0,0000 | 142/593 (23,9 %) | 142/593 (23,9 %) | 142/585 (24,3 %) | 142/585 (24,3 %) |
| academic_researcher | every-1 | 0 | 210 | 0,1232 | 570/593 (96,1 %) | 570/593 (96,1 %) | 569/585 (97,3 %) | 569/585 (97,3 %) |
| academic_researcher | every-5 | 0 | 42 | 0,0502 | 537/593 (90,6 %) | 537/593 (90,6 %) | 536/585 (91,6 %) | 536/585 (91,6 %) |
| academic_researcher | every-10 | 0 | 21 | 0,0398 | 470/593 (79,3 %) | 470/593 (79,3 %) | 470/585 (80,3 %) | 470/585 (80,3 %) |
| academic_researcher | every-20 | 0 | 10 | 0,0327 | 451/593 (76,1 %) | 451/593 (76,1 %) | 451/585 (77,1 %) | 451/585 (77,1 %) |
| academic_researcher | every-50 | 0 | 4 | 0,0277 | 359/593 (60,5 %) | 359/593 (60,5 %) | 358/585 (61,2 %) | 358/585 (61,2 %) |
| academic_researcher | triggered-phrases-any | 0 | 159 | 0,1012 | 579/593 (97,6 %) | 579/593 (97,6 %) | 578/585 (98,8 %) | 578/585 (98,8 %) |
| business_executive | never | 0 | 0 | 0,0000 | 151/548 (27,6 %) | 151/548 (27,6 %) | 151/537 (28,1 %) | 151/537 (28,1 %) |
| business_executive | every-1 | 0 | 210 | 0,1142 | 517/548 (94,3 %) | 518/548 (94,5 %) | 516/537 (96,1 %) | 517/537 (96,3 %) |
| business_executive | every-5 | 0 | 42 | 0,0473 | 475/548 (86,7 %) | 476/548 (86,9 %) | 475/537 (88,5 %) | 476/537 (88,6 %) |
| business_executive | every-10 | 0 | 21 | 0,0371 | 438/548 (79,9 %) | 438/548 (79,9 %) | 438/537 (81,6 %) | 438/537 (81,6 %) |
| business_executive | every-20 | 0 | 10 | 0,0302 | 402/548 (73,4 %) | 402/548 (73,4 %) | 402/537 (74,9 %) | 402/537 (74,9 %) |
| business_executive | every-50 | 0 | 4 | 0,0267 | 315/548 (57,5 %) | 315/548 (57,5 %) | 313/537 (58,3 %) | 313/537 (58,3 %) |
| business_executive | triggered-phrases-any | 0 | 160 | 0,0943 | 525/548 (95,8 %) | 526/548 (96,0 %) | 524/537 (97,6 %) | 525/537 (97,8 %) |
| content_writer | never | 0 | 0 | 0,0000 | 146/614 (23,8 %) | 146/614 (23,8 %) | 146/601 (24,3 %) | 146/601 (24,3 %) |
| content_writer | every-1 | 0 | 210 | 0,1291 | 549/614 (89,4 %) | 550/614 (89,6 %) | 549/601 (91,3 %) | 550/601 (91,5 %) |
| content_writer | every-5 | 0 | 42 | 0,0482 | 514/614 (83,7 %) | 515/614 (83,9 %) | 514/601 (85,5 %) | 515/601 (85,7 %) |
| content_writer | every-10 | 0 | 21 | 0,0387 | 490/614 (79,8 %) | 490/614 (79,8 %) | 490/601 (81,5 %) | 490/601 (81,5 %) |
| content_writer | every-20 | 0 | 10 | 0,0310 | 434/614 (70,7 %) | 434/614 (70,7 %) | 433/601 (72,0 %) | 433/601 (72,0 %) |
| content_writer | every-50 | 0 | 4 | 0,0256 | 349/614 (56,8 %) | 349/614 (56,8 %) | 347/601 (57,7 %) | 347/601 (57,7 %) |
| content_writer | triggered-phrases-any | 0 | 147 | 0,0983 | 550/614 (89,6 %) | 551/614 (89,7 %) | 549/601 (91,3 %) | 550/601 (91,5 %) |
| creative_designer | never | 0 | 0 | 0,0000 | 153/596 (25,7 %) | 153/596 (25,7 %) | 153/581 (26,3 %) | 153/581 (26,3 %) |
| creative_designer | every-1 | 0 | 210 | 0,1204 | 558/596 (93,6 %) | 558/596 (93,6 %) | 556/581 (95,7 %) | 556/581 (95,7 %) |
| creative_designer | every-5 | 0 | 42 | 0,0490 | 527/596 (88,4 %) | 527/596 (88,4 %) | 525/581 (90,4 %) | 525/581 (90,4 %) |
| creative_designer | every-10 | 0 | 21 | 0,0395 | 487/596 (81,7 %) | 487/596 (81,7 %) | 487/581 (83,8 %) | 487/581 (83,8 %) |
| creative_designer | every-20 | 0 | 10 | 0,0322 | 440/596 (73,8 %) | 440/596 (73,8 %) | 434/581 (74,7 %) | 434/581 (74,7 %) |
| creative_designer | every-50 | 0 | 4 | 0,0280 | 336/596 (56,4 %) | 336/596 (56,4 %) | 336/581 (57,8 %) | 336/581 (57,8 %) |
| creative_designer | triggered-phrases-any | 0 | 161 | 0,0972 | 552/596 (92,6 %) | 552/596 (92,6 %) | 552/581 (95,0 %) | 552/581 (95,0 %) |
| financial_analyst | never | 0 | 0 | 0,0000 | 146/565 (25,8 %) | 146/565 (25,8 %) | 146/559 (26,1 %) | 146/559 (26,1 %) |
| financial_analyst | every-1 | 0 | 210 | 0,1233 | 542/565 (95,9 %) | 542/565 (95,9 %) | 542/559 (97,0 %) | 542/559 (97,0 %) |
| financial_analyst | every-5 | 0 | 42 | 0,0499 | 498/565 (88,1 %) | 498/565 (88,1 %) | 497/559 (88,9 %) | 497/559 (88,9 %) |
| financial_analyst | every-10 | 0 | 21 | 0,0401 | 461/565 (81,6 %) | 462/565 (81,8 %) | 460/559 (82,3 %) | 461/559 (82,5 %) |
| financial_analyst | every-20 | 0 | 10 | 0,0320 | 416/565 (73,6 %) | 416/565 (73,6 %) | 416/559 (74,4 %) | 416/559 (74,4 %) |
| financial_analyst | every-50 | 0 | 4 | 0,0287 | 336/565 (59,5 %) | 336/565 (59,5 %) | 336/559 (60,1 %) | 336/559 (60,1 %) |
| financial_analyst | triggered-phrases-any | 0 | 152 | 0,1004 | 546/565 (96,6 %) | 547/565 (96,8 %) | 546/559 (97,7 %) | 547/559 (97,9 %) |
| management_consultant | never | 0 | 0 | 0,0000 | 148/583 (25,4 %) | 148/583 (25,4 %) | 148/545 (27,2 %) | 148/545 (27,2 %) |
| management_consultant | every-1 | 0 | 210 | 0,1202 | 531/583 (91,1 %) | 532/583 (91,3 %) | 525/545 (96,3 %) | 526/545 (96,5 %) |
| management_consultant | every-5 | 0 | 42 | 0,0467 | 506/583 (86,8 %) | 507/583 (87,0 %) | 503/545 (92,3 %) | 504/545 (92,5 %) |
| management_consultant | every-10 | 0 | 21 | 0,0367 | 453/583 (77,7 %) | 453/583 (77,7 %) | 448/545 (82,2 %) | 448/545 (82,2 %) |
| management_consultant | every-20 | 0 | 10 | 0,0309 | 412/583 (70,7 %) | 412/583 (70,7 %) | 409/545 (75,0 %) | 409/545 (75,0 %) |
| management_consultant | every-50 | 0 | 4 | 0,0273 | 342/583 (58,7 %) | 342/583 (58,7 %) | 337/545 (61,8 %) | 337/545 (61,8 %) |
| management_consultant | triggered-phrases-any | 0 | 156 | 0,0962 | 545/583 (93,5 %) | 547/583 (93,8 %) | 539/545 (98,9 %) | 541/545 (99,3 %) |
| marketing_manager | never | 0 | 0 | 0,0000 | 153/572 (26,7 %) | 153/572 (26,7 %) | 153/569 (26,9 %) | 153/569 (26,9 %) |
| marketing_manager | every-1 | 0 | 210 | 0,1278 | 553/572 (96,7 %) | 554/572 (96,9 %) | 553/569 (97,2 %) | 554/569 (97,4 %) |
| marketing_manager | every-5 | 0 | 42 | 0,0505 | 493/572 (86,2 %) | 494/572 (86,4 %) | 493/569 (86,6 %) | 494/569 (86,8 %) |
| marketing_manager | every-10 | 0 | 21 | 0,0406 | 450/572 (78,7 %) | 450/572 (78,7 %) | 450/569 (79,1 %) | 450/569 (79,1 %) |
| marketing_manager | every-20 | 0 | 10 | 0,0314 | 415/572 (72,6 %) | 415/572 (72,6 %) | 415/569 (72,9 %) | 415/569 (72,9 %) |
| marketing_manager | every-50 | 0 | 4 | 0,0276 | 332/572 (58,0 %) | 332/572 (58,0 %) | 332/569 (58,3 %) | 332/569 (58,3 %) |
| marketing_manager | triggered-phrases-any | 0 | 163 | 0,1028 | 560/572 (97,9 %) | 561/572 (98,1 %) | 560/569 (98,4 %) | 561/569 (98,6 %) |
| sales_manager | never | 0 | 0 | 0,0000 | 148/573 (25,8 %) | 148/573 (25,8 %) | 148/569 (26,0 %) | 148/569 (26,0 %) |
| sales_manager | every-1 | 0 | 210 | 0,1243 | 561/573 (97,9 %) | 561/573 (97,9 %) | 561/569 (98,6 %) | 561/569 (98,6 %) |
| sales_manager | every-5 | 0 | 42 | 0,0496 | 510/573 (89,0 %) | 510/573 (89,0 %) | 510/569 (89,6 %) | 510/569 (89,6 %) |
| sales_manager | every-10 | 0 | 21 | 0,0398 | 466/573 (81,3 %) | 466/573 (81,3 %) | 466/569 (81,9 %) | 466/569 (81,9 %) |
| sales_manager | every-20 | 0 | 10 | 0,0320 | 421/573 (73,5 %) | 421/573 (73,5 %) | 421/569 (74,0 %) | 421/569 (74,0 %) |
| sales_manager | every-50 | 0 | 4 | 0,0271 | 333/573 (58,1 %) | 333/573 (58,1 %) | 333/569 (58,5 %) | 333/569 (58,5 %) |
| sales_manager | triggered-phrases-any | 0 | 163 | 0,1042 | 559/573 (97,6 %) | 559/573 (97,6 %) | 559/569 (98,2 %) | 559/569 (98,2 %) |
| software_engineer | never | 0 | 0 | 0,0000 | 156/561 (27,8 %) | 156/561 (27,8 %) | 156/553 (28,2 %) | 156/553 (28,2 %) |
| software_engineer | every-1 | 0 | 210 | 0,1135 | 536/561 (95,5 %) | 537/561 (95,7 %) | 534/553 (96,6 %) | 535/553 (96,7 %) |
| software_engineer | every-5 | 0 | 42 | 0,0491 | 499/561 (88,9 %) | 500/561 (89,1 %) | 497/553 (89,9 %) | 498/553 (90,1 %) |
| software_engineer | every-10 | 0 | 21 | 0,0399 | 465/561 (82,9 %) | 465/561 (82,9 %) | 463/553 (83,7 %) | 463/553 (83,7 %) |
| software_engineer | every-20 | 0 | 10 | 0,0321 | 412/561 (73,4 %) | 412/561 (73,4 %) | 410/553 (74,1 %) | 410/553 (74,1 %) |
| software_engineer | every-50 | 0 | 4 | 0,0293 | 329/561 (58,6 %) | 329/561 (58,6 %) | 327/553 (59,1 %) | 327/553 (59,1 %) |
| software_engineer | triggered-phrases-any | 0 | 160 | 0,0951 | 534/561 (95,2 %) | 534/561 (95,2 %) | 532/553 (96,2 %) | 532/553 (96,2 %) |
| startup_founder | never | 0 | 0 | 0,0000 | 144/581 (24,8 %) | 144/581 (24,8 %) | 144/539 (26,7 %) | 144/539 (26,7 %) |
| startup_founder | every-1 | 0 | 210 | 0,1281 | 523/581 (90,0 %) | 523/581 (90,0 %) | 522/539 (96,8 %) | 522/539 (96,8 %) |
| startup_founder | every-5 | 0 | 42 | 0,0522 | 491/581 (84,5 %) | 491/581 (84,5 %) | 490/539 (90,9 %) | 490/539 (90,9 %) |
| startup_founder | every-10 | 0 | 21 | 0,0403 | 451/581 (77,6 %) | 451/581 (77,6 %) | 436/539 (80,9 %) | 436/539 (80,9 %) |
| startup_founder | every-20 | 0 | 10 | 0,0330 | 403/581 (69,4 %) | 403/581 (69,4 %) | 390/539 (72,4 %) | 390/539 (72,4 %) |
| startup_founder | every-50 | 0 | 4 | 0,0283 | 307/581 (52,8 %) | 307/581 (52,8 %) | 304/539 (56,4 %) | 304/539 (56,4 %) |
| startup_founder | triggered-phrases-any | 0 | 156 | 0,1056 | 525/581 (90,4 %) | 525/581 (90,4 %) | 523/539 (97,0 %) | 523/539 (97,0 %) |
| academic_researcher | never | 1 | 0 | 0,0000 | 142/593 (23,9 %) | 142/593 (23,9 %) | 142/585 (24,3 %) | 142/585 (24,3 %) |
| academic_researcher | every-1 | 1 | 210 | 0,1235 | 576/593 (97,1 %) | 576/593 (97,1 %) | 576/585 (98,5 %) | 576/585 (98,5 %) |
| academic_researcher | every-5 | 1 | 42 | 0,0505 | 536/593 (90,4 %) | 536/593 (90,4 %) | 536/585 (91,6 %) | 536/585 (91,6 %) |
| academic_researcher | every-10 | 1 | 21 | 0,0412 | 487/593 (82,1 %) | 487/593 (82,1 %) | 486/585 (83,1 %) | 486/585 (83,1 %) |
| academic_researcher | every-20 | 1 | 10 | 0,0319 | 448/593 (75,5 %) | 448/593 (75,5 %) | 448/585 (76,6 %) | 448/585 (76,6 %) |
| academic_researcher | every-50 | 1 | 4 | 0,0285 | 352/593 (59,4 %) | 352/593 (59,4 %) | 352/585 (60,2 %) | 352/585 (60,2 %) |
| academic_researcher | triggered-phrases-any | 1 | 159 | 0,0999 | 571/593 (96,3 %) | 571/593 (96,3 %) | 571/585 (97,6 %) | 571/585 (97,6 %) |
| business_executive | never | 1 | 0 | 0,0000 | 150/548 (27,4 %) | 150/548 (27,4 %) | 150/537 (27,9 %) | 150/537 (27,9 %) |
| business_executive | every-1 | 1 | 210 | 0,1146 | 516/548 (94,2 %) | 517/548 (94,3 %) | 516/537 (96,1 %) | 517/537 (96,3 %) |
| business_executive | every-5 | 1 | 42 | 0,0483 | 485/548 (88,5 %) | 486/548 (88,7 %) | 485/537 (90,3 %) | 486/537 (90,5 %) |
| business_executive | every-10 | 1 | 21 | 0,0373 | 435/548 (79,4 %) | 435/548 (79,4 %) | 435/537 (81,0 %) | 435/537 (81,0 %) |
| business_executive | every-20 | 1 | 10 | 0,0298 | 403/548 (73,5 %) | 403/548 (73,5 %) | 401/537 (74,7 %) | 401/537 (74,7 %) |
| business_executive | every-50 | 1 | 4 | 0,0261 | 319/548 (58,2 %) | 319/548 (58,2 %) | 317/537 (59,0 %) | 317/537 (59,0 %) |
| business_executive | triggered-phrases-any | 1 | 160 | 0,0989 | 520/548 (94,9 %) | 521/548 (95,1 %) | 520/537 (96,8 %) | 521/537 (97,0 %) |
| content_writer | never | 1 | 0 | 0,0000 | 146/614 (23,8 %) | 146/614 (23,8 %) | 146/601 (24,3 %) | 146/601 (24,3 %) |
| content_writer | every-1 | 1 | 210 | 0,1276 | 554/614 (90,2 %) | 555/614 (90,4 %) | 553/601 (92,0 %) | 554/601 (92,2 %) |
| content_writer | every-5 | 1 | 42 | 0,0475 | 532/614 (86,6 %) | 534/614 (87,0 %) | 532/601 (88,5 %) | 534/601 (88,9 %) |
| content_writer | every-10 | 1 | 21 | 0,0396 | 485/614 (79,0 %) | 485/614 (79,0 %) | 485/601 (80,7 %) | 485/601 (80,7 %) |
| content_writer | every-20 | 1 | 10 | 0,0314 | 449/614 (73,1 %) | 449/614 (73,1 %) | 446/601 (74,2 %) | 446/601 (74,2 %) |
| content_writer | every-50 | 1 | 4 | 0,0269 | 347/614 (56,5 %) | 347/614 (56,5 %) | 347/601 (57,7 %) | 347/601 (57,7 %) |
| content_writer | triggered-phrases-any | 1 | 147 | 0,0932 | 554/614 (90,2 %) | 556/614 (90,6 %) | 552/601 (91,8 %) | 554/601 (92,2 %) |
| creative_designer | never | 1 | 0 | 0,0000 | 153/596 (25,7 %) | 153/596 (25,7 %) | 153/581 (26,3 %) | 153/581 (26,3 %) |
| creative_designer | every-1 | 1 | 210 | 0,1180 | 568/596 (95,3 %) | 568/596 (95,3 %) | 565/581 (97,2 %) | 565/581 (97,2 %) |
| creative_designer | every-5 | 1 | 42 | 0,0485 | 527/596 (88,4 %) | 527/596 (88,4 %) | 525/581 (90,4 %) | 525/581 (90,4 %) |
| creative_designer | every-10 | 1 | 21 | 0,0387 | 485/596 (81,4 %) | 485/596 (81,4 %) | 485/581 (83,5 %) | 485/581 (83,5 %) |
| creative_designer | every-20 | 1 | 10 | 0,0329 | 445/596 (74,7 %) | 445/596 (74,7 %) | 439/581 (75,6 %) | 439/581 (75,6 %) |
| creative_designer | every-50 | 1 | 4 | 0,0286 | 332/596 (55,7 %) | 332/596 (55,7 %) | 332/581 (57,1 %) | 332/581 (57,1 %) |
| creative_designer | triggered-phrases-any | 1 | 161 | 0,1012 | 552/596 (92,6 %) | 552/596 (92,6 %) | 550/581 (94,7 %) | 550/581 (94,7 %) |
| financial_analyst | never | 1 | 0 | 0,0000 | 146/565 (25,8 %) | 146/565 (25,8 %) | 146/559 (26,1 %) | 146/559 (26,1 %) |
| financial_analyst | every-1 | 1 | 210 | 0,1279 | 550/565 (97,3 %) | 550/565 (97,3 %) | 550/559 (98,4 %) | 550/559 (98,4 %) |
| financial_analyst | every-5 | 1 | 42 | 0,0495 | 490/565 (86,7 %) | 490/565 (86,7 %) | 490/559 (87,7 %) | 490/559 (87,7 %) |
| financial_analyst | every-10 | 1 | 21 | 0,0399 | 457/565 (80,9 %) | 458/565 (81,1 %) | 457/559 (81,8 %) | 458/559 (81,9 %) |
| financial_analyst | every-20 | 1 | 10 | 0,0315 | 421/565 (74,5 %) | 421/565 (74,5 %) | 421/559 (75,3 %) | 421/559 (75,3 %) |
| financial_analyst | every-50 | 1 | 4 | 0,0281 | 328/565 (58,1 %) | 328/565 (58,1 %) | 328/559 (58,7 %) | 328/559 (58,7 %) |
| financial_analyst | triggered-phrases-any | 1 | 152 | 0,1013 | 548/565 (97,0 %) | 548/565 (97,0 %) | 548/559 (98,0 %) | 548/559 (98,0 %) |
| management_consultant | never | 1 | 0 | 0,0000 | 148/583 (25,4 %) | 148/583 (25,4 %) | 148/545 (27,2 %) | 148/545 (27,2 %) |
| management_consultant | every-1 | 1 | 210 | 0,1197 | 539/583 (92,5 %) | 540/583 (92,6 %) | 532/545 (97,6 %) | 533/545 (97,8 %) |
| management_consultant | every-5 | 1 | 42 | 0,0465 | 507/583 (87,0 %) | 508/583 (87,1 %) | 501/545 (91,9 %) | 502/545 (92,1 %) |
| management_consultant | every-10 | 1 | 21 | 0,0374 | 469/583 (80,4 %) | 469/583 (80,4 %) | 452/545 (82,9 %) | 452/545 (82,9 %) |
| management_consultant | every-20 | 1 | 10 | 0,0314 | 430/583 (73,8 %) | 430/583 (73,8 %) | 414/545 (76,0 %) | 414/545 (76,0 %) |
| management_consultant | every-50 | 1 | 4 | 0,0283 | 344/583 (59,0 %) | 344/583 (59,0 %) | 340/545 (62,4 %) | 340/545 (62,4 %) |
| management_consultant | triggered-phrases-any | 1 | 156 | 0,0956 | 543/583 (93,1 %) | 544/583 (93,3 %) | 537/545 (98,5 %) | 538/545 (98,7 %) |
| marketing_manager | never | 1 | 0 | 0,0000 | 150/572 (26,2 %) | 150/572 (26,2 %) | 150/569 (26,4 %) | 150/569 (26,4 %) |
| marketing_manager | every-1 | 1 | 210 | 0,1205 | 528/572 (92,3 %) | 529/572 (92,5 %) | 528/569 (92,8 %) | 529/569 (93,0 %) |
| marketing_manager | every-5 | 1 | 42 | 0,0507 | 473/572 (82,7 %) | 474/572 (82,9 %) | 472/569 (83,0 %) | 473/569 (83,1 %) |
| marketing_manager | every-10 | 1 | 21 | 0,0394 | 467/572 (81,6 %) | 467/572 (81,6 %) | 467/569 (82,1 %) | 467/569 (82,1 %) |
| marketing_manager | every-20 | 1 | 10 | 0,0313 | 421/572 (73,6 %) | 421/572 (73,6 %) | 421/569 (74,0 %) | 421/569 (74,0 %) |
| marketing_manager | every-50 | 1 | 4 | 0,0269 | 328/572 (57,3 %) | 328/572 (57,3 %) | 328/569 (57,6 %) | 328/569 (57,6 %) |
| marketing_manager | triggered-phrases-any | 1 | 163 | 0,1010 | 527/572 (92,1 %) | 529/572 (92,5 %) | 527/569 (92,6 %) | 529/569 (93,0 %) |
| sales_manager | never | 1 | 0 | 0,0000 | 148/573 (25,8 %) | 148/573 (25,8 %) | 148/569 (26,0 %) | 148/569 (26,0 %) |
| sales_manager | every-1 | 1 | 210 | 0,1285 | 559/573 (97,6 %) | 559/573 (97,6 %) | 559/569 (98,2 %) | 559/569 (98,2 %) |
| sales_manager | every-5 | 1 | 42 | 0,0503 | 509/573 (88,8 %) | 509/573 (88,8 %) | 509/569 (89,5 %) | 509/569 (89,5 %) |
| sales_manager | every-10 | 1 | 21 | 0,0400 | 466/573 (81,3 %) | 466/573 (81,3 %) | 466/569 (81,9 %) | 466/569 (81,9 %) |
| sales_manager | every-20 | 1 | 10 | 0,0316 | 428/573 (74,7 %) | 428/573 (74,7 %) | 428/569 (75,2 %) | 428/569 (75,2 %) |
| sales_manager | every-50 | 1 | 4 | 0,0307 | 343/573 (59,9 %) | 343/573 (59,9 %) | 343/569 (60,3 %) | 343/569 (60,3 %) |
| sales_manager | triggered-phrases-any | 1 | 163 | 0,1043 | 559/573 (97,6 %) | 560/573 (97,7 %) | 559/569 (98,2 %) | 560/569 (98,4 %) |
| software_engineer | never | 1 | 0 | 0,0000 | 156/561 (27,8 %) | 156/561 (27,8 %) | 156/553 (28,2 %) | 156/553 (28,2 %) |
| software_engineer | every-1 | 1 | 210 | 0,1149 | 537/561 (95,7 %) | 537/561 (95,7 %) | 535/553 (96,7 %) | 535/553 (96,7 %) |
| software_engineer | every-5 | 1 | 42 | 0,0489 | 505/561 (90,0 %) | 506/561 (90,2 %) | 503/553 (91,0 %) | 504/553 (91,1 %) |
| software_engineer | every-10 | 1 | 21 | 0,0400 | 451/561 (80,4 %) | 451/561 (80,4 %) | 449/553 (81,2 %) | 449/553 (81,2 %) |
| software_engineer | every-20 | 1 | 10 | 0,0330 | 389/561 (69,3 %) | 389/561 (69,3 %) | 387/553 (70,0 %) | 387/553 (70,0 %) |
| software_engineer | every-50 | 1 | 4 | 0,0280 | 326/561 (58,1 %) | 326/561 (58,1 %) | 321/553 (58,0 %) | 321/553 (58,0 %) |
| software_engineer | triggered-phrases-any | 1 | 160 | 0,0949 | 529/561 (94,3 %) | 530/561 (94,5 %) | 527/553 (95,3 %) | 528/553 (95,5 %) |
| startup_founder | never | 1 | 0 | 0,0000 | 144/581 (24,8 %) | 144/581 (24,8 %) | 144/539 (26,7 %) | 144/539 (26,7 %) |
| startup_founder | every-1 | 1 | 210 | 0,1262 | 521/581 (89,7 %) | 521/581 (89,7 %) | 519/539 (96,3 %) | 519/539 (96,3 %) |
| startup_founder | every-5 | 1 | 42 | 0,0499 | 472/581 (81,2 %) | 473/581 (81,4 %) | 471/539 (87,4 %) | 472/539 (87,6 %) |
| startup_founder | every-10 | 1 | 21 | 0,0417 | 439/581 (75,6 %) | 439/581 (75,6 %) | 435/539 (80,7 %) | 435/539 (80,7 %) |
| startup_founder | every-20 | 1 | 10 | 0,0323 | 395/581 (68,0 %) | 395/581 (68,0 %) | 392/539 (72,7 %) | 392/539 (72,7 %) |
| startup_founder | every-50 | 1 | 4 | 0,0274 | 315/581 (54,2 %) | 315/581 (54,2 %) | 311/539 (57,7 %) | 311/539 (57,7 %) |
| startup_founder | triggered-phrases-any | 1 | 156 | 0,1010 | 517/581 (89,0 %) | 517/581 (89,0 %) | 515/539 (95,5 %) | 515/539 (95,5 %) |

### 4.5 Personas enteras, por tramo (repetición 0)

La misma salida de `table`, sección "Whole personas, per stretch". La fila s1–210 de cada persona entera es la de la grilla r0.

| persona | política | tramo | sueños | mantenimiento $ | oficial | indulgente | oficial sin marcadas | indulgente sin marcadas | invented | nothing_logged | partial_total |
| --- | --- | --- | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| startup_founder | every-1 | s1-210 | 210 | 0,1281 | 523/581 (90,0 %) | 523/581 (90,0 %) | 522/539 (96,8 %) | 522/539 (96,8 %) | 24 | 0 | 18 |
| startup_founder | every-1 | s211-420 | 210 | 0,2104 | 638/678 (94,1 %) | 638/678 (94,1 %) | 637/664 (95,9 %) | 637/664 (95,9 %) | 2 | 0 | 0 |
| startup_founder | every-1 | s421-end | 186 | 0,2211 | 530/560 (94,6 %) | 530/560 (94,6 %) | 529/549 (96,4 %) | 529/549 (96,4 %) | 4 | 2 | 0 |
| startup_founder | every-5 | s1-210 | 42 | 0,0522 | 491/581 (84,5 %) | 491/581 (84,5 %) | 490/539 (90,9 %) | 490/539 (90,9 %) | 24 | 0 | 18 |
| startup_founder | every-5 | s211-420 | 42 | 0,0638 | 575/678 (84,8 %) | 575/678 (84,8 %) | 574/664 (86,4 %) | 574/664 (86,4 %) | 2 | 0 | 0 |
| startup_founder | every-5 | s421-end | 37 | 0,0596 | 495/560 (88,4 %) | 496/560 (88,6 %) | 494/549 (90,0 %) | 495/549 (90,2 %) | 9 | 1 | 5 |
| academic_researcher | every-1 | s1-210 | 210 | 0,1232 | 570/593 (96,1 %) | 570/593 (96,1 %) | 569/585 (97,3 %) | 569/585 (97,3 %) | 0 | 0 | 0 |
| academic_researcher | every-1 | s211-420 | 210 | 0,2059 | 604/637 (94,8 %) | 605/637 (95,0 %) | 603/631 (95,6 %) | 604/631 (95,7 %) | 1 | 0 | 0 |
| academic_researcher | every-1 | s421-end | 199 | 0,2227 | 496/579 (85,7 %) | 497/579 (85,8 %) | 495/545 (90,8 %) | 496/545 (91,0 %) | 31 | 1 | 26 |
| academic_researcher | every-5 | s1-210 | 42 | 0,0502 | 537/593 (90,6 %) | 537/593 (90,6 %) | 536/585 (91,6 %) | 536/585 (91,6 %) | 3 | 3 | 1 |
| academic_researcher | every-5 | s211-420 | 42 | 0,0643 | 564/637 (88,5 %) | 565/637 (88,7 %) | 563/631 (89,2 %) | 564/631 (89,4 %) | 14 | 4 | 10 |
| academic_researcher | every-5 | s421-end | 39 | 0,0623 | 481/579 (83,1 %) | 481/579 (83,1 %) | 481/545 (88,3 %) | 481/545 (88,3 %) | 24 | 0 | 21 |

Brecha every-1 − every-5, en puntos de `oficial sin marcadas` (resta de las filas de arriba):

| persona | s1–210 | s211–420 | s421–end |
| --- | --: | --: | --: |
| startup_founder | 5,9 | 9,5 | 6,4 |
| academic_researcher | 5,7 | 6,4 | 2,5 |

- **En academic_researcher la brecha se achica en el último tramo,** como en P6 (allá 8,1 → 4,1). El motivo es que `every-1` cae a 90,8 %.
- **En startup_founder no se achica:** `every-1` se mantiene entre 95,9 % y 96,8 % en los tres tramos.
- **Con dos personas,** la compresión de P6 no es general: aparece en una de dos. El IC y la comparación formal son de P7b.

### 4.6 Costo: estimado contra pagado

Salida de cada `run`: "estimate for … $X" antes y "this run: $Y" después. Si una corrida se cortó, su pagado es la suma de los intentos.

| corrida | estimado | pagado |
| --- | --: | --: |
| r0 academic_researcher | 0,5624 | 0,5257 |
| r0 startup_founder | 0,5364 | 0,5494 (0,1071 + 0,4423, corte por límite) |
| r0 software_engineer | 0,4961 | 0,5011 |
| r0 content_writer | 0,5108 | 0,5172 |
| r0 marketing_manager | 0,5136 | 0,5382 |
| r0 business_executive | 0,5155 | 0,4927 |
| r0 creative_designer | 0,5157 | 0,5236 (0,3555 + 0,1681, timeout) |
| r0 management_consultant | 0,5206 | 0,5026 |
| r0 financial_analyst | 0,5387 | 0,5231 (0,1769 + 0,3462, timeout) |
| r0 sales_manager | 0,5653 | 0,5307 |
| **r0, 10 personas** | **5,2751** | **5,2043** (−1,3 %) |
| 2a startup_founder every-1 entera | 0,5210 | 0,5146 |
| 2b startup_founder every-5 entera | 0,2214 | 0,2037 |
| 2b academic_researcher every-1 entera | 0,5503 | 0,5102 |
| 2b academic_researcher every-5 entera | 0,2322 | 0,2064 |
| **Enteras** | **1,5249** | **1,4349** (−5,9 %) |
| r1 academic_researcher | 0,5624 | 0,5298 |
| r1 startup_founder | 0,5364 | 0,5433 |
| r1 software_engineer | 0,4961 | 0,5030 |
| r1 content_writer | 0,5108 | 0,5216 (0,4036 + 0,1180, corte por límite) |
| r1 marketing_manager | 0,5136 | 0,5251 (0,2566 + 0,2685, reinicio del daemon) |
| r1 business_executive | 0,5155 | 0,5020 |
| r1 creative_designer | 0,5157 | 0,5259 |
| r1 management_consultant | 0,5206 | 0,5159 (0,0533 + 0,4626, timeout) |
| r1 financial_analyst | 0,5387 | 0,5291 |
| r1 sales_manager | 0,5653 | 0,5374 |
| **r1, 10 personas** | **5,2751** | **5,2331** (−0,8 %) |
| **Total p7a** (`BudgetedClient("p7a", 0).spent()`) | **12,0752** | **11,8724** (−1,7 %) de 13,00 |

El primer intento de marketing_manager r1 murió con el daemon y no imprimió "this run". Su pagado es la diferencia entre el "after" del `run` anterior (content_writer, $8,7370) y el "before" del `run` que lo retomó ($8,9936). Las sumas de las tres secciones dan $11,8723, un décimo de milésimo menos que el libro por el redondeo de cada `run`.

Después del segundo corte, `PYTHONHASHSEED=0 uv run python -m final.grid estimate` daba $3,2855 por pagar, y un total proyectado de $11,90. Lo pagado al final fue $11,8724.

## 5. Opciones descartadas y por qué

- **Reintentar después del error de límite:** la regla del proyecto lo prohíbe. El error dice que el acceso vuelve el 01/12, y un reintento en bucle no cambia eso.
- **Comparar la precisión con el umbral del que responde (1,2 pp):** marcaría como fuera de rango casi cualquier corrida nueva, porque también cambian los sueños.
- **Parar si se rompe el orden de las fijas:** el contrato no lo pide. `compare` lo muestra, y la decisión se toma al revisarlo.
- **Calcular el pagado por paso desde el libro de gasto:** el libro registra persona y repetición, pero no a qué paso pertenece una llamada (s1–210 r0 y la persona entera comparten persona y repetición). Uso la salida de `run`, que mide cada corrida.

## 6. Limitaciones

- **El límite de la organización cortó dos veces** antes del tope de p7a. La segunda vez, con el límite en $25, p7a llevaba $8,62 y la organización ya había gastado unos $9,19 antes de P7a. No puedo ver el contador de la consola, así que no sé qué más se gastó.
- **Una llamada cortada pudo haberse cobrado sin quedar en el libro.** El cliente escribe el libro recién cuando llega la respuesta. Fueron como mucho 4 llamadas (3 timeouts y el reinicio del daemon), de algunos milésimos de dólar cada una.
- **Una sola corrida antes y una después:** la validación no distingue un corrimiento real del ruido de una repetición. Para el −3,0 de `every-10`, la repetición 1 sugiere ruido (82,1 %).
- **El modelo de costo de P5 está fijo,** no se reajustó sobre el caché nuevo. En las corridas de la tabla de §4.6, el pagado quedó entre −11,1 % (academic_researcher every-5 entera) y +4,8 % (marketing_manager r0) de lo estimado.
- **Dos personas enteras** no alcanzan para afirmar si la compresión hacia el final del mes es general.
