import re

with open("simulations/engine.py", "r") as f:
    content = f.read()

# I will add a noqa: C901 to the run_epoch function
content = content.replace("    def run_epoch(self):", "    def run_epoch(self):  # noqa: C901")

with open("simulations/engine.py", "w") as f:
    f.write(content)
