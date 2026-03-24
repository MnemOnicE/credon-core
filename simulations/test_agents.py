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
