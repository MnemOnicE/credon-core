---
title: "Agent API"
description: "Reference for the Agent class that models balances, interactions, endorsements, defaults, and graduation rewards."
---

`Agent` in `simulations/agents.py` is the basic state container for every participant in the simulation. Honest and malicious behavior both start from this class; the difference is mostly in constructor flags and how `Engine.run_epoch()` uses each instance.

Import path:

```python
from simulations.agents import Agent
```

<Callout type="info">The source file is untyped. The typed signatures below are effective signatures inferred from actual runtime usage in `simulations/agents.py` and `simulations/engine.py`.</Callout>

## Constructor

Source file: `simulations/agents.py`

Source signature:

```python
def __init__(self, agent_id, is_malicious=False, b=500, l_amount=400, r=75):
```

Effective typed signature:

```python
def __init__(
    self,
    agent_id: str,
    is_malicious: bool = False,
    b: int = 500,
    l_amount: int = 400,
    r: int = 75,
) -> None:
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `agent_id` | `str` | — | Identifier such as `H_0` or `M_0`. |
| `is_malicious` | `bool` | `False` | Selects the malicious starting balance and attack role. |
| `b` | `int` | `500` | Bond amount stored as `self.B`. |
| `l_amount` | `int` | `400` | Loan principal stored as `self.L`. |
| `r` | `int` | `75` | Integrity reward stored as `self.R`. |

Important attributes initialized by the constructor:

- `balance`: `2500` for honest agents, `50000` for malicious agents.
- `cred_balance`: governance balance minted on graduation.
- `staked_cred`: reserved for proposal locking behavior.
- `active_loans`: currently unused by the main epoch loop.
- `interactions`: adjacency map of counterparty ID to cumulative value.

Example:

```python
from simulations.agents import Agent

honest = Agent("H_0")
attacker = Agent("M_0", is_malicious=True)

print(honest.balance)
print(attacker.balance)
```

## Methods

### `interact_with`

Source signature:

```python
def interact_with(self, other_agent_id, value=1):
```

Effective typed signature:

```python
def interact_with(self, other_agent_id: str, value: int | float = 1) -> None:
```

Records weighted interactions in the local adjacency map.

Example:

```python
agent = Agent("H_0")
agent.interact_with("H_1", value=10)
agent.interact_with("H_1", value=5)
print(agent.interactions["H_1"])
```

### `try_sponsor`

Source signature:

```python
def try_sponsor(self, candidate_id, current_epoch):
```

Effective typed signature:

```python
def try_sponsor(self, candidate_id: str, current_epoch: int) -> dict[str, object] | None:
```

Debits one sponsor bond and returns a pending loan record if balance is sufficient.

Example:

```python
agent = Agent("H_0")
record = agent.try_sponsor(candidate_id="H_1", current_epoch=3)
print(record["status"] if record else None)
```

### `post_candidate_bond`

Source signature:

```python
def post_candidate_bond(self):
```

Effective typed signature:

```python
def post_candidate_bond(self) -> int:
```

Debits the candidate-side bond and returns the amount posted, or `0` when balance is insufficient.

Example:

```python
candidate = Agent("H_1")
posted = candidate.post_candidate_bond()
print(posted, candidate.balance)
```

### `receive_loan`

Source signature:

```python
def receive_loan(self, loan_amount):
```

Effective typed signature:

```python
def receive_loan(self, loan_amount: int | float) -> None:
```

Credits the agent with loan principal.

Example:

```python
borrower = Agent("H_2")
borrower.receive_loan(400)
print(borrower.balance)
```

### `process_graduation`

Source signature:

```python
def process_graduation(self, bond_returned, reward):
```

Effective typed signature:

```python
def process_graduation(self, bond_returned: int | float, reward: int | float) -> None:
```

Returns the bond, applies the reward, and increments `cred_balance`.

Example:

```python
agent = Agent("H_0")
agent.process_graduation(bond_returned=500, reward=75)
print(agent.balance, agent.cred_balance)
```

### `execute_default`

Source signature:

```python
def execute_default(self, loan_record):
```

Effective typed signature:

```python
def execute_default(self, loan_record: dict[str, object]) -> dict[str, object]:
```

Marks the loan record as defaulted. The balance-side consequences are handled by the caller.

Example:

```python
agent = Agent("M_0", is_malicious=True)
record = {"status": "pending"}
print(agent.execute_default(record)["status"])
```

### `repay_loan`

Source signature:

```python
def repay_loan(self, loan_amount, loan_record):
```

Effective typed signature:

```python
def repay_loan(self, loan_amount: int | float, loan_record: dict[str, object]) -> bool:
```

Repays the loan if balance is sufficient and marks the record as `repaid`.

Example:

```python
agent = Agent("H_0")
record = {"status": "pending"}
agent.receive_loan(400)
print(agent.repay_loan(400, record))
print(record["status"])
```

## Common patterns

The most common composition is:

```python
sponsor = Agent("H_0")
candidate = Agent("H_1")

record = sponsor.try_sponsor(candidate.id, 1)
if record and candidate.post_candidate_bond() == candidate.B:
    candidate.receive_loan(candidate.L)
    if candidate.repay_loan(candidate.L, record):
        sponsor.process_graduation(sponsor.B, sponsor.R)
        candidate.process_graduation(candidate.B, candidate.R)
```

That is effectively the primitive that `Engine.run_epoch()` repeats at scale.

Related pages: [Bonded Endorsements](/docs/bonded-endorsements) and [Engine API](/docs/api-reference/engine).
