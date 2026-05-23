---
title: "Explore Parameter Sweeps"
description: "Run the built-in analytics scripts to compare loan-size and reward-rate scenarios and generate charts."
---

This guide covers the repo's main research workflow: change a policy parameter, replay multiple simulations, and inspect the aggregate charts written to `docs/results/`.

## Problem

Reading one epoch trace is not enough if you want to compare policy choices. You need a repeatable way to answer questions like:

- What happens if `L` approaches or exceeds the safe range relative to `B`?
- How does a larger `rho` affect circulating supply?
- Does trust divergence between honest and malicious agents widen or collapse under different settings?

## Solution

Use `simulations/sweep.py`. It already packages two experiments:

- `sweep_leverage()` varies `L` while keeping `B = 500`.
- `sweep_reward_rate()` varies `rho` and charts circulating supply over time.

<Steps>
<Step>
### Install the analytics stack

```bash
python -m pip install pandas matplotlib seaborn
```

</Step>
<Step>
### Run the bundled sweep script

```bash
python simulations/sweep.py
```

This runs both sweeps from the module's `__main__` block.

</Step>
<Step>
### Inspect the generated artifacts

The script creates these files in `docs/results/`:

- `roi_vs_leverage.png`
- `trust_divergence.png`
- `circulating_supply_vs_rho.png`

Those names come directly from `simulations/sweep.py`.

</Step>
<Step>
### Modify one parameter and rerun

```python
from simulations.engine import Engine

engine = Engine(num_honest=20, num_malicious=5)
engine.B = 500
engine.L = 800

for _ in range(20):
    engine.run_epoch()

print(engine.get_results()[-1])
```

Use this when the built-in sweep ranges are close but not exactly what you want.

</Step>
</Steps>

## Complete runnable example

The fastest way to add your own leverage checkpoints is to copy the internal pattern used by `sweep_leverage()`.

```bash
python - <<'PY'
import os
import sys

sys.path.insert(0, os.path.abspath("/workspace/home/credon-core"))
from simulations.engine import Engine

for loan_amount in (200, 400, 700):
    engine = Engine(num_honest=20, num_malicious=5)
    engine.B = 500
    engine.L = loan_amount
    for _ in range(10):
        engine.run_epoch()
    latest = engine.get_results()[-1]
    print(loan_amount, latest["avg_h_roi"], latest["avg_m_roi"], latest["avg_h_trust"], latest["avg_m_trust"])
PY
```

## How to interpret the charts

`roi_vs_leverage.png` answers whether the honest path remains economically preferable as the loan grows relative to the bond. Since the malicious expected value in the engine is `L - 2B`, larger `L` directly weakens the deterrent.

`trust_divergence.png` shows whether the TrustLedger still distinguishes honest and malicious actors when leverage changes. If malicious trust rises too quickly, then the graph defenses are not doing enough.

`circulating_supply_vs_rho.png` shows how aggressively the reservoir-release policy expands supply. That chart is the clearest output for testing whether the mint throttle is strong enough.

<Callout type="warn">The sweep code uses the current `Engine` implementation directly. If you change trust weights, governance thresholds, or malicious behavior, all existing charts become scenario-specific rather than reusable baselines. Regenerate them after every material logic change.</Callout>

For the underlying API, see [Sweep API Reference](/docs/api-reference/sweep). For performance tuning, continue to [Benchmark Core Math](/docs/guides/benchmark-core-math).
