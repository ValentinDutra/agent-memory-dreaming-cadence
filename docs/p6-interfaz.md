# P6 · Interfaz entre P6a (de dónde sale cada inventada) y P6b (¿crece con la vida del agente?)

P6 diagnostica las respuestas `invented` de P5. P6a clasifica cada una por causa; P6b mide si su tasa crece con las sesiones y depende de la política. Comparten este contrato, el motor de P5 (`policies/engine.py`, sin cambios) y el caché de P5.

## Contrato

```python
# diagnosis/invented.py  (dueño: P6; no llama a la API)
@dataclass(frozen=True)
class LineOrigin:
    line: str
    written_after: int               # sesión del sueño que escribió esta línea exacta, que siguió sin cortes hasta el examen
    sessions_read: tuple[int, ...]   # las sesiones que leyó ese sueño

@dataclass(frozen=True)
class WrongAnswer:
    policy: str; period: str; persona: str; repetition: int
    question: Question               # exam/schema.py: prompt, probe, current, history, session_id
    answer: str | None               # tal como lo escribió el modelo
    grade: Grade                     # outcome, expected, given
    notes: str                       # lo que leyó el examen
    last_dream: int | None           # sesión del sueño que dejó esas notas; None si todavía no había soñado
    related: tuple[LineOrigin, ...]  # líneas de la nota sobre el hecho de la pregunta, la de origen más viejo primero

def wrong_answers(run: PolicyRun, outcomes=("invented",)) -> list[WrongAnswer]
def related_lines(notes: str, question: Question) -> list[str]
    # mismo dominio y nombre parecido (dreaming.quality.similarity); para un total, toda línea con fecha en su rango
def line_origin(dreams: list[Step], line: str) -> LineOrigin
def describe(wrong: WrongAnswer) -> str   # bloque Markdown para los informes
```

CLI, desde el caché (tope $0 con `--check-cache`):

```bash
uv run python -m diagnosis.invented monthly/academic_researcher --policies every-5 --check-cache
uv run python -m diagnosis.invented monthly/academic_researcher:210 --policies never every-5 --outcomes invented stale --check-cache
```

`related_lines` es un primer filtro, no la clasificación: empareja por palabras, así que para un gasto trae también los de fechas vecinas. P6a lo puede afinar; si cambia la firma, avisa a P6 antes.

Para la exactitud línea por línea a lo largo del tiempo (P6b), usar lo de P4b sin cambios: `dreaming.quality.compare_notes(step.notes, timeline, step.session_id, transcript_text)` sobre cada `Step` con `dreamt=True` de un `PolicyRun`.

## Lo que ya se ve (punto de partida, sin interpretar)

`every-5` sobre monthly/academic_researcher entera (619 sesiones, 88 exámenes), salida en `results/p6/every-5-full-invented.txt`:

| dominio/probe | invented |
| --- | --: |
| expense/aggregate | 32 |
| expense/stable | 4 |
| expense/new | 3 |
| steps/aggregate | 1 |
| preference/recent_change | 1 |
| calendar/stable | 1 |

`never` en s1–210 (25): expense/aggregate 12, steps/aggregate 10, calendar/stable 3. Con notas vacías, un total "0" sale `invented` (P3 §4.1 ya lo había visto en el piso).

Hipótesis a probar, no conclusiones: 40 de 42 son gastos y pasos, y 33 son totales. Un total al que le falta un gasto, o con un error de suma, la corrección de P2 lo cuenta `invented` (P2 §3: "un error de suma sale `invented` dentro de `aggregate`"). Hay que separar eso de una nota falsa.

## Caché y presupuesto

- El caché de P5 está copiado en `results/` de este worktree (ignorado por git). P6a y P6b lo copian al suyo, solo lectura sobre el origen (`cp -R <worktree de P5>/results ./results`).
- Todo lo de academic_researcher que corrió P5 sale gratis: las 11 políticas en s1–210 y `every-5` entera.
- **Choque de cachés.** El mismo pedido hecho en dos worktrees da respuestas distintas (P5 §6). Solo P6b corre cadenas nuevas. Si P6a necesita llamar a la API (por ejemplo, re-preguntar un examen con otra nota), usa un `run` propio que empiece con `p6a/`, nunca `p5/`.
- Topes, con `BudgetedClient(<budget_name>, <tope>)`: P6a `p6a` $0,80; P6b `p6b` $1,60; integración `p6` $0,60.
