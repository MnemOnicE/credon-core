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
    engine = Engine(num_honest=50, num_malicious=10)
    for _ in range(20):
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
    NUMBER_OF_EXECUTIONS = 1000
    execution_time = timeit.timeit(benchmark_func, number=NUMBER_OF_EXECUTIONS)

    avg_time = (execution_time / NUMBER_OF_EXECUTIONS) * 1000  # Convert to ms

    print(f"Total time for {NUMBER_OF_EXECUTIONS} executions: {execution_time:.4f} seconds")
    print(f"Average time per execution: {avg_time:.4f} ms")


if __name__ == "__main__":
    run_benchmark()
