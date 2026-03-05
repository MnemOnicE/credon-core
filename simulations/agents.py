import random

class Candidate:
    def __init__(self, id, sponsor_id, start_step, bond_amount):
        self.id = id
        self.sponsor_id = sponsor_id
        self.start_step = start_step
        self.bond_amount = bond_amount
        self.status = "pending"  # pending, graduated, defaulted

class HonestAgent:
    def __init__(self, id, initial_balance=2500):
        self.id = id
        self.balance = initial_balance
        self.active_bonds = []

    def try_sponsor(self, step, candidate_id, bond_amount=500):
        # 5% chance per step, requires >= bond_amount
        if self.balance >= bond_amount and random.random() < 0.05:
            self.balance -= bond_amount
            new_candidate = Candidate(candidate_id, self.id, step, bond_amount)
            self.active_bonds.append(new_candidate)
            return new_candidate
        return None

    def process_graduation(self, candidate, reward):
        self.balance += candidate.bond_amount + reward
        candidate.status = "graduated"
        self.active_bonds.remove(candidate)

    def process_slash(self, candidate):
        # Bond is lost, so we just remove the candidate and don't refund
        candidate.status = "defaulted"
        self.active_bonds.remove(candidate)

class SybilAttacker:
    def __init__(self, id, initial_balance=50000):
        self.id = id
        self.balance = initial_balance
        self.active_fakes = []
        self.initial_balance = initial_balance

    def spawn_and_sponsor_fake(self, step, candidate_id, bond_amount=500):
        # Every 10 steps. Needs to post BOTH bonds (Candidate + Sponsor)
        total_required = bond_amount * 2
        if step % 10 == 0 and self.balance >= total_required:
            self.balance -= total_required
            new_fake = Candidate(candidate_id, self.id, step, bond_amount)
            self.active_fakes.append(new_fake)
            return new_fake
        return None

    def execute_default(self, fake, stolen_principal=500):
        # The fake "defaults" and steals the principal. The attacker gains the principal.
        # But loses the 1000 total bonds they posted.
        self.balance += stolen_principal
        fake.status = "defaulted"
        self.active_fakes.remove(fake)
        return fake

    def graduate_fake(self, fake, reward):
        # If a fake somehow survives (maybe they don't default), they'd get both bonds back + 2x reward
        self.balance += (fake.bond_amount * 2) + (reward * 2)
        fake.status = "graduated"
        self.active_fakes.remove(fake)
