"""
[EXPLANATORY: Script to verify that the optimized `calculate_transitive_trust` produces results identical to the original logic.]
[IDENTIFIER: verify_trust_parity_module]
"""

import math
import random
from engine import Engine


def original_transitive_trust_logic(engine):
    """
    [EXPLANATORY: Re-implementation of the original, unoptimized transitive trust logic.]
    [IDENTIFIER: original_transitive_trust_logic]
    [DIRECTIONAL: val]
    """
    E = {agent_id: 1.0 for agent_id in engine.agents}
    iterations = 5

    agent_normalized_weights = {}
    for u in engine.agents.values():
        total_interactions = sum(math.sqrt(w) for w in u.interactions.values())
        normalized_interactions = {}
        if total_interactions > 0:
            for v_id, weight in u.interactions.items():
                normalized_interactions[v_id] = math.sqrt(weight) / total_interactions
        agent_normalized_weights[u.id] = normalized_interactions

    for _ in range(iterations):
        new_E = {agent_id: 0.0 for agent_id in engine.agents}
        for u_id, normalized_interactions in agent_normalized_weights.items():
            if normalized_interactions:
                for v_id, normalized_weight in normalized_interactions.items():
                    new_E[v_id] += E[u_id] * normalized_weight

        total_E = sum(new_E.values())
        if total_E > 0:
            E = {k: v / total_E * len(engine.agents) for k, v in new_E.items()}
        else:
            E = new_E
    return E


def verify_parity():
    """
    [EXPLANATORY: Compares results from the original logic and the optimized engine method.]
    [IDENTIFIER: verify_parity]
    """
    print("Verifying parity between original and optimized transitive trust logic...")
    NUM_AGENTS = 100
    engine = Engine(num_honest=80, num_malicious=20)
    # Run some epochs to populate interactions
    for _ in range(10):
        engine.run_epoch()

    original_results = original_transitive_trust_logic(engine)
    optimized_results = engine.calculate_transitive_trust()

    assert set(original_results.keys()) == set(optimized_results.keys())

    max_diff = 0.0
    for agent_id in original_results:
        diff = abs(original_results[agent_id] - optimized_results[agent_id])
        max_diff = max(max_diff, diff)

    print(f"Maximum difference: {max_diff}")
    if max_diff < 1e-9:
        print("SUCCESS: Optimized results match original results within tolerance.")
    else:
        print("FAILURE: Optimized results do not match original results.")
        exit(1)


if __name__ == "__main__":
    verify_parity()
