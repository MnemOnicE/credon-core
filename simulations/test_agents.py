"""
[EXPLANATORY: Tests for Agent class]
[IDENTIFIER: TestAgent]
"""
from simulations.agents import Agent

class TestAgent:
    """
    [EXPLANATORY: TestAgent]
    [IDENTIFIER: TestAgent]
    """

    def test_try_sponsor_insufficient_balance(self):
        """
        [EXPLANATORY: test_try_sponsor_insufficient_balance]
        [IDENTIFIER: test_try_sponsor_insufficient_balance]
        [DIRECTIONAL: val]
        """
        agent = Agent(agent_id="H_0", b=500)
        agent.balance = 100  # Less than B=500
        result = agent.try_sponsor(candidate_id="H_1", current_epoch=1)
        assert result is None

    def test_try_sponsor_sufficient_balance(self):
        """
        [EXPLANATORY: test_try_sponsor_sufficient_balance]
        [IDENTIFIER: test_try_sponsor_sufficient_balance]
        [DIRECTIONAL: val]
        """
        initial_balance = 1000
        bond_amount = 500
        agent = Agent(agent_id="H_0", b=bond_amount)
        agent.balance = initial_balance

        result = agent.try_sponsor(candidate_id="H_1", current_epoch=5)

        expected_result = {
            "candidate_id": "H_1",
            "sponsor_id": "H_0",
            "epoch_started": 5,
            "B_s": bond_amount,
            "status": "pending",
        }
        assert result == expected_result
        assert agent.balance == initial_balance - bond_amount
