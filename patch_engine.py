import re

with open("simulations/engine.py", "r") as f:
    content = f.read()

# Replace M_epoch logic
old_m_epoch = """        # Calculate Minted amount
        M_epoch = self.rho * self.R_res"""

new_m_epoch = """        # Calculate Minted amount
        # [EXPLANATORY: Throttles M_epoch during Sybil swarms so it never exceeds 1% of the circulating supply.]
        # [IDENTIFIER: engine_calc_m_epoch]
        M_epoch = min(self.rho * self.R_res, 0.01 * self.circulating_supply)"""

content = content.replace(old_m_epoch, new_m_epoch)

with open("simulations/engine.py", "w") as f:
    f.write(content)
print("Patched simulations/engine.py")
