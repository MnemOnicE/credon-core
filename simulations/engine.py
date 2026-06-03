import math
import random

from agents import Agent


class Proposal:
    """
    [EXPLANATORY: Proposal]
    [IDENTIFIER: Proposal]
    """

    def __init__(self, prop_id, proposer_id, target_rho, creation_epoch, is_core=True):
        """
        [EXPLANATORY: __init__]
        [IDENTIFIER: __init__]
        """
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
        """
        [EXPLANATORY: cast_vote]
        [IDENTIFIER: cast_vote]
        """
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
        """
        [EXPLANATORY: update_conviction]
        [IDENTIFIER: update_conviction]
        [DIRECTIONAL: val]
        """
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
    """
    [EXPLANATORY: Engine]
    [IDENTIFIER: Engine]
    """

    def __init__(self, num_honest=20, num_malicious=5):
        """
        [EXPLANATORY: __init__]
        [IDENTIFIER: __init__]
        """
        if num_honest + num_malicious <= 0:
            raise ValueError("Simulation must have at least one agent.")
        # ---------------- Game Theory Parameters ----------------
        self.B = 500  # Bond size (B_c and B_s)
        self.L = 400  # Loan principal (must be < 2B)
        self.R = 75  # Integrity reward

        # ---------------- Monetary Policy Parameters ----------------
        self.R_res = 0.0  # Rewards Reservoir
        self.circulating_supply = 0.0
        self.rho = 0.05
        self.M_EPOCH_CIRCULATING_SUPPLY_CAP = 0.01  # Reward Release Rate (5%)

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
            self.agents[agent_id] = Agent(agent_id, is_malicious=False, b=self.B, l_amount=self.L, r=self.R)
            self.circulating_supply += self.agents[agent_id].balance

        for i in range(num_malicious):
            agent_id = f"M_{i}"
            # Malicious attacker orchestrates Sybils
            self.agents[agent_id] = Agent(agent_id, is_malicious=True, b=self.B, l_amount=self.L, r=self.R)
            self.circulating_supply += self.agents[agent_id].balance

        # Track Time-Weighted Conviction W for all agents using EMA
        self.W = {agent_id: 0.0 for agent_id in self.agents}
        # Track past epoch verified activity for EMA calculation
        self.recent_activity = {agent_id: 0 for agent_id in self.agents}

        # Track initial balances to compute ROI later
        self.initial_balances = {a_id: self.agents[a_id].balance for a_id in self.agents}
        self.history = []

        # Global Loan Registry
        self.active_loans = []

        # Initialize cryptographically secure random number generator
        self.rng = random.SystemRandom()

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
        """Calculates EigenTrust-style E(u) for all agents.
        [EXPLANATORY: calculate_transitive_trust]
        [IDENTIFIER: calculate_transitive_trust]
        [DIRECTIONAL: val]
        """
        agent_ids = list(self.agents.keys())
        num_agents = len(agent_ids)
        id_to_idx = {agent_id: i for i, agent_id in enumerate(agent_ids)}

        # Initial flat trust as a list
        E_list = [1.0] * num_agents
        iterations = 5  # Small number of power iterations to converge local graph

        # Pre-compute and flatten the interaction graph for fast iteration
        flattened_interactions = self._get_flattened_interactions(agent_ids, id_to_idx)

        for _ in range(iterations):
            E_list = self._run_trust_iteration(E_list, flattened_interactions, num_agents)

        # Convert back to dictionary
        return dict(zip(agent_ids, E_list))

    def _get_flattened_interactions(self, agent_ids, id_to_idx):
        """
        [EXPLANATORY: Flattens the interaction graph into a list of (u_idx, v_idx, weight) tuples.]
        [IDENTIFIER: _get_flattened_interactions]
        [DIRECTIONAL: val]
        """
        flattened = []
        for u_id in agent_ids:
            u = self.agents[u_id]
            u_idx = id_to_idx[u_id]
            total_interactions = sum(math.sqrt(w) for w in u.interactions.values())
            if total_interactions > 0:
                for v_id, weight in u.interactions.items():
                    if v_id in id_to_idx:
                        v_idx = id_to_idx[v_id]
                        normalized_weight = math.sqrt(weight) / total_interactions
                        flattened.append((u_idx, v_idx, normalized_weight))
        return flattened

    def _run_trust_iteration(self, E_list, flattened_interactions, num_agents):
        """
        [EXPLANATORY: Runs one power iteration for transitive trust calculation.]
        [IDENTIFIER: _run_trust_iteration]
        [DIRECTIONAL: val]
        """
        new_E_list = [0.0] * num_agents
        for u_idx, v_idx, normalized_weight in flattened_interactions:
            new_E_list[v_idx] += E_list[u_idx] * normalized_weight

        # Normalize to prevent explosion
        total_E = sum(new_E_list)
        if total_E > 0:
            scale = num_agents / total_E
            return [v * scale for v in new_E_list]
        return new_E_list

    def calculate_social_connectivity(self):
        """Calculates PageRank-style P(u) for all agents.
        [EXPLANATORY: calculate_social_connectivity]
        [IDENTIFIER: calculate_social_connectivity]
        [DIRECTIONAL: val]
        """
        agent_ids = list(self.agents.keys())
        num_agents = len(agent_ids)
        id_to_idx = {agent_id: i for i, agent_id in enumerate(agent_ids)}

        P_list = [1.0 / num_agents] * num_agents
        d = 0.85  # Damping factor
        iterations = 10

        # Pre-compute normalized interactions and identify sink indices
        flattened_interactions, sink_indices = self._get_social_connectivity_structures(agent_ids, id_to_idx)

        for _ in range(iterations):
            P_list = self._run_social_iteration(P_list, flattened_interactions, sink_indices, num_agents, d)

        # Scale and convert back to dictionary
        return {agent_ids[i]: P_list[i] * num_agents for i in range(num_agents)}

    def _get_social_connectivity_structures(self, agent_ids, id_to_idx):
        """
        [EXPLANATORY: Pre-computes normalized interactions and sink indices for PageRank.]
        [IDENTIFIER: _get_social_connectivity_structures]
        [DIRECTIONAL: val]
        """
        flattened = []
        sinks = []
        for u_id in agent_ids:
            u = self.agents[u_id]
            u_idx = id_to_idx[u_id]
            out_degree = sum(u.interactions.values())
            if out_degree > 0:
                for v_id, weight in u.interactions.items():
                    if v_id in id_to_idx:
                        v_idx = id_to_idx[v_id]
                        flattened.append((u_idx, v_idx, weight / out_degree))
            else:
                sinks.append(u_idx)
        return flattened, sinks

    def _run_social_iteration(self, P_list, flattened_interactions, sink_indices, num_agents, d):
        """
        [EXPLANATORY: Runs one power iteration for social connectivity calculation.]
        [IDENTIFIER: _run_social_iteration]
        [DIRECTIONAL: val]
        """
        base_p = (1.0 - d) / num_agents
        new_P_list = [base_p] * num_agents

        for u_idx, v_idx, norm_weight in flattened_interactions:
            new_P_list[v_idx] += P_list[u_idx] * d * norm_weight

        sink_contribution = sum(P_list[idx] for idx in sink_indices) * d / num_agents
        if sink_contribution > 0:
            for i in range(num_agents):
                new_P_list[i] += sink_contribution

        return new_P_list

    def update_time_weighting(self):
        """Calculates W(u, t) using discrete EMA of verified recent activity.
        [EXPLANATORY: update_time_weighting]
        [IDENTIFIER: update_time_weighting]
        [DIRECTIONAL: val]
        """
        for agent_id in self.agents:
            activity = self.recent_activity[agent_id]
            # EMA = (Value_today * decay) + (EMA_yesterday * (1 - decay))
            self.W[agent_id] = (activity * self.ema_decay) + (self.W[agent_id] * (1 - self.ema_decay))
            self.recent_activity[agent_id] = 0  # Reset for next epoch
        return self.W

    def calculate_trust_scores(self):
        r"""T(u, t) = \alpha E(u) + \beta P(u) + \gamma W(u, t)
        [EXPLANATORY: calculate_trust_scores]
        [IDENTIFIER: calculate_trust_scores]
        [DIRECTIONAL: val]
        """
        E = self.calculate_transitive_trust()
        P = self.calculate_social_connectivity()
        W = self.update_time_weighting()

        T = {}
        for a in self.agents:
            T[a] = (self.alpha * E[a]) + (self.beta * P[a]) + (self.gamma * W[a])
        return T

    # ---------------- Simulation Step ----------------
    def run_epoch(self):
        """
        [EXPLANATORY: run_epoch]
        [IDENTIFIER: run_epoch]
        """
        self.epoch += 1

        # 1. Action Phase
        epoch_repaid_principal = self._perform_honest_actions()
        self._perform_malicious_actions()

        # 2. Analytics Phase
        T_scores = self.calculate_trust_scores()

        # 3. Monetary Policy Phase
        M_epoch, inflation_rate = self._update_monetary_policy(epoch_repaid_principal)

        # 4. Governance Phase
        total_cred, active_proposals = self._handle_governance(inflation_rate)
        self._tally_governance_votes(active_proposals, total_cred)

        # 5. Finalize State
        self.R_res -= M_epoch
        self.circulating_supply += M_epoch

        # 6. Record Results
        self._record_telemetry(epoch_repaid_principal, T_scores, total_cred, active_proposals)

    def _perform_honest_actions(self):
        """
        [EXPLANATORY: Simulates honest agent activities including interactions and sponsorships.]
        [IDENTIFIER: _perform_honest_actions]
        [DIRECTIONAL: val]
        """
        repaid_principal = 0
        for a_id in self.honest_ids:
            sponsor = self.agents[a_id]
            # Build social graph
            other_honest_ids = [hid for hid in self.honest_ids if hid != a_id]
            if other_honest_ids:
                friends = self.rng.sample(other_honest_ids, min(3, len(other_honest_ids)))
                for friend in friends:
                    sponsor.interact_with(friend, self.L)

            # Sponsoring
            if sponsor.balance >= self.B:
                candidate_id = self.rng.choice(self.honest_ids)
                candidate = self.agents[candidate_id]
                if candidate.post_candidate_bond() == self.B:
                    loan_record = sponsor.try_sponsor(candidate_id, self.epoch)
                    if loan_record:
                        candidate.receive_loan(self.L)
                        self.active_loans.append(loan_record)
                        if candidate.repay_loan(self.L, loan_record):
                            repaid_principal += self.L
                            self.recent_activity[sponsor.id] += 1
                            self.recent_activity[candidate.id] += 1
                            sponsor.process_graduation(self.B, self.R)
                            candidate.process_graduation(self.B, self.R)
                            self.circulating_supply += self.R * 2
        return repaid_principal

    def _perform_malicious_actions(self):
        """
        [EXPLANATORY: Simulates malicious agent activities including link farms and defaults.]
        [IDENTIFIER: _perform_malicious_actions]
        """
        for m_id in self.malicious_ids:
            attacker = self.agents[m_id]
            for other_m in self.malicious_ids:
                if other_m != m_id:
                    attacker.interact_with(other_m, self.L * 5)

            if attacker.balance >= (self.B * 2):
                fake_candidate_id = m_id
                b_c = attacker.post_candidate_bond()
                loan_record = attacker.try_sponsor(fake_candidate_id, self.epoch)
                if loan_record and b_c == self.B:
                    attacker.receive_loan(self.L)
                    self.active_loans.append(loan_record)
                    attacker.execute_default(loan_record)
                    self.circulating_supply -= (self.B * 2) - self.L

    def _update_monetary_policy(self, repaid_principal):
        """
        [EXPLANATORY: Updates monetary policy parameters based on epoch activity.]
        [IDENTIFIER: _update_monetary_policy]
        [DIRECTIONAL: val]
        """
        delta_r = math.sqrt(repaid_principal)
        self.R_res += delta_r
        M_epoch = min(self.rho * self.R_res, 0.01 * self.circulating_supply)
        inflation_rate = (M_epoch / self.circulating_supply) if self.circulating_supply > 0 else 0
        return M_epoch, inflation_rate

    def _handle_governance(self, inflation_rate):
        """
        [EXPLANATORY: Handles proposal creation and voting logic for agents.]
        [IDENTIFIER: _handle_governance]
        [DIRECTIONAL: val]
        """
        total_cred = sum(agent.cred_balance for agent in self.agents.values())
        active_proposals = [p for p in self.proposals if p.status == "active"]

        if total_cred > 0:
            self._handle_honest_governance(inflation_rate, active_proposals)
            self._handle_malicious_governance(active_proposals)

        return total_cred, active_proposals

    def _handle_honest_governance(self, inflation_rate, active_proposals):
        """
        [EXPLANATORY: Honest governance actions.]
        [IDENTIFIER: _handle_honest_governance]
        """
        target_rho = None
        if inflation_rate > 0.02:
            target_rho = max(0.01, self.rho - 0.01)
        elif inflation_rate < 0.02 and self.R_res > (0.001 * self.circulating_supply):
            target_rho = min(0.50, self.rho + 0.01)

        honest_proposal = next((p for p in active_proposals if p.target_rho == target_rho), None)
        if target_rho is not None and honest_proposal is None:
            proposer = next((self.agents[a_id] for a_id in self.honest_ids if self.agents[a_id].cred_balance > 0), None)
            if proposer:
                new_prop = Proposal(self.next_proposal_id, proposer.id, target_rho, self.epoch, is_core=True)
                self.proposals.append(new_prop)
                self.next_proposal_id += 1
                active_proposals.append(new_prop)

        reasonable = [p for p in active_proposals if abs(p.target_rho - self.rho) <= 0.0100000001]
        extreme = [p for p in active_proposals if abs(p.target_rho - self.rho) > 0.0100000001]

        for a_id in self.honest_ids:
            agent = self.agents[a_id]
            if agent.cred_balance > 0:
                for p in reasonable:
                    p.cast_vote(a_id, agent.cred_balance, True, self.epoch)
                for p in extreme:
                    p.cast_vote(a_id, agent.cred_balance, False, self.epoch)

    def _handle_malicious_governance(self, active_proposals):
        """
        [EXPLANATORY: Malicious governance actions.]
        [IDENTIFIER: _handle_malicious_governance]
        """
        malicious_target_rho = 0.50
        malicious_proposal = next((p for p in active_proposals if p.target_rho == malicious_target_rho), None)
        if malicious_proposal is None and self.malicious_ids:
            m_proposer = next((self.agents[m_id] for m_id in self.malicious_ids if self.agents[m_id].cred_balance > 0), None)
            if m_proposer:
                new_prop = Proposal(self.next_proposal_id, m_proposer.id, malicious_target_rho, self.epoch, is_core=True)
                self.proposals.append(new_prop)
                self.next_proposal_id += 1
                active_proposals.append(new_prop)

        target_mal = [p for p in active_proposals if math.isclose(p.target_rho, malicious_target_rho, abs_tol=1e-9)]
        other_mal = [p for p in active_proposals if not math.isclose(p.target_rho, malicious_target_rho, abs_tol=1e-9)]

        for m_id in self.malicious_ids:
            agent = self.agents[m_id]
            if agent.cred_balance > 0:
                for p in target_mal:
                    p.cast_vote(m_id, agent.cred_balance, True, self.epoch)
                for p in other_mal:
                    p.cast_vote(m_id, agent.cred_balance, False, self.epoch)

    def _tally_governance_votes(self, active_proposals, total_cred):
        """
        [EXPLANATORY: Tallies votes and updates proposal statuses.]
        [IDENTIFIER: _tally_governance_votes]
        """
        for p in active_proposals:
            if p.is_core:
                p.update_conviction(self.alpha_conviction, self.t_max, self.epoch)
                max_conviction = total_cred / (1 - self.alpha_conviction) if self.alpha_conviction < 1 else total_cred
                threshold = 0.20 * max_conviction

                if p.y_t_yes > threshold and p.y_t_yes > p.y_t_no:
                    self.rho = p.target_rho
                    p.status = "executed"
                    print(f"-> Governance: Proposal {p.id} executed! New rho: {self.rho:.4f}")
                elif p.y_t_no > threshold and p.y_t_no > p.y_t_yes:
                    p.status = "rejected"
                    print(f"-> Governance: Proposal {p.id} rejected due to high 'No' conviction.")
            else:
                v_t_yes, v_t_no, staked = p.update_conviction(0, self.t_max, self.epoch)
                if staked >= self.minor_quorum * total_cred:
                    total_v = v_t_yes + v_t_no
                    if total_v > 0 and (v_t_yes / total_v) >= self.minor_approval:
                        p.status = "executed"
                        print(f"-> Governance: Minor Proposal {p.id} executed!")
                    else:
                        p.status = "rejected"
                        print(f"-> Governance: Minor Proposal {p.id} rejected!")

    def _record_telemetry(self, repaid, T_scores, total_cred, active_props):
        """
        [EXPLANATORY: Records and prints epoch summary data.]
        [IDENTIFIER: _record_telemetry]
        """
        ev_h = (0.95 * self.R) - (0.05 * self.B)
        ev_m = self.L - (2 * self.B)
        avg_h_roi = sum(self.agents[a].balance - self.initial_balances[a] for a in self.honest_ids) / len(self.honest_ids) if self.honest_ids else 0
        avg_m_roi = sum(self.agents[m].balance - self.initial_balances[m] for m in self.malicious_ids) / len(self.malicious_ids) if self.malicious_ids else 0

        print(f"\n=== EPOCH {self.epoch} SUMMARY ===")
        print(f"Verified Volume: {repaid} | R_res: {self.R_res:.2f} | Supply: {self.circulating_supply:.2f}")
        print(f"EV(H): {ev_h:.2f} | EV(M): {ev_m:.2f} | Avg H ROI: {avg_h_roi:.2f} | Avg M ROI: {avg_m_roi:.2f}")

        avg_h_t = sum(T_scores[a] for a in self.honest_ids) / len(self.honest_ids) if self.honest_ids else 0
        avg_m_t = sum(T_scores[m] for m in self.malicious_ids) / len(self.malicious_ids) if self.malicious_ids else 0
        print(f"Avg Trust H: {avg_h_t:.4f} | Avg Trust M: {avg_m_t:.4f}")

        self.history.append({
            "epoch": self.epoch, "verified_volume": repaid, "rewards_reservoir": self.R_res,
            "circulating_supply": self.circulating_supply, "ev_honest": ev_h, "ev_attacker": ev_m,
            "avg_h_roi": avg_h_roi, "avg_m_roi": avg_m_roi, "avg_h_trust": avg_h_t,
            "avg_m_trust": avg_m_t, "total_cred": total_cred
        })

    def get_results(self):
        """
        [EXPLANATORY: get_results]
        [IDENTIFIER: get_results]
        [DIRECTIONAL: val]
        """
        return self.history


if __name__ == "__main__":
    engine = Engine(num_honest=20, num_malicious=5)
    for _ in range(15):
        engine.run_epoch()
