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

    def test_update_conviction_no_votes(self, proposal):
        """
        [EXPLANATORY: test_update_conviction_no_votes]
        [IDENTIFIER: test_update_conviction_no_votes]
        """
        v_yes, v_no, total = proposal.update_conviction(alpha=0.9, t_max=10, current_epoch=2)
        assert v_yes == 0.0
        assert v_no == 0.0
        assert total == 0.0
        assert proposal.y_t_yes == 0.0
        assert proposal.y_t_no == 0.0

    def test_update_conviction_only_yes(self, proposal):
        """
        [EXPLANATORY: test_update_conviction_only_yes]
        [IDENTIFIER: test_update_conviction_only_yes]
        """
        proposal.cast_vote(agent_id="H_1", amount=100.0, vote=True, current_epoch=2)
        v_yes, v_no, total = proposal.update_conviction(alpha=0.9, t_max=10, current_epoch=2)
        assert v_yes == 100.0
        assert v_no == 0.0
        assert total == 100.0
        assert proposal.y_t_yes == 100.0
        assert proposal.y_t_no == 0.0

    def test_update_conviction_only_no(self, proposal):
        """
        [EXPLANATORY: test_update_conviction_only_no]
        [IDENTIFIER: test_update_conviction_only_no]
        """
        proposal.cast_vote(agent_id="H_1", amount=100.0, vote=False, current_epoch=2)
        v_yes, v_no, total = proposal.update_conviction(alpha=0.9, t_max=10, current_epoch=2)
        assert v_yes == 0.0
        assert v_no == 100.0
        assert total == 100.0
        assert proposal.y_t_yes == 0.0
        assert proposal.y_t_no == 100.0

    def test_update_conviction_mixed_votes(self, proposal):
        """
        [EXPLANATORY: test_update_conviction_mixed_votes]
        [IDENTIFIER: test_update_conviction_mixed_votes]
        """
        proposal.cast_vote(agent_id="H_1", amount=100.0, vote=True, current_epoch=2)
        proposal.cast_vote(agent_id="M_1", amount=50.0, vote=False, current_epoch=2)
        v_yes, v_no, total = proposal.update_conviction(alpha=0.9, t_max=10, current_epoch=2)
        assert v_yes == 100.0
        assert v_no == 50.0
        assert total == 150.0
        assert proposal.y_t_yes == 100.0
        assert proposal.y_t_no == 50.0

    def test_update_conviction_decay(self, proposal):
        """
        [EXPLANATORY: test_update_conviction_decay]
        [IDENTIFIER: test_update_conviction_decay]
        """
        proposal.cast_vote(agent_id="H_1", amount=100.0, vote=True, current_epoch=2)
        proposal.cast_vote(agent_id="M_1", amount=50.0, vote=False, current_epoch=2)

        # Epoch 1: Add votes
        proposal.update_conviction(alpha=0.9, t_max=10, current_epoch=2)
        assert proposal.y_t_yes == 100.0
        assert proposal.y_t_no == 50.0

        # Epoch 2: Same votes should increase conviction due to accumulation
        # alpha = 0.9. Next y_t_yes = (0.9 * 100) + 100 = 190.0
        # Next y_t_no = (0.9 * 50) + 50 = 95.0
        proposal.update_conviction(alpha=0.9, t_max=10, current_epoch=3)
        assert proposal.y_t_yes == 190.0
        assert proposal.y_t_no == 95.0

        # Change vote to see it reflect
        proposal.cast_vote(agent_id="H_1", amount=0.0, vote=True, current_epoch=4)  # H_1 removes stake

        # Epoch 3: Conviction decays
        # Next y_t_yes = (0.9 * 190) + 0 = 171.0
        # Next y_t_no = (0.9 * 95) + 50 = 135.5
        proposal.update_conviction(alpha=0.9, t_max=10, current_epoch=4)
        assert proposal.y_t_yes == 171.0
        assert proposal.y_t_no == 135.5
