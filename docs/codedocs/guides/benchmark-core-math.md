---
title: "Benchmark Core Math"
description: "Measure the slow paths in Credon Core: transitive trust, social connectivity, and governance voting loops."
---

This guide is for contributors who want to understand which parts of Credon Core are expensive enough to deserve optimization work.

## Problem

`Engine.run_epoch()` already packs a lot of behavior into one method. If you want to scale the simulation to larger populations or more proposals, you need to know which pieces are likely to dominate runtime.

## Solution

Use the three benchmark scripts in `simulations/`:

- `benchmark_trust.py` for `calculate_transitive_trust()`
- `benchmark_pagerank.py` for `calculate_social_connectivity()`
- `benchmark_voting.py` for the honest and malicious voting loops

<Steps>
<Step>
### Run the transitive trust benchmark

```bash
cd simulations
python benchmark_trust.py
```

This warms an engine for twenty epochs and then runs `calculate_transitive_trust()` one thousand times.

</Step>
<Step>
### Run the social connectivity benchmark

```bash
cd simulations
python benchmark_pagerank.py
```

This creates a sink-heavy graph with one thousand honest agents and repeatedly calls `calculate_social_connectivity()`.

</Step>
<Step>
### Run the voting benchmark

```bash
python simulations/benchmark_voting.py
```

This preloads agents with `cred_balance`, creates many proposals, and times the optimized honest and malicious voting loops.

</Step>
</Steps>

## Complete runnable pattern

Use this if you want one compact benchmark sweep in a shell session:

```bash
cd simulations
python benchmark_trust.py
python benchmark_pagerank.py
cd ..
python simulations/benchmark_voting.py
```

## What each script tells you

`benchmark_trust.py` is mostly about graph propagation cost. If you make the trust model richer, this is the first benchmark that will move.

`benchmark_pagerank.py` is about sink handling. The script deliberately creates an all-sink graph because naive redistribution logic can become a bottleneck in sparse networks.

`benchmark_voting.py` reflects an explicit optimization direction mentioned in `simulations/CHANGELOG.md`: proposals are pre-categorized and agents with zero `cred_balance` are filtered out before the nested loops run.

## Applying benchmark results

If trust is slow:

- Reduce repeated object lookups inside `calculate_transitive_trust()`.
- Consider exposing the iteration count as a parameter and lowering it for exploratory runs.

If PageRank is slow:

- Revisit sink handling and normalized interaction caching.
- Profile whether your workload is sink-heavy or dense; the same optimization does not help both equally.

If voting is slow:

- Keep proposal categorization outside inner loops.
- Avoid iterating over agents with zero stake.

<Callout type="warn">These scripts measure isolated hot spots, not end-to-end simulation throughput. A faster trust function can still leave `run_epoch()` dominated by printing, proposal growth, or chart-generation overhead depending on how you run the system.</Callout>

For the broader system flow, go back to [Architecture](/docs/architecture). For the exact trust and voting methods involved, use the [Engine API](/docs/api-reference/engine) and [Proposal API](/docs/api-reference/proposal).
