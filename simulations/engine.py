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
        self.votes[agent_id] = {
            "amount": amount,
            "epoch_staked": current_epoch,
            "vote": vote,
        }

    @staticmethod
    def create_batch_updates(active_agents, vote, current_epoch):
        """
        [EXPLANATORY: create_batch_updates]
        [IDENTIFIER: create_batch_updates]
        [DIRECTIONAL: val]
        """
        return {
            agent_id: {
                "amount": amount,
                "epoch_staked": current_epoch,
                "vote": vote,
            }
            for agent_id, amount in active_agents
        }

    def cast_votes_batch(self, updates):
        """
        [EXPLANATORY: cast_votes_batch]
        [IDENTIFIER: cast_votes_batch]
        """
        self.votes.update(updates)

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
            vote = vote_data["vote"]

            total_staked_in_vote += amount

            if vote:
                v_t_yes += amount
            else:
                v_t_no += amount

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
        self.rho = 0.10  # Initial Inflation target per epoch
        self.max_inflation = 0.50
        self.max_reservoir_multiplier = 5.0
        self.max_mint = 50000

        # ---------------- Governance Parameters ----------------
        self.proposals = []
        self.next_proposal_id = 1
        self.alpha_conviction = 0.9  # Decay factor a, so a=0.9 means 10% decay per epoch
        self.t_max = 10  # Used in Aragon formulas, here conceptual (epochs to reach 99% max conviction = ~44 epochs)

        # ---------------- Trust & Network State ----------------
        self.agents = {}
        self.initial_balances = {}
        self.epoch = 0
        self.history = []

        self.rng = random.SystemRandom()

        # Initialize Honest Agents
        self.honest_ids = [f"H_{i}" for i in range(num_honest)]
        for h_id in self.honest_ids:
            self.agents[h_id] = Agent(h_id, initial_balance=2000)
            self.initial_balances[h_id] = 2000

        # Initialize Malicious Agents
        self.malicious_ids = [f"M_{i}" for i in range(num_malicious)]
        for m_id in self.malicious_ids:
            self.agents[m_id] = Agent(m_id, initial_balance=2000)
            self.initial_balances[m_id] = 2000

    def _simulate_honest_agents_behavior(self) -> int:
        """
        [EXPLANATORY: Simulates interactions for honest agents, returning epoch volume.]
        [IDENTIFIER: engine_simulate_honest]
        [DIRECTIONAL: val]
        """
        epoch_repaid_principal = 0
        honest_ids = self.honest_ids

        # 1. Simulate Agent Interactions (P2P verifiable loans)
        # Honest agents randomly pair up, sponsor each other, take loans, and repay them.
        for h_id in honest_ids:
            agent = self.agents[h_id]
            # Honest agent tries to find a random sponsor
            potential_sponsors = [s_id for s_id in honest_ids if s_id != h_id]
            if not potential_sponsors:
                continue

            sponsor_id = self.rng.choice(potential_sponsors)
            sponsor = self.agents[sponsor_id]

            # Sponsor vouches for Agent
            if sponsor.try_sponsor(agent.id, self.B):
                # Agent posts candidate bond
                if agent.post_candidate_bond(self.B):
                    # Agent gets loan L
                    agent.balance += self.L
                    # Agent interacts off-chain, succeeds, repays loan
                    agent.repay_loan(self.L)
                    epoch_repaid_principal += self.L
                    # Record positive interaction (Sponsor -> Candidate)
                    self.agents[agent.id].record_interaction(sponsor.id, True)

        return epoch_repaid_principal

    def _simulate_malicious_agents_behavior(self):
        """
        [EXPLANATORY: Simulates interactions for malicious agents.]
        [IDENTIFIER: engine_simulate_malicious]
        """
        malicious_ids = self.malicious_ids
        honest_ids = self.honest_ids

        # Malicious agents try to trick honest agents into sponsoring them, then default
        # or they sponsor each other to build fake trust, then default on an external victim
        for m_id in malicious_ids:
            attacker = self.agents[m_id]
            # Attacker strategy: Try to get an honest sponsor if possible
            potential_victims = [h_id for h_id in honest_ids if self.agents[h_id].balance >= self.B]

            if potential_victims:
                victim_id = self.rng.choice(potential_victims)
                victim = self.agents[victim_id]
                if victim.try_sponsor(attacker.id, self.B):
                    if attacker.post_candidate_bond(self.B):
                        # Attacker gets loan L
                        attacker.balance += self.L
                        # Attacker DEFAULTS.
                        # Both bonds (victim's B_s and attacker's B_c) are slashed and sent to dead address
                        # The loan L is kept by the attacker.
                        victim.slashed_count += 1
                        # Record negative interaction (Victim -> Attacker)
                        self.agents[attacker.id].record_interaction(victim.id, False)
            else:
                # If no honest victims, sybil ring: Malicious sponsor Malicious
                # They don't default here because they would just burn their own money.
                # They do this to build fake transitive trust.
                sybil_sponsors = [
                    s_id for s_id in malicious_ids if s_id != m_id and self.agents[s_id].balance >= self.B
                ]
                if sybil_sponsors:
                    s_id = self.rng.choice(sybil_sponsors)
                    sponsor = self.agents[s_id]
                    if sponsor.try_sponsor(attacker.id, self.B):
                        if attacker.post_candidate_bond(self.B):
                            attacker.balance += self.L
                            attacker.repay_loan(self.L)
                            self.agents[attacker.id].record_interaction(sponsor.id, True)

    def _calculate_monetary_policy(self, epoch_repaid_principal: int) -> tuple[float, int, dict]:
        """
        [EXPLANATORY: Calculates transitive trust, graduation rewards, and minting parameters.]
        [IDENTIFIER: engine_monetary_policy]
        [DIRECTIONAL: val]
        """
        # 2. Transitive Trust & Graduation (Monetary Policy)
        # We need a global trust score to calculate the Network Integrity Factor (I_n).
        # We simulate the EigenTrust/PageRank off-chain rollup computation here.

        # Build interaction graph
        interactions = []
        for a in self.agents.values():
            for p, success in a.interactions:
                weight = 1.0 if success else -1.0
                interactions.append((p, a.id, weight))

        # Calculate Trust
        T_scores = self.calculate_transitive_trust(self.agents.keys(), interactions)

        # Calculate Network Integrity Factor I_n
        total_positive_trust = sum(t for t in T_scores.values() if t > 0)
        I_n = total_positive_trust / len(self.agents) if self.agents else 0.0
        # Normalize I_n to be roughly between 0 and 1.
        # Max positive trust per agent is ~1 if well connected.
        I_n = min(1.0, max(0.0, I_n))

        # Core Monetary Policy Function: Calculate M_epoch
        # M_epoch = min(rho * C_s * I_n, M_max)
        inflation_rate = self.rho * I_n
        M_epoch = int(self.circulating_supply * inflation_rate)
        if self.circulating_supply == 0:
            M_epoch = int(100000 * inflation_rate)  # Base supply if 0

        M_epoch = min(M_epoch, self.max_mint)

        # Distribute M_epoch to Rewards Reservoir
        # R_res_max = max_multiplier * sum(active_bonds)
        active_bonds = sum(self.B for a in self.agents.values() if a.bond_active)
        R_res_max = self.max_reservoir_multiplier * active_bonds

        if self.R_res + M_epoch > R_res_max:
            # Throttle minting
            M_epoch = max(0, R_res_max - self.R_res)

        self.R_res += M_epoch

        # Agent Graduation
        # Agents who successfully repaid loans get their bonds back + Reward R + $CRED
        for a_id, agent in self.agents.items():
            # In actual implementation, verification happens via SMT proof
            if agent.repaid_this_epoch:
                agent.balance += self.B  # Return candidate bond
                agent.balance += self.R  # Pay Integrity Reward
                agent.process_graduation()  # Mint $CRED Sbt SMT node
                agent.repaid_this_epoch = False
                agent.bond_active = False

                # Return Sponsor Bond
                if agent.current_sponsor and agent.current_sponsor in self.agents:
                    sp = self.agents[agent.current_sponsor]
                    sp.balance += self.B
                    sp.bond_active = False
                agent.current_sponsor = None

        return inflation_rate, M_epoch, T_scores

    def calculate_transitive_trust(self, agent_ids, interactions, iterations=10, damping_factor=0.85):
        """
        [EXPLANATORY: calculate_transitive_trust]
        [IDENTIFIER: calculate_transitive_trust]
        [DIRECTIONAL: val]
        """
        id_list = list(agent_ids)
        num_agents = len(id_list)
        if num_agents == 0:
            return {}

        # 1. Create a mapping from agent_id to an integer index
        id_to_idx = {agent_id: idx for idx, agent_id in enumerate(id_list)}

        # 2. Build the adjacency list using indices
        #    out_links[u_idx] = [(v_idx, weight), ...]
        out_links = [[] for _ in range(num_agents)]
        for u, v, w in interactions:
            if u in id_to_idx and v in id_to_idx:
                u_idx = id_to_idx[u]
                v_idx = id_to_idx[v]
                out_links[u_idx].append((v_idx, w))

        # 3. Initialize scores and out_degrees
        scores = [1.0 / num_agents] * num_agents
        out_degrees = [0.0] * num_agents

        for i in range(num_agents):
            degree = sum(max(0, w) for _, w in out_links[i])
            out_degrees[i] = degree

        # 4. Flatten the graph into a list of pre-calculated normalized edges
        #    edges = [(u_idx, v_idx, normalized_weight), ...]
        edges = []
        for u_idx in range(num_agents):
            degree = out_degrees[u_idx]
            if degree > 0:
                for v_idx, w in out_links[u_idx]:
                    if w > 0:
                        edges.append((u_idx, v_idx, w / degree))

        # Find sinks (indices with no out_degrees)
        sinks = [i for i, degree in enumerate(out_degrees) if degree == 0]

        # 5. Iterative power update loop
        base_score = (1.0 - damping_factor) / num_agents
        for _ in range(iterations):
            new_scores = [base_score] * num_agents

            # Add contributions from sinks
            sink_contrib = sum(scores[s] for s in sinks)
            if sink_contrib > 0:
                sink_share = (damping_factor * sink_contrib) / num_agents
                for i in range(num_agents):
                    new_scores[i] += sink_share

            # Accumulate trust flowing through edges
            for u_idx, v_idx, norm_w in edges:
                new_scores[v_idx] += damping_factor * scores[u_idx] * norm_w

            scores = new_scores

        # 6. Map back to agent_ids
        return {id_list[idx]: scores[idx] for idx in range(num_agents)}

    def _process_governance_proposals(self, inflation_rate: float, total_cred: int, active_proposals: list):
        """
        [EXPLANATORY: Processes proposal creation and active voting behavior.]
        [IDENTIFIER: engine_governance]
        """
        honest_ids = self.honest_ids
        malicious_ids = self.malicious_ids

        # 3. Aragon Conviction Voting (Governance Policy)
        # Agents use $CRED to vote on adjusting self.rho (Inflation target)

        # Honest Agent Behavior
        # If inflation > 0.05 (too high), propose to lower rho.
        # If inflation < 0.01 (too low), propose to raise rho.
        target_rho = None
        if inflation_rate > 0.05:
            target_rho = max(0.01, self.rho - 0.01)
        elif inflation_rate < 0.01:
            target_rho = min(self.max_inflation, self.rho + 0.01)

        honest_proposal = None
        if target_rho is not None:
            honest_proposal = next(
                (p for p in active_proposals if math.isclose(p.target_rho, target_rho, abs_tol=1e-9)), None
            )

            if target_rho is not None and honest_proposal is None:
                # Find an honest agent with $CRED to propose
                proposer = next(
                    (self.agents[a_id] for a_id in honest_ids if self.agents[a_id].cred_balance > 0),
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

            # Categorize proposals once for efficiency
            reasonable_proposals = []
            extreme_proposals = []
            for p in active_proposals:
                if p.target_rho <= self.rho + 0.01 and p.target_rho >= self.rho - 0.01:
                    reasonable_proposals.append(p)
                else:
                    extreme_proposals.append(p)

            # Pre-filter agents with balance to avoid redundant dictionary lookups
            active_honest = [
                (a_id, self.agents[a_id].cred_balance) for a_id in honest_ids if self.agents[a_id].cred_balance > 0
            ]

            # Honest agents vote
            updates_yes = Proposal.create_batch_updates(active_honest, True, self.epoch)
            updates_no = Proposal.create_batch_updates(active_honest, False, self.epoch)
            for p in reasonable_proposals:
                p.cast_votes_batch(updates_yes)
            for p in extreme_proposals:
                p.cast_votes_batch(updates_no)

        # Malicious Agent Behavior
        # They always want to maximize rho to trigger hyperinflation
        malicious_target_rho = 0.50
        malicious_proposal = next(
            (p for p in active_proposals if math.isclose(p.target_rho, malicious_target_rho, abs_tol=1e-9)), None
        )

        if malicious_proposal is None and malicious_ids:
            # Malicious agent tries to propose if they have $CRED (unlikely if they default)
            m_proposer = next(
                (self.agents[m_id] for m_id in malicious_ids if self.agents[m_id].cred_balance > 0),
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

        # Categorize proposals for malicious agents
        target_malicious = []
        other_malicious = []
        for p in active_proposals:
            if math.isclose(p.target_rho, malicious_target_rho, abs_tol=1e-9):
                target_malicious.append(p)
            else:
                other_malicious.append(p)

        # Pre-filter malicious agents with balance
        active_malicious = [
            (m_id, self.agents[m_id].cred_balance) for m_id in malicious_ids if self.agents[m_id].cred_balance > 0
        ]

        # Malicious agents vote
        updates_yes = Proposal.create_batch_updates(active_malicious, True, self.epoch)
        updates_no = Proposal.create_batch_updates(active_malicious, False, self.epoch)
        for p in target_malicious:
            p.cast_votes_batch(updates_yes)
        for p in other_malicious:
            p.cast_votes_batch(updates_no)

    def _tally_votes_and_update_status(self, total_cred: int, active_proposals: list):
        """
        [EXPLANATORY: Tallies votes for active proposals and executes or rejects them.]
        [IDENTIFIER: engine_tally_votes]
        """
        for p in active_proposals:
            if p.is_core:
                # Update conviction y_t
                _, _, _ = p.update_conviction(self.alpha_conviction, self.t_max, self.epoch)

                # Check if conviction threshold is met
                # Threshold: 20% of maximum theoretical network conviction
                max_conviction = total_cred * 1.0  # multiplier maxes at 1.0
                conviction_threshold = 0.20 * max_conviction

                # For continuous voting, we need to compare y_t to something stable or max possible.
                # In Aragon style, threshold = beta - (alpha * R) / (total_supply - y_t_yes) or similar.
                # For this simulation, max steady state conviction = total_cred / (1 - alpha_conviction).
                steady_state_max = (
                    max_conviction / (1 - self.alpha_conviction) if self.alpha_conviction < 1 else max_conviction
                )
                conviction_threshold = 0.20 * steady_state_max

                # Quorum check (just simple check if total votes > quorum)
                # Note: Conviction voting usually handles quorum implicitly by requiring enough y_t

                if p.y_t_yes > conviction_threshold and p.y_t_yes > p.y_t_no:
                    self.rho = p.target_rho
                    p.status = "executed"
                    print(f"-> Governance: Proposal {p.id} executed! New rho: {self.rho:.4f}")
                elif p.y_t_no > conviction_threshold and p.y_t_no > p.y_t_yes:
                    p.status = "rejected"
                    print(f"-> Governance: Proposal {p.id} rejected due to high 'No' conviction.")
            else:
                # Minor proposal - Discrete voting with dynamic quorums
                # Get actual time-weighted voting power V_t, and total raw staked tokens.
                v_t_yes, v_t_no, total_staked_in_vote = p.update_conviction(0, self.t_max, self.epoch)

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

    def _calculate_telemetry(
        self, epoch_repaid_principal: int, T_scores: dict, total_cred: int, active_proposals: list
    ):
        """
        [EXPLANATORY: Calculates epoch telemetry and records metrics to history.]
        [IDENTIFIER: engine_telemetry]
        """
        honest_ids = self.honest_ids
        malicious_ids = self.malicious_ids

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

        print(f"\n=== EPOCH {self.epoch} === SUMMARY ===")
        print(f"Epoch Verified Volume (Repaid L): {epoch_repaid_principal}")
        print(f"Rewards Reservoir R_res (Locked):  {self.R_res:.2f} CRE")
        print(f"Circulating Supply:              {self.circulating_supply:.2f} CRE")
        print(f"Game Theory EV(Honest):          {ev_honest:.2f} CRE per interaction")
        print(f"Game Theory EV(Attacker):        {ev_attacker:.2f} CRE per interaction (Attacker ROI)")
        print(f"Actual Avg Honest ROI so far:    {avg_h_roi:.2f} CRE")
        print(f"Actual Avg Attacker ROI so far:  {avg_m_roi:.2f} CRE")
        print(f"Governance - Total $CRED:        {total_cred}")
        print(f"Governance - Active Proposals:   {len(active_proposals)}")
        for p in active_proposals:
            print(f"  Prop {p.id}: Target rho={p.target_rho:.4f}, y_t_yes={p.y_t_yes:.2f}, y_t_no={p.y_t_no:.2f}")

        # Print Trust Scores to show Sybil isolation
        avg_h_trust = sum(T_scores[a] for a in honest_ids) / len(honest_ids) if honest_ids else 0
        avg_m_trust = sum(T_scores[a] for a in malicious_ids) / len(malicious_ids) if malicious_ids else 0
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

    def run_epoch(self):
        """
        [EXPLANATORY: Orchestrates a single simulation epoch.]
        [IDENTIFIER: run_epoch]
        """
        self.epoch += 1
        print(f"\n--- Starting Epoch {self.epoch} ---")

        epoch_repaid_principal = self._simulate_honest_agents_behavior()
        self._simulate_malicious_agents_behavior()

        inflation_rate, M_epoch, T_scores = self._calculate_monetary_policy(epoch_repaid_principal)

        total_cred = sum(agent.cred_balance for agent in self.agents.values())
        active_proposals = [p for p in self.proposals if p.status == "active"]

        self._process_governance_proposals(inflation_rate, total_cred, active_proposals)
        self._tally_votes_and_update_status(total_cred, active_proposals)

        self._calculate_telemetry(epoch_repaid_principal, T_scores, total_cred, active_proposals)

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
