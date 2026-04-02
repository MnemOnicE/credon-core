"""
[EXPLANATORY: Benchmark script to measure the execution time of honest and malicious voting loops.]
[IDENTIFIER: benchmark_voting_module]
"""

import timeit
import random
from simulations.engine import Engine, Proposal

def setup_benchmark(num_honest=500, num_malicious=100, num_proposals=50):
    """
    [EXPLANATORY: Sets up the Engine for benchmarking, giving agents cred and creating proposals.]
    [IDENTIFIER: setup_benchmark]
    [DIRECTIONAL: val]
    """
    engine = Engine(num_honest=num_honest, num_malicious=num_malicious)
    # Give some cred to agents so they can vote
    for agent in engine.agents.values():
        agent.cred_balance = 100

    # Create many proposals
    for i in range(num_proposals):
        target_rho = random.uniform(0.01, 0.50)
        p = Proposal(engine.next_proposal_id, "H_0", target_rho, engine.epoch, is_core=True)
        engine.proposals.append(p)
        engine.next_proposal_id += 1

    return engine

def benchmark_honest_voting(engine):
    """
    [EXPLANATORY: Executes the honest voting logic block for benchmarking.]
    [IDENTIFIER: benchmark_honest_voting]
    """
    honest_ids = engine.honest_ids
    active_proposals = [p for p in engine.proposals if p.status == "active"]
    rho = engine.rho
    epoch = engine.epoch

    # Categorize proposals once for efficiency
    reasonable_proposals = []
    extreme_proposals = []
    for p in active_proposals:
        if p.target_rho <= rho + 0.01 and p.target_rho >= rho - 0.01:
            reasonable_proposals.append(p)
        else:
            extreme_proposals.append(p)

    # Honest agents vote
    for a_id in honest_ids:
        agent = engine.agents[a_id]
        if agent.cred_balance > 0:
            for p in reasonable_proposals:
                # Vote yes on reasonable proposals
                p.cast_vote(a_id, agent.cred_balance, True, epoch)
            for p in extreme_proposals:
                # Vote no on extreme proposals
                p.cast_vote(a_id, agent.cred_balance, False, epoch)

def benchmark_malicious_voting(engine):
    """
    [EXPLANATORY: Executes the malicious voting logic block for benchmarking.]
    [IDENTIFIER: benchmark_malicious_voting]
    """
    malicious_ids = engine.malicious_ids
    active_proposals = [p for p in engine.proposals if p.status == "active"]
    epoch = engine.epoch
    malicious_target_rho = 0.50

    # Categorize proposals for malicious agents
    target_malicious = []
    other_malicious = []
    for p in active_proposals:
        if math.isclose(p.target_rho, malicious_target_rho, abs_tol=1e-9):
            target_malicious.append(p)
        else:
            other_malicious.append(p)

    # Malicious agents vote
    for m_id in malicious_ids:
        agent = engine.agents[m_id]
        if agent.cred_balance > 0:
            for p in target_malicious:
                p.cast_vote(m_id, agent.cred_balance, True, epoch)
            for p in other_malicious:
                p.cast_vote(m_id, agent.cred_balance, False, epoch)

def run_benchmark():
    """
    [EXPLANATORY: Executes the timeit benchmark and prints the results.]
    [IDENTIFIER: run_benchmark]
    """
    engine = setup_benchmark()

    NUMBER_OF_EXECUTIONS = 10

    print("Running benchmark on honest voting loop (OPTIMIZED)...")
    h_time = timeit.timeit(lambda: benchmark_honest_voting(engine), number=NUMBER_OF_EXECUTIONS)
    h_avg = (h_time / NUMBER_OF_EXECUTIONS) * 1000
    print(f"Average time per honest voting execution: {h_avg:.4f} ms")

    print("Running benchmark on malicious voting loop (OPTIMIZED)...")
    m_time = timeit.timeit(lambda: benchmark_malicious_voting(engine), number=NUMBER_OF_EXECUTIONS)
    m_avg = (m_time / NUMBER_OF_EXECUTIONS) * 1000
    print(f"Average time per malicious voting execution: {m_avg:.4f} ms")

    print(f"Total average voting time: {h_avg + m_avg:.4f} ms")

if __name__ == "__main__":
    run_benchmark()
