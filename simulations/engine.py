import math
from agents import Agent

class Engine:
    def __init__(self, num_honest=20, num_malicious=5):
        if num_honest + num_malicious <= 0:
            raise ValueError("Simulation must have at least one agent.")
        # ---------------- Game Theory Parameters ----------------
        self.B = 500  # Bond size (B_c and B_s)
        self.L = 400  # Loan principal (must be < 2B)
        self.R = 75   # Integrity reward

        # ---------------- Monetary Policy Parameters ----------------
        self.R_res = 0.0          # Rewards Reservoir
        self.circulating_supply = 0.0
        self.rho = 0.05           # Reward Release Rate (5%)

        # ---------------- TrustLedger Math Weights ----------------
        self.alpha = 0.4  # Transitive Trust (E) weight
        self.beta = 0.4   # Social Connectivity (P) weight
        self.gamma = 0.2  # Time-Weighting (W) weight
        self.ema_decay = 0.1 # Decay for Time-Weighting (W) EMA

        # ---------------- Simulation State ----------------
        self.epoch = 0
        self.agents = {}

        # Initialize agents
        for i in range(num_honest):
            agent_id = f"H_{i}"
            self.agents[agent_id] = Agent(agent_id, is_malicious=False, b=self.B, l_amount=self.L, r=self.R)
            self.circulating_supply += self.agents[agent_id].balance

        for i in range(num_malicious):
            agent_id = f"M_{i}"
            # Malicious attacker orchestrates Sybils
            self.agents[agent_id] = Agent(agent_id, is_malicious=True, b=self.B, l=self.L, r=self.R)
            self.circulating_supply += self.agents[agent_id].balance

        # Track Time-Weighted Conviction W for all agents using EMA
        self.W = {agent_id: 0.0 for agent_id in self.agents}
        # Track past epoch verified activity for EMA calculation
        self.recent_activity = {agent_id: 0 for agent_id in self.agents}

        # Track initial balances to compute ROI later
        self.initial_balances = {a_id: self.agents[a_id].balance for a_id in self.agents}

        # Global Loan Registry
        self.active_loans = []

    # ---------------- TrustLedger Functions ----------------
    def calculate_transitive_trust(self):
        """Calculates EigenTrust-style E(u) for all agents."""
        E = {agent_id: 1.0 for agent_id in self.agents} # Initial flat trust
        iterations = 5 # Small number of power iterations to converge local graph

        for _ in range(iterations):
            new_E = {agent_id: 0.0 for agent_id in self.agents}
            for u in self.agents.values():
                total_interactions = sum(u.interactions.values())
                if total_interactions > 0:
                    for v_id, weight in u.interactions.items():
                        # u vouches for v_id
                        normalized_weight = weight / total_interactions
                        new_E[v_id] += E[u.id] * normalized_weight

            # Normalize to prevent explosion
            total_E = sum(new_E.values())
            if total_E > 0:
                E = {k: v / total_E * len(self.agents) for k, v in new_E.items()}
            else:
                E = new_E
        return E

    def calculate_social_connectivity(self):
        """Calculates PageRank-style P(u) for all agents."""
        P = {agent_id: 1.0 / len(self.agents) for agent_id in self.agents}
        d = 0.85 # Damping factor
        iterations = 10

        for _ in range(iterations):
            new_P = {agent_id: (1.0 - d) / len(self.agents) for agent_id in self.agents}
            for u in self.agents.values():
                out_degree = sum(u.interactions.values())
                if out_degree > 0:
                    for v_id, weight in u.interactions.items():
                        new_P[v_id] += d * (P[u.id] * (weight / out_degree))
                else:
                    # Handle sinks
                    for v_id in self.agents:
                        new_P[v_id] += d * (P[u.id] / len(self.agents))
            P = new_P

        # Scale to meaningful values roughly matching E
        return {k: v * len(self.agents) for k, v in P.items()}

    def update_time_weighting(self):
        """Calculates W(u, t) using discrete EMA of verified recent activity."""
        for agent_id in self.agents:
            activity = self.recent_activity[agent_id]
            # EMA = (Value_today * decay) + (EMA_yesterday * (1 - decay))
            self.W[agent_id] = (activity * self.ema_decay) + (self.W[agent_id] * (1 - self.ema_decay))
            self.recent_activity[agent_id] = 0 # Reset for next epoch
        return self.W

    def calculate_trust_scores(self):
        r"""T(u, t) = \alpha E(u) + \beta P(u) + \gamma W(u, t)"""
        E = self.calculate_transitive_trust()
        P = self.calculate_social_connectivity()
        W = self.update_time_weighting()

        T = {}
        for a in self.agents:
            T[a] = (self.alpha * E[a]) + (self.beta * P[a]) + (self.gamma * W[a])
        return T

    # ---------------- Simulation Step ----------------
    def run_epoch(self):
        self.epoch += 1
        epoch_repaid_principal = 0

        # 1. Honest Agents Act (Simulate a network graph of interactions)
        honest_ids = [a_id for a_id in self.agents if not self.agents[a_id].is_malicious]
        for a_id in honest_ids:
            sponsor = self.agents[a_id]
            # Interact with a few other honest nodes randomly to build the social graph
            import random
            friends = random.sample(honest_ids, min(3, len(honest_ids)))
            for friend in friends:
                if friend != a_id:
                    sponsor.interact_with(friend, 1)

            # Try to sponsor a candidate
            if sponsor.balance >= self.B:
                # Random honest candidate
                candidate_id = random.choice(honest_ids)
                candidate = self.agents[candidate_id]

                # Check candidate bond
                if candidate.post_candidate_bond() == self.B:
                    # Sponsor posts bond
                    loan_record = sponsor.try_sponsor(candidate_id, self.epoch)
                    if loan_record:
                        # Give loan L to candidate
                        candidate.receive_loan(self.L)
                        self.active_loans.append(loan_record)

                        # At graduation (for simplicity we resolve in same epoch here for volume tracking,
                        # or track it over time. Let's resolve immediately for this mathematical proof loop)

                        # Candidate repays loan L
                        if candidate.repay_loan(self.L, loan_record):
                            epoch_repaid_principal += self.L
                            # Verified activity goes up
                            self.recent_activity[sponsor.id] += 1
                            self.recent_activity[candidate.id] += 1

                            # Both get bonds back. Reward R is minted later, let's distribute it here
                            # Assuming 1 R to sponsor, 1 R to candidate
                            sponsor.process_graduation(self.B, self.R)
                            candidate.process_graduation(self.B, self.R)
                            # Decrease circulating supply temporarily since R is drawn from M later
                            # Or we can just let circulating supply float and track it
                            self.circulating_supply += (self.R * 2)

        # 2. Malicious Agents Act (Sybil Swarm)
        malicious_ids = [a_id for a_id in self.agents if self.agents[a_id].is_malicious]
        for m_id in malicious_ids:
            attacker = self.agents[m_id]
            # Sybil graph: attackers only interact with themselves (link farms)
            for other_m in malicious_ids:
                if other_m != m_id:
                    attacker.interact_with(other_m, 5) # High internal interaction

            # Attacker controls Sponsor and Candidate (which is another Sybil or themselves)
            if attacker.balance >= (self.B * 2): # Needs 2B
                fake_candidate_id = m_id # Themselves for simplicity

                # Post both bonds
                b_c = attacker.post_candidate_bond()
                loan_record = attacker.try_sponsor(fake_candidate_id, self.epoch)

                if loan_record and b_c == self.B:
                    attacker.receive_loan(self.L)
                    self.active_loans.append(loan_record)

                    # Sybil ATTACK: Default to steal L!
                    attacker.execute_default(loan_record)

                    # Because they defaulted, they keep L, but lose B_c and B_s
                    # Volume is NOT added to epoch_repaid_principal.
                    # Circulating supply decreases by the burned bonds
                    self.circulating_supply -= (self.B * 2)
                    self.circulating_supply += self.L # But they kept L
                    # Actually L was already in circulating supply (from the protocol's TVL theoretically).
                    # If loan L comes from TVL, the net change in circulating supply of users is:
                    # -2B (burned) + L (kept).
                    # Net: User loses 2B - L.

        # 3. Monetary Policy & Trust Math at Epoch Boundary
        T_scores = self.calculate_trust_scores()

        # Calculate Delta R_res (verified volume sub-linear throttle)
        delta_r = math.sqrt(epoch_repaid_principal)
        self.R_res += delta_r

        # Calculate Minted amount
        M_epoch = self.rho * self.R_res
        # Subtract minted amount from reservoir
        self.R_res -= M_epoch
        # Add to circulating supply (distributed across network conceptually)
        self.circulating_supply += M_epoch

        # 4. Expected Value / ROI Telemetry Math
        # EV_honest = (p_success * R) - ((1 - p_success) * B)
        # We assume p_success based on the TrustLedger is very high. Say p_success = 0.95
        p_success = 0.95
        ev_honest = (p_success * self.R) - ((1.0 - p_success) * self.B)

        # EV_attacker = L - 2B
        ev_attacker = self.L - (2 * self.B)

        # Calculate actual average ROI
        h_roi_total = sum((self.agents[a_id].balance - self.initial_balances[a_id]) for a_id in honest_ids)
        avg_h_roi = h_roi_total / len(honest_ids) if honest_ids else 0

        m_roi_total = sum((self.agents[a_id].balance - self.initial_balances[a_id]) for a_id in malicious_ids)
        avg_m_roi = m_roi_total / len(malicious_ids) if malicious_ids else 0

        print(f"\n=== EPOCH {self.epoch} SUMMARY ===")
        print(f"Epoch Verified Volume (Repaid L): {epoch_repaid_principal}")
        print(f"Rewards Reservoir R_res (Locked):  {self.R_res:.2f} CRE")
        print(f"Circulating Supply:              {self.circulating_supply:.2f} CRE")
        print(f"Game Theory EV(Honest):          {ev_honest:.2f} CRE per interaction")
        print(f"Game Theory EV(Attacker):        {ev_attacker:.2f} CRE per interaction (Attacker ROI)")
        print(f"Actual Avg Honest ROI so far:    {avg_h_roi:.2f} CRE")
        print(f"Actual Avg Attacker ROI so far:  {avg_m_roi:.2f} CRE")

        # Print Trust Scores to show Sybil isolation
        avg_h_trust = sum(T_scores[a] for a in honest_ids) / len(honest_ids) if honest_ids else 0
        avg_m_trust = sum(T_scores[a] for a in malicious_ids) / len(malicious_ids) if malicious_ids else 0
        print(f"Avg Trust Score (Honest):        {avg_h_trust:.4f}")
        print(f"Avg Trust Score (Malicious):     {avg_m_trust:.4f}")

if __name__ == "__main__":
    engine = Engine(num_honest=20, num_malicious=5)
    for _ in range(5):
        engine.run_epoch()
