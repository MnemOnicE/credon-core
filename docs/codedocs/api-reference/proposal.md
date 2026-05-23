---
title: "Proposal API"
description: "Reference for the Proposal class used by Credon Core governance and conviction vote accounting."
---

`Proposal` is defined in `simulations/engine.py` and stores all governance-side vote state. The engine uses it for core `rho` changes and includes a secondary branch for non-core proposals with simpler quorum rules.

Import path:

```python
from simulations.engine import Proposal
```

<Callout type="warn">The current source file contains duplicated declarations around `create_batch_updates` and `cast_votes_batch`. The signatures below document the last effective definitions in the file, because those are the ones a cleaned-up version of the module would expose.</Callout>

## Constructor

Source file: `simulations/engine.py`

Source signature:

```python
def __init__(self, prop_id, proposer_id, target_rho, creation_epoch, is_core=True):
    ...
```

Effective typed signature:

```python
def __init__(
    self,
    prop_id: int,
    proposer_id: str,
    target_rho: float,
    creation_epoch: int,
    is_core: bool = True,
) -> None:
    ...
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `prop_id` | `int` | — | Proposal identifier assigned by the engine. |
| `proposer_id` | `str` | — | Agent ID that opened the proposal. |
| `target_rho` | `float` | — | Proposed reward release rate. |
| `creation_epoch` | `int` | — | Epoch when the proposal was created. |
| `is_core` | `bool` | `True` | Whether conviction voting should be used. |

Important attributes:

- `votes`: mapping of agent IDs to amount, stake epoch, and vote direction.
- `status`: starts as `active`, then moves to `executed` or `rejected`.
- `y_t_yes` and `y_t_no`: accumulated conviction values.

Example:

```python
from simulations.engine import Proposal

proposal = Proposal(1, "H_0", 0.06, 1, is_core=True)
print(proposal.status)
```

## Methods

### `cast_vote`

Source signature:

```python
def cast_vote(self, agent_id, amount, vote, current_epoch):
    ...
```

Effective typed signature:

```python
def cast_vote(self, agent_id: str, amount: int | float, vote: bool, current_epoch: int) -> None:
    ...
```

Stores or replaces one agent's voting record.

Example:

```python
proposal = Proposal(1, "H_0", 0.06, 1)
proposal.cast_vote("H_1", amount=10, vote=True, current_epoch=2)
print(proposal.votes["H_1"])
```

### `create_batch_updates`

Source signature:

```python
def create_batch_updates(active_agents, vote, current_epoch):
    ...
```

Effective typed signature:

```python
@staticmethod
def create_batch_updates(
    active_agents: list[tuple[str, int | float]],
    vote: bool,
    current_epoch: int,
) -> dict[str, dict[str, object]]:
    ...
```

Builds a vote-update dictionary that can be passed to `cast_votes_batch`.

Example:

```python
updates = Proposal.create_batch_updates(
    [("H_1", 10), ("H_2", 5)],
    vote=True,
    current_epoch=3,
)
print(updates["H_1"]["vote"])
```

### `cast_votes_batch`

Source signature:

```python
def cast_votes_batch(self, updates):
    ...
```

Effective typed signature:

```python
def cast_votes_batch(self, updates: dict[str, dict[str, object]]) -> None:
    ...
```

Merges precomputed updates into the proposal vote map.

Example:

```python
proposal = Proposal(1, "H_0", 0.06, 1)
updates = Proposal.create_batch_updates([("H_1", 10)], True, 2)
proposal.cast_votes_batch(updates)
print(proposal.votes)
```

### `update_conviction`

Source signature:

```python
def update_conviction(self, alpha, t_max, current_epoch):
    ...
```

Effective typed signature:

```python
def update_conviction(
    self,
    alpha: float,
    t_max: int,
    current_epoch: int,
) -> tuple[float, float, float]:
    ...
```

Recomputes the current epoch's yes and no stake totals, updates `y_t_yes` and `y_t_no`, and returns `(v_t_yes, v_t_no, total_staked_in_vote)`.

Example:

```python
proposal = Proposal(1, "H_0", 0.06, 1)
proposal.cast_vote("H_1", 10, True, 1)
proposal.cast_vote("H_2", 4, False, 1)

v_yes, v_no, total = proposal.update_conviction(alpha=0.8, t_max=5, current_epoch=1)
print(v_yes, v_no, total)
print(proposal.y_t_yes, proposal.y_t_no)
```

## Common patterns

The engine's core path is:

```python
proposal = Proposal(engine.next_proposal_id, proposer.id, target_rho, engine.epoch, is_core=True)
proposal.cast_vote(a_id, balance, True, engine.epoch)
proposal.update_conviction(engine.alpha_conviction, engine.t_max, engine.epoch)
```

That combination is what eventually drives `engine.rho` updates.

Related pages: [Governance and Monetary Policy](/docs/governance-and-monetary-policy) and [Engine API](/docs/api-reference/engine).
