# P2 · Interfaz entre P2a (qué preguntar y cuándo) y P2b (cómo corregir)

P2a decide **qué** se pregunta y **en qué sesión**. P2b decide **cuál es la respuesta correcta** y **cómo se clasifica** lo que contesta el agente. Lo único que comparten es `exam/schema.py` (dueño: P2).

El examen es fijo: depende solo de `(period, persona)` y de la verdad de P1, nunca de la política de dreaming. Todas las políticas responden las mismas preguntas con los mismos `question_id`.

## Contrato

```python
# exam/schema.py  (dueño: P2)
DOMAINS = ("preference", "todo", "calendar", "goal", "content", "expense", "steps")
Probe = "recent_change" | "new" | "stable" | "never_existed" | "aggregate"   # P2a puede pedir cambios
AnswerFormat = "choice" | "value" | "number"
UNKNOWN = "unknown"
Outcome = "correct" | "stale" | "missing" | "invented" | "unparseable"     # unparseable: falla de formato (pedido de P2b)

@dataclass(frozen=True)
class Question:
    question_id: str                  # estable entre corridas
    period: str
    persona: str
    session_id: int                   # se pregunta justo después de esta sesión: verdad = state_after(session_id)
    domain: str                       # uno de DOMAINS; todo resultado se puede separar por dominio
    probe: Probe                      # por qué está en el examen
    fact: FactId | None               # (domain, key) de P1; None solo para "aggregate"
    field: str | None                 # campo del valor que se pregunta ("preference", "event_date", "amount"...); None = "¿el hecho existe?"
    answer_format: AnswerFormat
    options: tuple[str, ...]          # para "choice"; () en otro caso
    prompt: str                       # texto en inglés que ve el agente
    current: dict | None              # valor del hecho después de session_id; None = no vale
    history: tuple[dict | None, ...]  # estados anteriores hasta session_id, del más viejo al más nuevo, sin repetidos; None = no valía

@dataclass(frozen=True)
class Grade:
    question_id: str
    outcome: Outcome
    expected: str                     # respuesta correcta canónica
    given: str                        # respuesta del agente normalizada

def fact_states(timeline, fact, session_id) -> (history, current)   # helper común, ya implementado
```

### Semántica

- **Reloj.** `session_id` de Memora, igual que en P1. El examen de la sesión N se toma después de la sesión N y antes de la N+1. Si una política sueña después de la sesión N, el examen de N **ve** ese dream (decisión de orden que P2a debe justificar o cambiar).
- **`history` siempre arranca en `None`** (todo hecho empieza sin existir), salvo para `never_existed`, donde `history == ()` y `current is None`.
- **Aggregate.** `fact = None`, `field = "value"`, `current = {"value": total}` y `history` = los totales anteriores distintos. Así un total que no incluye los gastos nuevos sale como `stale`, igual que un hecho viejo.
- **`answer_format`.**
  - `choice`: la respuesta es una de `options` o `UNKNOWN`. Para "¿existe?" (`field is None`) las opciones son `("yes", "no")`.
  - `value`: texto libre que P2b normaliza (fecha, nombre, monto de presupuesto).
  - `number`: número; la tolerancia la define P2b.
- **Qué es "correcto" lo decide P2b**, a partir de `current`, `history`, `field` y `answer_format`. P2a no fija `expected`. Ejemplo: después del borrado de Bonobo, P2b decide si la respuesta correcta es `"dislike"`, `"no"` o `UNKNOWN`.

### Ejemplos reales (salida de `fact_states` sobre weekly/software_engineer)

| Hecho | Sesión | `history` | `current` |
| --- | --: | --- | --- |
| `("preference", ("music", "artists", "Bonobo"))` | 29 | `(None,)` | `{"preference": "like"}` |
| ídem | 40 | `(None, {"preference": "like"})` | `None` (borrado en la 30) |
| `("preference", ("music", "genres", "deep house"))` | 131 | `(None,)` | `{"preference": "dislike"}` (agregado en la 129) |
| ídem | 150 | `(None, {"preference": "dislike"})` | `{"preference": "like"}` (invertido en la 132) |
| `("calendar", ("Mechanic visit",))` | 104 | `(None, {…"event_date": "2025-06-15"})` | `{…"event_date": "2025-06-11"}` (reprogramado en la 87) |

Una pregunta posible (la forma exacta la elige P2a):

```python
Question(
    question_id="weekly/software_engineer/s040/preference/music|artists|Bonobo",
    period="weekly", persona="software_engineer", session_id=40,
    domain="preference", probe="recent_change",
    fact=("preference", ("music", "artists", "Bonobo")), field="preference",
    answer_format="choice", options=("like", "dislike"),
    prompt="Does the user like or dislike the music artist Bonobo? Answer like, dislike or unknown.",
    current=None, history=(None, {"preference": "like"}),
)
```

## Qué entrega cada subproblema

### P2a · `exam/questions.py`

```python
EXAM_SEED: int
def exam_sessions(period: str, persona: str) -> list[int]       # en qué sesiones se examina
def build_exam(period: str, persona: str) -> list[Question]     # determinista, independiente de la política
```

Más un CLI `uv run python -m exam.questions weekly monthly` que imprime cuántas preguntas hay por dominio × probe (y por persona).

### P2b · `exam/grading.py`

```python
def render(question: Question, state: dict | None) -> str       # lo que contestaría un agente que cree que el hecho vale `state`
def expected_answer(question: Question) -> str                  # render(question, question.current), salvo la regla de borrados
def grade(question: Question, answer: str | None) -> Grade      # None = el agente no contestó
def tally(questions: list[Question], grades: list[Grade]) -> dict[tuple[str, str, str], int]   # (domain, probe, outcome) -> cantidad
```

`render` es lo que permite la prueba de humo sin modelo: respuestas perfectas = `expected_answer`, todas `UNKNOWN`, todas viejas = `render(question, question.history[-1])`.

P2b no depende del código de P2a: puede construir `Question` a mano con `fact_states` sobre datos reales.

## Quién toca qué

| Archivo | Dueño | Notas |
| --- | --- | --- |
| `exam/schema.py`, `docs/p2-interfaz.md` | P2 | Los subproblemas no los editan: un cambio pasa por P2. |
| `exam/questions.py`, `tests/test_questions.py`, `docs/p2a-<nombre>.md` | P2a | |
| `exam/grading.py`, `tests/test_grading.py`, `docs/p2b-<nombre>.md` | P2b | |
| `truth/` | P1 (cerrado) | No se modifica salvo bug demostrado con un test; se reporta a P2. |
