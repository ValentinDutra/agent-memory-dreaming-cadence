# P1 · Interfaz entre P1a (extraer cambios) y P1b (representar y validar)

P1a convierte cada sesión de Memora en una lista de `Change`. P1b consume esa lista y construye la verdad en el tiempo. Lo único que comparten es `truth/changes.py`.

## Contrato

```python
# truth/changes.py  (dueño: P1a)
MEMORA_DATA: Path                     # ruta absoluta a vendor/Memora/data (solo lectura)
PERIODS = ("weekly", "monthly", "quarterly")

@dataclass(frozen=True)
class Change:
    session_id: int                   # session_id de Memora (no el número de archivo)
    date: str                         # "date" de la sesión, "YYYY-MM-DD"
    action: "add" | "update" | "remove"
    domain: str                       # "preference", "todo", ... (P1a define la lista)
    key: tuple[str, ...]              # identifica el hecho dentro del dominio
    value: dict | None                # valor del hecho DESPUÉS del cambio; None si action == "remove"
    previous: dict | None = None      # valor que Memora dice que tenía ANTES; None = Memora no lo dice
    evidence_turns: tuple[int, ...] = ()  # turnos con share_memory=True

def personas(period) -> list[str]
def load_sessions(period, persona) -> list[dict]    # JSON crudo, en orden cronológico
def extract_changes(session: dict) -> list[Change]  # en el orden en que se aplican
def persona_changes(period, persona) -> list[Change]
```

### Semántica que P1b puede asumir

Un hecho se identifica por `(domain, key)`.

| action   | precondición                       | efecto                          |
| -------- | ---------------------------------- | ------------------------------- |
| `add`    | el hecho no existe                 | el hecho pasa a valer `value`   |
| `update` | el hecho existe (y vale `previous`, si `previous` no es None) | el hecho pasa a valer `value` |
| `remove` | el hecho existe (y vale `previous`, si `previous` no es None) | el hecho deja de existir |

- Una sesión puede producir 0, 1 o varios cambios. Se aplican en el orden de la lista.
- Una precondición que no se cumple **no** es un error de P1a: es un hallazgo que P1b reporta (defecto del dataset o error de extracción).
- Los cambios de una sesión N forman parte del estado "después de la sesión N".
- `value` y `previous` son dicts JSON planos y comparables con `==`.

### Ejemplo real (stub actual)

`weekly/academic_researcher/session_0040.json` (`preference_update`, `value_update`):

```python
Change(40, "2025-06-02", "remove", "preference", ("actors", "Joan Crawford"), None, {"preference": "like"}, (16,))
Change(40, "2025-06-02", "add",    "preference", ("actors", "Grace Kelly"),   {"preference": "like"}, None, (16,))
```

## Estado actual del stub

`truth/changes.py` ya cubre preferencias (add, delete, `preference_update`, `value_update`) y pendientes (`todo_list` add/delete). Devuelve `[]` para todo lo demás. Corre sobre los datos reales:

```
uv run python -c "from truth.changes import *; print(len(persona_changes('weekly', 'academic_researcher')))"
54
```

## Quién toca qué

| Archivo                         | Dueño | Notas |
| ------------------------------- | ----- | ----- |
| `truth/changes.py`              | P1a   | Puede agregar dominios y cambiar claves/valores. No cambia la firma de `Change` ni de las funciones sin pasar por P1. |
| `tests/test_changes.py`         | P1a   | |
| `docs/p1a-<nombre>.md`          | P1a   | |
| `truth/timeline.py`             | P1b   | Representación de la verdad en el tiempo y validación. Solo importa de `truth/changes.py`. |
| `tests/test_timeline.py`        | P1b   | |
| `docs/p1b-<nombre>.md`          | P1b   | |

P1b no edita `truth/changes.py`. Si necesita algo nuevo de P1a, pasa por P1, que integra los dos.

## Qué expone P1b para P2–P7

Como mínimo, una consulta "estado después de la sesión N":

```python
# truth/timeline.py  (dueño: P1b)
def state_after(changes: list[Change], session_id: int) -> dict[tuple[str, tuple[str, ...]], dict]
#   clave: (domain, key); valor: value
```

más la lista de inconsistencias encontradas. La representación interna (estado completo por sesión, registro de eventos, intervalos de validez, etc.) la elige P1b.
