# P5 · Interfaz entre P5a (cadencias fijas) y P5b (sueño disparado por contradicción)

Una **política** decide, después de cada sesión, si el agente sueña ahora. El **motor** (`policies/engine.py`, dueño: P5) encadena los sueños a lo largo de una persona, toma los exámenes y cuenta los resultados igual para todas las políticas. P5a escribe las políticas fijas, P5b la disparada. Lo único que comparten es este contrato, el motor y `policies/session_changes.py`.

## Contrato

```python
# policies/engine.py  (dueño: P5)
@dataclass(frozen=True)
class Decision:
    dream: bool
    cost: float = 0.0          # dólares gastados en decidir (una llamada del detector); 0 en una cadencia fija
    input_tokens: int = 0
    output_tokens: int = 0

class Policy(Protocol):
    name: str                  # nombra su carpeta de caché y su fila en los reportes, p. ej. "every-20"
    def decide(self, notes: str, pending: list[Session], client: BudgetedClient, run: str) -> Decision
        # ¿soñar justo después de pending[-1]? pending = las sesiones desde el último sueño, la más vieja primero

@dataclass(frozen=True)
class Step:        # una por sesión
    session_id: int; dreamt: bool; sessions_read: int
    dream_cost: float; dream_input_tokens: int; dream_output_tokens: int
    decision_cost: float
    notes: str     # después de la sesión (y de su sueño, si soñó)

@dataclass(frozen=True)
class ExamResult:  # uno por examen tomado
    session_id: int; questions: tuple[Question, ...]; answers: tuple[str | None, ...]; grades: tuple[Grade, ...]; cost: float

@dataclass(frozen=True)
class PolicyRun:
    policy: str; period: str; persona: str; repetition: int
    steps: tuple[Step, ...]; exams: tuple[ExamResult, ...]
    def dreams() -> int; def dream_cost() -> float; def decision_cost() -> float; def exam_cost() -> float

def run_policy(policy, period, persona, client, exam_every=7, through=None, repetition=0) -> PolicyRun
def score(run, domains=None) -> Score     # official, lenient, y los dos sin las preguntas marcadas; outcomes por clase
def runs_table(runs) -> str               # una fila por corrida, Markdown

# policies/session_changes.py  (dueño: P5; lee la verdad: ninguna política lo puede importar)
def session_change(timeline, session_id) -> "none" | "add" | "change"
```

### Semántica del motor

- **Decidir.** Después de cada sesión, el motor llama a `policy.decide(notes, pending, client, run)`. `pending` son las sesiones desde el último sueño; la última es la que acaba de terminar.
- **Soñar.** Si la política dice que sí, el sueño de P4 (`dreaming.dream.dream`) lee las notas y **todo** `pending`, y `pending` vuelve a quedar vacío. Si dice que no, la sesión espera al próximo sueño. Así cada sueño lee exactamente las sesiones desde el anterior.
- **Examinar.** Después de cada sesión N múltiplo de `exam_every`, se contesta el examen de N con las notas que quedaron después del sueño de N, si lo hubo (P2: el examen de N es la primera pregunta de la sesión N+1). El examen es el de P2, idéntico para todas las políticas: `build_exam` no depende de la política ni de una semilla del motor.
- **El final.** El motor corre las sesiones 1..`through` (todas por omisión) y no fuerza un sueño al final. Las sesiones que quedan sin soñar después del último examen no cambian ningún resultado; las que quedan sin soñar antes de un examen son justamente el costo de esperar, y se miden.
- **`exam_every` tiene que ser múltiplo de 7.** Con 7 cada examen cae en todas las fases de las cadencias 5, 20 y 50 (P2a). Un múltiplo mayor ahorra exámenes pero sesga la fase: 28 comparte el 4 con la cadencia 20, y 49 ≡ −1 (mod 50) deja a la cadencia 50 siempre con 38–49 sesiones de retraso. Para validar barato conviene `exam_every=7` con `through` corto, no un paso mayor.
- **Caché compartido entre políticas.** Los sueños se guardan en `results/raw/p5/r<repetition>/dream/<period>/<persona>/` y los exámenes en `.../exam/...`, sin el nombre de la política. Dos políticas con las mismas notas y las mismas sesiones reciben el mismo sueño, y dos con las mismas notas, las mismas respuestas. Es más barato y además empareja las comparaciones: las diferencias entre políticas no son ruido del muestreo. `repetition=1` vuelve a muestrear todo. Las decisiones del detector se guardan en `.../decide/<policy>/...`.
- **El costo.** `DreamResult.cost`, `Decision.cost` y el costo del examen son los dólares que se pagaron la primera vez, también cuando la respuesta sale del caché. Así una corrida repetida desde el caché reporta el mismo costo, y P6 lo puede sumar.

### Cómo se cuenta (decisiones de P2 y P4)

`score(run)` devuelve, sobre todas las preguntas de los exámenes tomados:

- **official:** `correct` del conteo estricto de P2.
- **lenient:** además, "dislike" después de un gusto borrado cuenta como correcto (`negates_removed_preference`; decisión de P2).
- **official / lenient without marked:** lo mismo sin las preguntas que ningún sueño puede acertar (`exam/unreachable.py`; decisión (c), `docs/p2-examen.md` § "Decisiones"). Monthly: 395 de 18.214 preguntas; weekly: 151 de 4.039.

Todo informe reporta las cuatro columnas, más las cinco clases del conteo oficial (`runs_table`).

### Regla anti-trampa (obligatoria, también para el detector)

Una política solo ve lo que vería un agente real: las notas y `Session` (`speaker`, `message`, `session_id`, `date`). **Nunca** `share_memory`, `operation`, `operation_details`, `session_type`, `persona`, ni nada de `truth/`, `exam/` o `policies/session_changes.py`.

- Las políticas reciben `Session`, armada campo por campo por `dreaming/transcripts.py`.
- Los módulos de políticas (`policies/fixed.py`, `policies/triggered.py`) no importan `truth`, `exam` ni `policies.session_changes`. Los scripts que miden (precisión del detector, informes) sí, pero solo para medir.
- P5b agrega un test como `tests/test_transcripts.py::test_the_dream_never_sees_the_answer_key`: cambia la hoja de respuestas de una sesión real y exige el mismo prompt del detector.

### Cliente y presupuesto

`answering/client.py` sin cambios: `claude-haiku-5-5`, thinking adaptativo con effort `medium` por omisión, tope persistente por `budget_name`, caché en `results/raw/`. El sueño **tiene** que usar ese cliente con esa configuración (P4a §4.3). Un detector puede usar su propio `BudgetedClient` con otra configuración (p. ej. `thinking={"type": "disabled"}`) y **el mismo `budget_name`**, para que el tope siga siendo uno.

| Proceso | `budget_name` | Tope |
| --- | --- | --: |
| P5a | `p5a` | $1,50 |
| P5b | `p5b` | $1,50 |
| Integración (P5) | `p5` | $1,00 |

- La organización tiene un límite mensual y quedan unos $5,5 para todo el proyecto. **Si una llamada falla por límite de gasto o de crédito, no se reintenta:** se para, y se guarda lo hecho (el caché ya lo guarda).
- Los prompts quedan por debajo de 100k tokens.
- Antes de cada corrida, una estimación; después, el costo real (`client.spent()` antes y después).

## Datos medidos al definir la interfaz

- **Prueba del motor:** `tests/test_engine.py`, sin API, sobre weekly/software_engineer s1–14 con sueños después de s3, s7 y s12. Verifica que cada sueño lee exactamente las sesiones desde el anterior (1–3, 4–7, 8–12), que el examen de s7 ve las notas del sueño de s7 y que el de s14 ve las del sueño de s12. Una pasada con la API (cadencia 7, s1–14, $0,0029 del presupuesto `p5`) devolvió notas en el formato de P3 y 18/18 correctas; P5a la repite con un comando del repo.
- **Qué hace cada sesión con la verdad** (`uv run python -m policies.session_changes weekly monthly`):

  ```
  weekly: 1551 sessions | none 520 (34%) | add 740 (48%) | change 291 (19%)
  monthly: 6150 sessions | none 2414 (39%) | add 2548 (41%) | change 1188 (19%)
  ```

  `change` = un hecho que valía cambió de valor o dejó de valer; `add` = solo empezaron a valer hechos nuevos (un gasto, un pendiente, un gusto). Un detector que dispare con cualquier hecho nuevo soñaría en el 61 % de las sesiones monthly; uno que dispare solo con contradicciones, en el 19 %, y deja los hechos nuevos esperando al próximo disparo.
- **Costo de un sueño** (P4a): ≈ $0,00047 + $0,00004 por cada 1.000 caracteres de notas + $0,0001 por sesión leída. Un sueño de 1 sesión monthly cuesta ≈ $0,001; de 50, ≈ $0,0076 (P4 §4.4).
- **Calidad según cuántas sesiones lee un sueño** (P4 §4.4, desde notas perfectas): pierde 0,2 / 0,2 / 0,9 / 2,2 % de los hechos con k = 1 / 5 / 20 / 50 en weekly. Soñar seguido no degrada: solo cuesta. Las omisiones de un sueño son permanentes.
- **Ruido:** dos corridas del mismo sueño difieren hasta 1,9 puntos de examen (P4 §4.3). Hacen falta ≥ 2 repeticiones y ≥ 2 personas por política antes de concluir algo.

## Personas para validar

Para que la integración reuse el caché de los dos subproblemas, los dos validan sobre las mismas personas y los mismos tramos:

- **weekly/software_engineer**, todas sus sesiones (161), `exam_every=7`.
- **monthly/academic_researcher**, sesiones 1–210, `exam_every=7` (la que integra P5).
- Si sobra presupuesto: **monthly/startup_founder** 1–210.

Al integrar, P5 copia `results/raw/p5/` de cada subproblema a su worktree: los pedidos idénticos tienen el mismo hash, así que la corrida de integración sale del caché.

## Quién toca qué

| Archivo | Dueño | Notas |
| --- | --- | --- |
| `policies/engine.py`, `policies/session_changes.py`, `exam/unreachable.py`, `tests/test_engine.py`, `tests/test_unreachable.py`, `docs/p5-interfaz.md` | P5 | Los subproblemas no los editan: un cambio pasa por P5. |
| `policies/fixed.py` (y módulos `policies/fixed_*.py`), tests propios, `docs/p5a-<nombre>.md` | P5a | |
| `policies/triggered.py` (y módulos `policies/triggered_*.py`), tests propios, `docs/p5b-<nombre>.md` | P5b | |
| `truth/`, `exam/` (salvo `unreachable.py`), `answering/`, `dreaming/` | P1–P4 (cerrados) | No se modifican salvo bug demostrado con un test; se reporta a P5. |

`results/` está ignorado por git: cada número de un informe sale de un comando `uv run` que está en el repo.
