with open("simulations/engine.py", "r") as f:
    content = f.read()

# Replace the specific random candidate choice
old_str = """                # Random honest candidate
                candidate_id = random.choice(honest_ids)
                candidate = self.agents[candidate_id]"""

new_str = """                # Random honest candidate, excluding self
                other_honest_ids = [hid for hid in honest_ids if hid != a_id]
                if not other_honest_ids:
                    continue
                candidate_id = random.choice(other_honest_ids)
                candidate = self.agents[candidate_id]"""

content = content.replace(old_str, new_str)

with open("simulations/engine.py", "w") as f:
    f.write(content)
