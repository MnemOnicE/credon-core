---
title: "Getting Started"
description: "Understand what Credon Core models, what code is actually implemented in this checkout, and how to run the simulation baseline."
---

Credon Core is a Python simulation framework for modeling trust-backed lending, Sybil resistance, and governance in the Credon Protocol.

<Callout type="info">The README describes a larger protocol roadmap that includes Solidity contracts and ZK components, but the executable code in this checkout lives in `simulations/` and models the protocol mechanics in Python.</Callout>

## The Problem

- Traditional lending models privilege capital, not demonstrated reliability.
- Purely social credit systems are easy to game with Sybil accounts and closed interaction rings.
- Token-weighted governance can let well-capitalized actors force inflationary or self-serving policy changes.
- Protocol designers need a fast way to test incentive loops before they commit them to smart contracts.

## The Solution

Credon Core turns those questions into a simulation loop. `simulations/agents.py` models honest and malicious actors, `simulations/engine.py` runs sponsored loans plus TrustLedger scoring and governance, and `simulations/sweep.py` generates charts for leverage and reward-policy experiments.

This example assumes you are running the script from the repository root (or have set `PYTHONPATH` to include the project root) so that the `simulations.engine` import works.

```python
from simulations.engine import Engine

engine = Engine(num_honest=20, num_malicious=5)

for _ in range(3):
    engine.run_epoch()

latest = engine.get_results()[-1]
print(latest["epoch"], latest["avg_h_trust"], latest["avg_m_trust"])
```

This gives you a single object that evolves the lending market, accumulates reputation signals, and records telemetry you can chart or compare across parameter sweeps.

## Installation

<Callout type="warn">Credon Core is not published as an npm package. The tabs below are present to match the docs shell, but every path ends with cloning the repository and installing Python dependencies because that is the only runnable surface in this checkout.</Callout>

<Tabs items={["npm", "pnpm", "yarn", "bun"]}>
<Tab>

```bash
git clone https://github.com/mnemonice/credon-core.git
cd credon-core
python -m pip install pytest pandas matplotlib seaborn
```

</TabItem>
<TabItem value="pnpm">

```bash
git clone https://github.com/mnemonice/credon-core.git
cd credon-core
python -m pip install pytest pandas matplotlib seaborn
```

</TabItem>
<TabItem value="yarn">

```bash
git clone https://github.com/mnemonice/credon-core.git
cd credon-core
python -m pip install pytest pandas matplotlib seaborn
```

</TabItem>
<TabItem value="bun">

```bash
git clone https://github.com/mnemonice/credon-core.git
cd credon-core
python -m pip install pytest pandas matplotlib seaborn
```

</TabItem>
</Tabs>

## Quick start

The smallest deterministic example is the `Agent` loan lifecycle.

```python
from simulations.agents import Agent

borrower = Agent(agent_id="H_0")
loan_record = {"status": "pending"}

borrower.receive_loan(400)
repaid = borrower.repay_loan(400, loan_record)

print(repaid)
print(loan_record["status"])
print(borrower.cred_balance)
```

Expected output:

```text
True
repaid
0
```

For the full system, run the engine script from the repository root:

```bash
python simulations/engine.py
```

That prints epoch summaries with verified volume, circulating supply, ROI telemetry, governance state, and average trust scores.

## Key features

- Bonded endorsement mechanics with separate sponsor and candidate bonds.
- Honest-versus-malicious agent behaviors in the same simulation loop.
- A three-part TrustLedger score built from transitive trust, social connectivity, and time-weighted activity.
- Governance proposals that adjust the reward release rate `rho` with conviction voting for core changes.
- Sweep scripts that output leverage and monetary-policy charts to `docs/results/`.
- Benchmark scripts for trust, PageRank-style connectivity, and voting-loop performance.

## Supported environments

- Python scripts executed directly from the repository.
- Optional analytics dependencies: `pandas`, `matplotlib`, and `seaborn`.
- Developer tooling implied by the repo: `pytest` for tests and Ruff-compatible lint settings in `ruff.toml`.

## Where to go next

<Cards>
  <Card title="Architecture" href="/docs/architecture">See how agents, trust scoring, governance, and analytics fit together.</Card>
  <Card title="Core Concepts" href="/docs/trust-ledger">Start with the TrustLedger, then move to bonded endorsements and governance.</Card>
  <Card title="API Reference" href="/docs/api-reference/engine">Jump into the `Engine`, `Proposal`, `Agent`, and sweep function details.</Card>
</Cards>
