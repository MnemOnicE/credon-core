---
title: "Engine API"
description: "Reference for the Engine class that orchestrates agents, trust scoring, rewards, governance, and telemetry."
---

`Engine` in `simulations/engine.py` is the central object in Credon Core. It owns global parameters, creates the initial population, executes one simulation epoch at a time, and records telemetry rows in `history`.

Import path:

```python
from simulations.engine import Engine
```

<Callout type="warn">Because `simulations/engine.py` imports `Agent` with `from agents import Agent`, direct package-style imports can be fragile in this checkout. Running the file as a script or placing `simulations/` on `PYTHONPATH` is the most reliable current workflow.</Callout>

## Constructor

Source file: `simulations/engine.py`

Source signature:

```python
def __init__(self, num_honest=20, num_malicious=5):
```

Effective typed signature:

```python
def __init__(self, num_honest: int = 20, num_malicious: int = 5) -> None:
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `num_honest` | `int` | `20` | Number of honest agents to initialize. |
| `num_malicious` | `int` | `5` | Number of malicious agents to initialize. |

Core public configuration fields created by the constructor:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `B` | `int` | `500` | Bond size used by sponsor and candidate. |
| `L` | `int` | `400` | Loan principal. |
| `R` | `int` | `75` | Integrity reward. |
| `R_res` | `float` | `0.0` | Rewards reservoir. |
| `circulating_supply` | `float` | derived | Sum of initial balances plus later minting effects. |
| `rho` | `float` | `0.05` | Reward release rate. |
| `M_EPOCH_CIRCULATING_SUPPLY_CAP` | `float` | `0.01` | Intended cap constant, although the epoch logic currently hardcodes `0.01`. |
| `alpha_conviction` | `float` | `0.8` | Conviction accumulation factor. |
| `t_max` | `int` | `5` | Stored with governance settings; currently not used directly in conviction math. |
| `core_quorum` | `float` | `0.25` | Core governance quorum placeholder. |
| `core_approval` | `float` | `0.66` | Core governance approval placeholder. |
| `minor_quorum` | `float` | `0.10` | Minor proposal quorum. |
| `minor_approval` | `float` | `0.51` | Minor proposal approval threshold. |
| `alpha` | `float` | `0.4` | Trust weight for transitive trust `E`. |
| `beta` | `float` | `0.4` | Trust weight for social connectivity `P`. |
| `gamma` | `float` | `0.2` | Trust weight for time weighting `W`. |
| `ema_decay` | `float` | `0.1` | Exponential moving average decay for `W`. |

The constructor raises `ValueError` when `num_honest + num_malicious <= 0`, and this is tested in `simulations/test_engine.py`.

Example:

```python
from engine import Engine

engine = Engine(num_honest=10, num_malicious=2)
print(len(engine.agents))
print(engine.rho)
```

## Methods

### `calculate_transitive_trust`

Source signature:

```python
def calculate_transitive_trust(self):
```

Effective typed signature:

```python
def calculate_transitive_trust(self) -> dict[str, float]:
```

Computes the EigenTrust-style component `E` from the interaction graph.

Example:

```python
engine = Engine(3, 1)
scores = engine.calculate_transitive_trust()
print(scores)
```

### `calculate_social_connectivity`

Source signature:

```python
def calculate_social_connectivity(self):
```

Effective typed signature:

```python
def calculate_social_connectivity(self) -> dict[str, float]:
```

Computes the PageRank-style component `P`, including sink redistribution.

Example:

```python
engine = Engine(3, 1)
scores = engine.calculate_social_connectivity()
print(scores)
```

### `update_time_weighting`

Source signature:

```python
def update_time_weighting(self):
```

Effective typed signature:

```python
def update_time_weighting(self) -> dict[str, float]:
```

Updates the EMA-based recency term `W` from `recent_activity` and resets the per-epoch activity counters.

Example:

```python
engine = Engine(2, 0)
engine.recent_activity["H_0"] = 2
print(engine.update_time_weighting()["H_0"])
```

### `calculate_trust_scores`

Source signature:

```python
def calculate_trust_scores(self):
```

Effective typed signature:

```python
def calculate_trust_scores(self) -> dict[str, float]:
```

Combines `E`, `P`, and `W` into the final trust score `T`.

Example:

```python
engine = Engine(3, 1)
scores = engine.calculate_trust_scores()
print(scores["H_0"])
```

### `run_epoch`

Source signature:

```python
def run_epoch(self):
```

Effective typed signature:

```python
def run_epoch(self) -> None:
```

Runs one full simulation epoch: honest interactions, honest sponsored loans, malicious self-sponsored defaults, trust updates, reservoir math, governance voting, proposal execution, and telemetry recording.

Example:

```python
engine = Engine(20, 5)
engine.run_epoch()
print(engine.get_results()[-1]["epoch"])
```

### `get_results`

Source signature:

```python
def get_results(self):
```

Effective typed signature:

```python
def get_results(self) -> list[dict[str, float | int]]:
```

Returns the telemetry history accumulated so far.

Example:

```python
engine = Engine(5, 1)
for _ in range(2):
    engine.run_epoch()
print(engine.get_results())
```

## Common patterns

### Baseline run

```python
from engine import Engine

engine = Engine(num_honest=20, num_malicious=5)
for _ in range(15):
    engine.run_epoch()

history = engine.get_results()
print(history[-1]["avg_h_roi"], history[-1]["avg_m_roi"])
```

### Parameter tuning

```python
engine = Engine(num_honest=20, num_malicious=5)
engine.B = 500
engine.L = 300
engine.rho = 0.04
engine.alpha = 0.5
engine.beta = 0.3
engine.gamma = 0.2
```

### Governance inspection

```python
engine = Engine(20, 5)
for _ in range(10):
    engine.run_epoch()

print(engine.rho)
print([(p.id, p.target_rho, p.status) for p in engine.proposals])
```

## Notes on stability

This is the most important API in the repo, but it is still a research-oriented surface:

- Many behaviors are hardcoded inside `run_epoch()` rather than separated into strategy hooks.
- Printing is part of the method's side effects.
- Proposal batch helpers exist in the file but are not part of the main epoch path.
- `M_EPOCH_CIRCULATING_SUPPLY_CAP` is defined as a field, but the mint logic currently uses a literal `0.01` instead.

Related pages: [Architecture](/docs/architecture), [Trust Ledger](/docs/trust-ledger), and [Proposal API](/docs/api-reference/proposal).
