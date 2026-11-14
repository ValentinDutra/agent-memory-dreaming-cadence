# P7 · Interfaz entre P7a (corrida final) y P7b (análisis)

P7a corre la grilla de las decisiones de P6 (`docs/p6-inventadas.md` § "Decisiones") y escribe dos CSV chicos. P7b los lee y escribe el análisis y los gráficos. Lo único que comparten es este contrato: P7b nunca llama a la API ni importa el motor para correr.

**Re-corrida sin caché (13/11).** El 13/11 se borraron los worktrees de P7, P7a y P7b, y con ellos `results/`: el caché unificado de P5+P6 (102 MB) y los libros de gasto, que estaban en `.gitignore`. No hay copia. Esta versión del contrato parte de `results/` vacío: toda llamada se paga de nuevo, incluidas las corridas que antes salían del caché.

## La grilla (P7a)

| Qué | Personas | Políticas | Sesiones | Repeticiones |
| --- | --- | --- | --- | --- |
| Grilla | las 10 monthly | `never`, `every-1`, `every-5`, `every-10`, `every-20`, `every-50`, `triggered-phrases-any` | s1–210 | 0 y 1 |
| Persona entera | startup_founder y academic_researcher | `every-1`, `every-5` | 1..fin | 0 |

**Orden** (si se corta por el límite de la organización, lo hecho tiene que valer solo):

1. Repetición 0 de la grilla, persona por persona: primero academic_researcher y startup_founder, que validan (ver abajo), después las otras 8, la más barata primero.
2. Personas enteras, repetición 0:
   - **2a.** `every-1` entera en startup_founder: la agregó la opción (b) de P6.
   - **2b.** `every-5` entera en startup_founder, y `every-1` y `every-5` enteras en academic_researcher. Ya las habían pagado P5 y P6b y se perdieron con el caché. Se pagan solo si decido volver a pagarlas. Sin ellas no queda ninguna persona con las dos políticas enteras, y P7b no puede medir la compresión de distancias por tramo.
3. Repetición 1 de la grilla, en el mismo orden que la 0.

Si cuando P7a termina 2a todavía no decidí 2b, sigue con 3 y deja 2b para el final. La persona entera va antes que la repetición 1 porque responde una pregunta que s1–210 no puede ver (P6 §3.4). La repetición 1 solo achica el ruido dentro de cada persona, y el IC se arma sobre personas.

**Estimación sin caché** (`PYTHONHASHSEED=0 uv run python -m final.grid estimate`, calcula sin llamar a nada). Usa el modelo de costo de P5 fijado en `final/grid.py` (`docs/p5-politicas.md` §4.3), porque el caché donde se ajustaba se perdió. Descuenta lo que comparten las políticas dentro de la misma repetición. Ese modelo sobreestimó los exámenes un 19 % en P5 §4.2.

| Paso | $ |
| --- | --: |
| 1. s1–210 r0, 10 personas ($0,50–0,57 cada una) | 5,2751 |
| 2a. `every-1` entera, startup_founder | 0,5210 |
| 2b. `every-5` entera, startup_founder | 0,2214 |
| 2b. `every-1` entera, academic_researcher | 0,5503 |
| 2b. `every-5` entera, academic_researcher | 0,2322 |
| 3. s1–210 r1, 10 personas | 5,2751 |
| **Total** | **12,0752** |

Una persona entera paga solo s211–fin: s1–210 es la misma cadena que la grilla con repetición 0.

## Validación (reemplaza la comprobación "idéntica a P5/P6 desde el caché")

Sin caché, academic_researcher y startup_founder s1–210 r0 son una muestra nueva de las mismas corridas. Se comparan con los números de antes del borrado, que eran los de P5/P6 y quedaron en `data/p7-runs-before-loss.csv` (copia de `data/p7-runs.csv` en el commit 8e6bcff, 23 filas: las 14 corridas s1–210 r0 de las dos personas y las 3 corridas enteras de 2b, por tramo). Una excepción: `triggered-phrases-any` de startup_founder no venía de P5/P6; la pagó P7a minutos antes del borrado.

- **Iguales, exactos:** `sessions`, `dreams`, `sessions_read`, `exams` y `asked` de cada política y tramo. Las cadencias fijas y el detector de frases deciden sin leer las notas (`policies/projection.py`), así que una diferencia acá es un bug. Si pasa, P7a para y avisa.
- **Precisión oficial, por política: dentro de 2,8 puntos.** Es el ruido de una política repetida entera (P5a §4.4: hasta 2,8 puntos entre r0 y r1; P4 midió 1,9). El ruido del que responde con notas fijas es menor, ≤ 1,2 pp (P3b §4.3), pero una corrida nueva también vuelve a muestrear los sueños, así que esa banda queda corta. Entre 2,8 y 5,6 puntos (el doble del ruido), P7a lo reporta y sigue. Más de 5,6 puntos en alguna política, para y avisa.
- **Orden de las fijas:** every-1 > 5 > 10 > 20 > 50 > never en las dos personas, como en P5a (3 personas, 2 repeticiones).
- **Costo:** por persona, lo pagado contra la estimación de arriba.

P7a hace la comparación con un script commiteado y la cita en su informe. Las corridas enteras de 2b se comparan igual, por tramo, contra las mismas filas.

## Contrato

```python
# final/grid.py  (dueño: P7a)
POLICIES = ("never", "every-1", "every-5", "every-10", "every-20", "every-50", "triggered-phrases-any")
STRETCHES = (("s1-210", 1, 210), ("s211-420", 211, 420), ("s421-end", 421, None))

def stretch_rows(run: PolicyRun, scope: str) -> list[dict]      # una fila de data/p7-runs.csv por tramo con sesiones
def probe_rows(run: PolicyRun, scope: str) -> list[dict]        # filas de data/p7-probes.csv
```

CLI:

```bash
PYTHONHASHSEED=0 uv run python -m final.grid estimate                       # $ por persona, s1–210 y enteras, sin llamar a nada
PYTHONHASHSEED=0 uv run python -m final.grid run monthly/<persona>:210 --repetition 0 --limit 13.00   # paga, tope p7a
PYTHONHASHSEED=0 uv run python -m final.grid table                          # reescribe los dos CSV desde el caché, tope $0
```

`table` recorre toda la grilla con tope $0. Una corrida que no está entera en el caché no entra al CSV, y se lista en la salida. Así el CSV siempre es reproducible y P7b lo puede leer en cualquier momento. Con el caché vacío, el CSV de la rama arranca con las filas de antes del borrado (8e6bcff); el primer `table` de P7a las reemplaza por las nuevas.

### `data/p7-runs.csv`

Una fila por (persona, política, repetición, alcance, tramo). Separador `,`, punto decimal, dólares con 6 decimales. Columnas, en este orden:

| Columna | Qué es |
| --- | --- |
| `period` | `monthly` |
| `persona` | p. ej. `academic_researcher` |
| `policy` | una de `POLICIES` |
| `repetition` | 0 o 1 |
| `scope` | `s1-210` (la grilla) o `whole` (persona entera). La fila `whole` del tramo `s1-210` repite la de la grilla con repetición 0, porque el caché es el mismo. |
| `stretch` | `s1-210`, `s211-420` o `s421-end` |
| `sessions` | sesiones del tramo |
| `dreams` | sueños con sesión en el tramo |
| `sessions_read` | sesiones leídas por esos sueños |
| `dream_cost` | $ de esos sueños, lo pagado la primera vez (P5) |
| `decision_cost` | $ del detector (0 para todas las de P7) |
| `maintenance_cost` | `dream_cost + decision_cost`: lo que cuesta mantener la memoria. **Los exámenes no entran**: son instrumentación, no parte de la política. |
| `exam_cost` | $ de los exámenes del tramo |
| `exams` | exámenes del tramo (sesión múltiplo de 7) |
| `asked`, `official`, `lenient` | preguntas, correctas oficiales y correctas indulgentes |
| `reachable_asked`, `reachable_official`, `reachable_lenient` | lo mismo sin las preguntas marcadas (`exam/unreachable.py`) |
| `correct`, `stale`, `missing`, `invented`, `unparseable` | las 5 clases del conteo oficial, sobre todas las preguntas |
| `nothing_logged` | de las `invented`, las que `diagnosis.criteria.nothing_logged` pasaría a `stale` (decisión 2): con la regla nueva, `invented − nothing_logged` y `stale + nothing_logged` |
| `partial_total` | de las `invented`, las que `diagnosis.criteria.partial_total` reconoce como total incompleto. Solo diagnóstico (decisión 3). |
| `reachable_invented`, `reachable_nothing_logged` | `invented` y `nothing_logged` sin las preguntas marcadas |

Invariantes que `table` comprueba antes de escribir: `correct == official`; las 5 clases suman `asked`; por corrida, la suma de los tramos da el total de `PolicyRun` (sueños, $ y preguntas).

### `data/p7-probes.csv`

Una fila por (persona, política, repetición, alcance, tramo, dominio, probe) con al menos una pregunta:

`period, persona, policy, repetition, scope, stretch, domain, probe, asked, official, lenient, reachable_asked, reachable_official, reachable_lenient`

Los probes son los de P2, que el análisis puede nombrar así: `new`, `recent_change`, `stable` (sin cambios), `never_existed` (señuelo), `aggregate` (total). Los dominios son `calendar`, `content`, `expense`, `goal`, `preference`, `steps` y `todo`. Por corrida y tramo, la suma de `p7-probes.csv` da la fila de `p7-runs.csv`.

## El análisis (P7b)

```bash
uv run python -m final.analysis data/p7-runs.csv data/p7-probes.csv       # tablas Markdown + docs/p7/*.svg
```

- **Unidad del IC: la persona.** Las preguntas de una persona no son independientes: un gasto mal fechado arruina unos 20 totales seguidos (P6 §3.1). Bootstrap sobre las personas, con reemplazo, con semilla fija. Primero se promedian las repeticiones dentro de cada persona.
- **Diferencias emparejadas.** Para comparar dos políticas, la diferencia se calcula dentro de cada persona remuestreada. Las dos comparten persona, examen y caché.
- **El gráfico principal** pone en x el costo de mantener la memoria (`maintenance_cost`, sin exámenes) y en y la precisión, con un punto por política e IC en los dos ejes. Las cadencias fijas van unidas en orden de k, y `triggered-phrases-any` va aparte.
- **Gráficos chicos** en SVG escrito a mano (librería estándar), en `docs/p7/`.
- **Re-correr con el CSV final** tiene que dar el informe entero sin tocar nada a mano.

## Caché, presupuesto y reglas

- **Un solo caché, el de P7a.** Arranca vacío, en `results/` del worktree de P7a, y P7a es el único proceso que llama a la API. P7b lee los CSV, solo lectura, desde el worktree de P7a: `<worktree de P7a>/data/p7-runs.csv` y `<worktree de P7a>/data/p7-probes.csv` (la ruta absoluta va en el prompt de P7b). Si necesita algo del caché, lo copia a su worktree y corre con tope $0.
- **Topes** con `BudgetedClient(<nombre>, <tope>)`: P7a `p7a` $13,00, P7b $0, integración `p7` $1,00.
- **Límite de gasto de la organización.** Si una llamada falla por límite de gasto o de crédito, no se reintenta: se para, se guarda lo hecho (el caché ya lo guarda), se corre `table` y se anota cuántas personas quedaron completas.
- **`PYTHONHASHSEED=0`** en toda corrida (P6 §6).
- **No se tocan** `truth/`, `exam/`, `answering/`, `dreaming/` ni `policies/`, salvo por un bug demostrado con un test, y se reporta qué resultados anteriores cambian.
