import pytest
from simulations.agents import Agent

class TestAgent:
    """
    [EXPLANATORY: TestAgent]
    [IDENTIFIER: TestAgent]
    """

    @pytest.fixture
    def agent(self):
        """
        [EXPLANATORY: agent]
        [IDENTIFIER: agent]
        [DIRECTIONAL: val]
        """
        return Agent(agent_id="H_0", is_malicious=False)

    def test_repay_loan_success(self, agent):
        """
        [EXPLANATORY: test_repay_loan_success]
        [IDENTIFIER: test_repay_loan_success]
        """
        initial_balance = agent.balance
        loan_amount = 400
        loan_record = {"status": "active"}

        result = agent.repay_loan(loan_amount, loan_record)

        assert result is True
        assert agent.balance == initial_balance - loan_amount
        assert loan_record["status"] == "repaid"

    def test_repay_loan_insufficient_balance(self, agent):
        """
        [EXPLANATORY: test_repay_loan_insufficient_balance]
        [IDENTIFIER: test_repay_loan_insufficient_balance]
        """
        agent.balance = 100
        initial_balance = agent.balance
        loan_amount = 400
        loan_record = {"status": "active"}

        result = agent.repay_loan(loan_amount, loan_record)

        assert result is False
        assert agent.balance == initial_balance
        assert loan_record["status"] == "active"

    def test_try_sponsor_insufficient_balance(self, agent):
        """
        [EXPLANATORY: test_try_sponsor_insufficient_balance]
        [IDENTIFIER: test_try_sponsor_insufficient_balance]
        """
        agent.balance = 100  # Less than default B=500
        initial_balance = agent.balance
        result = agent.try_sponsor(candidate_id="H_1", current_epoch=1)
        assert result is None
        assert agent.balance == initial_balance

    def test_try_sponsor_sufficient_balance(self, agent):
        """
        [EXPLANATORY: test_try_sponsor_sufficient_balance]
        [IDENTIFIER: test_try_sponsor_sufficient_balance]
        """
        initial_balance = agent.balance
        bond_amount = agent.B

        result = agent.try_sponsor(candidate_id="H_1", current_epoch=5)

        expected_result = {
            "candidate_id": "H_1",
            "sponsor_id": agent.id,
            "epoch_started": 5,
            "B_s": bond_amount,
            "status": "pending",
        }
        assert result == expected_result
        assert agent.balance == initial_balance - bond_amount
