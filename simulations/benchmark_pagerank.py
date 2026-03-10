import timeit
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from engine import Engine


def setup_benchmark_engine():
    """
    [EXPLANATORY: setup_benchmark_engine initializes an Engine instance with a large number of inactive agents to test sink performance.]
    [IDENTIFIER: setup_benchmark_engine]
    [DIRECTIONAL: val]
    """
    # Create a large network (e.g. 1000 agents).
    # Since we don't run run_epoch(), NONE of them have interactions.
    # Therefore, ALL 1000 agents are sinks (out_degree == 0).
    engine = Engine(num_honest=1000, num_malicious=0)
    return engine


def run_benchmark():
    """
    [EXPLANATORY: run_benchmark executes the timeit module to measure the execution time of the calculate_social_connectivity method.]
    [IDENTIFIER: run_benchmark]
    [DIRECTIONAL: none]
    """
    print("Initializing benchmark engine...")
    engine = setup_benchmark_engine()
    print(f"Engine initialized with {len(engine.agents)} agents. All agents are sinks.")

    iterations = 50

    print(f"Running calculate_social_connectivity {iterations} times...")

    def wrapper():
        """
        [EXPLANATORY: wrapper encapsulates the calculate_social_connectivity method call for timing.]
        [IDENTIFIER: benchmark_wrapper]
        [DIRECTIONAL: val]
        """
        engine.calculate_social_connectivity()

    execution_time = timeit.timeit(wrapper, number=iterations)

    avg_time = execution_time / iterations

    print("-" * 40)
    print(f"Total time for {iterations} iterations: {execution_time:.4f} seconds")
    print(f"Average time per iteration: {avg_time:.6f} seconds")
    print("-" * 40)


if __name__ == "__main__":
    run_benchmark()
