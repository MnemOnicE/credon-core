"""
[EXPLANATORY: Benchmark script to measure the execution time of the `calculate_transitive_trust` function.]
[IDENTIFIER: benchmark_trust_module]
"""

import timeit
from engine import Engine


def setup_engine():
    """
    [EXPLANATORY: Sets up the Engine for benchmarking, running it for 20 epochs to generate interaction data.]
    [IDENTIFIER: setup_engine]
    [DIRECTIONAL: val]
    """
    NUM_HONEST_AGENTS = 50
    NUM_MALICIOUS_AGENTS = 10
    NUM_EPOCHS = 20
    engine = Engine(num_honest=NUM_HONEST_AGENTS, num_malicious=NUM_MALICIOUS_AGENTS)
    for _ in range(NUM_EPOCHS):
        engine.run_epoch()
    return engine


def run_benchmark():
    """
    [EXPLANATORY: Executes the timeit benchmark and prints the results.]
    [IDENTIFIER: run_benchmark]
    """
    engine = setup_engine()

    # We want to measure only the calculate_transitive_trust execution time.
    def benchmark_func():
        """
        [EXPLANATORY: Wrapper function for the code we are benchmarking.]
        [IDENTIFIER: benchmark_func]
        """
        engine.calculate_transitive_trust()

    print("Running benchmark on calculate_transitive_trust...")
    # Run 1000 times for a good measurement
    number_of_executions = 1000
    execution_time = timeit.timeit(benchmark_func, number=number_of_executions)

    avg_time = (execution_time / number_of_executions) * 1000  # Convert to ms

    print(f"Total time for {number_of_executions} executions: {execution_time:.4f} seconds")
    print(f"Average time per execution: {avg_time:.4f} ms")


if __name__ == "__main__":
    run_benchmark()
