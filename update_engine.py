import re

with open("simulations/engine.py", "r") as f:
    content = f.read()

# Replace magic numbers
content = content.replace("inflation_rate > 0.02:", "inflation_rate > self.INFLATION_TARGET:")
content = content.replace("inflation_rate < 0.02 and self.R_res > (0.001 * self.circulating_supply):", "inflation_rate < self.INFLATION_TARGET and self.R_res > (self.CAPITALIZATION_THRESHOLD * self.circulating_supply):")
content = content.replace("max(0.01, self.rho - 0.01)", "max(0.01, self.rho - self.RHO_ADJUSTMENT_STEP)")
content = content.replace("min(0.50, self.rho + 0.01)", "min(self.RHO_MAX, self.rho + self.RHO_ADJUSTMENT_STEP)")
content = content.replace("p.target_rho <= self.rho + 0.01 and p.target_rho >= self.rho - 0.01", "p.target_rho <= self.rho + self.RHO_ADJUSTMENT_STEP and p.target_rho >= self.rho - self.RHO_ADJUSTMENT_STEP")
content = content.replace("malicious_target_rho = 0.50", "malicious_target_rho = self.RHO_MAX")

# Define constants
constants = """        self.minor_approval = 0.51

        # Honest Agent Constants
        self.INFLATION_TARGET = 0.02
        self.RHO_ADJUSTMENT_STEP = 0.01
        self.RHO_MAX = 0.50
        self.CAPITALIZATION_THRESHOLD = 0.001
"""
content = content.replace("self.minor_approval = 0.51\n", constants)

# Remove redundant assignment
content = content.replace("conviction_threshold = 0.20 * max_conviction\n                \n                # For continuous voting", "# For continuous voting")

# Update log printing
new_log = """        # Refetch active proposals before printing to ensure accurate status is displayed
        active_proposals_for_log = [p for p in self.proposals if p.status == "active"]
        print(f"Governance - Total $CRED:        {total_cred}")
        print(f"Governance - Active Proposals:   {len(active_proposals_for_log)}")
        for p in active_proposals_for_log:"""

content = content.replace("""        print(f"Governance - Total $CRED:        {total_cred}")
        print(f"Governance - Active Proposals:   {len(active_proposals)}")
        for p in active_proposals:""", new_log)

# Add calculate_discrete_votes function
new_function = """        self.y_t_yes = (alpha * self.y_t_yes) + v_t_yes
        self.y_t_no = (alpha * self.y_t_no) + v_t_no

        return v_t_yes, v_t_no, total_staked_in_vote

    def calculate_discrete_votes(self, current_epoch, t_max):
        \"\"\"Calculates votes for minor proposals without modifying conviction state.\"\"\"
        v_t_yes = 0.0
        v_t_no = 0.0
        total_staked_in_vote = 0.0

        for agent_id, vote_data in self.votes.items():
            amount = vote_data["amount"]
            epoch_staked = vote_data["epoch_staked"]
            vote = vote_data["vote"]

            # Calculate time-weighted voting power.
            # For discrete votes evaluated in the current epoch, time-weight is 1.0
            # to allow immediate impact.
            t_staked = current_epoch - epoch_staked
            multiplier = min(1.0, (t_staked + 1) / t_max) if t_max > 0 else 1.0 # Added +1 so current epoch votes count
            V = amount * multiplier
            total_staked_in_vote += amount

            if vote:
                v_t_yes += V
            else:
                v_t_no += V

        return v_t_yes, v_t_no, total_staked_in_vote
"""

content = content.replace("""        self.y_t_yes = (alpha * self.y_t_yes) + v_t_yes
        self.y_t_no = (alpha * self.y_t_no) + v_t_no

        return v_t_yes, v_t_no, total_staked_in_vote\n""", new_function)


with open("simulations/engine.py", "w") as f:
    f.write(content)
