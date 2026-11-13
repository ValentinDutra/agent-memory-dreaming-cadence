# P4 · Interfaz entre P4a (qué entra y qué sale) y P4b (calidad del sueño)

P4a decide **qué lee un sueño, qué devuelve y con qué configuración** (`dreaming/dream.py`). P4b mide **qué tan buenas son las notas que deja**, con el examen de P3 y con una comparación directa contra la verdad de P1. Lo único que comparten es este contrato, `dreaming/transcripts.py` y `answering/client.py`.

Mientras P4a no termine, P4b usa el stub de `dreaming/dream.py`: una sola llamada que reescribe las notas enteras con un prompt mínimo. Al integrar, P4 reemplaza el stub por la versión de P4a y repite las mediciones de P4b con ella.

## Contrato

```python
# dreaming/transcripts.py  (dueño: P4; lo único que un sueño puede leer)
@dataclass(frozen=True)
class Turn: speaker: str; message: str              # speaker = "user_agent" | "ai_agent", como en Memora
@dataclass(frozen=True)
class Session: session_id: int; date: str; turns: tuple[Turn, ...]
def load_transcripts(period, persona) -> list[Session]          # todas, ordenadas por session_id
def sessions_between(sessions, after, through) -> list[Session]  # after < session_id <= through

# dreaming/dream.py  (dueño: P4a)
@dataclass(frozen=True)
class DreamResult:
    notes: str            # notas completas en el formato de P3 (answering/notes.py), listas para answer_exam
    input_tokens: int
    output_tokens: int    # incluye thinking
    cost: float           # dólares de la llamada (o la suma, si P4a usa más de una)
    from_cache: bool
def dream(notes: str, sessions: list[Session], client: BudgetedClient, run: str) -> DreamResult
```

### Semántica

- **Un sueño = notas actuales + transcripciones desde el último sueño → notas nuevas.** El primer sueño recibe `notes=""`. Las sesiones llegan ordenadas y son exactamente `sessions_between(todas, último_sueño, ahora)`.
- **Lo que devuelve siempre son las notas completas**, en el formato de P3, aunque por dentro P4a elija ediciones (agregar, cambiar o borrar líneas) aplicadas por código. Así P5 encadena sueños sin saber cómo se hicieron y P3 las lee sin cambios.
- **Sin totales semanales** (decisión de P3, `docs/p3-respuestas.md` § "Decisiones").
- **Las listas cerradas tienen que estar completas** (pendientes, calendario, elementos de documentos): el que responde contesta "no" a lo que no figura. Un pendiente cumplido que el sueño no borra sale `stale`.
- **El costo de un sueño** es `DreamResult.cost`, en dólares con los precios de `answering/client.py`, y los tokens de entrada y salida. Todas las llamadas pasan por `BudgetedClient`, así que quedan en el libro de gasto y en `results/raw/`.
- **Una llamada por sueño** salvo que P4a muestre con números que conviene más de una.

### Regla anti-trampa (obligatoria)

Un sueño solo ve lo que vería un agente real: `speaker`, `message`, `session_id` y `date`. **Nunca** `share_memory`, `operation`, `operation_details`, `session_type`, `persona`, ni nada de `truth/` o `exam/`.

- `dreaming/transcripts.py` arma cada `Session` campo por campo desde una lista permitida. El sueño recibe `Session`, nunca el dict de Memora.
- `tests/test_transcripts.py::test_the_dream_never_sees_the_answer_key` llama a `dream` con un cliente falso que guarda el prompt, sobre la s30 real de weekly/software_engineer. Cambia la hoja de respuestas y exige el mismo prompt, sin los nombres de esos campos y con "Bonobo" adentro. P4a no puede usar las palabras `session_type`, `operation`, `operation_details` ni `share_memory` en su prompt, y el test tiene que seguir pasando con su `dream`.
- `dreaming/dream.py` no importa `truth` ni `exam`. P4b sí los usa, pero solo para medir.

### Cliente

`answering/client.py` (dueño: P3, cambiado por P4): igual que en P3 (`docs/p3-interfaz.md`), con una diferencia: ahora la llamada es por streaming. El SDK rechaza una llamada sin streaming cuyo `max_tokens` pueda tardar más de 10 minutos (unos 21k tokens), y un sueño que reescribe notas monthly necesita más. La respuesta, el costo y el caché no cambian.

| Proceso | `budget_name` | Tope | `run` |
| --- | --- | --: | --- |
| P4a | `p4a` | $1.00 | `p4a/...` |
| P4b | `p4b` | $1.20 | `p4b/...` |
| Integración (P4) | `p4` | $0.80 | `p4/...` |

Si un proceso necesita más, se lo pide a P4 antes de pasarse: la organización tiene un límite de $10/mes y quedan unos $7,40 para todo el proyecto.

Precios por millón de tokens: $0.10 entrada / $0.50 salida con prompts de hasta 100k tokens; $0.50 / $2.50 por encima. **Los prompts de un sueño tienen que quedar por debajo de 100k tokens.**

## Datos medidos al definir la interfaz

- **Tamaño de una sesión:** weekly/software_engineer tiene 163 sesiones de unos 2.000 caracteres de texto (máximo 3.624). Monthly tiene 601–635 sesiones por persona, del mismo tamaño.
- **El stub, primer sueño de weekly/software_engineer sobre las sesiones 1–35:** 66.914 caracteres de prompt → 22.038 tokens de entrada, 3.147 de salida (thinking incluido), **$0.0038**. Bonobo (like en s17, borrado en s30) no quedó en las notas, como debe ser. Las etiquetas que inventa difieren de las de P3: "Upbeat electronic music (Music / Electronic)" o "LinkedIn post" en lugar de "Social media post". Ese es justo el tipo de cosa que P4b tiene que medir.
- **Cuántas sesiones caben:** a ~600 tokens por sesión, un sueño de 50 sesiones lee ~30k tokens más las notas (≤ 10k en monthly). 100k tokens alcanzan para unas 140 sesiones con notas monthly.
- **Casos de control** (weekly/software_engineer, de P1/P2): Bonobo like en s17 → borrado en s30; deep house dislike en s129 → like en s132; Mechanic visit agregado en s82 y reprogramado en s87 y s105 (defecto 1 de P1: la fecha guardada no coincide con el texto, el examen solo pregunta si existe).

## Quién toca qué

| Archivo | Dueño | Notas |
| --- | --- | --- |
| `dreaming/transcripts.py`, `tests/test_transcripts.py`, `docs/p4-interfaz.md`, `answering/client.py` | P4 | Los subproblemas no los editan: un cambio pasa por P4. |
| `dreaming/dream.py`, `tests/test_dream.py`, `docs/p4a-<nombre>.md` | P4a | Puede agregar módulos en `dreaming/` con prefijo `dream_` para variantes que compara. |
| `dreaming/quality*.py` (o el nombre que elija, con prefijo `quality`), `tests/test_quality.py`, `docs/p4b-<nombre>.md` | P4b | No edita `dream.py`. Si quiere probar una hipótesis sobre el sueño, lo hace en su propio módulo y lo propone en el informe. |
| `truth/`, `exam/`, `answering/` (salvo `client.py`) | P1, P2, P3 (cerrados) | No se modifican salvo bug demostrado con un test; se reporta a P4. |

`results/` está ignorado por git y no viaja entre worktrees: cada número de un informe tiene que salir de un comando que esté en el repo y que se pueda volver a correr.
