import pytest
from simulations.engine import Engine

@pytest.mark.parametrize(
    ("num_honest", "num_malicious"),
    [
        (0, 0),    # Total is zero
        (-1, 1),   # Total is zero
        (0, -1),   # Total is negative
        (-5, 2),   # Total is negative
    ],
)
def test_engine_init_invalid_agent_count(num_honest, num_malicious):
    with pytest.raises(ValueError, match="Simulation must have at least one agent."):
        Engine(num_honest=num_honest, num_malicious=num_malicious)
