from simulations.engine import Proposal
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


class TestProposal:
    @pytest.fixture
    def proposal(self):
        return Proposal(prop_id=1, proposer_id="H_0", target_rho=0.1, creation_epoch=1, is_core=True)


    def test_cast_vote_new(self, proposal):
        # Test voting for the first time
        proposal.cast_vote(agent_id="H_1", amount=100.0, vote=True, current_epoch=2)

        assert "H_1" in proposal.votes
        assert proposal.votes["H_1"]["amount"] == 100.0
        assert proposal.votes["H_1"]["epoch_staked"] == 2
        assert proposal.votes["H_1"]["vote"] is True

    def test_cast_vote_change_direction(self, proposal):
        # Test voting initially
        proposal.cast_vote(agent_id="H_1", amount=100.0, vote=True, current_epoch=2)

        # Test changing the vote direction later
        proposal.cast_vote(agent_id="H_1", amount=150.0, vote=False, current_epoch=4)

        assert "H_1" in proposal.votes
        assert proposal.votes["H_1"]["amount"] == 150.0
        assert proposal.votes["H_1"]["epoch_staked"] == 4
        assert proposal.votes["H_1"]["vote"] is False

    def test_cast_vote_change_amount_only(self, proposal):
        # Test voting initially
        proposal.cast_vote(agent_id="H_1", amount=100.0, vote=True, current_epoch=2)

        # Test changing the amount but keeping the same vote
        proposal.cast_vote(agent_id="H_1", amount=200.0, vote=True, current_epoch=5)

        assert "H_1" in proposal.votes
        assert proposal.votes["H_1"]["amount"] == 200.0
        # epoch_staked should NOT update if the vote direction didn't change
        assert proposal.votes["H_1"]["epoch_staked"] == 2
        assert proposal.votes["H_1"]["vote"] is True

    def test_cast_vote_multiple_agents(self, proposal):
        proposal.cast_vote(agent_id="H_1", amount=100.0, vote=True, current_epoch=2)
        proposal.cast_vote(agent_id="M_1", amount=50.0, vote=False, current_epoch=3)

        assert len(proposal.votes) == 2
        assert proposal.votes["H_1"]["vote"] is True
        assert proposal.votes["M_1"]["vote"] is False
