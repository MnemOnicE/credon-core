import pytest
import math
from simulations.engine import Engine
from simulations.engine import Proposal


@pytest.mark.parametrize(
    ("num_honest", "num_malicious"),
    [
        (0, 0),  # Total is zero
        (-1, 1),  # Total is zero
        (0, -1),  # Total is negative
        (-5, 2),  # Total is negative
    ],
)
def test_engine_init_invalid_agent_count(num_honest, num_malicious):
    """
    [EXPLANATORY: test_engine_init_invalid_agent_count]
    [IDENTIFIER: test_engine_init_invalid_agent_count]
    """
    with pytest.raises(ValueError, match="Simulation must have at least one agent."):
        Engine(num_honest=num_honest, num_malicious=num_malicious)


class TestProposal:
    """
    [EXPLANATORY: TestProposal]
    [IDENTIFIER: TestProposal]
    """

    @pytest.fixture
    def proposal(self):
        """
        [EXPLANATORY: proposal]
        [IDENTIFIER: proposal]
        [DIRECTIONAL: val]
        """
        return Proposal(prop_id=1, proposer_id="H_0", target_rho=0.1, creation_epoch=1, is_core=True)

    def test_cast_vote_new(self, proposal):
        """
        [EXPLANATORY: test_cast_vote_new]
        [IDENTIFIER: test_cast_vote_new]
        """
        # Test voting for the first time
        proposal.cast_vote(agent_id="H_1", amount=100.0, vote=True, current_epoch=2)

        assert proposal.votes == {"H_1": {"amount": 100.0, "epoch_staked": 2, "vote": True}}

    def test_cast_vote_change_direction(self, proposal):
        """
        [EXPLANATORY: test_cast_vote_change_direction]
        [IDENTIFIER: test_cast_vote_change_direction]
        """
        # Test voting initially
        proposal.cast_vote(agent_id="H_1", amount=100.0, vote=True, current_epoch=2)

        # Test changing the vote direction later
        proposal.cast_vote(agent_id="H_1", amount=150.0, vote=False, current_epoch=4)

        assert proposal.votes == {"H_1": {"amount": 150.0, "epoch_staked": 4, "vote": False}}

    def test_cast_vote_change_amount_only(self, proposal):
        """
        [EXPLANATORY: test_cast_vote_change_amount_only]
        [IDENTIFIER: test_cast_vote_change_amount_only]
        """
        # Test voting initially
        proposal.cast_vote(agent_id="H_1", amount=100.0, vote=True, current_epoch=2)

        # Test changing the amount but keeping the same vote
        proposal.cast_vote(agent_id="H_1", amount=200.0, vote=True, current_epoch=5)

        # epoch_staked should now track the latest change due to fixed conviction accumulation math
        assert proposal.votes == {"H_1": {"amount": 200.0, "epoch_staked": 5, "vote": True}}

    def test_cast_vote_multiple_agents(self, proposal):
        """
        [EXPLANATORY: test_cast_vote_multiple_agents]
        [IDENTIFIER: test_cast_vote_multiple_agents]
        """
        proposal.cast_vote(agent_id="H_1", amount=100.0, vote=True, current_epoch=2)
        proposal.cast_vote(agent_id="M_1", amount=50.0, vote=False, current_epoch=3)

        assert proposal.votes == {
            "H_1": {"amount": 100.0, "epoch_staked": 2, "vote": True},
            "M_1": {"amount": 50.0, "epoch_staked": 3, "vote": False},
        }


class TestTransitiveTrust:
    """
    [EXPLANATORY: TestTransitiveTrust]
    [IDENTIFIER: TestTransitiveTrust]
    """

    @pytest.fixture
    def engine(self):
        """
        [EXPLANATORY: engine]
        [IDENTIFIER: engine]
        [DIRECTIONAL: val]
        """
        # Create a small engine with 3 honest and 1 malicious agent
        return Engine(num_honest=3, num_malicious=1)

    def test_trust_no_interactions(self, engine):
        """
        [EXPLANATORY: test_trust_no_interactions]
        [IDENTIFIER: test_trust_no_interactions]
        """
        for agent in engine.agents.values():
            agent.interactions = {}

        trust = engine.calculate_transitive_trust()

        # With no interactions, total_E becomes 0, so everyone gets 0.0 trust
        for agent_id in engine.agents:
            assert math.isclose(trust[agent_id], 0.0, abs_tol=1e-9)

    def test_trust_simple_chain(self, engine):
        """
        [EXPLANATORY: test_trust_simple_chain]
        [IDENTIFIER: test_trust_simple_chain]
        """
        # H_0 -> H_1 -> H_2
        for agent in engine.agents.values():
            agent.interactions = {}

        engine.agents["H_0"].interact_with("H_1", value=10)
        engine.agents["H_1"].interact_with("H_2", value=10)

        trust = engine.calculate_transitive_trust()

        # In a strict DAG (chain), trust leaks out of the system after enough iterations.
        # Since iterations=5, chain length is 2, trust goes to 0 for all.
        assert math.isclose(trust["H_2"], 0.0, abs_tol=1e-9)
        assert math.isclose(trust["H_1"], 0.0, abs_tol=1e-9)
        assert math.isclose(trust["H_0"], 0.0, abs_tol=1e-9)

    def test_trust_mutual(self, engine):
        """
        [EXPLANATORY: test_trust_mutual]
        [IDENTIFIER: test_trust_mutual]
        """
        for agent in engine.agents.values():
            agent.interactions = {}

        # H_0 <-> H_1
        engine.agents["H_0"].interact_with("H_1", value=10)
        engine.agents["H_1"].interact_with("H_0", value=10)

        trust = engine.calculate_transitive_trust()

        # H_0 and H_1 trap trust between them. Trust normalizes to (num_agents / components)
        # So it's 2.0 for H_0 and 2.0 for H_1, disconnected get 0.
        assert math.isclose(trust["H_0"], 2.0, rel_tol=1e-9)
        assert math.isclose(trust["H_1"], 2.0, rel_tol=1e-9)
        assert math.isclose(trust["H_2"], 0.0, abs_tol=1e-9)
        assert math.isclose(trust["M_0"], 0.0, abs_tol=1e-9)

    def test_trust_complex(self, engine):
        """
        [EXPLANATORY: test_trust_complex]
        [IDENTIFIER: test_trust_complex]
        """
        for agent in engine.agents.values():
            agent.interactions = {}

        # Everyone trusts H_0 highly
        engine.agents["H_1"].interact_with("H_0", value=50)
        engine.agents["H_2"].interact_with("H_0", value=50)
        engine.agents["M_0"].interact_with("H_0", value=50)

        # H_0 spreads a little trust
        engine.agents["H_0"].interact_with("H_1", value=10)
        engine.agents["H_0"].interact_with("H_2", value=5)

        trust = engine.calculate_transitive_trust()

        # H_0 should be overwhelmingly trusted (converges around 3.0)
        assert trust["H_0"] > trust["H_1"]
        assert trust["H_0"] > trust["H_2"]
        assert trust["H_0"] > trust["M_0"]

        # H_1 receives more outgoing trust from H_0 (value=10) than H_2 (value=5)
        assert trust["H_1"] > trust["H_2"]

        # M_0 has no incoming trust, so it goes to 0
        assert math.isclose(trust["M_0"], 0.0, abs_tol=1e-9)
