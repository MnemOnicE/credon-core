import math
import random

from agents import Agent


class Proposal:
    def __init__(self, prop_id, proposer_id, target_rho, creation_epoch, is_core=True):
        self.id = prop_id
        self.proposer_id = proposer_id
        self.target_rho = target_rho
        self.creation_epoch = creation_epoch
        self.is_core = is_core

        # Dictionary of agent_id -> { "amount": staked_cred, "epoch_staked": epoch, "vote": True/False }
        self.votes = {}
        self.status = "active"

        # Conviction voting state for core proposals
        self.y_t_yes = 0.0
        self.y_t_no = 0.0

    def cast_vote(self, agent_id, amount, vote, current_epoch):
        if agent_id in self.votes:
            if self.votes[agent_id]["vote"] != vote:
                self.votes[agent_id]["epoch_staked"] = current_epoch
                self.votes[agent_id]["vote"] = vote

            self.votes[agent_id]["amount"] = amount
        else:
            self.votes[agent_id] = {
                "amount": amount,
                "epoch_staked": current_epoch,
                "vote": vote,
            }

    def update_conviction(self, alpha, t_max, current_epoch):
        v_t_yes = 0.0
        v_t_no = 0.0

        total_staked_in_vote = 0.0

        for agent_id, vote_data in self.votes.items():
            amount = vote_data["amount"]
            epoch_staked = vote_data["epoch_staked"]
            vote = vote_data["vote"]

            # Calculate time-weighted voting power
            t_staked = current_epoch - epoch_staked
            multiplier = min(1.0, t_staked / t_max) if t_max > 0 else 1.0
            V = amount * multiplier
            total_staked_in_vote += amount

            if vote:
                v_t_yes += V
            else:
                v_t_no += V

        # y_t = alpha * y_{t-1} + V_t
        self.y_t_yes = (alpha * self.y_t_yes) + v_t_yes
        self.y_t_no = (alpha * self.y_t_no) + v_t_no

        return v_t_yes, v_t_no, total_staked_in_vote


class Engine:
    def __init__(self, num_honest=20, num_malicious=5):
        if num_honest + num_malicious <= 0:
            raise ValueError("Simulation must have at least one agent.")
        # ---------------- Game Theory Parameters ----------------
        self.B = 500  # Bond size (B_c and B_s)
        self.L = 400  # Loan principal (must be < 2B)
        self.R = 75  # Integrity reward

        # ---------------- Monetary Policy Parameters ----------------
        self.R_res = 0.0  # Rewards Reservoir
        self.circulating_supply = 0.0
        self.rho = 0.05  # Reward Release Rate (5%)

        # ---------------- Governance Parameters ----------------
        self.proposals = []
        self.next_proposal_id = 1
        self.alpha_conviction = 0.8
        self.t_max = 5
        self.core_quorum = 0.25
        self.core_approval = 0.66
        self.minor_quorum = 0.10
        self.minor_approval = 0.51

        # ---------------- TrustLedger Math Weights ----------------
        self.alpha = 0.4  # Transitive Trust (E) weight
        self.beta = 0.4  # Social Connectivity (P) weight
        self.gamma = 0.2  # Time-Weighting (W) weight
        self.ema_decay = 0.1  # Decay for Time-Weighting (W) EMA

        # ---------------- Simulation State ----------------
        self.epoch = 0
        self.agents = {}

        # Initialize agents
        for i in range(num_honest):
            agent_id = f"H_{i}"
            self.agents[agent_id] = Agent(
                agent_id, is_malicious=False, b=self.B, l_amount=self.L, r=self.R
            )
            self.circulating_supply += self.agents[agent_id].balance

        for i in range(num_malicious):
            agent_id = f"M_{i}"
            # Malicious attacker orchestrates Sybils
            self.agents[agent_id] = Agent(
                agent_id, is_malicious=True, b=self.B, l_amount=self.L, r=self.R
            )
            self.circulating_supply += self.agents[agent_id].balance

        # Track Time-Weighted Conviction W for all agents using EMA
        self.W = {agent_id: 0.0 for agent_id in self.agents}
        # Track past epoch verified activity for EMA calculation
        self.recent_activity = {agent_id: 0 for agent_id in self.agents}

        # Track initial balances to compute ROI later
        self.initial_balances = {
            a_id: self.agents[a_id].balance for a_id in self.agents
        }
        self.history = []

        # Global Loan Registry
        self.active_loans = []

        # Pre-compute static agent groups for performance optimization
        self.honest_ids = []
        self.malicious_ids = []
        for a_id, agent in self.agents.items():
            if agent.is_malicious:
                self.malicious_ids.append(a_id)
            else:
                self.honest_ids.append(a_id)

    # ---------------- TrustLedger Functions ----------------
    def calculate_transitive_trust(self):
        """Calculates EigenTrust-style E(u) for all agents."""
        E = {agent_id: 1.0 for agent_id in self.agents}  # Initial flat trust
        iterations = 5  # Small number of power iterations to converge local graph

        for _ in range(iterations):
            new_E = {agent_id: 0.0 for agent_id in self.agents}
            for u in self.agents.values():
                total_interactions = sum(math.sqrt(w) for w in u.interactions.values())
                if total_interactions > 0:
                    for v_id, weight in u.interactions.items():
                        # u vouches for v_id
                        normalized_weight = math.sqrt(weight) / total_interactions
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
        d = 0.85  # Damping factor
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
            self.W[agent_id] = (activity * self.ema_decay) + (
                self.W[agent_id] * (1 - self.ema_decay)
            )
            self.recent_activity[agent_id] = 0  # Reset for next epoch
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
    def run_epoch(self):  # noqa: C901
        self.epoch += 1
        epoch_repaid_principal = 0

        # 1. Honest Agents Act (Simulate a network graph of interactions)
        honest_ids = self.honest_ids
        for a_id in honest_ids:
            sponsor = self.agents[a_id]
            # Interact with a few other honest nodes randomly to build the social graph
            other_honest_ids = [hid for hid in honest_ids if hid != a_id]
            if other_honest_ids:
                friends = random.sample(other_honest_ids, min(3, len(other_honest_ids)))
                for friend in friends:
                    sponsor.interact_with(friend, self.L)

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
                            self.circulating_supply += self.R * 2

        # 2. Malicious Agents Act (Sybil Swarm)
        malicious_ids = self.malicious_ids
        for m_id in malicious_ids:
            attacker = self.agents[m_id]
            # Sybil graph: attackers only interact with themselves (link farms)
            for other_m in malicious_ids:
                if other_m != m_id:
                    attacker.interact_with(
                        other_m, self.L * 5
                    )  # High internal interaction

            # Attacker controls Sponsor and Candidate (which is another Sybil or themselves)
            if attacker.balance >= (self.B * 2):  # Needs 2B
                fake_candidate_id = m_id  # Themselves for simplicity

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
                    self.circulating_supply -= self.B * 2
                    self.circulating_supply += self.L  # But they kept L
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
        # [EXPLANATORY: Throttles M_epoch during Sybil swarms so it never exceeds 1% of the circulating supply.]
        # [IDENTIFIER: engine_calc_m_epoch]
        M_epoch = min(self.rho * self.R_res, 0.01 * self.circulating_supply)

        # Calculate inflation rate
        inflation_rate = (
            (M_epoch / self.circulating_supply) if self.circulating_supply > 0 else 0
        )

        # 3.5 Governance: Agents Propose and Vote

        # Total $CRED in network
        total_cred = sum(agent.cred_balance for agent in self.agents.values())

        active_proposals = [p for p in self.proposals if p.status == "active"]

        # Honest Agent Behavior
        if total_cred > 0:
            target_rho = None
            if inflation_rate > 0.02:
                target_rho = max(0.01, self.rho - 0.01)
            # Lowering the threshold so they propose for simulation purposes
            elif inflation_rate < 0.02 and self.R_res > (
                0.001 * self.circulating_supply
            ):
                target_rho = min(0.50, self.rho + 0.01)

            # Check if there is an active proposal matching the target
            honest_proposal = next(
                (p for p in active_proposals if p.target_rho == target_rho), None
            )

            if target_rho is not None and honest_proposal is None:
                # Find an honest agent with $CRED to propose
                proposer = next(
                    (
                        self.agents[a_id]
                        for a_id in honest_ids
                        if self.agents[a_id].cred_balance > 0
                    ),
                    None,
                )
                if proposer:
                    new_prop = Proposal(
                        self.next_proposal_id,
                        proposer.id,
                        target_rho,
                        self.epoch,
                        is_core=True,
                    )
                    self.proposals.append(new_prop)
                    self.next_proposal_id += 1
                    active_proposals.append(new_prop)
                    honest_proposal = new_prop

            # Honest agents vote
            for a_id in honest_ids:
                agent = self.agents[a_id]
                if agent.cred_balance > 0:
                    for p in active_proposals:
                        if (
                            p.target_rho <= self.rho + 0.01
                            and p.target_rho >= self.rho - 0.01
                        ):
                            # Vote yes on reasonable proposals
                            p.cast_vote(a_id, agent.cred_balance, True, self.epoch)
                        else:
                            # Vote no on extreme proposals
                            p.cast_vote(a_id, agent.cred_balance, False, self.epoch)

        # Malicious Agent Behavior
        # They always want to maximize rho to trigger hyperinflation
        malicious_target_rho = 0.50
        malicious_proposal = next(
            (p for p in active_proposals if p.target_rho == malicious_target_rho), None
        )

        if malicious_proposal is None and malicious_ids:
            # Malicious agent tries to propose if they have $CRED (unlikely if they default)
            m_proposer = next(
                (
                    self.agents[m_id]
                    for m_id in malicious_ids
                    if self.agents[m_id].cred_balance > 0
                ),
                None,
            )
            if m_proposer:
                new_prop = Proposal(
                    self.next_proposal_id,
                    m_proposer.id,
                    malicious_target_rho,
                    self.epoch,
                    is_core=True,
                )
                self.proposals.append(new_prop)
                self.next_proposal_id += 1
                active_proposals.append(new_prop)
                malicious_proposal = new_prop

        # Malicious agents vote
        for m_id in malicious_ids:
            agent = self.agents[m_id]
            if agent.cred_balance > 0:
                for p in active_proposals:
                    if p.target_rho == malicious_target_rho:
                        p.cast_vote(m_id, agent.cred_balance, True, self.epoch)
                    else:
                        p.cast_vote(m_id, agent.cred_balance, False, self.epoch)

        # 3.6 Tally Votes and Update Status
        for p in active_proposals:
            if p.is_core:
                # Update conviction y_t
                _, _, _ = p.update_conviction(
                    self.alpha_conviction, self.t_max, self.epoch
                )

                # Check if conviction threshold is met
                # Threshold: 20% of maximum theoretical network conviction
                max_conviction = total_cred * 1.0  # multiplier maxes at 1.0
                conviction_threshold = 0.20 * max_conviction

                # For continuous voting, we need to compare y_t to something stable or max possible.
                # In Aragon style, threshold = beta - (alpha * R) / (total_supply - y_t_yes) or similar.
                # For this simulation, max steady state conviction = total_cred / (1 - alpha_conviction).
                steady_state_max = (
                    max_conviction / (1 - self.alpha_conviction)
                    if self.alpha_conviction < 1
                    else max_conviction
                )
                conviction_threshold = 0.20 * steady_state_max

                # Quorum check (just simple check if total votes > quorum)
                # Note: Conviction voting usually handles quorum implicitly by requiring enough y_t

                if p.y_t_yes > conviction_threshold and p.y_t_yes > p.y_t_no:
                    self.rho = p.target_rho
                    p.status = "executed"
                    print(
                        f"-> Governance: Proposal {p.id} executed! New rho: {self.rho:.4f}"
                    )
                elif p.y_t_no > conviction_threshold and p.y_t_no > p.y_t_yes:
                    p.status = "rejected"
                    print(
                        f"-> Governance: Proposal {p.id} rejected due to high 'No' conviction."
                    )
            else:
                # Minor proposal - Discrete voting with dynamic quorums
                # Get actual time-weighted voting power V_t, and total raw staked tokens.
                v_t_yes, v_t_no, total_staked_in_vote = p.update_conviction(
                    0, self.t_max, self.epoch
                )

                # Check Quorum (total actual tokens staked regardless of time weight)
                if total_staked_in_vote >= self.minor_quorum * total_cred:
                    # Check Approval
                    total_v = v_t_yes + v_t_no
                    if total_v > 0:
                        if (v_t_yes / total_v) >= self.minor_approval:
                            # Execute minor proposal (for this sim, just marking it done)
                            p.status = "executed"
                            print(f"-> Governance: Minor Proposal {p.id} executed!")
                        else:
                            p.status = "rejected"
                            print(f"-> Governance: Minor Proposal {p.id} rejected!")

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
        h_roi_total = sum(
            (self.agents[a_id].balance - self.initial_balances[a_id])
            for a_id in honest_ids
        )
        avg_h_roi = h_roi_total / len(honest_ids) if honest_ids else 0

        m_roi_total = sum(
            (self.agents[a_id].balance - self.initial_balances[a_id])
            for a_id in malicious_ids
        )
        avg_m_roi = m_roi_total / len(malicious_ids) if malicious_ids else 0

        print(f"\n=== EPOCH {self.epoch} SUMMARY ===")
        print(f"Epoch Verified Volume (Repaid L): {epoch_repaid_principal}")
        print(f"Rewards Reservoir R_res (Locked):  {self.R_res:.2f} CRE")
        print(f"Circulating Supply:              {self.circulating_supply:.2f} CRE")
        print(f"Game Theory EV(Honest):          {ev_honest:.2f} CRE per interaction")
        print(
            f"Game Theory EV(Attacker):        {ev_attacker:.2f} CRE per interaction (Attacker ROI)"
        )
        print(f"Actual Avg Honest ROI so far:    {avg_h_roi:.2f} CRE")
        print(f"Actual Avg Attacker ROI so far:  {avg_m_roi:.2f} CRE")
        print(f"Governance - Total $CRED:        {total_cred}")
        print(f"Governance - Active Proposals:   {len(active_proposals)}")
        for p in active_proposals:
            print(
                f"  Prop {p.id}: Target rho={p.target_rho:.4f}, y_t_yes={p.y_t_yes:.2f}, y_t_no={p.y_t_no:.2f}"
            )

        # Print Trust Scores to show Sybil isolation
        avg_h_trust = (
            sum(T_scores[a] for a in honest_ids) / len(honest_ids) if honest_ids else 0
        )
        avg_m_trust = (
            sum(T_scores[a] for a in malicious_ids) / len(malicious_ids)
            if malicious_ids
            else 0
        )
        print(f"Avg Trust Score (Honest):        {avg_h_trust:.4f}")
        print(f"Avg Trust Score (Malicious):     {avg_m_trust:.4f}")
        # Append telemetry data to history
        self.history.append(
            {
                "epoch": self.epoch,
                "verified_volume": epoch_repaid_principal,
                "rewards_reservoir": self.R_res,
                "circulating_supply": self.circulating_supply,
                "ev_honest": ev_honest,
                "ev_attacker": ev_attacker,
                "avg_h_roi": avg_h_roi,
                "avg_m_roi": avg_m_roi,
                "avg_h_trust": avg_h_trust,
                "avg_m_trust": avg_m_trust,
                "total_cred": total_cred,
            }
        )

    def get_results(self):
        return self.history


if __name__ == "__main__":
    engine = Engine(num_honest=20, num_malicious=5)
    for _ in range(15):
        engine.run_epoch()
