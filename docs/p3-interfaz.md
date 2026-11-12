# P3 · Interfaz entre P3a (formato) y P3b (techo, piso y ruido)

P3a decide **cómo se escriben las notas** y **cómo se le presenta el examen** al modelo. P3b mide, con ese formato, **cuánto acierta el modelo con notas perfectas, con notas vacías y repitiendo el mismo examen**. Lo único que comparten es este contrato y `answering/client.py` (dueño: P3).

Mientras P3a no termine, P3b usa los stubs de `answering/notes.py` y `answering/answer.py`. Al integrar, P3 reemplaza los stubs por la versión de P3a y repite las mediciones de P3b con ese formato.

## Contrato

```python
# answering/notes.py  (dueño: P3a; Markdown por dominio, ver docs/p3a-formato.md)
def render_notes(facts: dict[FactId, dict]) -> str
    # facts = Timeline.state_after(N): notas que contienen exactamente esos hechos. {} -> notas vacías.

# answering/answer.py  (dueño: P3a; respuestas dentro de <answers>, ver docs/p3a-formato.md)
def answer_exam(notes: str, questions: list[Question], client: BudgetedClient, run: str, repeat: int = 0) -> list[str | None]
    # Una sola llamada por examen. Una respuesta por pregunta, en el mismo orden; None si el modelo no la dio.
    # Cada respuesta es texto que exam.grading.grade(question, answer) puede leer.

# answering/client.py  (dueño: P3)
MODEL = "claude-haiku-5-5"
TEMPERATURE = "model default (not settable)"   # ver "Temperatura" abajo
THINKING = {"type": "adaptive"}; EFFORT = "medium"  # configuración oficial para contestar exámenes (decisión de P3 al integrar)
class BudgetedClient(budget_name, limit_dollars, thinking=THINKING, effort=EFFORT):
    def complete(run, system, user, max_tokens, repeat=0) -> Completion   # text, tokens, cost, from_cache, temperature, thinking, effort, model
    def spent() -> float
class BudgetExceeded(RuntimeError)
```

### Semántica

- **Las notas son lo único que ve el modelo.** Ni la transcripción, ni el `session_id`, ni la verdad. El examen de la sesión N se contesta con `render_notes(timeline.state_after(N))` para el techo y con `render_notes({})` para el piso.
- **El formato lo va a escribir un dream (P4).** Tiene que poder escribirlo y mantenerlo un modelo leyendo conversaciones: nada de claves internas que el modelo nunca ve. Ejemplo: la clave de un gasto es `(session_id,)`; en las notas un gasto se identifica por fecha y tipo, igual que en la pregunta.
- **Las notas del techo solo contienen lo que un dream puede escribir y mantener.** Un dato derivado, como un total semanal precalculado, entra en las notas solo si P4 se compromete a mantenerlo. Si entra, este documento dice cuál es y cómo se actualiza, para que P4 lo herede. El techo se reporta siempre con y sin esos datos derivados, para que el efecto de la aritmética quede visible.
- **`answer_exam` no conoce la verdad.** Solo recibe las notas y los `Question.prompt` (puede usar `answer_format` y `options` para pedir el formato). No puede leer `current` ni `history`.
- **Una llamada por examen** (P2a §3.2: monthly costaría ≈ 970 M tokens con una llamada por pregunta).

### Cliente con tope de gasto

- **Tope por proceso, persistente.** Cada respuesta pagada se anota en `results/spend/<budget_name>.jsonl`. Antes de cada llamada, `complete` suma ese libro y aborta con `BudgetExceeded` si `gastado + peor caso > tope`. El peor caso usa los bytes del prompt como cota de los tokens de entrada (un token BPE nunca es más corto que un byte) y `max_tokens` como salida.
- **Respuestas crudas.** Cada respuesta pagada queda en `results/raw/<run>/<hash>.json` con el pedido completo, el texto, `usage`, el costo, el modelo, el thinking, el effort y la temperatura. El mismo pedido con el mismo `repeat` se lee de ahí sin pagar; así se puede recorregir gratis. Para medir ruido, se cambia `repeat`.
- **Precios** (por millón de tokens): $0.10 entrada y $0.50 salida con prompts de hasta 100k tokens; $0.50 y $2.50 por encima. Cache: escritura 1,25×, lectura 0,1×. Los prompts tienen que quedar por debajo de 100k: las notas perfectas de monthly pesan entre 1,6 y 54 KB (media 35 KB), unos 10k tokens.
- **Las llamadas son secuenciales.** El chequeo del tope no es seguro con hilos en paralelo.

| Proceso | `budget_name` | Tope |
| --- | --- | --: |
| P3a | `p3a` | $0.80 |
| P3b | `p3b` | $1.20 |
| Integración (P3) | `p3` | $1.00 |

### Lo que P4 hereda de P3

- **Formato de las notas:** el de `answering/notes.py` (P3a §3.1). Markdown con una sección por dominio y un hecho por línea, todo nombrado como lo nombra el usuario. Las listas cerradas (pendientes, calendario) se escriben aunque estén vacías (`- (none)`). Sin la prosa larga de los documentos.
- **Las notas tienen que estar completas.** El prompt de respuesta dice que las listas son cerradas: lo que no figura no está, y la respuesta es "no". Un pendiente cumplido que el dream no borra sale `stale`; un pendiente nuevo que no anota también sale `stale` ("no").
- **Sin totales semanales precalculados.** Decisión de P3: el dream **no** mantiene totales. Con el prompt final el techo sin totales es 97,7 % en weekly y 100 % en monthly; con totales, 100 % en los dos (`docs/p3-respuestas.md` §4). Si el dream sumara, sus errores de aritmética se mezclarían con los de memoria en las preguntas `aggregate`. Sin totales, ese error queda del lado del que responde, y está medido acá. Si algún día se cambia, la especificación probada es `answering/format_totals.py`: semanas de domingo a sábado, un total "so far" por semana, cada gasto o registro de pasos nuevo se suma a la semana de su fecha, y nunca hay que restar.

### Temperatura

Claude Haiku 5.5 no acepta `temperature`, `top_p` ni `top_k`. La guía de migración dice: *"On Claude Haiku 5.5, omit `temperature`, `top_p`, and `top_k` and use prompting to guide the model's behavior instead"* (https://platform.claude.com/docs/en/models/haiku-5-5/migration-guide), y el SDK 2.6.0 ya no tiene el parámetro (`TypeError: Messages.create() got an unexpected keyword argument 'temperature'`). Por eso:

- La temperatura queda en el valor por omisión del modelo y se registra como tal en cada resultado.
- Lo que sí se fija y se registra es el **thinking** y el **effort**. Por omisión, desde la integración: `{"type": "adaptive"}` y `"medium"`. Con effort `low`, el thinking adaptativo no piensa en 18 de 69 exámenes y ahí caen los errores que se repiten (P3a §3.3). `{"type": "disabled"}` sigue disponible por cliente; con `disabled`, `usage.output_tokens_details.thinking_tokens == 0`.
- El ruido de P3b mide la variación del modelo con su muestreo por omisión.

## Prueba del stub (P3, costo real $0.00085)

weekly/software_engineer, examen de la s147, notas perfectas con el stub: 16 `correct`, 3 `missing`, 2 `invented` de 21. Los errores ya muestran dónde mirar:

- **`missing` en listas cerradas.** "¿Está 'X' en la lista de pendientes?" con un distractor: el modelo contesta "unknown" en lugar de "no". El prompt no le dice que las notas están completas.
- **`invented` en totales.** Total de gastos esperado 258,23 y el modelo da 503; pasos 46.312 y da 52.181. Es una suma sobre las notas, sin thinking.
- **Un `stable` de gusto contestado "unknown".**

## Quién toca qué

| Archivo | Dueño | Notas |
| --- | --- | --- |
| `answering/client.py`, `tests/test_client.py`, `docs/p3-interfaz.md` | P3 | Los subproblemas no los editan: un cambio pasa por P3. |
| `answering/notes.py`, `answering/answer.py`, `tests/test_answer.py`, `docs/p3a-<nombre>.md` | P3a | Puede agregar módulos en `answering/` con prefijo `format_` para las variantes que compara. |
| `answering/bounds.py` (o el nombre que elija, con prefijo `bounds`), `tests/test_bounds.py`, `docs/p3b-<nombre>.md` | P3b | No edita `notes.py` ni `answer.py`: si necesita un cambio de formato para probar una hipótesis (p. ej. totales precalculados), lo hace en su propio módulo y lo propone en el informe. |
| `truth/`, `exam/` | P1, P2 (cerrados) | No se modifican salvo bug demostrado con un test; se reporta a P3. |
