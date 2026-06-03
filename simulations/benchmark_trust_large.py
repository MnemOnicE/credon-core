"""
[EXPLANATORY: Benchmark script to measure the execution time of the `calculate_transitive_trust` function at scale.]
[IDENTIFIER: benchmark_trust_large_module]
"""

import timeit
from engine import Engine


def setup_engine():
    """
    [EXPLANATORY: Sets up a larger Engine for benchmarking, running it for 20 epochs.]
    [IDENTIFIER: setup_engine_large]
    [DIRECTIONAL: val]
    """
    NUM_HONEST_AGENTS = 800
    NUM_MALICIOUS_AGENTS = 200
    NUM_EPOCHS = 20
    engine = Engine(num_honest=NUM_HONEST_AGENTS, num_malicious=NUM_MALICIOUS_AGENTS)
    for _ in range(NUM_EPOCHS):
        engine.run_epoch()
    return engine


def run_benchmark():
    """
    [EXPLANATORY: Executes the timeit benchmark and prints the results.]
    [IDENTIFIER: run_benchmark_large]
    """
    engine = setup_engine()

    def benchmark_func():
        """
        [EXPLANATORY: Wrapper function for the code we are benchmarking.]
        [IDENTIFIER: benchmark_func_large]
        """
        engine.calculate_transitive_trust()

    print("Running benchmark on calculate_transitive_trust (Large Scale)...")
    NUMBER_OF_EXECUTIONS = 100
    execution_time = timeit.timeit(benchmark_func, number=NUMBER_OF_EXECUTIONS)

    avg_time = (execution_time / NUMBER_OF_EXECUTIONS) * 1000  # Convert to ms

    print(f"Total time for {NUMBER_OF_EXECUTIONS} executions: {execution_time:.4f} seconds")
    print(f"Average time per execution: {avg_time:.4f} ms")


if __name__ == "__main__":
    run_benchmark()
