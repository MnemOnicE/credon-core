import pytest
from simulations.engine import Engine

def test_engine_init_zero_agents():
    with pytest.raises(ValueError, match="Simulation must have at least one agent."):
        Engine(num_honest=0, num_malicious=0)
