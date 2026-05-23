---
title: "Sweep API"
description: "Reference for the analytics functions that replay Credon Core under multiple leverage and reward-rate settings."
---

The sweep functions in `simulations/sweep.py` are the repo's experiment harness. They are not new protocol logic; they are wrappers around repeated `Engine` runs plus chart generation with `pandas`, `matplotlib`, and `seaborn`.

Import path:

```python
from simulations.sweep import sweep_leverage, sweep_reward_rate
```

<Callout type="info">`simulations/sweep.py` inserts the repository root into `sys.path` before importing `simulations.engine`. That makes the file runnable as a script from the repository root even though the engine module is not packaged cleanly yet.</Callout>

## `sweep_leverage`

Source file: `simulations/sweep.py`

Source signature:

```python
def sweep_leverage():
```

Effective typed signature:

```python
def sweep_leverage() -> None:
```

Runs the engine across loan amounts `100` through `800` in steps of `100`, with:

- `b_value = 500`
- `epochs = 20`
- `num_honest = 20`
- `num_malicious = 5`

Outputs:

- `docs/results/roi_vs_leverage.png`
- `docs/results/trust_divergence.png`

Example:

```python
from simulations.sweep import sweep_leverage

sweep_leverage()
```

## `sweep_reward_rate`

Source file: `simulations/sweep.py`

Source signature:

```python
def sweep_reward_rate():
```

Effective typed signature:

```python
def sweep_reward_rate() -> None:
```

Runs the engine across reward release rates `[0.01, 0.05, 0.10, 0.20]`, each for twenty epochs, and generates `docs/results/circulating_supply_vs_rho.png`.

Example:

```python
from simulations.sweep import sweep_reward_rate

sweep_reward_rate()
```

## Combined usage

The module's `__main__` block runs both sweeps back to back:

```bash
python simulations/sweep.py
```

If you want to script the functions yourself:

```python
from simulations.sweep import sweep_leverage, sweep_reward_rate

sweep_leverage()
sweep_reward_rate()
```

## Parameter assumptions

These functions bake in several assumptions instead of taking arguments:

| Setting | `sweep_leverage` | `sweep_reward_rate` | Description |
|---------|------------------|---------------------|-------------|
| Honest agents | `20` | `20` | Baseline honest population per experiment. |
| Malicious agents | `5` | `5` | Baseline malicious population per experiment. |
| Epochs | `20` | `20` | Number of epochs per scenario. |
| Output directory | `docs/results` | `docs/results` | Written with `os.makedirs(..., exist_ok=True)`. |

If you need configurable sweeps, the usual extension is to copy the function body and expose the hardcoded values as parameters rather than trying to monkey-patch globals.

## Related scripts

The benchmark files in `simulations/benchmark_trust.py`, `simulations/benchmark_pagerank.py`, and `simulations/benchmark_voting.py` serve a similar operational purpose but are aimed at performance profiling rather than scenario analysis. They are best treated as contributor tools, not stable API.

Related pages: [Explore Parameter Sweeps](/docs/guides/explore-parameter-sweeps) and [Engine API](/docs/api-reference/engine).
