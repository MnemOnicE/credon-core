class Agent:
    def __init__(self, agent_id, is_malicious=False, b=500, l_amount=400, r=75):
        self.id = agent_id
        self.is_malicious = is_malicious
        self.B = b # Bond amount
        self.L = l_amount # Loan principal amount (typically under-collateralized vs 2B)
        self.R = r # Integrity reward
        self.balance = 50000 if is_malicious else 2500 # Starting capital
        self.cred_balance = 0 # Soulbound governance token
        self.staked_cred = 0 # Amount of $CRED currently locked in proposals
        self.active_loans = []

        # Local memory/state for custom adjacency list
        # Tracks who they interact with and interaction count/value
        # {interacted_agent_id: interaction_value}
        self.interactions = {}

    def interact_with(self, other_agent_id, value=1):
        """Records an interaction with another agent to build the social graph."""
        if other_agent_id not in self.interactions:
            self.interactions[other_agent_id] = 0
        self.interactions[other_agent_id] += value

    def try_sponsor(self, candidate_id, current_epoch):
        """Attempts to sponsor a candidate. Costs 1 Bond (B_s)."""
        if self.balance >= self.B:
            self.balance -= self.B
            return {
                "candidate_id": candidate_id,
                "sponsor_id": self.id,
                "epoch_started": current_epoch,
                "B_s": self.B,
                "status": "pending"
            }
        return None

    def post_candidate_bond(self):
        """Candidate posts their side of the bond (B_c) to receive the loan."""
        if self.balance >= self.B:
            self.balance -= self.B
            return self.B
        return 0

    def receive_loan(self, loan_amount):
        """Receives the loan principal L."""
        self.balance += loan_amount

    def process_graduation(self, bond_returned, reward):
        """Receives back their bond + the Integrity Reward R."""
        self.balance += bond_returned + reward
        self.cred_balance += 1 # Mint 1 $CRED for verified activity

    def execute_default(self, loan_record):
        """Malicious agent defaults, keeping the loan L but losing bonds."""
        loan_record["status"] = "defaulted"
        return loan_record

    def repay_loan(self, loan_amount, loan_record):
        """Honest agent repays the loan L."""
        if self.balance >= loan_amount:
            self.balance -= loan_amount
            loan_record["status"] = "repaid"
            return True
        return False
