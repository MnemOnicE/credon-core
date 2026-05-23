---
title: "Run a Baseline Simulation"
description: "Execute the main Credon Core engine loop and inspect the telemetry it records after each epoch."
---

This guide is for the most common first task: run the protocol model as-is and inspect how honest and malicious agents diverge over time.

## Problem

You want to see the whole system working together, not just isolated methods. That means running the epoch loop that combines sponsored loans, attack behavior, trust math, rewards, and governance.

## Solution

Use the bundled `simulations/engine.py` script from the repository root. That is the path that best matches the current import layout in the checkout.

<Steps>
<Step>
### Install the Python dependencies you need

```bash
python -m pip install pytest pandas matplotlib seaborn
```

Only `pytest` is needed for the unit tests. The analytics stack is needed later if you also want to run the sweep scripts.

</Step>
<Step>
### Run the engine script

```bash
python simulations/engine.py
```

The file's `__main__` block creates `Engine(num_honest=20, num_malicious=5)` and runs fifteen epochs.

</Step>
<Step>
### Read the epoch summary output

You should see repeated blocks containing:

```text
=== EPOCH N SUMMARY ===
Epoch Verified Volume (Repaid L): ...
Rewards Reservoir R_res (Locked): ...
Circulating Supply: ...
Game Theory EV(Honest): ...
Game Theory EV(Attacker): ...
Actual Avg Honest ROI so far: ...
Actual Avg Attacker ROI so far: ...
Governance - Total $CRED: ...
Avg Trust Score (Honest): ...
Avg Trust Score (Malicious): ...
```

Those values are printed by `Engine.run_epoch()` after it updates `history`.

</Step>
<Step>
### Script the engine for your own scenarios

```python
from engine import Engine

engine = Engine(num_honest=30, num_malicious=10)
engine.B = 500
engine.L = 300
engine.rho = 0.05

for _ in range(8):
    engine.run_epoch()

for row in engine.get_results():
    print(row["epoch"], row["avg_h_roi"], row["avg_m_roi"])
```

Run that from inside the `simulations/` directory or set `PYTHONPATH=simulations` first, because `engine.py` currently imports `Agent` with `from agents import Agent`.

</Step>
</Steps>

## Complete runnable pattern

```bash
cd simulations
python - <<'PY'
from engine import Engine

engine = Engine(num_honest=10, num_malicious=3)
for _ in range(5):
    engine.run_epoch()

latest = engine.get_results()[-1]
print("epoch:", latest["epoch"])
print("honest_roi:", latest["avg_h_roi"])
print("malicious_roi:", latest["avg_m_roi"])
print("honest_trust:", latest["avg_h_trust"])
print("malicious_trust:", latest["avg_m_trust"])
PY
```

## What to watch for

- `avg_h_roi` versus `avg_m_roi` tells you whether the incentive structure is separating honest and malicious behavior.
- `avg_h_trust` versus `avg_m_trust` tells you whether the interaction graph is isolating Sybil clusters.
- `rho`, `R_res`, and the proposal list tell you whether governance is responding to inflation and activity the way you expect.

<Callout type="warn">The repo does not currently ship packaging metadata such as `pyproject.toml`, so script execution is more reliable than package-style importing. If you plan to embed the engine in another project, fix the import boundary first.</Callout>

Related reading: [Architecture](/docs/architecture), [Trust Ledger](/docs/trust-ledger), and the [Engine API reference](/docs/api-reference/engine).
