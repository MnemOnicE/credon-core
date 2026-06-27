import pytest
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

        # epoch_staked should NOT update if the vote direction didn't change
        assert proposal.votes == {"H_1": {"amount": 200.0, "epoch_staked": 2, "vote": True}}

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
