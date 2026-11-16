# How often should an agent dream?

An agent keeps notes between sessions, and "dreaming" is the offline pass that rereads past sessions and fixes those notes. Lance Martin's "The components of agent memory" (Anthropic, November 6, 2026) leaves open how to "carefully tune the cadence of dreaming". This repo measures that question on the [Memora](https://github.com/geniesinc/Memora) benchmark with Claude Haiku 5.5.

Sessions never write notes; only a dream does. Every 7 sessions an exam is answered from the notes alone, and graded against the true state of the user's facts at that point.

## Result

10 monthly personas, sessions 1–210, 2 repetitions, 95% intervals resampled by persona (`docs/p7-corrida-final.md`):

| Schedule | Exam accuracy (official) | Maintenance cost per persona |
| --- | --: | --: |
| Dream when a phrase detector spots a new fact | 94.2% [92.5, 95.8] | $0.0993 |
| Dream after every session | 94.1% [92.4, 95.7] | $0.1223 |
| Dream every 5 sessions | 87.2% [85.7, 88.5] | $0.0492 |
| Dream every 10 sessions | 80.1% [79.1, 81.0] | $0.0394 |
| Dream every 20 sessions | 72.9% [71.6, 74.0] | $0.0317 |
| Dream every 50 sessions | 57.7% [56.5, 58.6] | $0.0278 |
| Never dream | 25.7% [24.9, 26.5] | $0 |

- The phrase-triggered schedule ties dreaming every session (−0.1 points [−0.6, +0.5]) at 81% of the cost.
- Dreaming every 5 sessions loses 7.0 points [6.0, 8.1] in all 10 personas, all of it on new or recently changed facts.
- The dream's main error is leaving facts out, by rule. Three rules that name them cut those omissions from 34 to 9 (`docs/p8b-sueno-nombrado.md`). The recommended agent is the phrase-triggered schedule with that dream (`dreaming/dream_named.py`).

Limits: Memora is synthetic and its users mostly state changes explicitly; one model; the named dream was measured with the phrase-triggered schedule only.

## Setup

| | |
| --- | --- |
| Model | Claude Haiku 5.5 (`claude-haiku-5-5`) for every API call: dreams and exam answers. Adaptive thinking at medium effort. Haiku 5.5 takes no temperature, so repetitions measure its own sampling noise (`answering/client.py`) |
| No model | Grading is deterministic code (`exam/grading.py`). The phrase detector is regular expressions over the user's turns (`policies/triggered.py`) |
| Dream | Reads the current notes and every turn of the sessions since the last dream, and replies with edits in the style of the memory tool's `str_replace`, not a rewrite (`dreaming/dream.py`; the adopted version is `dreaming/dream_named.py`) |
| Exam | Every 7 sessions, answered from the notes alone; 30 exams per persona over sessions 1–210 (`exam/questions.py`) |
| Data | Memora commit `a6493188`, monthly period: 10 personas, 601 to 635 sessions each, about 20 a day over one month |
| Statistics | 2 repetitions per run; 95% intervals from a bootstrap over personas, 10,000 resamples, seed 20261113 (`final/analysis.py`); `PYTHONHASHSEED=0` on every run |
| Spend | A dollar cap in code on every client (`BudgetedClient`), and every response cached in `results/`. Final grid $11.87, named-dream run $2.72 |

## Code

| Folder | What it holds | Step |
| --- | --- | --- |
| `truth/` | Which facts are true after each session, from Memora's traces | P1 |
| `exam/` | Questions, grading, and the questions no dream can get right | P2 |
| `answering/` | The API client and answering an exam from notes | P3 |
| `dreaming/` | The dream, its alternatives and its quality measurements | P4, P8 |
| `policies/` | When to dream: fixed cadences, triggered dreaming, the engine that runs them | P5 |
| `diagnosis/` | Where wrong and invented answers come from | P6 |
| `final/` | The final grid, analysis, charts, and the P7c and P8 scripts | P7, P8 |

## Steps

Each step has a tag at its final commit and reports in `docs/` (in Spanish).

| Tag | Step | Reports |
| --- | --- | --- |
| `p1` | Ground truth: which facts are true after each session | `docs/p1-verdad.md`, `p1a-cambios.md`, `p1b-estado.md` |
| `p2` | The exam: what to ask, when, and how to grade | `docs/p2-examen.md`, `p2a-que-preguntar-y-cuando.md`, `p2b-como-corregir.md` |
| `p3` | Answering from notes only: format, ceiling, floor and noise | `docs/p3-respuestas.md`, `p3a-formato.md`, `p3b-techo-piso-ruido.md` |
| `p4` | One dream: what goes in and out, and its quality | `docs/p4-sueno.md`, `p4a-entrada-y-salida.md`, `p4b-calidad-del-sueno.md` |
| `p5` | Cadence policies: fixed and triggered | `docs/p5-politicas.md`, `p5a-cadencias-fijas.md`, `p5b-sueno-disparado.md` |
| `p6` | Where invented answers come from | `docs/p6-inventadas.md`, `p6a-origen-de-las-inventadas.md`, `p6b-crece-con-la-vida.md` |
| `p7` | Final run, analysis and diagnosis | `docs/p7-corrida-final.md`, `p7a-corrida-final.md`, `p7b-analisis.md`, `p7c-diagnostico.md` |
| `p8` | Dreams that leave facts out | `docs/p8a-omisiones.md`, `p8b-sueno-nombrado.md` |

Each step also has a `docs/pN-interfaz.md` with the contract its two halves shared.

## Reproduce

1. Clone Memora into `vendor/Memora` (the runs used commit `a6493188`):
   `git clone https://github.com/geniesinc/Memora vendor/Memora`
2. In a git worktree, which has neither `vendor/` nor `.env`, set `MEMORA_ROOT` and `ENV_FILE` to the main checkout's copies.
3. Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY`.
4. `uv sync`, then `uv run pytest -q`. The tests make no API calls.
5. Commands for each run are in section 4 of each report. Every run uses `PYTHONHASHSEED=0` and a spend cap in code. API responses are cached in `results/`, which is not in git, so a fresh run pays again: the final grid cost $11.87 and the named-dream run $2.72.
